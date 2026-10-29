# ═══════════════════════════════════════════════════════════════
#  terminal-setup · macOS. open, pbcopy / pbpaste and the ssh-agent (with the
#  keychain) come with the system, so there is little to add here.
# ═══════════════════════════════════════════════════════════════

# GNU ls colours for completion come from coreutils' gdircolors (see zshrc); eza
# covers ls itself. BSD tools that differ from Linux get their GNU name when present:
(( $+commands[gnumfmt] )) && alias numfmt=gnumfmt
