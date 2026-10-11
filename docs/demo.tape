# Demo recording for the README. Render with: vhs docs/demo.tape   (brew install vhs)
# Runs in a scratch folder; needs copier (uv tool install copier) and python3 on PATH.
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

Type "uvx copier copy --defaults -d owner=Robin -d 'owner_full=Robin Vale' -d vault=notes gh:smithbr/tidyvault notes"
Enter
Sleep 4s

Type "cd notes && git init -q && git add -A && git commit -qm 'New vault from tidyvault' && python3 .scripts/vault-lint"
Enter
Sleep 3s

Type "printf -- '---\nkind: task\n---\nCall Northwind Dental to book the cleaning before the trip\n' > _captures/capture-1.md && ls _captures"
Enter
Sleep 2s

Type "python3 .scripts/import-files inventory"
Enter
Sleep 3s

Type "python3 .scripts/vault-lint --review --days 7 | head -30"
Enter
Sleep 4s
