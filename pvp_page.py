"""PSL PvP: two-player face-off in private rooms.

Flow: Player 1 creates a room and gets a code -> Player 2 joins with the code -> both press
Ready -> 3 rounds: each player locks in a photo within a shared 15-second window, the server
scores each photo exactly once, both screens reveal the same result -> overall winner
(a tiebreaker round if the points are level) -> rematch or leave.

Shared state lives in an in-memory store (st.cache_resource) guarded by a lock, so every
browser connected to the same running app sees the same match. It is cleared when the
server restarts, and it only works with a single server process (fine for Streamlit Cloud).
"""
from __future__ import annotations

import base64
import html
import random
import threading
import time
import uuid

import streamlit as st

ROUNDS = 3               # normal rounds; one extra tiebreaker round if the points are level
SUBMIT_SECONDS = 15      # shared window to lock in a photo
REVEAL_SECONDS = 9       # how long each round's result stays up before the next round
ROOM_TTL = 3 * 3600      # rooms older than this are cleaned up
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I mix-ups
HIGHER_SCORE_WINS = True  # flip to False if your team wants lower-score-wins


# =====================================================================
# Shared match store
# =====================================================================
@st.cache_resource
def _store() -> dict:
    return {"rooms": {}, "lock": threading.Lock()}


def _me() -> str:
    """This browser session's private player ID (nicknames are never used as identity)."""
    if "pvp_id" not in st.session_state:
        st.session_state["pvp_id"] = uuid.uuid4().hex
    return st.session_state["pvp_id"]


def _new_code(rooms: dict) -> str:
    while True:
        code = "".join(random.choice(CODE_CHARS) for _ in range(6))
        if code not in rooms:
            return code


def _fresh_round_state(room: dict):
    room["subs"] = {}
    room["results"] = {}
    room["analysis"] = "idle"
    room["outcome"] = None


def _bump(room: dict):
    room["version"] += 1


def _create_room(name: str) -> str:
    s = _store()
    with s["lock"]:
        now = time.time()
        for code in [c for c, r in s["rooms"].items() if now - r["created"] > ROOM_TTL]:
            del s["rooms"][code]
        code = _new_code(s["rooms"])
        room = {"code": code, "created": now, "players": {}, "order": [], "phase": "lobby", "round": 0,
                "deadline": None, "reveal_until": None, "log": [], "version": 0, "notice": ""}
        _fresh_round_state(room)
        room["players"][_me()] = {"name": name, "ready": False, "points": 0}
        room["order"].append(_me())
        s["rooms"][code] = room
    return code


def _join_room(code: str, name: str) -> str | None:
    """Returns an error message, or None on success."""
    s = _store()
    with s["lock"]:
        room = s["rooms"].get(code)
        if not room:
            return "No room with that code."
        if _me() in room["players"]:
            return None
        if len(room["players"]) >= 2:
            return "That room is full."
        if room["phase"] != "lobby":
            return "That match has already started."
        room["players"][_me()] = {"name": name, "ready": False, "points": 0}
        room["order"].append(_me())
        room["notice"] = ""
        _bump(room)
    return None


def _leave_room(code: str):
    s = _store()
    with s["lock"]:
        room = s["rooms"].get(code)
        if room and _me() in room["players"]:
            name = room["players"].pop(_me())["name"]
            room["order"].remove(_me())
            if not room["players"]:
                del s["rooms"][code]
            else:  # back to the lobby for whoever is left
                room.update(phase="lobby", round=0, deadline=None, reveal_until=None, log=[],
                            notice=f"{name} left the room.")
                _fresh_round_state(room)
                for p in room["players"].values():
                    p.update(ready=False, points=0)
                _bump(room)
    st.session_state.pop("pvp_room", None)


def _set_ready(code: str, ready: bool):
    s = _store()
    with s["lock"]:
        room = s["rooms"].get(code)
        if room and _me() in room["players"]:
            room["players"][_me()]["ready"] = ready
            _bump(room)


def _submit(code: str, data: bytes, name: str):
    s = _store()
    with s["lock"]:
        room = s["rooms"].get(code)
        if room and room["phase"] == "submit" and _me() in room["players"] and _me() not in room["subs"]:
            if time.time() <= room["deadline"]:
                room["subs"][_me()] = {"bytes": data, "name": name}
                _bump(room)


