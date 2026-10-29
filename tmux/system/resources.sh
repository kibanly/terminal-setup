#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Resources pane of the `system` session (Info tab), redrawn in place every 2 s:
#    header   host · uptime · load · CPUs
#    CPU RAM Swap GPU WSL-disk C:   bars (green / yellow ≥70% / red ≥90%)
#    Net      download / upload speed now, with a short history
#    Web      online?, latency to 1.1.1.1, interface and IP
#  GPU only when nvidia-smi exists (WSL ships it in /usr/lib/wsl/lib).
#  Never prints more lines than the pane has (no scrolling, no flicker).
# ═══════════════════════════════════════════════════════════════

C_TEXT=$'\e[38;2;205;214;244m' C_DIM=$'\e[38;2;108;112;134m' C_TRACK=$'\e[38;2;69;71;90m'
C_OK=$'\e[38;2;166;227;161m' C_WARN=$'\e[38;2;249;226;175m' C_BAD=$'\e[38;2;243;139;168m'
C_HEAD=$'\e[38;2;137;180;250m' C_DOWN=$'\e[38;2;137;220;235m' C_UP=$'\e[38;2;203;166;247m'
B=$'\e[1m' X=$'\e[0m'
SPARK=(▁ ▂ ▃ ▄ ▅ ▆ ▇ █)
NVSMI=$(command -v nvidia-smi || { [[ -x /usr/lib/wsl/lib/nvidia-smi ]] && echo /usr/lib/wsl/lib/nvidia-smi; })
IFACE=$(ip -o route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "dev") print $(i + 1)}')
IFACE=${IFACE:-eth0}

human() { numfmt --to=iec --suffix=B --format='%.1f' "$1" 2>/dev/null | sed 's/\.0B$/B/; s/B$//'; }

# bar <percent> <width>
bar() {
  local p=$1 w=$2 fill col full="" empty="" n
  (( fill = p * w / 100, fill > w ? fill = w : 0 ))
  col=$C_OK; (( p >= 70 )) && col=$C_WARN; (( p >= 90 )) && col=$C_BAD
  for (( n = 0; n < fill; n++ )); do full+="█"; done
  for (( n = fill; n < w; n++ )); do empty+="░"; done
  printf '%s%s%s%s%s' "$col" "$full" "$C_TRACK" "$empty" "$X"
}

