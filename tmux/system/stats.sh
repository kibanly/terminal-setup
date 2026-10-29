#!/usr/bin/env bash
# CPU and RAM for the tmux status bar (#(…), every status-interval seconds).
# CPU is the average since the previous call, kept in a small cache file.
cache=${XDG_RUNTIME_DIR:-/tmp}/tmux-cpu-$UID
read -r _ u n s i w q sq _ < /proc/stat; total=$((u+n+s+i+w+q+sq)); idle=$((i+w))
cpu=0
if [[ -r $cache ]] && read -r pt pi < "$cache" && (( total > pt )); then
  cpu=$(( 100 * ((total - pt) - (idle - pi)) / (total - pt) ))
fi
echo "$total $idle" > "$cache"
while read -r k v _; do case $k in MemTotal:) mt=$v;; MemAvailable:) ma=$v;; esac; done < /proc/meminfo
mem=$(( (mt - ma) * 100 / mt ))
colour() { if (( $1 >= 90 )); then echo '#f38ba8'; elif (( $1 >= 70 )); then echo '#f9e2af'; else echo '#a6adc8'; fi; }
used=$(awk -v k=$(( mt - ma )) 'BEGIN { printf "%.1fG", k/1048576 }')
printf '#[fg=%s]󰍛 %d%%  #[fg=%s]󰘚 %s' "$(colour $cpu)" "$cpu" "$(colour $mem)" "$used"
