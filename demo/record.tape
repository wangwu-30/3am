# VHS tape for recording 3am demo
# Run with: vhs demo/record.tape

Output demo/3am-demo.gif

Set FontSize 14
Set Width 1200
Set Height 800
Set Theme "Catppuccin Mocha"

Type "# 3am Demo: From 288 alerts to 1 page" Sleep 1s Enter Sleep 1s

Type "# Step 1: Check the raw alerts" Sleep 500ms Enter
Type "wc -l bench/fixtures/real/aliyun-arms-cert-alerts.jsonl" Sleep 500ms Enter
Sleep 2s

Type "head -n 3 bench/fixtures/real/aliyun-arms-cert-alerts.jsonl | jq ." Sleep 500ms Enter
Sleep 4s

Type "# 288 emails, all Chinese, mostly duplicates... 😵" Sleep 2s Enter Sleep 1s

Type "# Step 2: Normalize with 3am" Sleep 500ms Enter
Type "python3 skills/3am/normalize.py bench/fixtures/real/aliyun-arms-cert-alerts.jsonl | jq ." Sleep 500ms Enter
Sleep 6s

Type "# Step 3: Check the compression" Sleep 500ms Enter
Type "python3 bench/run_bench.py" Sleep 500ms Enter
Sleep 5s

Type "# 99.3% token reduction! 🎉" Sleep 2s Enter Sleep 1s
Type "# Now your AI can reason about this without context overflow" Sleep 2s Enter
Sleep 2s
