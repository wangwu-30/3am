# VHS tape for recording 3am demo
# Run with: vhs demo/record.tape

Output demo/3am-demo.gif

Set FontSize 13
Set Width 1100
Set Height 650
Set Theme "Dracula"
Set TypingSpeed 50ms

Type "# 3am: Let your AI take the 3 AM page" Sleep 800ms Enter
Sleep 1s

Type "echo 'Step 1: 288 alert emails...'" Sleep 300ms Enter
Sleep 800ms

Type "head -n 5 bench/fixtures/real/aliyun-arms-cert-alerts.jsonl | jq -c '{subject, time: .received_at_utc}'" Sleep 300ms Enter
Sleep 3s

Type "echo '...288 alerts, mostly duplicates 😵'" Sleep 300ms Enter
Sleep 1s

Type "echo ''" Enter
Type "echo 'Step 2: Normalize with 3am'" Sleep 300ms Enter
Sleep 800ms

Type "python3 skills/3am/normalize.py bench/fixtures/real/aliyun-arms-cert-alerts.jsonl | jq -c '.summary'" Sleep 300ms Enter
Sleep 3s

Type "echo ''" Enter
Type "echo 'Step 3: The headline insight ✨'" Sleep 300ms Enter
Sleep 800ms

Type "python3 skills/3am/normalize.py bench/fixtures/real/aliyun-arms-cert-alerts.jsonl | jq -r '.summary.last_known_good_evidence[]'" Sleep 300ms Enter
Sleep 4s

Type "echo ''" Enter
Type "echo '✅ Last known good ≈ 2026-10-08 03:31 +08:00'" Sleep 500ms Enter
Sleep 1s
Type "echo '✅ Two rules agree within 45s!'" Sleep 500ms Enter
Sleep 1s

Type "echo ''" Enter
Type "echo '🎯 99% token reduction (30,762 → 320 tokens)'" Sleep 500ms Enter
Sleep 2s
