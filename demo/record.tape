# VHS tape for recording 3am demo
# Run with: vhs demo/record.tape

Output demo/3am-demo.gif

Set FontSize 15
Set Width 1200
Set Height 700
Set Theme "Dracula"
Set TypingSpeed 30ms

# 0-3s: Show the alert wall (pain!)
Type "# 3am: 288 alerts at 3 AM 😵" Sleep 500ms Enter
Sleep 800ms
Type "head -n 30 bench/fixtures/real/aliyun-arms-cert-alerts.jsonl | jq -c .subject" Enter
Sleep 2500ms

# 3-6s: Run the magic command
Type "clear" Enter
Sleep 300ms
Type "# Turn the chaos into clarity:" Sleep 300ms Enter
Sleep 500ms
Type "python3 skills/3am/normalize.py bench/fixtures/real/aliyun-arms-cert-alerts.jsonl | python3 skills/3am/brief.py -" Enter

# 6-20s: Show the beautiful brief and let it stay
Sleep 14s
