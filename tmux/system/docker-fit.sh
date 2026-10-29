#!/usr/bin/env bash
# window-resized hook of the docker tab (and run once when it is built): the Containers
# list keeps 38% of the height, never under 8 rows (title, column titles, a few
# containers and the detail line) while Container + Logs below keep 8 too.
# tmux alone takes the rows a smaller window loses from the top pane first, which left
# Containers with 2 rows in a small terminal.
# docker-fit.sh <containers pane>
cont=$1
H=$(tmux display -p -t "$cont" '#{window_height}' 2>/dev/null) || exit 0
want=$(( H * 38 / 100 ))
(( want < 8 )) && want=8
(( want > H - 9 )) && want=$(( H - 9 ))
(( want >= 3 )) && tmux resize-pane -t "$cont" -y "$want" 2>/dev/null
exit 0
