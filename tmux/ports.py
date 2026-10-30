#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
#  Ports pane of the `system` session (tmux/system.sh)
#  Listening TCP / UDP ports from `ss -tulpnH` (macOS: lsof), refreshed every 2 s.
#
#  Double-click a TCP port: open http://localhost:PORT in the Windows browser.
#  Right-click a port: open it in the browser
#  · copy localhost:PORT · stop / force kill its process (asks first)
#  · show the process (jumps to the Processes pane).
#  Without sudo, ss cannot tell which process owns ports of other users (root):
#  those rows show "?" and say how to deal with them.
# ═══════════════════════════════════════════════════════════════

import os
import re
import shutil
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import tmuxlink
from table import Column, TableApp, run
from tui import BLUE, DIM, SUB, TEXT

ICON_WEB, ICON_COPY, ICON_STOP, ICON_KILL, ICON_PROC = ("\U000F059F", "\U000F018F", "\U000F04DB",
                                                        "\U000F0A7A", "\U000F0430")
ICON_DOCKER = "\U000F0868"


def docker_ports():
    """Published host port → container name (those ports belong to docker-proxy, i.e. root)."""
    try:
        out = subprocess.run(["docker", "ps", "--format", "{{.Names}}|{{.Ports}}"], capture_output=True,
                             text=True, timeout=5).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}
    found = {}
    for line in out.splitlines():
        name, _, ports = line.partition("|")
        for port in re.findall(r":(\d+)->", ports):
            found[int(port)] = name
    return found
PROC = re.compile(r'\("([^"]+)",pid=(\d+)')


