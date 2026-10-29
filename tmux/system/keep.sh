#!/usr/bin/env bash
# Runs a pane of the `system` session and, if it is closed (q in btop, Ctrl+c…),
# offers to start it again instead of leaving a hole in the layout.
while :; do
  "$@"
  printf '\n\e[38;2;108;112;134m  %s closed · Enter starts it again · Ctrl+a x closes this pane\e[0m' "${1##*/}"
  read -rs
  clear
done
