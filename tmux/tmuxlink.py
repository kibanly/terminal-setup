# ═══════════════════════════════════════════════════════════════
#  How the panes of the `system` session talk to each other:
#  global tmux options (@docker-selected, @pkg-selected, @ports-query…) and
#  focusing a pane by its @label (switching tab if needed).
# ═══════════════════════════════════════════════════════════════

import os
import subprocess
import time


def tmux(*args):
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def get(option):
    return tmux("show", "-gqv", option).stdout.rstrip("\n")


def put(option, value):
    if value is None or value == "":
        tmux("set", "-gu", option)
    else:
        tmux("set", "-g", option, str(value))


def take(option):
    """Read a one-shot message left by another pane, and clear it."""
    value = get(option)
    if value:
        tmux("set", "-gu", option)
    return value


def focus(label):
    """Select the pane whose @label is `label` in this session, switching tab if needed."""
    out = tmux("list-panes", "-s", "-F", "#{pane_id}\t#{window_id}\t#{@label}").stdout
    for line in out.splitlines():
        pane, window, lab = line.split("\t")
        if lab == label:
            tmux("select-window", "-t", window)
            tmux("select-pane", "-t", pane)
            return True
    return False


# tmux does not say when the pointer leaves a pane, so every pane of the session notes
# "the pointer is over me" in @pointer while the mouse moves on it (at most every 0.25 s).
# A list only selects the row the pointer rests on if the pointer is still its own.
_LABEL = None
_noted = 0.0


def my_label():
    global _LABEL
    if _LABEL is None:
        pane = os.environ.get("TMUX_PANE", "")
        _LABEL = tmux("display", "-p", "-t", pane, "#{@label}").stdout.strip() if pane else ""
    return _LABEL


def pointer_here(force=False):
    global _noted
    now = time.monotonic()
    if (force or now - _noted >= 0.25) and my_label():
        _noted = now
        put("@pointer", my_label())


def pointer_is_here():
    return bool(my_label()) and get("@pointer") == my_label()


def pane_state(option):
    """(is this pane's window zoomed, value of a global option) in one tmux call."""
    pane = os.environ.get("TMUX_PANE", "")
    fmt = "#{window_zoomed_flag}\t" + ("#{" + option + "}" if option else "")
    out = tmux("display", "-p", *(("-t", pane) if pane else ()), fmt).stdout.rstrip("\n")
    zoomed, _, value = out.partition("\t")
    return zoomed == "1", (value or None)


def pane_view(option):
    """(zoomed, visible, value of a global option) in one tmux call. Visible: someone is
    attached to this session, this pane's tab is the current one and no other pane is zoomed."""
    pane = os.environ.get("TMUX_PANE", "")
    fmt = ("#{window_zoomed_flag}\t"
           "#{&&:#{&&:#{window_active},#{session_attached}},#{||:#{?window_zoomed_flag,0,1},#{pane_active}}}\t"
           + ("#{" + option + "}" if option else ""))
    out = tmux("display", "-p", *(("-t", pane) if pane else ()), fmt).stdout.rstrip("\n")
    zoomed, visible, value = (out.split("\t", 2) + ["", ""])[:3]
    return zoomed == "1", visible == "1", (value or None)


def toggle_zoom():
    pane = os.environ.get("TMUX_PANE", "")
    tmux("resize-pane", "-Z", *(("-t", pane) if pane else ()))


def free_select():
    """Put this pane in tmux copy mode: drag selects any text, only inside this pane;
    releasing copies it and the pane goes back to its program (see MouseDragEnd1Pane)."""
    pane = os.environ.get("TMUX_PANE", "")
    tmux("copy-mode", *(("-t", pane) if pane else ()))
    tmux("display-message", "drag over the text to copy it · q or Esc to leave")


# ~/.tmux/system/open.sh opens it with the desktop's browser of each system (Windows' one in
# WSL, `open` on macOS, xdg-open on Linux). TMUX_OPEN_URL replaces it (tests).
BROWSER = os.environ.get("TMUX_OPEN_URL") or os.path.expanduser("~/.tmux/system/open.sh")


def open_url(url):
    """Open url in the Windows browser; False when that cannot be started."""
    try:
        subprocess.Popen([BROWSER, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        return True
    except OSError:
        return False


def copy(text):
    tmux("set-buffer", "-w", "--", text)
