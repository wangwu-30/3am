# 3am: Take the 3 AM Page

**让 AI 编码助手帮你处理凌晨三点的告警页面。**

## What This Skill Does

When handed a pile of production alerts (email exports, webhook JSON, log snippets), this skill produces a fixed-format **incident brief**:

- **Deduplicated alert counts** per rule/severity
- **Inferred "last known good" time** (when the system was healthy)
- **Escalation timeline** (when P2 became P1, when alerts started repeating)
- **Root-cause hypotheses** with cited evidence from alert content
- **READ-ONLY diagnostic commands** for next steps

## Guardrails

✅ **Evidence before conclusions** — All hypotheses must cite specific alert content  
✅ **Read-only operations only** — NEVER run write/mutating commands (no `kubectl delete`, `docker restart`, `systemctl stop`, etc.)  
✅ **Clear boundaries** — Explicitly state what CANNOT be determined from alerts alone  

## How to Use

### Step 1: Normalize the Alerts

First, convert the raw alert dump into a normalized timeline using the helper script:

```bash
# For JSONL files (one alert per line)
python3 skills/3am/normalize.py path/to/alerts.jsonl > normalized.json

# The script auto-detects:
# - Aliyun ARMS/CloudMonitor emails (Chinese text)
# - Prometheus Alertmanager webhooks
# - Grafana alert webhooks
```

The normalized output is token-efficient: 288 repetitive alerts → 1 compact timeline.

### Step 2: Analyze the Timeline

Read the normalized JSON and produce an **incident brief** with this structure:

```markdown
## Incident Brief

### Alert Summary
- Total alerts: N
- Unique rules: M
- Time range: YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM
- Last known good: YYYY-MM-DD HH:MM (inferred from first alert - <duration> ago)

### Escalation Timeline
| Time (UTC+8) | Event | Priority |
|-------------|-------|----------|
| 2026-10-09 05:31:13 | Alert "XXX" first fired | P2 |
| 2026-10-09 05:41:00 | Repeating every ~10min | P2 |
| 2026-10-10 03:31:58 | Escalated to P1 | P1 |

### Alert Details
1. **Rule Name** (P2, fired 120 times)
   - First: 2026-10-09 05:31:13
   - Last: 2026-10-10 08:24:09
   - Content: "证书自动化已超过26小时没有完成一次完整收敛"
   - Cluster: VPC-vpc-xxx-cn-north

2. **Rule Name 2** (P1, fired 45 times)
   - ...

### Root-Cause Hypotheses

1. **Certificate reconciler stuck** (HIGH confidence)
   - Evidence: Alert content mentions "26小时没有完成一次完整收敛"
   - Evidence: Last known convergence ≈ 2026-10-08 03:30 UTC+8
   - Evidence: P2→P1 escalation after 48 hours suggests persistent failure
   
2. **External dependency failure** (MEDIUM confidence)
   - Evidence: Alert suggests checking "公网探针结果" (public probe results)
   - Cannot determine: Specific probe failures not in alert content

### What We DON'T Know (requires investigation)
- Current reconciler phase/status
- HOLD reasons
- Renewal plan state
- Public probe actual results
- Recent config/code changes

### READ-ONLY Diagnostic Commands

⚠️ **Run these to gather more context. DO NOT run mutating operations yet.**

```bash
# Check reconciler current state
kubectl get certificates -n cert-namespace -o yaml

# View recent reconciler logs
kubectl logs -n cert-namespace deployment/cert-reconciler --tail=200

# Check probe results
curl -s https://probe-endpoint/status | jq .

# Review recent events
kubectl get events -n cert-namespace --sort-by='.lastTimestamp' | tail -20
```

### Recommended Next Steps
1. Verify reconciler is running: `kubectl get pods -n cert-namespace`
2. Check for recent HOLD events in reconciler logs
3. Compare current certificate state vs. expected renewal schedule
4. Investigate public probe failures if found
5. Only after analysis: consider safe remediation (reconciler restart, manual trigger)
```

### Step 3: Follow the Guardrails

- **Cite evidence**: Every hypothesis must reference specific alert fields (timestamp, content, cluster)
- **Read-only first**: Gather diagnostics before suggesting any fixes
- **Be explicit**: If something cannot be determined from alerts, say so clearly
- **No speculation**: Don't guess at root causes without evidence

## Example Session

**User**: "Here are 288 alerts from last night. What happened?"

**Agent**:
1. First, I'll normalize these alerts to see the pattern...
   ```bash
   python3 skills/3am/normalize.py alerts.jsonl > timeline.json
   ```

2. Reading the timeline... I see:
   - 288 alerts compressed to 2 unique rules
   - P2 "Certificate reconciler >26h" started 2026-10-09 05:31:13
   - Repeated every 10min for 144 times
   - Escalated to P1 ">48h" on 2026-10-10 03:31:58
   - No recovery notices

3. [Produces structured incident brief as shown above]

## Supported Alert Sources

- ✅ **Aliyun ARMS/CloudMonitor** (Chinese alert emails)
- ✅ **Prometheus Alertmanager** (webhook JSON)
- ✅ **Grafana Alerts** (webhook JSON)
- 🔜 **Tencent Cloud CLS** (coming soon)
- 🔜 **PagerDuty** (coming soon)
- 🔜 **Datadog** (coming soon)

## Files in This Skill

- `SKILL.md` — This instruction file
- `normalize.py` — Alert parser and deduplicator (zero dependencies, stdlib only)

## Installation

```bash
# For Claude Code / Codex / Cursor
npx skills add wangwu-30/3am

# Manual installation
git clone https://github.com/wangwu-30/3am.git
# Copy skills/3am/ to your skills directory
```

## License

MIT © wangwu-30, 2026
