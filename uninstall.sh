#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  terminal-setup · undo the install
#    ./uninstall.sh            removes the links into this repo and puts back what
#                              was there before (the newest ~/.terminal-setup-backup/…)
#    ./uninstall.sh <backup>   puts back that backup instead
#  Packages, the font and the plugins stay installed (other things may use them).
#  Your data inside the linked ~/.tmux (logs, session descriptions) is copied into
#  the ~/.tmux that comes back, so nothing is lost.
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
. "$REPO/install/lib.sh"
ASSUME_YES=0

BACKUP=${1:-$(ls -d "$HOME"/.terminal-setup-backup/*/ 2>/dev/null | sort | tail -1)}
BACKUP=${BACKUP%/}

printf '\n%sterminal-setup · uninstall%s\n' "$B" "$R"
step "Plan"
links=""
for f in .zshrc .zsh_aliases .zsh_functions .tmux .tmux.conf .config/starship.toml .config/btop/btop.conf \
         .config/micro/settings.json; do
  case $(readlink "$HOME/$f" 2>/dev/null || true) in "$REPO"/*) links="$links $f" ;; esac
done
[ -n "$links" ] && info "remove the links:$(printf ' ~/%s' $links)" || ok "no links into this repo"
if [ -n "$BACKUP" ] && [ -f "$BACKUP/MANIFEST" ]; then
  info "put back from $(tilde "$BACKUP"): $(tr '\n' ' ' < "$BACKUP/MANIFEST")"
else
  warn "no backup to put back: you will have no ~/.zshrc, ~/.tmux.conf… until you make new ones"
fi
ask "Go ahead?" || { info "nothing changed"; exit 0; }

step "Uninstall"
for f in $links; do
  rm "$HOME/$f"
  ok "removed ~/$f"
done
if [ -n "$BACKUP" ] && [ -f "$BACKUP/MANIFEST" ]; then
  while read -r rel; do
    [ -e "$BACKUP/$rel" ] || [ -L "$BACKUP/$rel" ] || continue
    if [ -e "$HOME/$rel" ] || [ -L "$HOME/$rel" ]; then
      warn "~/$rel exists now: left as is (the old one stays in the backup)"
      continue
    fi
    mkdir -p "$(dirname "$HOME/$rel")"
    mv "$BACKUP/$rel" "$HOME/$rel"
    ok "put back ~/$rel"
  done < "$BACKUP/MANIFEST"
fi
# logs and session descriptions written while the setup was installed
if [ -d "$HOME/.tmux" ] && [ ! -L "$HOME/.tmux" ]; then
  for item in logs descriptions.tsv; do
    [ -e "$REPO/tmux/$item" ] && cp -R "$REPO/tmux/$item" "$HOME/.tmux/" && ok "kept ~/.tmux/$item"
  done
fi
tmux info >/dev/null 2>&1 && [ -f "$HOME/.tmux.conf" ] && tmux source-file "$HOME/.tmux.conf" >/dev/null 2>&1 || true
printf '\n    Done. Open a new terminal to use the previous config.\n\n'
