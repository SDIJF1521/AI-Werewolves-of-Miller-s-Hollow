const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

function authHeaders(session) {
  if (!session) return {}
  return {
    'X-Player-Id': session.playerId,
    'X-Session-Token': session.token,
  }
}

async function request(path, { method = 'GET', body, session, headers } = {}) {
  const res = await fetch(`${API_BASE}/api${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(session),
      ...(headers || {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }
  if (!res.ok) {
    const error = new Error(data?.detail || `请求失败（${res.status}）`)
    error.status = res.status
    error.data = data
    throw error
  }
  return data
}

export const api = {
  getConfig: () => request('/config'),
  getIce: () => request('/ice'),

  createRoom: (body) => request('/rooms', { method: 'POST', body }),
  getRoom: (code) => request(`/rooms/${encodeURIComponent(code)}`),
  joinRoom: (code, body) => request(`/rooms/${encodeURIComponent(code)}/join`, { method: 'POST', body }),
  getSnapshot: (code, session) => request(`/rooms/${encodeURIComponent(code)}/snapshot`, { session }),

  assignTeam: (code, session, teamSeat) =>
    request(`/rooms/${encodeURIComponent(code)}/team`, { method: 'POST', body: { teamSeat }, session }),
  setCaptain: (code, session, teamSeat, captainId) =>
    request(`/rooms/${encodeURIComponent(code)}/captain`, {
      method: 'POST',
      body: { teamSeat, captainId },
      session,
    }),
  setKey: (code, session, body) =>
    request(`/rooms/${encodeURIComponent(code)}/key`, { method: 'POST', body, session }),
  deleteKey: (code, session, seat) =>
    request(`/rooms/${encodeURIComponent(code)}/key?seat=${seat}`, { method: 'DELETE', session }),

  startGame: (code, session) =>
    request(`/rooms/${encodeURIComponent(code)}/start`, { method: 'POST', session }),
  advance: (code, session) =>
    request(`/rooms/${encodeURIComponent(code)}/advance`, { method: 'POST', session }),
  testKey: (body) => request('/ai/test', { method: 'POST', body }),
}

export function websocketUrl(code, session) {
  const explicit = import.meta.env.VITE_WS_BASE
  let base = explicit
  if (!base && API_BASE) {
    try {
      const url = new URL(API_BASE)
      base = `${url.protocol === 'https:' ? 'wss' : 'ws'}://${url.host}`
    } catch {
      base = ''
    }
  }
  if (!base) {
    base = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  }
  const query = new URLSearchParams({
    player_id: session.playerId,
    token: session.token,
  })
  return `${base.replace(/\/$/, '')}/ws/rooms/${encodeURIComponent(code)}?${query.toString()}`
}