def _rematch(code: str):
    s = _store()
    with s["lock"]:
        room = s["rooms"].get(code)
        if room and room["phase"] == "final":
            room.update(phase="lobby", round=0, deadline=None, reveal_until=None, log=[], notice="")
            _fresh_round_state(room)
            for p in room["players"].values():
                p.update(ready=False, points=0)
            _bump(room)


# =====================================================================
# Server-side game loop (runs under the lock, from whichever player's screen refreshes first)
# =====================================================================
def _start_round(room: dict, now: float):
    room["round"] += 1
    room["phase"] = "submit"
    room["deadline"] = now + SUBMIT_SECONDS
    room["reveal_until"] = None
    _fresh_round_state(room)
    _bump(room)


def _tick(room: dict, analyze) -> tuple | None:
    """Advance the match if it's time. Returns analysis work to start outside the lock, or None."""
    now = time.time()
    phase = room["phase"]
    if phase == "lobby":
        if len(room["players"]) == 2 and all(p["ready"] for p in room["players"].values()):
            room["log"] = []
            for p in room["players"].values():
                p["points"] = 0
            _start_round(room, now)
    elif phase == "submit":
        everyone_in = len(room["subs"]) == len(room["players"])
        if (everyone_in or now > room["deadline"]) and room["analysis"] == "idle":
            room["analysis"] = "running"      # claimed: no other session can start scoring this round
            room["phase"] = "analysis"
            _bump(room)
            return (room["code"], room["round"], dict(room["subs"]), analyze)
    elif phase == "reveal" and now >= room["reveal_until"]:
        points = [p["points"] for p in room["players"].values()]
        level = len(points) == 2 and points[0] == points[1]
        if room["round"] < ROUNDS or (room["round"] == ROUNDS and level):
            _start_round(room, now)           # next round, or the tiebreaker
        else:
            room["phase"] = "final"
            _bump(room)
    return None


def _run_analysis(code: str, rnd: int, subs: dict, analyze):
    """Score each locked photo once (in a background thread), then record the round outcome."""
    results = {}
    for pid, sub in subs.items():
        data, fallback = analyze(sub["bytes"], sub["name"])
        results[pid] = {**data, "fallback": fallback}
    s = _store()
    with s["lock"]:
        room = s["rooms"].get(code)
        if not room or room["round"] != rnd or room["phase"] != "analysis":
            return  # room left / reset meanwhile
        room["results"] = results
        room["outcome"] = _decide(room, results)
        winner = room["outcome"]["winner"]
        if winner in room["players"]:
            room["players"][winner]["points"] += 1
        room["log"].append({"round": rnd, **room["outcome"],
                            "scores": {pid: r["psl_score"] for pid, r in results.items()}})
        room["analysis"] = "done"
        room["phase"] = "reveal"
        room["reveal_until"] = time.time() + REVEAL_SECONDS
        _bump(room)


def _decide(room: dict, results: dict) -> dict:
    """Who takes the round. Sample (fallback) scores never decide a round."""
    names = {pid: p["name"] for pid, p in room["players"].items()}
    ids = list(room["players"])
    submitted = [pid for pid in ids if pid in results]
    if not submitted:
        return {"winner": None, "text": "Nobody locked in a photo. No point awarded."}
    if len(submitted) == 1:
        pid = submitted[0]
        return {"winner": pid, "text": f"{names[pid]} takes the round (opponent didn't lock in)."}
    if any(results[pid]["fallback"] for pid in submitted):
        return {"winner": None, "text": "Live AI scoring was unavailable, so this round isn't scored."}
    a, b = submitted
    sa, sb = results[a]["psl_score"], results[b]["psl_score"]
    if sa == sb:
        return {"winner": None, "text": f"Draw at {sa:.1f}. No point awarded."}
    better = a if (sa > sb) == HIGHER_SCORE_WINS else b
    return {"winner": better, "text": f"{names[better]} takes the round."}


def _snapshot(code: str, analyze) -> dict | None:
    """Tick the match and return a copy of the room that's safe to read without the lock."""
    s = _store()
    work = None
    with s["lock"]:
        room = s["rooms"].get(code)
        if not room:
            return None
        work = _tick(room, analyze)
        snap = {k: v for k, v in room.items() if k not in ("subs",)}
        snap["players"] = {pid: dict(p) for pid, p in room["players"].items()}
        snap["submitted"] = set(room["subs"])
        snap["sub_bytes"] = {pid: sub["bytes"] for pid, sub in room["subs"].items()}
        snap["results"] = {pid: dict(r) for pid, r in room["results"].items()}
        snap["log"] = list(room["log"])
    if work:
        threading.Thread(target=_run_analysis, args=work, daemon=True).start()
    return snap


