# ═══════════════════════════════════════════════════════════════
#  Interactive table for the system monitor panes (procs.py, ports.py)
#
#  Mouse: hover highlights · click a column title to sort (again to reverse)
#         · right-click a row for its menu (always with "Copy this row") · wheel scrolls
#         · double-click a row: its main action (on_double; the menu if the pane has none)
#         · 󰊓 zoom on the title row (or double-click the title) · 󰊔 restore
#  Narrow panes: columns shrink to their minimum and optional ones hide, so a row
#  never runs off the right edge.
#  Keys:  type to filter · ↑↓ PgUp PgDn move · Enter opens the row menu
#         · Del asks to stop it · Esc clears the filter · Ctrl+c quits
#  Rows refresh every few seconds; the highlighted row is followed by its id,
#  and refreshing pauses while a menu or a question is open.
# ═══════════════════════════════════════════════════════════════

import os
import subprocess
import sys
import threading
import time

import tmuxlink

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from tui import (ACCENT, BOLD, CLEAR_EOL, CRUST, DANGER_BG, DIM, GREEN, HOVER, RED, RESET, SUB, SURFACE,
                 TEXT, YELLOW, Menu, Screen, bg, cut, ellipsis, highlight, vlen)

ACTIVE_ZOOM = bg("#89b4fa") + CRUST + BOLD

WHEEL_STEP = 3
ICON_ZOOM, ICON_UNZOOM, ICON_COPY, ICON_SELECT = "\U000F0293", "\U000F0294", "\U000F018F", "\U000F0489"
TOP = 3            # first data row on screen (1-based): title, column titles, rows…, footer


class Column:
    def __init__(self, key, title, width=None, align="l", desc=False, fmt=str, sort=None, optional=False, min=None):
        self.key, self.title, self.width, self.align, self.desc, self.fmt = key, title, width, align, desc, fmt
        self.sort = sort or key        # field used to sort (e.g. bytes behind a "245M / 2G" text)
        self.optional = optional       # hidden first when the pane is too narrow
        self.min = min or (min_default(width, title) if width else 12)


def min_default(width, title):
    return max(3, min(width, len(title) + 2))


