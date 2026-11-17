import asyncio
import random

import pytest

from werewolf.application.ports.ai import AIConfig
from werewolf.application.presenters import room_public
from werewolf.bootstrap import build_container
from werewolf.domain.council.night import NightOrder, decide_night_order
from werewolf.domain.council.strategy import (
    Contributor,
    StrategyPackage,
    aggregate_packages,
    decide_adoption,
)
from werewolf.domain.game.entities import NightActions, create_game
from werewolf.domain.rooms.entities import MAX_LOBBY_VOICE, ModelProfile, create_room


# ---------------------------------------------------------------------------
# 板子与基础规则
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "variant_key,count",
    [("classic9", 9), ("classic12", 12), ("wolfking12", 12), ("whitewolf12", 12)],
)
def test_variant_roles(variant_key, count):
    game = create_game(variant_key)
    assert len(game.players) == count
    assert len(game.wolves) == (3 if count == 9 else 4)
    assert len(game.alive_gods) == (3 if count == 9 else 4)
    assert len(game.alive_villagers) == (3 if count == 9 else 4)


def test_good_wins_when_all_wolves_dead():
    game = create_game("classic9")
    for p in game.wolves:
        game.kill(p.seat, "test")
    assert game.check_winner()
    assert game.winner == "good"


def test_wolves_win_by_slaughtering_gods():
    game = create_game("classic9")
    for p in game.alive_gods:
        game.kill(p.seat, "test")
    assert game.check_winner()
    assert game.winner == "wolf"


def test_idiot_reveals_and_loses_vote():
    game = create_game("classic12")
    idiot = next(p for p in game.players if p.role == "idiot")
    result = game.exile(idiot.seat)
    assert result.kind == "idiot"
    assert idiot.alive
    assert idiot.idiot_revealed
    assert not idiot.can_vote
    assert game.exile(idiot.seat).kind == "immune"


def test_guard_and_witch_double_save_dies_in_wolfking_variant():
    game = create_game("wolfking12")
    target = next(
        p for p in game.players if p.alive and p.role not in ("guard", "witch") and p.camp == "good"
    )
    game.day = 1
    result = game.resolve_night(
        NightActions(guard_target=target.seat, wolf_target=target.seat, witch_save=True)
    )
    assert target.seat in [d["seat"] for d in result.deaths]
    assert not target.alive


def test_guard_alone_blocks_kill():
    game = create_game("wolfking12")
    target = next(p for p in game.players if p.alive and p.camp == "good" and p.role != "guard")
    game.day = 1
    result = game.resolve_night(NightActions(guard_target=target.seat, wolf_target=target.seat))
    assert not result.deaths
    assert target.alive


def test_white_wolf_explode():
    game = create_game("whitewolf12")
    white = next(p for p in game.players if p.role == "white_wolf_king")
    target = next(p for p in game.players if p.alive and p.camp == "good")
    result = game.white_wolf_explode(white.seat, target.seat)
    assert result["ok"]
    assert not white.alive
    assert not target.alive


def test_wolf_private_view_contains_teammates():
    game = create_game("classic9")
    wolf = game.wolves[0]
    private = game.private_for(wolf.seat)
    assert len(private["wolfMates"]) == 2
    assert all(mate["roleName"] in ("狼人", "狼王", "白狼王") for mate in private["wolfMates"])
    good = next(p for p in game.players if p.camp == "good")
    assert "wolfMates" not in game.private_for(good.seat)


# ---------------------------------------------------------------------------
# 权重与采纳
# ---------------------------------------------------------------------------
def _contributors(key_holder=False):
    return {
        "a": Contributor("a", "队长", 2.3 if key_holder else 1.3, is_captain=True, has_key=key_holder),
        "b": Contributor("b", "军师", 1.0),
    }


