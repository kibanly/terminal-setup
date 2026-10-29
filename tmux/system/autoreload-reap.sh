#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  tmux-autoreload starts a watcher (bash + entr) per tmux server and never stops it:
#  after `tmux kill-server` the old one stays, and reloads the config into the next
#  server too. Run from ~/.tmux.conf: end the watchers whose tmux server is gone.
#  A watcher knows its server from $TMUX (socket,server-pid,…); live servers are not touched.
# ═══════════════════════════════════════════════════════════════

for pid in $(pgrep -u "$UID" -f 'tmux-autoreload\.tmux -f$'); do
  server=$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | sed -n 's/^TMUX=[^,]*,\([0-9]*\),.*/\1/p')
  [[ -n $server ]] || continue
  [[ $(cat "/proc/$server/comm" 2>/dev/null) == tmux* ]] && continue      # its server still runs
  pkill -P "$pid" 2>/dev/null                                             # entr
  kill "$pid" 2>/dev/null
done
exit 0