class TableApp:
    icon = ""
    title = ""
    noun = "rows"
    interval = 2.0
    columns = []
    sort_key = None

    # ─── to override ───
    def fetch(self):
        """→ list of dicts, each with a unique 'id'."""
        return []

    def detail(self, row):
        """Footer text for the highlighted row."""
        return ""

    def menu_items(self, row):
        return []

    def row_colour(self, row):
        return SUB

    def on_double(self, row, col, x):
        """Double-click on a row (col: the column under the pointer). Default: its menu."""
        self.open_menu(row, x, TOP + self.cur_index() - self.top + 1)

    def on_delete(self, row):
        pass

    def keep(self, row):
        """False hides the row (a filter of the pane's own, e.g. by source)."""
        return True

    def chips(self):
        """Toggle buttons on the title row: [(name, label, active)] · a click calls on_chip(name)."""
        return []

    def on_chip(self, name):
        pass

    def summary(self):
        """Extra text after the count on the title row (totals…)."""
        return ""

    def empty_menu_items(self):
        """Menu for a right-click where there is no row (e.g. 'check for updates')."""
        return []

    def selected(self, row):
        """Called when the highlighted row changes (row may be None): detail panes follow it."""

    # When True, typing does not filter locally: fetch() reads self.query itself (a search box)
    remote_query = False

    # Master of a master/detail layout (Containers → details + logs, package lists → Package):
    # hovering only highlights; the row shown in the detail panes (marked ▌) changes on a
    # click, with the arrows, or after resting the pointer ~0.35 s on a row. So crossing
    # other rows on the way to the detail panes does not change what they show.
    master = False
    DWELL = 0.35
    # ticks come every `interval` seconds of quiet; the rows are fetched again on a tick
    # once `reload_every` seconds went by (0: every tick). A short interval with a long
    # reload_every notices other things (a message from another pane) quickly, cheaply.
    reload_every = 0

    # ─── engine ───
    def __init__(self, screen):
        self.screen = screen
        self.query = ""
        self.top = 0
        self.cur_id = None
        self.menu = None
        self.ask = None          # (question, action, row id) waiting for y / n
        self.prompt = None       # [label, text, on_submit] while typing in the footer
        self.busy = {}           # row id → what is running on it in the background
        self.msg = ""
        self.buttons = {}
        self.hover_col = None
        self._last_size = screen.size()
        self.sel_id = None
        self.hover_at = 0.0
        # sort_key may also be a hidden field (e.g. Docker's running-first order)
        col = next((c for c in self.columns if self.sort_key in (c.key, c.sort)), None)
        if col:
            self.sort_key, self.sort_desc = col.sort, col.desc
        else:
            self.sort_key, self.sort_desc = self.sort_key or self.columns[0].key, False
        self.reload()

    @property
    def frozen(self):
        return bool(self.menu or self.ask or self.prompt)

    def reload(self):
        self.reloaded_at = time.monotonic()
        self.all = self.fetch()
        self.apply()

    def apply(self):
        words = [] if self.remote_query else self.query.lower().split()
        rows = [r for r in self.all if self.keep(r)
                and all(w in " ".join(str(v) for k, v in r.items() if k != "id").lower() for w in words)]
        rows.sort(key=lambda r: (r.get(self.sort_key) is None, r.get(self.sort_key)), reverse=self.sort_desc)
        if self.sort_desc:   # keep empty values last when reversing
            rows.sort(key=lambda r: r.get(self.sort_key) is None)
        self.rows = rows
        ids = [r["id"] for r in rows]
        if self.cur_id not in ids:
            self.cur_id = ids[0] if ids else None
        if getattr(self, "sel_id", None) not in ids:      # the selection disappeared (filter, removed)
            self.sel_id = self.cur_id

    def cur_index(self):
        for i, r in enumerate(self.rows):
            if r["id"] == self.cur_id:
                return i
        return None

    def current(self):
        i = self.cur_index()
        return self.rows[i] if i is not None else None

    # ─── geometry ───
    def layout(self):
        self.h, self.w = self.screen.size()
        self.list_h = max(1, self.h - 3)
        self.max_top = max(0, len(self.rows) - self.list_h)
        self.top = min(self.top, self.max_top)
        # responsive columns: hide optional ones (rightmost first), then shrink fixed ones to
        # their minimum, so the row always fits the pane
        avail = self.w - 2
        cols = list(self.columns)
        need = lambda cs: sum((c.width or c.min) + 1 for c in cs)
        for c in reversed(self.columns):
            if need(cols) <= avail:
                break
            if c.optional and c.key != self.sort_key:
                cols.remove(c)
        widths = {c.key: (c.width or 0) for c in cols}
        excess = need(cols) - avail
        for c in sorted([c for c in cols if c.width], key=lambda c: c.width - c.min, reverse=True):
            if excess <= 0:
                break
            cut_by = min(excess, c.width - c.min)
            widths[c.key] -= cut_by
            excess -= cut_by
        flex = [c for c in cols if not c.width]
        rest = max(4, avail - sum(widths[c.key] + 1 for c in cols if c.width) - len(flex))
        for c in flex:
            widths[c.key] = max(4, rest // max(1, len(flex)))
        self.visible, self.widths = cols, widths
        x, self.col_spans = 3, {}
        for c in cols:
            self.col_spans[c.key] = (x, x + self.widths[c.key] - 1)
            x += self.widths[c.key] + 1

    def ensure_visible(self):
        i = self.cur_index()
        if i is None:
            return
        if i < self.top:
            self.top = i
        elif i >= self.top + self.list_h:
            self.top = i - self.list_h + 1

    def cells(self, row):
        out = []
        for c in self.visible:
            v = row.get(c.key)
            t = "" if v is None else c.fmt(v)
            t = ellipsis(t, self.widths[c.key])
            out.append(t.rjust(self.widths[c.key]) if c.align == "r" else t.ljust(self.widths[c.key]))
        return out

    # ─── drawing ───
    def draw(self):
        self.layout()
        if self.master and self.sel_id is None:
            self.sel_id = self.cur_id
        shown = self.sel_id if self.master else self.cur_id
        if shown != getattr(self, "_announced", object()):
            self._announced = shown
            self.selected(next((r for r in self.rows if r["id"] == shown), None))
        self.buttons = {}
        w = self.w
        filt = f"{DIM}filter ❯ {RESET}{TEXT}{self.query}{RESET}{YELLOW}▏"
        extra = self.summary()
        zb_len = 11
        # title row by priority: title + count + filter + zoom always; the noun, the summary
        # and the hint only when there is room
        chips = self.chips()
        chip_txt = "".join(f" {(ACTIVE_ZOOM if on else SURFACE + SUB)} {label} {RESET}" for _, label, on in chips)
        for parts in ((True, True, True), (True, False, True), (False, False, True), (False, False, False)):
            lead = (f" {ACCENT}{self.icon} {BOLD}{self.title}{RESET}  {DIM}{len(self.rows)}"
                    + (f" {self.noun}" if parts[0] else "") + RESET + " ")
            head = (lead + (chip_txt if parts[2] else "")
                    + (f" {DIM}·{RESET} {extra}{RESET}" if (extra and parts[1]) else "") + f"   {filt}")
            if vlen(head) + zb_len <= w:
                break
        if chips and parts[2]:                           # where each chip landed, for clicks
            x = vlen(lead) + 1
            for name, label, _ in chips:
                self.buttons[f"chip:{name}"] = (1, x + 1, x + len(label) + 2)
                x += len(label) + 3
        zoomed = getattr(self, "zoomed", False)
        zb = f" {ICON_UNZOOM} restore " if zoomed else f" {ICON_ZOOM} zoom "
        hint = "right-click a row · click a title to sort  "
        room = w - vlen(head) - len(zb)
        tail = (RESET + " " * (room - len(hint)) + DIM + hint) if room > len(hint) + 1 else ""
        self.zoom_span = (w - len(zb) + 1, w)
        lines = [cut(head + tail, w - len(zb)) + RESET + CLEAR_EOL + f"\x1b[{w - len(zb) + 1}G"
                 + (ACTIVE_ZOOM if zoomed else SURFACE + SUB) + zb]

        titles = "  "
        for c in self.visible:
            arrow = (" ▼" if self.sort_desc else " ▲") if c.sort == self.sort_key else ""
            t = ellipsis(c.title + arrow, self.widths[c.key])
            t = t.rjust(self.widths[c.key]) if c.align == "r" else t.ljust(self.widths[c.key])
            style = (ACCENT + BOLD) if c.sort == self.sort_key else (TEXT if c.key == self.hover_col else DIM)
            bgc = HOVER if c.key == self.hover_col else ""
            titles += f"{bgc}{style}{t}{RESET} "
        lines.append(cut(titles, w))

        hot = self.cur_index()
        asking = self.ask[2] if self.ask else None
        for n in range(self.list_h):
            i = self.top + n
            if i >= len(self.rows):
                lines.append("")
                continue
            r = self.rows[i]
            body = "  " + " ".join(self.cells(r))
            if asking is not None and r["id"] == asking:
                lines.append(DANGER_BG + CRUST + cut(body, w).ljust(w) + RESET)
            elif r["id"] in self.busy:
                tag = f" {self.busy[r['id']]}… "
                lines.append(cut(YELLOW + body, w - len(tag)) + RESET + CLEAR_EOL + f"\x1b[{w - len(tag) + 1}G" + YELLOW + tag)
            else:
                if self.master and r["id"] == self.sel_id:     # what the detail panes show
                    body = f"{ACCENT}▌{RESET}" + (TEXT + BOLD if i != hot else TEXT) + body[1:]
                lines.append(highlight(TEXT + body, w) if i == hot else cut(self.row_colour(r) + body, w))

        lines.append(cut(self.footer(self.h), w))
        self.screen.paint(lines)
        if self.menu:
            self.menu.draw()

    def footer(self, y):
        if self.prompt:
            label, text, _ = self.prompt
            return (f" {ACCENT}{label} {RESET}{TEXT}{text}{RESET}{YELLOW}▏{RESET}  {DIM}enter save · esc cancel")
        if self.ask:
            q = f" {RED}{BOLD}{self.ask[0]}{RESET}  "
            yes, no = f"{DANGER_BG}{CRUST}{BOLD} y  yes {RESET}", f"{SURFACE}{TEXT} n  no {RESET}"
            x = vlen(q) + 1
            self.buttons["yes"] = (y, x, x + 7)
            self.buttons["no"] = (y, x + 10, x + 15)
            return q + yes + "  " + no
        if self.msg:
            return " " + self.msg
        r = self.current()
        return " " + (self.detail(r) if r else f"{DIM}nothing matches")

    # ─── helpers for subclasses ───
    def confirm(self, question, action, row):
        self.menu, self.ask = None, (question, action, row["id"])

    def flash(self, text, ok=True):
        self.msg = (GREEN if ok else RED) + text
        self.msg_at = time.monotonic()

    def ask_text(self, label, text, on_submit):
        """Type a line in the footer; on_submit(text) on Enter."""
        self.menu, self.prompt = None, [label, text, on_submit]

    def background(self, row, doing, argv, done):
        """Run argv without freezing the pane; done(ok, output) when it finishes.
        The row shows `doing` meanwhile."""
        self.busy[row["id"]] = doing

        def work():
            res = subprocess.run(argv, capture_output=True, text=True)
            self.busy.pop(row["id"], None)
            done(res.returncode == 0, (res.stdout + res.stderr).strip())
            self.wake()
        threading.Thread(target=work, daemon=True).start()

    def wake(self):
        """Ask the event loop to refresh now (used by background work)."""
        os.kill(os.getpid(), __import__("signal").SIGWINCH)

    def popup(self, title, command, w="90%", h="80%"):
        """Open a tmux popup over this pane (logs, a shell, apt…)."""
        subprocess.Popen(["tmux", "display-popup", "-E", "-w", w, "-h", h, "-b", "rounded", "-S", "fg=#89b4fa",
                          "-T", f"#[align=centre,fg=#89b4fa,bold] {title} ", command],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ─── input ───
    def open_menu(self, row, x, y):
        if row:
            self.cur_id = row["id"]
            items = list(self.menu_items(row))
            text = "  ".join(t.strip() for t in self.cells(row) if t.strip())
            items += [("", "", None), (f"{ICON_COPY}  Copy this row", "y", lambda: self.copy_row(text)),
                      (f"{ICON_SELECT}  Select text freely…", "t", tmuxlink.free_select)]
            title = self.menu_title(row)
        else:
            items, title = self.empty_menu_items(), self.title
        if items:
            self.menu = Menu(title, items, x, y, self.h, self.w)

    def copy_row(self, text):
        tmuxlink.copy(text)
        self.flash("copied the row to the clipboard")

    def toggle_zoom(self):
        tmuxlink.toggle_zoom()
        self.zoomed = not getattr(self, "zoomed", False)

    def menu_title(self, row):
        return str(row["id"])

    def hit(self, x, y):
        for name, (row, x0, x1) in self.buttons.items():
            if y == row and x0 <= x <= x1:
                return name
        return None

    def row_at(self, y):
        i = self.top + (y - TOP)
        return self.rows[i] if TOP <= y < TOP + self.list_h and 0 <= i < len(self.rows) else None

    def col_at(self, x, y):
        if y != 2:
            return None
        for key, (x0, x1) in self.col_spans.items():
            if x0 <= x <= x1:
                return key
        return None

    def busy_changed(self):
        """True when this 'resize' was only background work asking for a redraw."""
        size = self.screen.size()
        same = size == getattr(self, "_last_size", None)
        self._last_size = size
        if same and not self.frozen:
            self.reload()
        return same

    def dwell(self):
        """Master tables: the pointer rested on a row long enough → it becomes the selection."""
        if (self.master and not self.frozen and self.cur_id != self.sel_id and self.hover_at
                and time.monotonic() - self.hover_at >= self.DWELL):
            self.hover_at = 0.0
            if not tmuxlink.pointer_is_here():           # it left for another pane: keep the selection
                return False
            self.sel_id = self.cur_id
            return True
        return False

    def answer(self, yes):
        action = self.ask[1] if self.ask else None
        self.ask = None
        if yes and action:
            action()

    def dispatch(self, ev):
        kind = ev[0]
        if kind == "tick":
            self.zoomed = tmuxlink.pane_state("")[0]
            if not self.frozen:
                if time.monotonic() - self.reloaded_at >= self.reload_every:
                    self.reload()
                if time.monotonic() - getattr(self, "msg_at", 0) > 6:   # messages stay ~6 s
                    self.msg = ""
            return
        if kind == "resize":
            self.zoomed = tmuxlink.pane_state("")[0]     # zoom / restore resize the pane
            if not self.busy_changed():
                self.menu = None
            return
        if self.menu:
            res = (self.menu.on_mouse(*ev[1:]) if kind == "mouse" else self.menu.on_key(kind, ev[1]))
            if res:
                self.menu = None
                if res[0] == "pick":
                    res[1]()
            return
        if self.prompt:
            if kind == "char":
                self.prompt[1] += ev[1]
            elif kind == "key" and ev[1] == "backspace":
                self.prompt[1] = self.prompt[1][:-1]
            elif kind == "key" and ev[1] == "ctrl-u":
                self.prompt[1] = ""
            elif kind == "key" and ev[1] in ("esc", "ctrl-c"):
                self.prompt = None
            elif kind == "key" and ev[1] == "enter":
                _, text, submit = self.prompt
                self.prompt = None
                submit(text.strip())
            elif kind == "mouse" and ev[1] in (0, 2) and not ev[4]:
                self.prompt = None                  # clicking away cancels
            return
        if self.ask:
            if kind == "char" and ev[1].lower() in "yn":
                self.answer(ev[1].lower() == "y")
            elif kind == "key" and ev[1] in ("esc", "ctrl-c"):
                self.answer(False)
            elif kind == "mouse" and ev[1] == 0 and not ev[4]:
                self.answer(self.hit(ev[2], ev[3]) == "yes")
            return
        if kind == "mouse":
            self.on_mouse(*ev[1:])
        elif kind == "key":
            self.on_key(ev[1])
        elif kind == "char":
            self.query += ev[1]
            self.msg = ""
            self.reload() if self.remote_query else self.apply()
            self.top = 0

    def on_key(self, name):
        refilter = self.reload if self.remote_query else self.apply
        if name == "esc":
            self.query, self.msg = "", ""
            refilter()
        elif name == "backspace":
            self.query = self.query[:-1]
            refilter()
        elif name == "ctrl-u":
            self.query = ""
            refilter()
        elif name in ("ctrl-c", "ctrl-d"):
            raise SystemExit
        elif name in ("up", "down", "pgup", "pgdn", "home", "end"):
            i = self.cur_index() or 0
            step = {"up": -1, "down": 1, "pgup": -self.list_h, "pgdn": self.list_h,
                    "home": -len(self.rows), "end": len(self.rows)}[name]
            if self.rows:
                self.cur_id = self.sel_id = self.rows[max(0, min(len(self.rows) - 1, i + step))]["id"]
                self.ensure_visible()
        elif name == "enter":
            r = self.current()
            i = self.cur_index()
            self.open_menu(r, 4, (TOP + i - self.top + 1) if r is not None else TOP)
        elif name == "delete":
            r = self.current()
            if r is not None:
                self.on_delete(r)

    def on_mouse(self, b, x, y, released):
        if b in (64, 65):
            self.top = max(0, min(self.max_top, self.top + (-WHEEL_STEP if b == 64 else WHEEL_STEP)))
            b, released = 35, False
        if b & 32:
            if self.master:
                tmuxlink.pointer_here()
            self.hover_col = self.col_at(x, y)
            r = self.row_at(y)
            if r is None:
                self.hover_at = 0.0                      # over the titles / empty space: no dwell
            elif r["id"] != self.cur_id:
                self.cur_id = r["id"]
                self.hover_at = time.monotonic()
                if self.master:
                    tmuxlink.pointer_here(force=True)    # a new row: say so right away
            return
        if released or b not in (0, 2):
            return
        if y == 1 and b == 0 and (self.hit(x, y) or "").startswith("chip:"):
            self.on_chip(self.hit(x, y)[5:])
            return
        if y == 1 and b == 0:
            a, z = getattr(self, "zoom_span", (0, -1))
            now = time.monotonic()
            if a <= x <= z or now - getattr(self, "_title_click", 0) < 0.4:   # button or double-click
                self.toggle_zoom()
                self._title_click = 0
            else:
                self._title_click = now
            return
        col = self.col_at(x, y)
        if b == 0 and col:
            c = next(c for c in self.columns if c.key == col)
            if c.sort == self.sort_key:
                self.sort_desc = not self.sort_desc
            else:
                self.sort_key, self.sort_desc = c.sort, c.desc
            self.apply()
            return
        r = self.row_at(y)
        if r is None:
            if b == 2 and y >= TOP:
                self.open_menu(None, x, y)
            return
        self.cur_id = self.sel_id = r["id"]
        if b == 2:
            self.open_menu(r, x, y)
        elif b == 0:                                     # a second click on the same row = double-click
            now = time.monotonic()
            last_id, last_at = getattr(self, "_row_click", (None, 0.0))
            if last_id == r["id"] and now - last_at < 0.4:
                self._row_click = (None, 0.0)
                col = next((k for k, (x0, x1) in self.col_spans.items() if x0 <= x <= x1), None)
                self.on_double(r, col, x)
            else:
                self._row_click = (r["id"], now)


def run(app_class):
    try:
        with Screen() as screen:
            app = app_class(screen)
            app.draw()
            # master tables tick fast to notice a pointer resting on a row (cheap: no fetch);
            # the real refresh still happens every app.interval seconds
            last = time.monotonic()
            for ev in screen.events(tick=0.12 if app.master else app.interval):
                if ev[0] == "tick" and app.master:
                    if time.monotonic() - last >= app.interval:
                        last = time.monotonic()
                        app.dispatch(ev)
                        app.draw()
                    elif app.dwell():
                        app.draw()
                    continue
                app.dispatch(ev)
                app.draw()
    except SystemExit as e:
        sys.exit(0 if e.code is None else e.code)
