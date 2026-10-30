#!/usr/bin/env bash
# tmux-resurrect post-save hook: drop the `system` session from the save file.
# resurrect could not restart btop & co, and tmux/system.sh rebuilds it anyway.
file=$1
[[ -f $file ]] || exit 0
awk -F'\t' '!(($1 == "pane" || $1 == "window" || $1 == "grouped_session") && $2 == "system")' "$file" > "$file.tmp" \
  && mv "$file.tmp" "$file"
