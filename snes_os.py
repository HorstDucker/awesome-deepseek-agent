#!/usr/bin/env python3
"""
ClaudeOS — Secret of Mana Edition
SNES 16-Bit style coworker terminal.

Controls:
  1-8    select a spirit
  F      fire selected spirit immediately
  E      enable selected spirit
  D      disable selected spirit
  Q/ESC  quit
"""

from __future__ import annotations

import select
import signal
import sys
import termios
import time
import tty
from typing import Any, Dict, List, Optional

from claude_os.kernel import Kernel

# ── SNES 256-color palette ────────────────────────────────────────────────────
R      = "\033[0m"
BD     = "\033[1m"
DM     = "\033[2m"
GOLD   = "\033[38;5;220m"
GREEN  = "\033[38;5;40m"
BLUE   = "\033[38;5;33m"
RED    = "\033[38;5;196m"
ORANGE = "\033[38;5;208m"
TEAL   = "\033[38;5;37m"
EARTH  = "\033[38;5;130m"
WIND   = "\033[38;5;153m"
LUMINA = "\033[38;5;226m"
SHADE  = "\033[38;5;93m"
LUNA   = "\033[38;5;189m"
DRYAD  = "\033[38;5;64m"
WHITE  = "\033[38;5;255m"
GRAY   = "\033[38;5;240m"
BG_DK  = "\033[48;5;232m"

HIDE   = "\033[?25l"
SHOW   = "\033[?25h"
CLEAR  = "\033[2J\033[H"

# ── 8 Mana Spirits ───────────────────────────────────────────────────────────
SPIRITS = [
    {"key":"1","name":"Undine",    "element":"Water","color":TEAL,   "sym":"≈","sched":"8s",
     "desc":"Memory guardian — tracks kernel memory keys"},
    {"key":"2","name":"Gnome",     "element":"Earth","color":EARTH,  "sym":"◆","sched":"12s",
     "desc":"Filesystem keeper — logs to virtual FS"},
    {"key":"3","name":"Sylphid",   "element":"Wind", "color":WIND,   "sym":"∿","sched":"5s",
     "desc":"Scheduler spirit — fastest runner"},
    {"key":"4","name":"Salamando", "element":"Fire", "color":ORANGE, "sym":"★","sched":"10s",
     "desc":"Fire spirit — pulses kernel stats"},
    {"key":"5","name":"Lumina",    "element":"Light","color":LUMINA, "sym":"☀","sched":"20s",
     "desc":"Secret warden — verifies vault integrity"},
    {"key":"6","name":"Shade",     "element":"Dark", "color":SHADE,  "sym":"●","sched":"15s",
     "desc":"Shadow keeper — scans fire log for errors"},
    {"key":"7","name":"Luna",      "element":"Moon", "color":LUNA,   "sym":"◑","sched":"30s",
     "desc":"Nightwatch — heartbeat & uptime tracker"},
    {"key":"8","name":"Dryad",     "element":"Wood", "color":DRYAD,  "sym":"♣","sched":"25s",
     "desc":"Forest elder — memory stats & cleanup"},
]

# ── Spirit action factories ───────────────────────────────────────────────────

def _make_action(kernel: Kernel, spirit: Dict) -> Any:
    name = spirit["name"]

    def undine(secrets: dict) -> str:
        keys = kernel.syscall("mem_list")
        kernel.syscall("mem_write", "undine.water_level", len(keys))
        return f"water_level={len(keys)}"

    def gnome(secrets: dict) -> str:
        ts = time.strftime("%H:%M:%S")
        kernel.syscall("fs_write", "/var/log/gnome.txt",
                       f"[{ts}] Gnome tilled the earth\n", mode="a")
        return f"logged at {ts}"

    def sylphid(secrets: dict) -> str:
        n = (kernel.syscall("mem_read", "sylphid.gusts") or 0) + 1
        kernel.syscall("mem_write", "sylphid.gusts", n)
        return f"gusts={n}"

    def salamando(secrets: dict) -> str:
        stats = kernel.syscall("kernel_stats")
        kernel.syscall("mem_write", "salamando.syscalls", stats["syscall_count"])
        return f"syscalls={stats['syscall_count']}"

    def lumina(secrets: dict) -> str:
        count = kernel.syscall("secret_list")
        status = "vault_ok" if count else "vault_empty"
        kernel.syscall("mem_write", "lumina.status", status)
        return status

    def shade(secrets: dict) -> str:
        log = kernel.syscall("cron_log", 20)
        errors = sum(1 for e in log if e.get("error"))
        kernel.syscall("mem_write", "shade.errors_seen", errors)
        return f"errors_seen={errors}"

    def luna(secrets: dict) -> str:
        uptime = kernel.syscall("kernel_stats")["uptime_seconds"]
        kernel.syscall("mem_write", "luna.uptime", round(uptime, 1))
        return f"uptime={uptime:.1f}s"

    def dryad(secrets: dict) -> str:
        keys = kernel.syscall("mem_list")
        kernel.syscall("mem_write", "dryad.mem_keys", len(keys))
        return f"mem_keys={len(keys)}"

    actions = {
        "Undine": undine, "Gnome": gnome, "Sylphid": sylphid,
        "Salamando": salamando, "Lumina": lumina, "Shade": shade,
        "Luna": luna, "Dryad": dryad,
    }
    return actions[name]

