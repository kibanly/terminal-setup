# ═══════════════════════════════════════════════════════════════
#  terminal-setup · the Nerd Font ("JetBrainsMono Nerd Font"): the icons of the
#  prompt, the tmux bar and the panels are drawn with it. It must be installed
#  where the terminal window is drawn:
#    macOS            the Brewfile installs it (cask font-jetbrains-mono-nerd-font)
#    Linux desktop    ~/.local/share/fonts (downloaded from the Nerd Fonts release)
#    WSL              in Windows: checked, and explained when it is missing
#    server over SSH  on the computer you connect from: nothing to do here
# ═══════════════════════════════════════════════════════════════

font_present_linux() { fc-list 2>/dev/null | grep -qi "JetBrainsMono Nerd Font"; }

font_present_windows() {
  local d
  for d in /mnt/c/Windows/Fonts /mnt/c/Users/*/AppData/Local/Microsoft/Windows/Fonts; do
    ls "$d" 2>/dev/null | grep -qi "JetBrainsMonoNerdFont" && return 0
  done
  return 1
}

font_plan() {
  FONT_TODO=none
  case "$OS:$IS_WSL" in
    macos:*) ;;                                    # Brewfile
    *:1)     font_present_windows || FONT_TODO=windows ;;
    *)       if [ "$HAS_DESKTOP" = 1 ]; then font_present_linux || FONT_TODO=linux; else FONT_TODO=remote; fi ;;
  esac
}

font_show_plan() {
  case $FONT_TODO in
    linux)   info "font: JetBrainsMono Nerd Font $NERD_FONT_VERSION → ~/.local/share/fonts" ;;
    windows) info "font: JetBrainsMono Nerd Font is missing in Windows → steps at the end" ;;
    remote)  info "font: no desktop here → install it on the computer you connect from" ;;
    none)    ok "font: JetBrainsMono Nerd Font is there" ;;
  esac
}

font_install() {
  [ "$FONT_TODO" = linux ] || return 0
  step "JetBrainsMono Nerd Font"
  local tmp
  tmp=$(mktemp -d)
  run curl -fsSL -o "$tmp/font.zip" \
    "https://github.com/ryanoasis/nerd-fonts/releases/download/$NERD_FONT_VERSION/$NERD_FONT.zip"
  run mkdir -p ~/.local/share/fonts/JetBrainsMonoNerdFont
  run unzip -oq "$tmp/font.zip" '*.ttf' -d ~/.local/share/fonts/JetBrainsMonoNerdFont
  run fc-cache -f >/dev/null
  rm -rf "$tmp"
  ok "installed · choose \"JetBrainsMono Nerd Font\" in your terminal's settings"
}

# the steps for Windows, shown at the end of the install
font_windows_steps() {
  cat <<EOF

    ${B}The font goes in Windows${R} (Windows Terminal draws the text). In PowerShell:

        winget install --id DEVCOM.JetBrainsMonoNerdFont

    or download https://github.com/ryanoasis/nerd-fonts/releases/download/$NERD_FONT_VERSION/$NERD_FONT.zip,
    unzip it, select the .ttf files › right-click › Install for all users.
    Then in Windows Terminal: Settings › your Ubuntu profile › Appearance ›
    Font face: ${B}JetBrainsMono Nerd Font${R} (more in windows/windows-terminal.md).
EOF
}
