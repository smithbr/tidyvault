# Demo recording for the README. Render with: vhs docs/demo.tape   (brew install vhs)
# Runs in a scratch folder; needs copier (uv tool install copier) and python3 on PATH.
# gh:smithbr/tidyvault renders the latest release tag. To record unreleased changes, point that URL at a
# clone of the kit tagged above the latest release, for this process only:
#   GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.file://<clone>.insteadOf \
#   GIT_CONFIG_VALUE_0=https://github.com/smithbr/tidyvault.git vhs docs/demo.tape
Output docs/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 960
Set Height 540
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set Padding 16
Set Framerate 10

Hide
Type "cd $(mktemp -d) && clear"
Enter
Show

# --quiet: skip Copier's list of every file it writes.
Type "uvx copier copy --quiet gh:smithbr/tidyvault notes"
Enter
Sleep 3s

# Full name, then the suggestions that follow from it.
Type "Robin Vale"
Sleep 500ms
Enter
Sleep 1s
Enter
Sleep 1s
Enter
Sleep 1s
Enter
Sleep 1s

# The five optional parts: keep the defaults, then turn on backups (y answers without Enter).
Enter
Sleep 800ms
Enter
Sleep 800ms
Enter
Sleep 800ms
Enter
Sleep 800ms
Enter
Sleep 800ms
Type "y"
Sleep 4s

Type "cd notes && ls"
Enter
Sleep 2s

Type "python3 .scripts/vault-lint"
Enter
Sleep 3s