# =====================================================================
# UI
# =====================================================================
CSS = """
.pvp-title { font-family: 'Instrument Serif', serif; font-size: clamp(44px, 7vw, 72px); line-height: 1; margin: 8px 0 4px; color: #fff; }
.pvp-kicker { font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; letter-spacing: .24em; text-transform: uppercase; color: #8a8a8a; margin-bottom: 18px; }
.pvp-card { border: 1px solid #2a2a2a; background: #0a0a0a; border-radius: 18px; padding: 18px 20px; margin: 10px 0; color: #ddd; }
.pvp-code { font-family: 'JetBrains Mono', monospace; font-size: clamp(34px, 7vw, 54px); font-weight: 700; letter-spacing: .18em; color: #fff; }
.pvp-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .2em; text-transform: uppercase; color: #8a8a8a; }
.pvp-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #1d1d1d; font-family: 'Inter', sans-serif; }
.pvp-row:last-child { border-bottom: 0; }
.pvp-ok { color: #22c55e; font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .12em; }
.pvp-wait { color: #8a8a8a; font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .12em; }
.pvp-timer { font-family: 'JetBrains Mono', monospace; font-size: 56px; font-weight: 700; text-align: center; color: #fff; }
.pvp-timer.low { color: #ff4d4d; }
.pvp-banner { text-align: center; font-family: 'Instrument Serif', serif; font-size: clamp(30px, 5vw, 44px); color: #fff; margin: 6px 0; }
.pvp-score { font-family: 'Audiowide', sans-serif; font-size: 44px; color: #fff; text-align: center; line-height: 1.1; }
.pvp-tier { text-align: center; color: #aaa; letter-spacing: 2px; font-size: 13px; margin-bottom: 6px; }
.pvp-name { text-align: center; font-family: 'Inter', sans-serif; font-weight: 600; font-size: 18px; color: #fff; margin-top: 6px; }
.pvp-win { outline: 2px solid #22c55e; box-shadow: 0 0 30px rgba(34, 197, 94, .25); }
.pvp-photo { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 14px; display: block; }
.pvp-sample { display: inline-block; padding: 2px 10px; border: 1px solid #ffb300; color: #ffb300; border-radius: 99px; font-size: 10px; letter-spacing: 2px; }
.pvp-advice { font-size: 13px; color: #bbb; line-height: 1.5; margin-top: 8px; }
"""


def _esc(text) -> str:
    return html.escape(str(text))


def _header():
    st.html(f"<style>{CSS}</style>")
    st.html('<div class="pvp-title">PSL PvP</div><div class="pvp-kicker">Face-off &middot; best of 3 &middot; 15-second rounds</div>')


def _entry_screen():
    """Not in a room yet: nickname, create or join."""
    name = st.text_input("Nickname", max_chars=16, key="pvp_name", placeholder="e.g. Mustafe").strip()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="pvp-label">New match</div>', unsafe_allow_html=True)
        if st.button("Create Room", key="pvp_create", disabled=not name, width="stretch"):
            st.session_state["pvp_room"] = _create_room(name)
            st.rerun()
    with c2:
        code = st.text_input("Room code", max_chars=6, key="pvp_join_code", placeholder="MOG7K2").strip().upper()
        if st.button("Join Room", key="pvp_join", disabled=not (name and len(code) == 6), width="stretch"):
            err = _join_room(code, name)
            if err:
                st.error(err)
            else:
                st.session_state["pvp_room"] = code
                st.rerun()
    if not name:
        st.caption("Enter a nickname to create or join a room.")


def _players_html(snap: dict, show_ready: bool) -> str:
    rows = []
    for pid in snap["order"]:
        p = snap["players"][pid]
        you = " (you)" if pid == _me() else ""
        if show_ready:
            status = '<span class="pvp-ok">READY</span>' if p["ready"] else '<span class="pvp-wait">NOT READY</span>'
        elif snap["phase"] == "submit":
            status = '<span class="pvp-ok">LOCKED IN</span>' if pid in snap["submitted"] else '<span class="pvp-wait">CHOOSING&hellip;</span>'
        else:
            status = f'<span class="pvp-ok">{p["points"]} PT</span>'
        rows.append(f'<div class="pvp-row"><span>{_esc(p["name"])}{you}</span>{status}</div>')
    if len(snap["order"]) < 2:
        rows.append('<div class="pvp-row"><span class="pvp-wait">Waiting for opponent&hellip;</span><span></span></div>')
    return "".join(rows)


