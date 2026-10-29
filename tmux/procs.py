#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
#  Processes pane of the `system` session (~/.tmux/system.sh)
#  Reads /proc every 2 s. CPU% is per core, like top (100% = one full core).
#
#  Right-click a process: stop (SIGTERM) · force kill (SIGKILL), both ask first
#  · show its ports (jumps to the Ports pane) · copy PID / command line.
#  Type to filter (name, user, command) · click a column title to sort.
# ═══════════════════════════════════════════════════════════════

import os
import pwd
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from table import Column, TableApp, run
from tui import DIM, SUB, TEXT, YELLOW

CLK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")
ME = os.getuid()
ICON_STOP, ICON_KILL, ICON_PORTS, ICON_COPY = "\U000F04DB", "\U000F0A7A", "\U000F0318", "\U000F018F"


def human(n):
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return f"{n:.0f}{unit}" if unit in ("B", "K") else f"{n:.1f}{unit}"
        n /= 1024


def mem_total():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    return 1


def tmux(*args):
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


class Procs(TableApp):
    icon = "\U000F0430"
    title = "Processes"
    noun = "processes"
    sort_key = "cpu"
    columns = [Column("pid", "PID", 7, "r"),
               Column("user", "USER", 9, optional=True),
               Column("cpu", "CPU%", 6, "r", desc=True, fmt=lambda v: f"{v:.1f}"),
               Column("rss", "MEM", 7, "r", desc=True, fmt=human),
               Column("name", "NAME")]

    def __init__(self, screen):
        self.prev = {}
        self.users = {}
        self.total = mem_total()
        out = tmux("display", "-p", "#{pid}").stdout.strip()
        # never offer to kill these: tmux itself, this pane, pid 1
        self.protected = {1, os.getpid(), os.getppid()} | ({int(out)} if out.isdigit() else set())
        super().__init__(screen)

    def user(self, uid):
        if uid not in self.users:
            try:
                self.users[uid] = pwd.getpwuid(uid).pw_name
            except KeyError:
                self.users[uid] = str(uid)
        return self.users[uid]

    def fetch(self):
        now = time.monotonic()
        rows, seen = [], {}
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            pid = int(d)
            try:
                with open(f"/proc/{d}/stat") as f:
                    stat = f.read()
                with open(f"/proc/{d}/cmdline", "rb") as f:
                    cmd = f.read().replace(b"\0", b" ").decode(errors="replace").strip()
                uid = os.stat(f"/proc/{d}").st_uid
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
            if not cmd:                        # kernel threads
                continue
            name = stat[stat.index("(") + 1:stat.rindex(")")]
            if len(name) == 15:                # the kernel cuts names at 15 chars: use the program
                exe = os.path.basename(cmd.split()[0]) if cmd else ""
                name = exe if exe.startswith(name[:8]) else name
            f = stat[stat.rindex(")") + 2:].split()
            ticks = int(f[11]) + int(f[12])
            seen[pid] = (ticks, now)
            p = self.prev.get(pid)
            cpu = (ticks - p[0]) / CLK / max(1e-3, now - p[1]) * 100 if p else 0.0
            rss = int(f[21]) * PAGE
            rows.append({"id": pid, "pid": pid, "user": self.user(uid), "uid": uid, "cpu": max(0.0, cpu),
                         "rss": rss, "name": name, "cmd": cmd, "state": f[0], "ppid": int(f[1])})
        self.prev = seen
        return rows

    def row_colour(self, row):
        if row["cpu"] >= 50:
            return YELLOW
        return SUB if row["uid"] == ME else DIM

    def detail(self, r):
        states = {"R": "running", "S": "sleeping", "D": "waiting on disk", "Z": "zombie", "T": "stopped",
                  "I": "idle"}
        mem = f"{r['rss'] / self.total * 100:.1f}% of RAM"
        return (f"{TEXT}{r['cmd']}{DIM}  · {states.get(r['state'], r['state'])} · parent {r['ppid']} · {mem}")

    def menu_title(self, r):
        return f"{r['name']} · {r['pid']}"

    def killable(self, r):
        return r["pid"] not in self.protected

    def menu_items(self, r):
        k = self.killable(r)
        note = "" if k else "  (tmux itself)"
        return [(f"{ICON_STOP}  Stop · SIGTERM…{note}", "s", (lambda: self.ask_kill(r, signal.SIGTERM)) if k else None),
                (f"{ICON_KILL}  Force kill · SIGKILL…{note}", "k", (lambda: self.ask_kill(r, signal.SIGKILL)) if k else None),
                ("", "", None),
                (f"{ICON_PORTS}  Show its ports", "p", lambda: self.show_ports(r)),
                (f"{ICON_COPY}  Copy PID", "c", lambda: self.copy(str(r["pid"]))),
                (f"{ICON_COPY}  Copy command line", "l", lambda: self.copy(r["cmd"]))]

    def on_delete(self, r):
        if self.killable(r):
            self.ask_kill(r, signal.SIGTERM)

    def ask_kill(self, r, sig):
        if sig == signal.SIGKILL:
            q = f"Force kill {r['name']} ({r['pid']})? it cannot clean up, unsaved work is lost"
        else:
            q = f"Stop {r['name']} ({r['pid']})?"
        self.confirm(q, lambda: self.kill(r, sig), r)

    def kill(self, r, sig):
        try:
            os.kill(r["pid"], sig)
            self.flash(f"sent {sig.name} to {r['name']} ({r['pid']})")
        except ProcessLookupError:
            self.flash(f"{r['name']} had already finished")
        except PermissionError:
            self.flash(f"{r['name']} belongs to {r['user']}: run  sudo kill -{sig.name[3:]} {r['pid']}", ok=False)
        self.reload()

    def copy(self, text):
        tmux("set-buffer", "-w", "--", text)
        self.flash(f"copied: {text[:60]}")

    def show_ports(self, r):
        tmux("set", "-g", "@ports-query", f"pid={r['pid']}")
        focus("Ports")
        self.flash(f"ports of {r['name']} → Ports pane")


def focus(label):
    """Select the pane of this window whose @label is `label`."""
    out = tmux("list-panes", "-F", "#{pane_id}\t#{@label}").stdout
    for line in out.splitlines():
        pid, _, lab = line.partition("\t")
        if lab == label:
            tmux("select-pane", "-t", pid)


class LinkedProcs(Procs):
    """Takes a filter from the Ports pane (@procs-query) on each refresh."""

    def dispatch(self, ev):
        if ev[0] == "tick":
            q = tmux("show", "-gqv", "@procs-query").stdout.strip()
            if q:
                tmux("set", "-gu", "@procs-query")
                self.query = q
        super().dispatch(ev)


if __name__ == "__main__":
    run(LinkedProcs)