def test_weighted_aggregate_respects_key_holder():
    packages = {
        "a": StrategyPackage(posture="冲锋", attack_seat=3, vote_seat=3, directive="今天必须出3"),
        "b": StrategyPackage(posture="表水", attack_seat=5, vote_seat=5, directive="出5"),
    }
    agg = aggregate_packages(packages, _contributors(key_holder=True), captain_id="a")
    assert agg is not None
    assert agg.package.attack_seat == 3
    assert agg.package.directive == "今天必须出3"
    assert agg.total_weight == pytest.approx(3.3)


def test_captain_directive_wins_even_without_key():
    packages = {
        "a": StrategyPackage(directive="队长原话", vote_seat=3),
        "b": StrategyPackage(directive="队员原话", vote_seat=5),
    }
    agg = aggregate_packages(packages, _contributors(False), captain_id="a")
    assert agg.package.vote_seat == 3
    assert agg.package.directive == "队长原话"
    assert "队员原话" in agg.notes


def test_adoption_extremes():
    packages = {"a": StrategyPackage(posture="悍跳", attack_seat=3, vote_seat=3, directive="跳预言家打3")}
    agg = aggregate_packages(packages, _contributors(True), captain_id="a")
    assert agg is not None
    rng = random.Random(1)
    full = decide_adoption(agg, obedience=0.95, logic=0.4, rng=rng, has_key=True)
    assert full.kind in ("full", "partial")
    rng = random.Random(1)
    defy = decide_adoption(agg, obedience=0.05, logic=0.9, rng=rng, has_key=False)
    assert defy.kind in ("misunderstood", "defy")


def test_night_order_is_followed_by_obedient_ai():
    order = NightOrder(action="kill", target=3, directive="今晚刀 3 号", auto=False)
    decision = decide_night_order(
        order,
        obedience=0.95,
        logic=0.4,
        has_key=True,
        role="werewolf",
        alive_targets=[2, 3, 4],
        rng=random.Random(1),
    )
    assert decision.kind in ("full", "partial")
    assert decision.target == 3
    assert decision.action == "kill"


def _seat_nine(room):
    host = room.members[room.host_id]
    room.assign_team(host, 1)
    for seat in range(2, 10):
        room.join(f"player{seat}", seat)
    return host


# ---------------------------------------------------------------------------
# 全流程（无 LLM，极速）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("variant", ["classic9", "classic12", "wolfking12", "whitewolf12"])
async def test_full_game_completes(variant):
    import werewolf.application.services.game_runner as runner_mod

    old_duration = runner_mod.GameRunner._speech_duration
    runner_mod.GameRunner._speech_duration = lambda self, text: 0.01
    try:
        container = build_container()
        room = container.service.create(
            host_name="tester", room_name="test", variant_key=variant, timing="fast", mode="practice"
        )
        host = _seat_nine(room)
        for key in room.timings:
            room.timings[key] = 0.01
        await container.service.start_game(room, host)
        for _ in range(1600):
            if room.status == "finished":
                break
            await asyncio.sleep(0.02)
        assert room.status == "finished", room.game.phase
        assert room.game.winner in ("good", "wolf")
        assert room.game.speeches
        assert room.game.review()["agents"]
    finally:
        runner_mod.GameRunner._speech_duration = old_duration