def _result_card(snap: dict, pid: str) -> str:
    p = snap["players"][pid]
    res = snap["results"].get(pid)
    img = snap["sub_bytes"].get(pid)
    winner = (snap.get("outcome") or {}).get("winner") == pid
    photo = (f'<img class="pvp-photo" src="data:image/jpeg;base64,{base64.b64encode(img).decode()}" alt="">'
             if img else '<div class="pvp-photo" style="background:#151515"></div>')
    if res:
        badge = '<div style="text-align:center;margin-top:6px"><span class="pvp-sample">SAMPLE SCORE</span></div>' if res["fallback"] else ""
        body = (f'<div class="pvp-score">{res["psl_score"]:.1f}</div><div class="pvp-tier">{_esc(res.get("tier", ""))}</div>'
                f'{badge}<div class="pvp-advice">{_esc(res.get("advice", ""))}</div>')
    else:
        body = '<div class="pvp-tier">NO PHOTO</div>'
    return (f'<div class="pvp-card{" pvp-win" if winner else ""}">{photo}'
            f'<div class="pvp-name">{_esc(p["name"])}{" (you)" if pid == _me() else ""}</div>{body}</div>')


def _scoreboard(snap: dict) -> str:
    rows = "".join(
        f'<div class="pvp-row"><span>{_esc(snap["players"][pid]["name"])}</span>'
        f'<span class="pvp-ok">{snap["players"][pid]["points"]} PT</span></div>'
        for pid in snap["order"])
    return f'<div class="pvp-card"><div class="pvp-label">Scoreboard</div>{rows}</div>'


def _round_label(snap: dict) -> str:
    return "Tiebreaker" if snap["round"] > ROUNDS else f"Round {snap['round']} of {ROUNDS}"


def _photo_input(snap: dict):
    """This player's photo for the current round (camera or upload), plus the lock-in button."""
    code, rnd = snap["code"], snap["round"]
    if _me() in snap["submitted"]:
        st.markdown('<div class="pvp-card" style="text-align:center"><span class="pvp-ok">YOUR PHOTO IS LOCKED IN</span><br>'
                    '<span class="pvp-wait">Waiting for your opponent&hellip;</span></div>', unsafe_allow_html=True)
        return
    src = st.radio("Photo source", ["Camera", "Upload"], horizontal=True, key=f"pvp_src_{code}_{rnd}",
                   label_visibility="collapsed")
    if src == "Camera":
        shot = st.camera_input("Take your photo", key=f"pvp_cam_{code}_{rnd}", label_visibility="collapsed")
    else:
        shot = st.file_uploader("Upload your photo", type=["jpg", "jpeg", "png", "heic", "heif"],
                                key=f"pvp_up_{code}_{rnd}", label_visibility="collapsed")
    if st.button("LOCK IN", key=f"pvp_lock_{code}_{rnd}", disabled=shot is None, width="stretch"):
        _submit(code, shot.getvalue(), getattr(shot, "name", "camera photo"))
        st.rerun()


def _room_screen(code: str, analyze, tier_for):
    snap = _snapshot(code, analyze)
    if snap is None or _me() not in snap["players"]:
        st.session_state.pop("pvp_room", None)
        st.warning("That room has closed.")
        if st.button("Back to PvP", key="pvp_back_entry"):
            st.rerun()
        return
    # tier labels for the reveal (computed here so the background thread doesn't need them)
    for res in snap["results"].values():
        res["tier"] = tier_for(res["psl_score"])
    st.session_state["pvp_seen"] = _screen_key(snap)
    phase = snap["phase"]

    top = st.columns([3, 1])
    with top[0]:
        st.markdown(f'<div class="pvp-label">Room code</div><div class="pvp-code">{_esc(code)}</div>', unsafe_allow_html=True)
    with top[1]:
        if st.button("Leave", key="pvp_leave", width="stretch"):
            _leave_room(code)
            st.rerun()

    _live(code, analyze)  # live part: refreshes every second

    if phase == "lobby":
        me = snap["players"][_me()]
        if len(snap["players"]) == 2:
            label = "NOT READY" if me["ready"] else "READY"
            if st.button(label, key=f"pvp_ready_{me['ready']}", width="stretch"):
                _set_ready(code, not me["ready"])
                st.rerun()
        else:
            st.caption("Share the code with your opponent. They open this site, go to PSL PvP and press Join Room.")
    elif phase == "submit":
        _photo_input(snap)
    elif phase == "reveal" or phase == "final":
        cols = st.columns(2)
        for col, pid in zip(cols, snap["order"]):
            with col:
                st.html(_result_card(snap, pid))
        if phase == "final":
            if st.button("REMATCH", key="pvp_rematch", width="stretch"):
                _rematch(code)
                st.rerun()


