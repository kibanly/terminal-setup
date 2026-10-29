#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  terminal-setup · installer
#  Ubuntu 24.04 / 26.04 (also in WSL) and macOS. Run it again at any time: it only
#  does what is still missing.
#
#    ./install.sh              shows the plan, asks, installs
#    ./install.sh --yes        no questions
#    ./install.sh --dry-run    only shows what it would do
#    ./install.sh --links-only only (re)links the config files (no packages, font, plugins)
#
#  1. packages (apt / Homebrew) that are missing, at the versions the setup needs
#  2. the Nerd Font
#  3. links: ~/.zshrc, ~/.tmux, ~/.tmux.conf… point into this repo (what was there
#     before goes to ~/.terminal-setup-backup/<date>/; ./uninstall.sh puts it back)
#  4. tmux and zsh plugins (install/plugins.lock)
#  5. zsh as your login shell
#  6. a final check (install/doctor.sh)
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
USER=${USER:-$(id -un)}                    # not set in some containers
# shellcheck source=install/lib.sh
. "$REPO/install/lib.sh"
. "$REPO/install/versions.sh"
. "$REPO/install/fonts.sh"
. "$REPO/install/plugins.sh"

ASSUME_YES=0 DRY_RUN=0 LINKS_ONLY=0
for arg in "$@"; do
  case $arg in
    -y|--yes)     ASSUME_YES=1 ;;
    -n|--dry-run) DRY_RUN=1 ;;
    --links-only) LINKS_ONLY=1 ;;
    -h|--help)    sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            die "unknown option: $arg (see ./install.sh --help)" ;;
  esac
done
BACKUP_DIR="$HOME/.terminal-setup-backup/$(date +%Y%m%d-%H%M%S)"

# what goes where: <file in the repo> <link in your home>
LINKS="
zsh/zshrc                  .zshrc
zsh/aliases.zsh            .zsh_aliases
zsh/functions.zsh          .zsh_functions
tmux                       .tmux
tmux/tmux.conf             .tmux.conf
config/starship.toml       .config/starship.toml
config/btop/btop.conf      .config/btop/btop.conf
config/micro/settings.json .config/micro/settings.json
"
# what lives inside an existing ~/.tmux and is yours (not in the repo): carried over into
# the linked one · the plugins too, so the versions you have are kept
TMUX_USER_DATA="plugins logs descriptions.tsv"

link_all() {
  step "Config files (links into the repo)"
  local src dst old
  while read -r src dst; do
    [ -n "$src" ] || continue
    if [ "$dst" = .tmux ] && [ -d "$HOME/.tmux" ] && [ ! -L "$HOME/.tmux" ]; then
      old=$HOME/.tmux
      link "$REPO/$src" "$HOME/$dst"
      # logs, session descriptions… from the old ~/.tmux (now in the backup) come along
      local item
      for item in $TMUX_USER_DATA; do
        if [ -e "$BACKUP_DIR/.tmux/$item" ] && [ ! -e "$REPO/tmux/$item" ]; then
          run cp -R "$BACKUP_DIR/.tmux/$item" "$REPO/tmux/$item"
          info "${D}kept your $(tilde "$old")/$item${R}"
        fi
      done
      continue
    fi
    link "$REPO/$src" "$HOME/$dst"
  done <<< "$LINKS"
}

login_shell_zsh() {
  local zsh_path current
  zsh_path=$(command -v zsh || true)
  [ -n "$zsh_path" ] || { warn "zsh is not installed: skipped"; return; }
  if [ "$OS" = macos ]; then
    current=$(dscl . -read "/Users/$USER" UserShell 2>/dev/null | awk '{print $2}')
  else
    current=$(getent passwd "$USER" | cut -d: -f7)
  fi
  case $current in */zsh) ok "zsh is already your login shell"; return ;; esac
  step "Login shell"
  if ask "Make zsh your login shell? (now: ${current:-unknown})"; then
    grep -qx "$zsh_path" /etc/shells || as_root sh -c "echo '$zsh_path' >> /etc/shells"
    as_root chsh -s "$zsh_path" "$USER" || warn "chsh failed: run  chsh -s $zsh_path  yourself"
    ok "zsh from the next login"
  fi
}

# ─── plan ───
detect_platform
printf '\n%sterminal-setup%s · %s · %s\n' "$B" "$R" "$OS_NAME" "$ARCH"
printf '%s%s%s\n' "$D" "repo: $(tilde "$REPO")" "$R"
[ "$DRY_RUN" = 1 ] && printf '%s(dry run: nothing is changed)%s\n' "$YELLOW" "$R"

case "$OS:$OS_VERSION" in
  ubuntu:24.04|ubuntu:26.04|macos:*) ;;
  ubuntu:*) warn "Ubuntu $OS_VERSION is not tested (24.04 and 26.04 are): going on with apt" ;;
  *)        [ "$LINKS_ONLY" = 1 ] || die "$OS_NAME is not supported (Ubuntu 24.04 / 26.04, WSL, macOS). ./install.sh --links-only links the config anyway." ;;
esac

if [ "$LINKS_ONLY" = 0 ]; then
  step "Plan"
  if [ "$OS" = macos ]; then
    . "$REPO/install/brew.sh"; brew_plan; brew_show_plan
  else
    . "$REPO/install/apt.sh"; apt_plan; apt_show_plan
  fi
  font_plan; font_show_plan
  plugins_plan; plugins_show_plan
fi
info "links: ~/.zshrc ~/.zsh_aliases ~/.zsh_functions ~/.tmux ~/.tmux.conf"
info "       ~/.config/starship.toml ~/.config/btop/btop.conf ~/.config/micro/settings.json"
info "${D}(whatever is there now is kept in $(tilde "$BACKUP_DIR"))${R}"

ask "Go ahead?" || { info "nothing changed"; exit 0; }

# ─── do it ───
if [ "$LINKS_ONLY" = 0 ]; then
  if [ "$OS" = macos ]; then brew_install; else apt_install; fi
  font_install
fi
link_all
[ "$LINKS_ONLY" = 0 ] && plugins_install
[ "$LINKS_ONLY" = 0 ] && login_shell_zsh

# a running tmux picks up the new config
if [ "$DRY_RUN" = 0 ] && tmux info >/dev/null 2>&1; then
  tmux source-file "$HOME/.tmux.conf" >/dev/null 2>&1 && ok "the running tmux reloaded its config"
fi

if [ "$DRY_RUN" = 0 ]; then
  step "Check"
  bash "$REPO/install/doctor.sh" || true
fi

[ "${FONT_TODO:-}" = windows ] && font_windows_steps
[ -d "$BACKUP_DIR" ] && printf '\n    Your previous files: %s · ./uninstall.sh puts them back\n' "$(tilde "$BACKUP_DIR")"
cat <<EOF

    ${B}Done.${R} Open a new terminal (or run: exec zsh). tmux starts by itself in the
    system monitor; Ctrl+a ? shows every shortcut, Ctrl+a Space the quick menu.

EOF
