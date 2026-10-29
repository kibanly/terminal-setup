# ═══════════════════════════════════════════════════════════════
#  terminal-setup · Linux (Ubuntu). Also loaded by wsl.zsh.
# ═══════════════════════════════════════════════════════════════

# open a file, folder or URL with the desktop's app (Ubuntu's own `open` is openvt)
open() { ~/.tmux/system/open.sh "${1:-.}" }

# pbcopy / pbpaste like on macOS, when a clipboard tool is there (Wayland, else X11)
if (( $+commands[wl-copy] )); then
  alias pbcopy='wl-copy'
  alias pbpaste='wl-paste --no-newline'
elif (( $+commands[xclip] )); then
  alias pbcopy='xclip -selection clipboard'
  alias pbpaste='xclip -selection clipboard -o'
fi

# Shared ssh-agent on a fixed socket: one agent for every terminal, keys expire after 8h.
# (A desktop session may already run one: then it is kept.)
if [[ -z $SSH_AUTH_SOCK || $SSH_AUTH_SOCK == $HOME/.ssh/agent.sock ]]; then
  export SSH_AUTH_SOCK="$HOME/.ssh/agent.sock"
  ssh-add -l >/dev/null 2>&1
  if (( $? == 2 )); then
    mkdir -p ~/.ssh && rm -f "$SSH_AUTH_SOCK"
    eval "$(ssh-agent -t 8h -a "$SSH_AUTH_SOCK")" >/dev/null
  fi
fi
