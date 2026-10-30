#!/usr/bin/env bash
# tmux-resurrect post-save hook: drop the `system` session from the save file.
# resurrect could not restart btop & co, and tmux/system.sh rebuilds it anyway.
#
# A save with nothing left (only `system` was open: WSL shutting down, a client going away
# before the sessions were restored…) must not replace the last real save, or the next start
# would bring back nothing. It is made identical to the last save, so resurrect drops it.
# `terminal kill-all` really means "nothing": it saves with TERMINAL_SAVE_EMPTY=1.
file=$1
[[ -f $file ]] || exit 0
awk -F'\t' '!(($1 == "pane" || $1 == "window" || $1 == "grouped_session") && $2 == "system")' "$file" > "$file.tmp" \
  && mv "$file.tmp" "$file"
last=$(dirname "$file")/last
if [[ -z $TERMINAL_SAVE_EMPTY ]] && ! grep -q '^pane' "$file" && grep -qs '^pane' "$last"; then
  cat "$last" > "$file"
fi
exit 0