# ── Render helpers ────────────────────────────────────────────────────────────

def _bar(val: int, cap: int = 16, width: int = 8, color: str = GREEN) -> str:
    filled = min(width, int(val / cap * width)) if cap > 0 else 0
    return color + "█" * filled + GRAY + "░" * (width - filled) + R

def _pad(s: str, w: int) -> str:
    return s + " " * max(0, w - len(s))

def _spirit_card(spirit: Dict, job: Optional[Dict], selected: bool, w: int) -> List[str]:
    col   = spirit["color"]
    sel   = GOLD if selected else col
    sym   = spirit["sym"]
    runs  = job["run_count"] if job else 0
    en    = job["enabled"]   if job else True
    last  = job["last_run"]  if job else "—"
    err   = (job["last_error"] or "")[:22] if job else ""
    sname = f"{sym} {spirit['name']}"
    elem  = f"[{spirit['element']}]"
    key   = spirit["key"]
    sched = spirit["sched"]
    inner = w - 2

    status_str = (GREEN + "ACTIVE" if en else RED + "SLEEP") + R
    bar_str    = _bar(runs % 17, 16)
    runs_str   = f" {runs}×"

    lines = []
    border_col = GOLD if selected else GRAY
    lines.append(border_col + "┌" + "─" * inner + "┐" + R)
    # title row
    title = f" {BD}{sel}{sname}{R} {DM}{elem}{R}"
    key_tag = f" [{GOLD}{key}{R}] {DM}{sched}{R} "
    title_plain = f"  {sname} {elem}  [{key}] {sched} "
    pad = max(0, inner - len(title_plain))
    lines.append(border_col + "│" + R + title + " " * pad + key_tag + border_col + "│" + R)
    # bar row
    bar_row = f" {bar_str}{runs_str}  {status_str}"
    bar_plain = f"  {'█'*8}{runs_str}  ACTIVE "
    lines.append(border_col + "│" + R + bar_row + " " * max(0, inner - len(bar_plain)) + border_col + "│" + R)
    # desc
    desc = f" {DM}{_pad(spirit['desc'], inner - 1)}{R}"
    lines.append(border_col + "│" + R + desc + border_col + "│" + R)
    # last run / error
    detail = f" last:{last}" + (f"  {RED}⚠{err}{R}" if err else "")
    detail_plain = f" last:{last}" + (f"  ⚠{err}" if err else "")
    lines.append(border_col + "│" + R + detail + " " * max(0, inner - len(detail_plain)) + border_col + "│" + R)
    lines.append(border_col + "└" + "─" * inner + "┘" + R)
    return lines

# ── Boot screen ───────────────────────────────────────────────────────────────

BOOT_ART = r"""
         /\
        /  \          ✦ ClaudeOS — Secret of Mana Edition ✦
       / ⚔  \
      /──────\       The 8 Mana Spirits guard the kernel.
     │ CLAUDE │       Each runs independently on its own
     │   OS   │       schedule. Command them wisely.
     │~~~~~~~~│
      \      /        kernel v0.2.0  ·  8 spirits await
       \    /
        \  /
         \/
"""

def _boot(kernel: Kernel) -> None:
    sys.stdout.write(CLEAR)
    width = 70
    border = GOLD + "╔" + "═" * (width - 2) + "╗" + R
    bot    = GOLD + "╚" + "═" * (width - 2) + "╝" + R
    print(border)
    for line in BOOT_ART.splitlines():
        padded = line.ljust(width - 2)[:width - 2]
        print(GOLD + "║" + R + GREEN + padded + R + GOLD + "║" + R)
    print(bot)
    print()
    print(GOLD + "  Awakening spirits…" + R, flush=True)
    time.sleep(0.4)
    for s in SPIRITS:
        print(f"  {s['color']}{s['sym']} {s['name']:<10}{R} {DM}({s['element']}) registered — every {s['sched']}{R}")
        time.sleep(0.07)
    print()
    print(GOLD + "  Press ENTER to enter the Mana World…" + R, flush=True)
    input()

# ── Main render ───────────────────────────────────────────────────────────────

