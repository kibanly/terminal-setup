#!/usr/bin/env bash
# Info pane of the `system` session: fastfetch, laid out to fit the pane (it never wraps):
#   wide enough → the big Ubuntu drawing next to the info · narrower → the small one
#   tall and narrow → the drawing on top · tiny → info only.
# Redrawn when the pane changes size and every 5 minutes.
CONF="$(dirname "$0")/fastfetch.jsonc"     # what to show (modules, disks)
# Drawn on the alternate screen (like btop or less): redraws replace the picture instead of
# piling copies of it up in the pane's scrollback.
[[ -n $TMUX_PANE ]] && tmux clear-history -t "$TMUX_PANE"
printf '\e[?1049h\e[?25l'
trap 'printf "\e[?25h\e[?1049l"; exit' INT TERM
trap ':' WINCH
last=""
while :; do
  cols=$(tput cols) rows=$(tput lines)
  if [[ "$cols $rows" == "$last" ]] && (( SECONDS - drawn < 300 )); then   # a WINCH without a real resize
    sleep 300 & wait $!; kill $! 2>/dev/null; continue
  fi
  last="$cols $rows" drawn=$SECONDS
  if   (( cols >= 110 && rows >= 22 )); then logo=()
  elif (( cols >= 86  && rows >= 18 )); then logo=(--logo ubuntu_small)
  elif (( cols >= 62  && rows >= 38 )); then logo=(--logo-position top)
  else                                       logo=(--logo none)
  fi
  printf '\e[H\e[2J'
  if (( ${#logo[@]} )) && [[ ${logo[*]} != "--logo ubuntu_small" ]]; then
    # drawing on top / no drawing: plain lines, cut to the pane so nothing wraps
    fastfetch --pipe false -c "$CONF" "${logo[@]}" 2>/dev/null | head -n "$rows" | python3 -I -c '
import sys; sys.path.insert(0, sys.argv[2]); from tui import cut
sys.stdout.write("\n".join(cut(l.rstrip("\n"), int(sys.argv[1])) + "\x1b[0m" for l in sys.stdin))' "$cols" "$(dirname "$0")/.."
  else
    fastfetch --pipe false -c "$CONF" "${logo[@]}" 2>/dev/null | head -n "$rows"
  fi
  # top-right "󰊓 zoom" / "󰊔 restore" (a click there zooms: see MouseDown1Pane in ~/.tmux.conf)
  if [[ $(tmux display -p -t "${TMUX_PANE:-}" '#{window_zoomed_flag}' 2>/dev/null) == 1 ]]; then
    printf '\e[1;%dH\e[48;2;137;180;250m\e[38;2;17;17;27m\e[1m 󰊔 restore \e[0m' $(( cols - 10 ))
  else
    printf '\e[1;%dH\e[48;2;49;50;68m\e[38;2;166;173;200m 󰊓 zoom \e[0m' $(( cols - 7 ))
  fi
  sleep 300 & wait $!          # a resize (WINCH) interrupts the wait and redraws
  kill $! 2>/dev/null
done
