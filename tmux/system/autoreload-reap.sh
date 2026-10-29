#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  tmux-autoreload starts a watcher (bash + entr) per tmux server and never stops it:
#  after `tmux kill-server` the old one stays, and reloads the config into the next
#  server too. Run from ~/.tmux.conf: end the watchers whose tmux server is gone.
#  A watcher knows its server from $TMUX (socket,server-pid,…); live servers are not touched.
#  Linux reads /proc/<pid>/environ; macOS has no /proc, but ps -E shows the environment.
# ═══════════════════════════════════════════════════════════════

# the server pid in a watcher's $TMUX
server_of() {
  if [[ -r /proc/$1/environ ]]; then
    tr '\0' '\n' < "/proc/$1/environ" 2>/dev/null | sed -n 's/^TMUX=[^,]*,\([0-9]*\),.*/\1/p'
  else
    ps -wwE -p "$1" -o command= 2>/dev/null | tr ' ' '\n' | sed -n 's/^TMUX=[^,]*,\([0-9]*\),.*/\1/p' | head -1
  fi
}

# is that pid a running tmux server
is_tmux() {
  if [[ -r /proc/$1/comm ]]; then [[ $(cat "/proc/$1/comm" 2>/dev/null) == tmux* ]]
  else [[ $(ps -p "$1" -o comm= 2>/dev/null) == *tmux* ]]; fi
}

for pid in $(pgrep -u "$UID" -f 'tmux-autoreload\.tmux -f$'); do
  server=$(server_of "$pid")
  [[ -n $server ]] || continue
  is_tmux "$server" && continue                                          # its server still runs
  pkill -P "$pid" 2>/dev/null                                             # entr
  kill "$pid" 2>/dev/null
done
exit 0
