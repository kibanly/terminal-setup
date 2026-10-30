#!/usr/bin/env bash
# Runs a pane of the `system` session and, if it is closed (q in btop, Ctrl+c…),
# offers to start it again instead of leaving a hole in the layout.
while :; do
  "$@"
  # its pid, noted for tmux to wake it (tmuxlink.note_wake), must not reach another process
  [[ -n $TMUX_PANE ]] && tmux set -pu -t "$TMUX_PANE" @wake 2>/dev/null
  name=${*: -1}; name=${name##*/}         # the program: python3 -I …/procs.py → procs.py
  printf '\n\e[38;2;108;112;134m  %s closed · Enter starts it again\e[0m' "$name"
  read -rs
  clear
done
