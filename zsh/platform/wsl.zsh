# ═══════════════════════════════════════════════════════════════
#  terminal-setup · WSL: Linux plus the Windows integration.
#  Windows apps are called by their full path: they are not on $PATH when
#  /etc/wsl.conf has appendWindowsPath=false (keeps the shell fast).
# ═══════════════════════════════════════════════════════════════

source "${0:A:h}/linux.zsh"       # open (→ Windows Explorer / browser here), clipboard, ssh-agent

# a terminal opened from Windows may start in /mnt/c/…: home is nicer (and much faster)
[[ $PWD == /mnt/c/* ]] && cd ~