# ---------------------------------------------------------------------------
# REST 大厅
# ---------------------------------------------------------------------------
def test_lobby_rest_flow():
    from fastapi.testclient import TestClient

    from werewolf.interfaces.http.app import app

    app.state.container = build_container()
    client = TestClient(app)
    res = client.post(
        "/api/rooms",
        json={"name": "房主", "roomName": "测试局", "variantKey": "classic9", "timing": "fast"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    code = data["code"]
    headers = {"X-Player-Id": data["playerId"], "X-Session-Token": data["token"]}

    res = client.post(f"/api/rooms/{code}/team", json={"teamSeat": 1}, headers=headers)
    assert res.status_code == 200, res.text

    res = client.post(f"/api/rooms/{code}/join", json={"name": "军师A", "teamSeat": 1})
    assert res.status_code == 200, res.text
    res = client.post(f"/api/rooms/{code}/join", json={"name": "军师B", "teamSeat": 1})
    assert res.status_code == 200, res.text
    res = client.post(f"/api/rooms/{code}/join", json={"name": "军师C", "teamSeat": 1})
    assert res.status_code == 400, res.text

    res = client.post(f"/api/rooms/{code}/join", json={"name": "军师2", "teamSeat": 2})
    assert res.status_code == 200, res.text
    assert res.json()["member"]["teamSeat"] == 2

    room = client.get(f"/api/rooms/{code}").json()["room"]
    assert room["teams"][0]["advisorCount"] == 3
    assert room["teams"][1]["advisorCount"] == 1
    assert room["teams"][0]["captainId"] == data["playerId"]
    assert room["maxAdvisors"] == 3


# ---------------------------------------------------------------------------
# Key 权限与领域隔离
# ---------------------------------------------------------------------------
async def test_key_holder_gets_weight_and_secret_is_masked():
    container = build_container()
    room = container.service.create(
        host_name="keyholder", room_name="key test", variant_key="classic9", timing="fast"
    )
    host = room.members[room.host_id]
    await container.service.assign_team(room, host, 1)
    secret = "sk-test-super-secret-123456"
    await container.service.set_key(
        room,
        host,
        AIConfig("deepseek", "https://api.deepseek.com/v1", "deepseek-chat", secret),
    )
    assert room.teams[1].has_key
    assert host.is_host
    assert room.member_weight(host) == pytest.approx(2.3)
    assert container.vault.get(room.code, 1).api_key == secret
    public_json = str(room_public(room))
    assert secret not in public_json
    assert "sk-test" not in public_json
    assert room.teams[1].key_public()["maskedKey"] != secret


async def test_project_requires_user_directive():
    container = build_container()
    room = container.service.create(
        host_name="host", room_name="directive", variant_key="classic9", timing="fast", mode="practice"
    )
    host = _seat_nine(room)
    room.start_game(create_game("classic9"))
    room.game.phase = "council"
    with pytest.raises(ValueError):
        room.submit_package(host, {"posture": "冲锋", "attackSeat": 3, "directive": ""})


def test_lobby_chat_and_voice_allow_spectators():
    room = create_room(name="lobby", host_name="host", variant_key="classic9", timing="fast")
    host = room.members[room.host_id]
    guest = room.join("观战者", None, True)
    msg = room.add_lobby_chat(guest, "大家好，我先看看牌")
    assert msg["name"] == "观战者"
    assert room.lobby_chat[-1]["text"] == "大家好，我先看看牌"
    assert room.voice_join(guest) == []
    peers = room.voice_join(host)
    assert any(p["memberId"] == guest.id for p in peers)
    assert guest.id in room.voice_channel_members(host)
    room.voice_leave(guest)
    assert guest.id not in room.lobby_voice


def test_lobby_voice_has_a_cap():
    room = create_room(name="cap", host_name="host", variant_key="classic9", timing="fast")
    for index in range(MAX_LOBBY_VOICE):
        member = room.join(f"p{index}", None, True)
        room.voice_join(member)
    extra = room.join("overflow", None, True)
    with pytest.raises(ValueError):
        room.voice_join(extra)


def test_ai_capacity_and_standard_key_requirements():
    room = create_room(name="strict", host_name="host", variant_key="classic9", timing="fast")
    host = room.members[room.host_id]
    room.assign_team(host, 1)
    room.join("second", 1)
    room.join("third", 1)
    with pytest.raises(ValueError):
        room.join("fourth", 1)
    with pytest.raises(ValueError):
        room.start_game(create_game("classic9"))
    for seat in range(2, 10):
        room.join(f"p{seat}", seat)
    with pytest.raises(ValueError, match="API Key"):
        room.start_game(create_game("classic9"))
    for seat in range(1, 10):
        member = room.team_members(seat)[0]
        room.bind_model(
            member,
            ModelProfile(
                provider="openai",
                base_url="https://api.openai.com/v1",
                model="gpt-4o-mini",
                masked_key="sk-***",
            ),
        )
    room.start_game(create_game("classic9"))
    assert room.status == "playing"
    assert all(len(room.team_members(seat)) >= 1 for seat in room.teams)


def test_practice_mode_can_start_with_one_player():
    room = create_room(name="practice", host_name="host", variant_key="classic9", timing="fast", mode="practice")
    host = room.members[room.host_id]
    room.assign_team(host, 1)
    room.start_game(create_game("classic9"))
    assert room.status == "playing"
    assert room.mode == "practice"


def test_last_player_timeout_marks_ai_offline():
    room = create_room(name="offline", host_name="host", variant_key="classic9", timing="fast", mode="practice")
    host = room.members[room.host_id]
    room.assign_team(host, 1)
    room.start_game(create_game("classic9"))
    result = room.remove_member(host.id)
    assert result["removed"] is True
    assert result["offline"] is True
    assert room.is_ai_offline(1) is True
    assert room.host_id is None


@pytest.mark.asyncio
async def test_disconnect_grace_allows_reconnect_then_timeout_removes():
    container = build_container()
    room = container.service.create(
        host_name="host", room_name="reconnect", variant_key="classic9", timing="fast", mode="practice"
    )
    host = room.members[room.host_id]
    room.assign_team(host, 1)
    room.start_game(create_game("classic9"))
    container.service.DISCONNECT_GRACE_SECONDS = 0.08

    await container.service.presence(room, host, False)
    assert room.member(host.id).reconnect_deadline is not None
    await asyncio.sleep(0.02)
    await container.service.presence(room, host, True)
    await asyncio.sleep(0.12)
    assert room.member(host.id) is not None
    assert room.is_ai_offline(1) is False

    await container.service.presence(room, host, False)
    await asyncio.sleep(0.12)
    assert room.member(host.id) is None
    assert room.is_ai_offline(1) is True


def test_team_voice_is_private_and_available_in_all_phases():
    room = create_room(name="voice", host_name="host", variant_key="classic9", timing="fast", mode="practice")
    host = room.members[room.host_id]
    room.assign_team(host, 1)
    mate = room.join("mate", 1)
    outsider = room.join("outsider", 2)
    room.start_game(create_game("classic9"))

    assert room.voice_join(host) == []
    peers = room.voice_join(mate)
    assert any(p["memberId"] == host.id for p in peers)
    assert room.voice_join(outsider) == []
    assert room.voice_channel_members(host) == {host.id, mate.id}
    assert outsider.id not in room.voice_channel_members(host)
    assert room.phase_voice_cleanup() is False


def test_night_order_is_validated_and_locked():
    room = create_room(name="night-order", host_name="host", variant_key="classic9", timing="fast", mode="practice")
    host = _seat_nine(room)
    game = create_game("classic9")
    room.start_game(game)
    game.phase = "night_council"
    player = game.by_seat(1)
    if player.camp == "wolf":
        target = next(p.seat for p in game.players if p.camp == "good")
        order = {"action": "kill", "target": target, "directive": "刀这个"}
    elif player.role == "seer":
        target = next(p.seat for p in game.players if p.seat != 1)
        order = {"action": "check", "target": target, "directive": "验这个"}
    elif player.role == "witch":
        order = {"action": "save", "directive": "救被刀的人"}
    elif player.role == "guard":
        target = next(p.seat for p in game.players if p.seat != 1)
        order = {"action": "protect", "target": target, "directive": "守这个"}
    else:
        order = {"action": "none", "directive": "本夜听队友的"}
    room.submit_night_order(host, order)
    assert room.teams[1].night_order is not None
    assert room.teams[1].night_locked
    with pytest.raises(ValueError):
        room.submit_night_order(host, order)
