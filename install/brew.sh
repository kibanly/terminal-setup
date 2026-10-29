# ═══════════════════════════════════════════════════════════════
#  terminal-setup · packages on macOS, with Homebrew (install/Brewfile)
#  Homebrew itself is installed first when it is missing (it asks for your
#  password and installs Apple's Command Line Tools if needed).
# ═══════════════════════════════════════════════════════════════

brew_bin() {
  local p
  for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$p" ] && { echo "$p"; return; }; done
  command -v brew 2>/dev/null
}

brew_plan() {
  BREW=$(brew_bin)
  BREW_MISSING=""
  if [ -z "$BREW" ]; then
    BREW_MISSING="(everything in install/Brewfile)"
    return
  fi
  local name kind formulae casks
  formulae=" $("$BREW" list --formula -1 2>/dev/null | tr '\n' ' ') "
  casks=" $("$BREW" list --cask -1 2>/dev/null | tr '\n' ' ') "
  while read -r kind name _; do
    name=${name//\"/}
    case $kind in
      brew) [[ $formulae == *" $name "* ]] || BREW_MISSING="$BREW_MISSING $name" ;;
      cask) [[ $casks == *" $name "* ]] || BREW_MISSING="$BREW_MISSING $name" ;;
    esac
  done < <(grep -E '^(brew|cask) ' "$REPO/install/Brewfile" | sed 's/#.*//')
}

brew_show_plan() {
  [ -z "$BREW" ] && info "Homebrew: not installed → installed first (https://brew.sh)"
  if [ -n "$BREW_MISSING" ]; then info "brew install:$BREW_MISSING"; else ok "every Homebrew package is there"; fi
}

brew_install() {
  step "Homebrew packages"
  if [ -z "$BREW" ]; then
    run /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    BREW=$(brew_bin)
    [ -n "$BREW" ] || [ "${DRY_RUN:-0}" = 1 ] || die "Homebrew did not install: see the messages above"
    eval "$("${BREW:-/opt/homebrew/bin/brew}" shellenv 2>/dev/null)"
  fi
  [ -n "$BREW_MISSING" ] && run "${BREW:-brew}" bundle --file="$REPO/install/Brewfile"
  ok "Homebrew packages ready"
}