def sockets():
    """Listening sockets as (proto, "addr:port", pid or None, program or "?").
    Linux: ss · macOS: lsof (without sudo it sees your own programs only, like ss)."""
    if shutil.which("ss"):
        out = subprocess.run(["ss", "-tulpnH"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = line.split(None, 6)
            if len(parts) < 5:
                continue
            m = PROC.search(parts[6]) if len(parts) > 6 else None
            yield parts[0], parts[4], (int(m[2]) if m else None), (m[1] if m else "?")
        return
    # two calls: lsof's TCP state filter would also drop every UDP socket
    out = "".join(subprocess.run(["lsof", "-nP", *sel, "-F", "pcPn"], capture_output=True, text=True).stdout
                  for sel in (["-iTCP", "-sTCP:LISTEN"], ["-iUDP"]))
    pid, cmd, proto = None, "?", ""
    for line in out.splitlines():
        tag, val = line[:1], line[1:]
        if tag == "p":
            pid, cmd = int(val), "?"
        elif tag == "c":
            cmd = val
        elif tag == "P":
            proto = val.lower()
        elif tag == "n" and "->" not in val:        # UDP: only bound sockets, not connections
            yield proto, val, pid, cmd


def tmux(*args):
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def where(addr):
    a = addr.strip("[]").split("%")[0]
    if a in ("0.0.0.0", "::", "*"):
        return "everyone"
    if a in ("127.0.0.1", "::1", "localhost") or a.startswith("127."):
        return "this machine"
    return a


class Ports(TableApp):
    icon = "\U000F0318"
    title = "Ports"
    noun = "listening"
    sort_key = "port"
    columns = [Column("port", "PORT", 6, "r"),
               Column("proto", "PROTO", 5, optional=True),
               Column("where", "OPEN TO", 15, min=8),
               Column("pid", "PID", 7, "r", optional=True),
               Column("name", "PROCESS")]

    def fetch(self):
        dock = docker_ports()
        rows, seen = [], set()
        for proto, local, pid, name in sockets():
            addr, _, port = local.rpartition(":")
            if not port.isdigit():
                continue
            container = dock.get(int(port)) if proto == "tcp" else None
            if container:
                name = f"docker:{container}"
            key = (proto, port, where(addr), pid)      # 127.0.0.53 and 127.0.0.54 are the same to you
            if key in seen:
                continue
            seen.add(key)
            rows.append({"id": f"{proto}|{addr}|{port}", "port": int(port), "proto": proto, "addr": addr,
                         "where": where(addr), "pid": pid, "name": name, "container": container})
        return rows

    def apply(self):
        super().apply()
        # your own programs and containers first; system ports you cannot touch go to the bottom
        self.rows.sort(key=lambda r: r["pid"] is None and not r["container"])

    def row_colour(self, r):
        if r["container"]:
            return BLUE
        if r["pid"] is None:
            return DIM
        return TEXT if r["where"] == "everyone" else SUB

    def detail(self, r):
        if r["container"]:
            return (f"{TEXT}container {r['container']}{DIM} publishes {r['addr']}:{r['port']}"
                    f"  · http://localhost:{r['port']} · right-click → Show the container")
        if r["pid"] is None:
            return (f"{DIM}{r['proto']} {r['addr']}:{r['port']} · owned by another user (root):"
                    f" see it with  sudo {'ss -tulpn' if shutil.which('ss') else 'lsof -nP -i'} | grep :{r['port']}")
        url = f"  · http://localhost:{r['port']}" if r["proto"] == "tcp" else ""
        return f"{TEXT}{r['name']}{DIM} (pid {r['pid']}) on {r['addr']}:{r['port']}{url}"

    def menu_title(self, r):
        return f":{r['port']} · {r['name']}"

    def menu_items(self, r):
        has = r["pid"] is not None
        tcp = r["proto"] == "tcp"
        if r["container"]:
            c = r["container"]
            return [(f"{ICON_WEB}  Open http://localhost:{r['port']}", "o", lambda: self.browse(r)),
                    (f"{ICON_COPY}  Copy localhost:{r['port']}", "c", lambda: self.copy(f"localhost:{r['port']}")),
                    ("", "", None),
                    (f"{ICON_DOCKER}  Show the container", "p", lambda: self.show_container(c)),
                    (f"{ICON_STOP}  Stop the container…", "s", lambda: self.confirm(
                        f"Stop the container {c}, which publishes :{r['port']}?",
                        lambda: self.background(r, "stopping", ["docker", "stop", c],
                                                lambda ok, out: self.flash(f"{c}: stop done" if ok else out, ok)), r))]
        return [(f"{ICON_WEB}  Open http://localhost:{r['port']}", "o", (lambda: self.browse(r)) if tcp else None),
                (f"{ICON_COPY}  Copy localhost:{r['port']}", "c", lambda: self.copy(f"localhost:{r['port']}")),
                ("", "", None),
                (f"{ICON_STOP}  Stop {r['name']} · SIGTERM…", "s", (lambda: self.ask_kill(r, signal.SIGTERM)) if has else None),
                (f"{ICON_KILL}  Force kill · SIGKILL…", "k", (lambda: self.ask_kill(r, signal.SIGKILL)) if has else None),
                (f"{ICON_PROC}  Show the process", "p", (lambda: self.show_proc(r)) if has else None)]

    def on_double(self, r, col, x):
        if r["proto"] == "tcp":
            self.browse(r)
        else:
            self.flash(f"udp :{r['port']} is not a web page · right-click for more", ok=False)

    def show_container(self, name):
        tmuxlink.put("@docker-focus", name)
        tmuxlink.focus("Containers")
        self.flash(f"{name} → docker tab")

    def on_delete(self, r):
        if r["pid"] is not None:
            self.ask_kill(r, signal.SIGTERM)

    def ask_kill(self, r, sig):
        what = f"{r['name']} ({r['pid']}), which listens on :{r['port']}"
        q = (f"Force kill {what}? unsaved work is lost" if sig == signal.SIGKILL else f"Stop {what}?")
        self.confirm(q, lambda: self.kill(r, sig), r)

    def kill(self, r, sig):
        try:
            os.kill(r["pid"], sig)
            self.flash(f"sent {sig.name} to {r['name']} ({r['pid']}) · port :{r['port']}")
        except ProcessLookupError:
            self.flash(f"{r['name']} had already finished")
        except PermissionError:
            self.flash(f"not yours: run  sudo kill -{sig.name[3:]} {r['pid']}", ok=False)
        self.reload()

    def browse(self, r):
        url = f"http://localhost:{r['port']}"
        if tmuxlink.open_url(url):
            self.flash(f"opening {url} in the browser")
        else:
            self.flash(f"could not start {tmuxlink.BROWSER}", ok=False)

    def copy(self, text):
        tmux("set-buffer", "-w", "--", text)
        self.flash(f"copied: {text}")

    def show_proc(self, r):
        tmux("set", "-g", "@procs-query", str(r["pid"]))
        out = tmux("list-panes", "-F", "#{pane_id}\t#{@label}").stdout
        for line in out.splitlines():
            pane, _, lab = line.partition("\t")
            if lab == "Processes":
                tmux("select-pane", "-t", pane)
        self.flash(f"{r['name']} → Processes pane")

    def dispatch(self, ev):
        if ev[0] == "tick":          # a filter sent from the Processes pane
            q = tmux("show", "-gqv", "@ports-query").stdout.strip()
            if q:
                tmux("set", "-gu", "@ports-query")
                self.query = q[4:] if q.startswith("pid=") else q
        super().dispatch(ev)


if __name__ == "__main__":
    run(Ports)