def _render(kernel: Kernel, selected: int, msg: str) -> str:
    import shutil
    cols = max(80, shutil.get_terminal_size((80, 24)).columns)
    card_w = (cols - 3) // 2

    jobs: List[Dict] = kernel.syscall("cron_list")
    workers: List[Dict] = kernel.syscall("coworker_list")
    stats: Dict = kernel.syscall("kernel_stats")
    fire: List[Dict] = kernel.syscall("cron_log", 4)

    job_by_name = {j["name"]: j for j in jobs}

    ts     = time.strftime("%H:%M:%S")
    uptime = stats["uptime_seconds"]

    out = []
    # header
    hdr = f"  ✦ ClaudeOS — Secret of Mana Edition  ·  uptime {uptime:.0f}s  ·  {ts}  "
    out.append(GOLD + BD + "╔" + "═" * (cols - 2) + "╗" + R)
    out.append(GOLD + BD + "║" + hdr.center(cols - 2) + "║" + R)
    out.append(GOLD + BD + "╚" + "═" * (cols - 2) + "╝" + R)
    out.append("")

    # spirit cards 2-column
    left_cards  = SPIRITS[::2]   # 0,2,4,6
    right_cards = SPIRITS[1::2]  # 1,3,5,7

    for i, (lsp, rsp) in enumerate(zip(left_cards, right_cards)):
        li = SPIRITS.index(lsp)
        ri = SPIRITS.index(rsp)
        lj = job_by_name.get(lsp["name"])
        rj = job_by_name.get(rsp["name"])
        llines = _spirit_card(lsp, lj, li == selected, card_w)
        rlines = _spirit_card(rsp, rj, ri == selected, card_w)
        for l, r in zip(llines, rlines):
            out.append(l + "  " + r)
        out.append("")

    # fire log
    out.append(GRAY + "─ Fire Log " + "─" * (cols - 12) + R)
    if fire:
        for e in reversed(fire):
            col = RED if e["error"] else GREEN
            err = f"  {RED}⚠ {e['error'][:30]}{R}" if e["error"] else ""
            out.append(f"  {col}{e['ts']}{R}  {e['name']:<12}  run={e['run_count']}{err}")
    else:
        out.append(f"  {DM}(no events yet){R}")

    # controls
    out.append("")
    sel_name = SPIRITS[selected]["color"] + SPIRITS[selected]["name"] + R
    ctrl = (f"  [{GOLD}1-8{R}] select   [{GOLD}F{R}] fire {sel_name}   "
            f"[{GOLD}E{R}] enable   [{GOLD}D{R}] disable   [{GOLD}Q{R}] quit")
    out.append(ctrl)
    if msg:
        out.append(f"  {GOLD}» {msg}{R}")
    else:
        out.append("")

    return "\n".join(out)

# ── Non-blocking input ────────────────────────────────────────────────────────

def _getch(timeout: float = 1.0) -> Optional[str]:
    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                sys.stdin.read(2)   # discard [ + letter for arrow keys
                return "ESC"
            return ch
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    kernel = Kernel()
    kernel.boot_silent()

    # register all 8 spirits
    for spirit in SPIRITS:
        action = _make_action(kernel, spirit)
        kernel.coworkers.register(
            name=spirit["name"],
            schedule=spirit["sched"],
            secret_names=[],
            action=action,
        )

    _boot(kernel)

    selected = 0
    msg      = ""
    msg_ts   = 0.0

    def _shutdown(sig=None, frame=None):
        kernel.shutdown_silent()
        sys.stdout.write(SHOW + "\n")
        print(GOLD + "  The Mana Tree sleeps. Farewell." + R)
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    sys.stdout.write(HIDE)

    try:
        while True:
            if time.time() - msg_ts > 4:
                msg = ""

            frame = _render(kernel, selected, msg)
            sys.stdout.write(CLEAR + frame + "\n")
            sys.stdout.flush()

            ch = _getch(1.0)
            if ch is None:
                continue

            ch = ch.lower()

            if ch in ("q", "ESC", "\x03"):
                _shutdown()

            elif ch in "12345678":
                selected = int(ch) - 1
                msg = f"{SPIRITS[selected]['name']} selected"
                msg_ts = time.time()

            elif ch == "f":
                name = SPIRITS[selected]["name"]
                ok   = kernel.coworkers.fire(name)
                msg  = f"{name} fired!" if ok else f"{name}: not found"
                msg_ts = time.time()

            elif ch == "e":
                name = SPIRITS[selected]["name"]
                kernel.coworkers.enable(name)
                msg  = f"{name} awakened"
                msg_ts = time.time()

            elif ch == "d":
                name = SPIRITS[selected]["name"]
                kernel.coworkers.disable(name)
                msg  = f"{name} put to sleep"
                msg_ts = time.time()

    finally:
        _shutdown()


if __name__ == "__main__":
    main()
