"""架构约束：用测试守住 DDD 的依赖方向。"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "werewolf"
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(.+)$", re.MULTILINE)


def _python_files(folder: Path):
    return [p for p in folder.rglob("*.py") if "__pycache__" not in str(p)]


def _imports(path: Path) -> str:
    return "\n".join(IMPORT_RE.findall(path.read_text(encoding="utf-8")))


def test_domain_is_framework_free():
    forbidden = ("fastapi", "starlette", "httpx", "websockets", "sqlalchemy", "redis")
    for path in _python_files(SRC / "domain"):
        imports = _imports(path)
        for name in forbidden:
            assert name not in imports, f"{path} 领域层不应依赖 {name}"


def test_application_does_not_import_infrastructure():
    for path in _python_files(SRC / "application"):
        assert "infrastructure" not in _imports(path), f"{path} 应用层只能依赖端口，不能依赖基础设施实现"


def test_infrastructure_implements_ports_without_interface_leak():
    for path in _python_files(SRC / "infrastructure"):
        assert "interfaces.http" not in _imports(path), f"{path} 基础设施层不应依赖 HTTP 接口层"