def _screen_key(snap: dict) -> tuple:
    """When this changes, the whole page reloads (new phase, new round, or someone joined/left)."""
    return snap["phase"], snap["round"], tuple(snap["order"])


@st.fragment(run_every=1)
def _live(code: str, analyze):
    """Refreshes every second: advances the match, shows the timer/status, and reloads the page
    when the phase or round changes so both players stay on the same screen."""
    snap = _snapshot(code, analyze)
    if snap is None or _me() not in snap["players"]:
        st.rerun(scope="app")
        return
    if _screen_key(snap) != st.session_state.get("pvp_seen"):
        st.rerun(scope="app")
        return
    phase = snap["phase"]
    if snap.get("notice"):
        st.info(snap["notice"])
    if phase == "lobby":
        st.html(f'<div class="pvp-card"><div class="pvp-label">Lobby</div>{_players_html(snap, True)}</div>')
    elif phase == "submit":
        left = max(0, int(snap["deadline"] - time.time() + 0.999))
        st.html(f'<div class="pvp-banner">{_round_label(snap)}</div>'
                f'<div class="pvp-timer{" low" if left <= 5 else ""}">{left}s</div>'
                f'<div class="pvp-card">{_players_html(snap, False)}</div>')
    elif phase == "analysis":
        st.html(f'<div class="pvp-banner">{_round_label(snap)}</div>'
                '<div class="pvp-card" style="text-align:center"><span class="pvp-ok">ANALYSING BOTH FACES&hellip;</span><br>'
                '<span class="pvp-wait">Gemma is scoring each photo once. This can take up to a minute.</span></div>')
    elif phase == "reveal":
        outcome = snap.get("outcome") or {}
        nxt = "Tiebreaker next" if snap["round"] >= ROUNDS else f"Round {snap['round'] + 1} starts soon"
        points = [p["points"] for p in snap["players"].values()]
        if snap["round"] >= ROUNDS and not (len(points) == 2 and points[0] == points[1]):
            nxt = "Final result next"
        st.html(f'<div class="pvp-banner">{_esc(outcome.get("text", ""))}</div>'
                f'<div class="pvp-kicker" style="text-align:center">{_round_label(snap)} &middot; {nxt}</div>'
                + _scoreboard(snap))
    elif phase == "final":
        players = [snap["players"][pid] for pid in snap["order"]]
        if len(players) == 2 and players[0]["points"] != players[1]["points"]:
            champ = max(players, key=lambda p: p["points"])
            title = f"{_esc(champ['name'])} wins the match"
        else:
            title = "The match is a draw"
        log = "".join(f'<div class="pvp-row"><span>{"Tiebreaker" if e["round"] > ROUNDS else "Round " + str(e["round"])}</span>'
                      f'<span class="pvp-wait">{_esc(e["text"])}</span></div>' for e in snap["log"])
        st.html(f'<div class="pvp-banner">{title}</div>{_scoreboard(snap)}'
                f'<div class="pvp-card"><div class="pvp-label">Rounds</div>{log}</div>')


def render(analyze=None, tier_for=None):
    """analyze(file_bytes, file_name) -> (result_dict, used_fallback); tier_for(score) -> tier label.
    Both come from score_face.py so PvP scores exactly like the PSL Score page."""
    _header()
    if analyze is None or tier_for is None:
        st.error("PvP needs the scoring functions from score_face.py.")
        return
    code = st.session_state.get("pvp_room")
    if code:
        _room_screen(code, analyze, tier_for)
    else:
        _entry_screen()