# line <label> <percent> <text>  → one more entry in $out; the bar takes what the text
# leaves, so the line always fits the pane (a wrapped line would push the header away)
line() {
  local text=$3
  (( cols - 16 - ${#text} < 6 )) && text=""          # no room for "used / total": bar and % only
  local w=$(( cols - 16 - ${#text} )); (( w > 60 )) && w=60; (( w < 6 )) && w=6
  out+=("$(printf ' %s%-6s%s ' "$C_TEXT" "$1" "$X"; bar "$2" "$w"; printf ' %s%3d%%%s %s%s%s' "$C_TEXT" "$2" "$X" "$C_DIM" "$text" "$X")")
}

# spark <width> <values…> → the last <width> values as ▁▂▃…█ scaled to their maximum
spark() {
  local w=$1; shift
  local -a v=("$@"); local n=${#v[@]} max=1 s="" i
  (( n > w )) && v=("${v[@]: -w}")
  for i in "${v[@]}"; do (( i > max )) && max=$i; done
  for i in "${v[@]}"; do s+=${SPARK[ i * 7 / max ]}; done
  printf '%s' "$s"
}

# top-right "󰊓 zoom" / "󰊔 restore": tmux turns a click there into resize-pane -Z (~/.tmux.conf)
zoom_button() {
  local z; z=$(tmux display -p -t "${TMUX_PANE:-}" '#{window_zoomed_flag}' 2>/dev/null)
  if [[ $z == 1 ]]; then printf '\e[1;%dH\e[48;2;137;180;250m\e[38;2;17;17;27m\e[1m 󰊔 restore \e[0m' $(( cols - 10 ))
  else printf '\e[1;%dH\e[48;2;49;50;68m\e[38;2;166;173;200m 󰊓 zoom \e[0m' $(( cols - 7 ))
  fi
}

rate() { local r; r=$(human "$1"); [[ $r == *[0-9] ]] && r+="B"; printf '%s/s' "${r:-0B}"; }

read -r _ u n s i w q sq _ < /proc/stat; prev_total=$((u+n+s+i+w+q+sq)); prev_idle=$((i+w))
read -r prev_rx prev_tx < <(awk -v i="$IFACE:" '$1 == i { print $2, $10 }' /proc/net/dev)
prev_t=$(date +%s%N)
down=() upl=()
# cursor hidden, and no autowrap: a line too long for the pane is cut instead of
# wrapping onto the next row (which would push the header out of the pane)
printf '\e[?25l\e[?7l'; trap 'printf "\e[?25h\e[?7h"; exit' INT TERM EXIT
trap ':' WINCH                 # a resize (zoom / restore) redraws right away
first=1
while :; do
  cols=$(tput cols 2>/dev/null || echo 60); rows=$(tput lines 2>/dev/null || echo 9); out=()
  # CPU, memory, uptime, load
  read -r _ u n s i w q sq _ < /proc/stat; total=$((u+n+s+i+w+q+sq)); idle=$((i+w))
  dt=$(( total - prev_total )); cpu=0; (( dt > 0 )) && cpu=$(( 100 * (dt - (idle - prev_idle)) / dt ))
  prev_total=$total prev_idle=$idle
  while read -r k v _; do case $k in
    MemTotal:) mt=$v;; MemAvailable:) ma=$v;; SwapTotal:) st=$v;; SwapFree:) sf=$v;; esac; done < /proc/meminfo
  read -r up _ < /proc/uptime; up=${up%.*}
  read -r l1 l5 l15 _ < /proc/loadavg
  # network speed since the last round
  read -r rx tx < <(awk -v i="$IFACE:" '$1 == i { print $2, $10 }' /proc/net/dev)
  now=$(date +%s%N); ms=$(( (now - prev_t) / 1000000 )); (( ms < 1 )) && ms=1
  drate=$(( (rx - prev_rx) * 1000 / ms )) urate=$(( (tx - prev_tx) * 1000 / ms ))
  (( drate < 0 )) && drate=0; (( urate < 0 )) && urate=0
  prev_rx=$rx prev_tx=$tx prev_t=$now
  down+=("$drate"); upl+=("$urate"); (( ${#down[@]} > 120 )) && down=("${down[@]:1}") upl=("${upl[@]:1}")

  if (( cols >= 75 )); then       # leave room for the zoom button on the right
    out+=("$(printf ' %s%s󰍛 %s%s  %sup %dd %dh %dm · load %s %s %s · %d CPU%s' "$B" "$C_HEAD" "$(hostname)" "$X" \
      "$C_DIM" $((up/86400)) $((up%86400/3600)) $((up%3600/60)) "$l1" "$l5" "$l15" "$(nproc)" "$X")")
  elif (( cols >= 50 )); then
    out+=("$(printf ' %s%s󰍛 %s%s  %sup %dd %dh · load %s%s' "$B" "$C_HEAD" "$(hostname)" "$X" \
      "$C_DIM" $((up/86400)) $((up%86400/3600)) "$l1" "$X")")
  else                            # narrow: the host only (the zoom button needs the rest)
    out+=("$(printf ' %s%s󰍛 %s%s' "$B" "$C_HEAD" "$(hostname)" "$X")")
  fi
  (( first )) && cpu=0
  line "CPU" "$cpu" ""
  line "RAM" $(( (mt - ma) * 100 / mt )) "$(human $(( (mt - ma) * 1024 ))) / $(human $((mt*1024)))"
  if (( st > 0 )); then line "Swap" $(( (st - sf) * 100 / st )) "$(human $(( (st - sf) * 1024 ))) / $(human $((st*1024)))"; fi
  if [[ -n $NVSMI ]] && IFS=', ' read -r gu gm gt gtemp gpow < <("$NVSMI" --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits 2>/dev/null | head -1) && [[ $gu =~ ^[0-9]+$ ]]; then
    gpu_txt="$(human $(( gm * 1048576 ))) / $(human $(( gt * 1048576 )))"
    (( cols >= 50 )) && gpu_txt+=" · ${gtemp%.*}°C"
    (( cols >= 60 )) && gpu_txt+=" · ${gpow%.*}W"
    line "GPU" "$gu" "$gpu_txt"
  fi
  while read -r size used mnt; do
    [[ -z $size || $size == 0 ]] && continue
    label="WSL"; [[ $mnt == /mnt/c ]] && label="C:"
    line "$label" $(( used * 100 / size )) "$(human $used) / $(human $size)"
  done < <(df -B1 --output=size,used,target / /mnt/c 2>/dev/null | tail -n +2)
  # Net: ↓ speed + history · ↑ speed + history (history width fits the pane)
  sw=$(( (cols - 36) / 2 )); (( sw < 4 )) && sw=4; (( sw > 40 )) && sw=40
  out+=("$(printf ' %s%-6s%s %s↓ %-9s%s%s  %s↑ %-9s%s%s' "$C_TEXT" "Net" "$X" \
    "$C_DOWN" "$(rate "$drate")" "$(spark "$sw" "${down[@]}")" "$X" "$C_UP" "$(rate "$urate")" "$(spark "$sw" "${upl[@]}")" "$X")")
  # Web: are we online, and how far is the internet
  ip=$(ip -o -4 addr show "$IFACE" 2>/dev/null | awk '{print $4; exit}')
  if ping_out=$(ping -c1 -W1 -n 1.1.1.1 2>/dev/null) && lat=$(grep -o 'time=[0-9.]*' <<< "$ping_out" | cut -d= -f2); then
    lc=$C_OK; (( ${lat%.*} >= 100 )) && lc=$C_WARN; (( ${lat%.*} >= 300 )) && lc=$C_BAD
    # as much as fits: a wrapped line would push the header out of the pane
    if   (( cols >= 70 )); then tail_txt=" to 1.1.1.1 · $IFACE $ip"
    elif (( cols >= 50 )); then tail_txt=" to 1.1.1.1"
    else                        tail_txt=""
    fi
    web="$(printf '%s● online%s %s· %s%s ms%s %s%s' "$C_OK" "$X" "$C_DIM" "$lc" "${lat%.*}" "$X" "$C_DIM" "$tail_txt")"
  else
    if (( cols >= 70 )); then tail_txt=" · no answer from 1.1.1.1 · $IFACE ${ip:-no IP}"; else tail_txt=" · no answer"; fi
    web="$(printf '%s● offline%s %s%s' "$C_BAD" "$X" "$C_DIM" "$tail_txt")"
  fi
  out+=("$(printf ' %s%-6s%s %s%s' "$C_TEXT" "Web" "$X" "$web" "$X")")

  # never more lines than the pane has (a trailing newline would scroll the header away)
  printf '\e[H'
  for (( n = 0; n < ${#out[@]} && n < rows; n++ )); do
    (( n )) && printf '\n'
    printf '%s\e[K' "${out[n]}"
  done
  printf '\e[J'
  zoom_button
  first=0
  sleep 2 & wait $!; kill $! 2>/dev/null
done
