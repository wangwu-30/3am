# Example: Analyzing Real Production Alerts with 3am

This document shows how an AI coding agent uses the 3am skill to analyze 288 production alerts.

## Input

```bash
$ wc -l bench/fixtures/real/aliyun-arms-cert-alerts.jsonl
288 bench/fixtures/real/aliyun-arms-cert-alerts.jsonl

$ head -n 1 bench/fixtures/real/aliyun-arms-cert-alerts.jsonl | jq .
{
  "received_at_utc": "2026-10-08T21:31:22Z",
  "from": "monitor@monitor.cloud-provider.example",
  "to": "oncall@example.com",
  "subject": "生产证书自动化超过26小时未成功收敛",
  "body": "## 生产证书自动化超过26小时未成功收敛 ### 发生P2告警..."
}
```

288 alert emails, all in Chinese, mostly repetitive.

## Step 1: Normalize

```bash
$ python3 skills/3am/normalize.py bench/fixtures/real/aliyun-arms-cert-alerts.jsonl
```

**Output**: Compressed to 2 unique rules

```json
{
  "summary": {
    "total_alerts": 288,
    "unique_rules": 2,
    "last_known_good": "2026-10-09T05:31:13Z"
  },
  "timeline": [
    {
      "rule": "生产证书自动化超过26小时未成功收敛",
      "priority": "P2",
      "cluster": "VPC-vpc-xxxxxxxxxxxxxxxx-cn-north",
      "count": 210,
      "first_seen": "2026-10-09T05:31:13Z",
      "last_seen": "2026-10-09T05:31:13Z",
      "content": "生产证书自动化已超过26小时没有完成一次完整收敛；请检查当前 phase、HOLD 原因、续期计划和公网探针结果。",
      "source": "aliyun-arms"
    },
    {
      "rule": "生产证书自动化超过48小时未成功收敛",
      "priority": "P1",
      "cluster": "VPC-vpc-xxxxxxxxxxxxxxxx-cn-north",
      "count": 78,
      "first_seen": "2026-10-10T03:31:58Z",
      "last_seen": "2026-10-10T03:31:58Z",
      "content": "生产证书自动化已超过48小时没有完成签发确认、云端绑定、全部域名严格 TLS 与业务探针收敛；请按 P1 处理并检查当前 HOLD 原因。",
      "source": "aliyun-arms"
    }
  ]
}
```

## Step 2: AI Agent Analysis

**Prompt to AI**: "Using the 3am skill, analyze this timeline and produce an incident brief."

**AI Response**:

---

## Incident Brief

### Alert Summary
- **Total alerts**: 288
- **Unique rules**: 2
- **Time range**: 2026-10-08 21:31:22Z to 2026-10-10 08:24:09Z (~35 hours)
- **Last known good**: 2026-10-08 03:30 UTC+8 (inferred: 26 hours before first P2 alert)

### Escalation Timeline

| Time (UTC+8)        | Event                                                | Priority |
|---------------------|------------------------------------------------------|----------|
| 2026-10-09 05:31:13 | Alert "生产证书自动化超过26小时未成功收敛" first fired | P2       |
| 2026-10-09 05:41:00 | Repeating every ~10 minutes                          | P2       |
| 2026-10-10 03:31:58 | Escalated to "超过48小时未成功收敛"                     | P1       |
| 2026-10-10 08:24:09 | Last alert received (still firing)                   | P1       |

### Alert Details

#### 1. 生产证书自动化超过26小时未成功收敛 (P2)
- **Count**: 210 alerts
- **First seen**: 2026-10-09 05:31:13 UTC+8
- **Last seen**: 2026-10-09 05:31:13 UTC+8 (same timestamp - Aliyun ARMS reports original alert time)
- **Cluster**: VPC-vpc-xxxxxxxxxxxxxxxx-cn-north
- **Content**: "生产证书自动化已超过26小时没有完成一次完整收敛；请检查当前 phase、HOLD 原因、续期计划和公网探针结果。"

#### 2. 生产证书自动化超过48小时未成功收敛 (P1)
- **Count**: 78 alerts
- **First seen**: 2026-10-10 03:31:58 UTC+8
- **Last seen**: 2026-10-10 03:31:58 UTC+8
- **Cluster**: VPC-vpc-xxxxxxxxxxxxxxxx-cn-north
- **Content**: "生产证书自动化已超过48小时没有完成签发确认、云端绑定、全部域名严格 TLS 与业务探针收敛；请按 P1 处理并检查当前 HOLD 原因。"

### Root-Cause Hypotheses

#### 1. Certificate reconciler has stopped converging (HIGH confidence)
**Evidence**:
- Alert content explicitly states "26小时没有完成一次完整收敛" (26 hours without completing one full convergence)
- Last successful convergence: ~2026-10-08 03:30 UTC+8 (inferred from 26h lookback)
- P2→P1 escalation after 48 hours indicates persistent failure, not transient network issue
- No recovery alerts in the dataset

**Mechanism**:
The certificate automation reconciler appears to have entered a non-converging state, failing to complete the reconciliation loop for 48+ hours.

#### 2. Reconciler stuck in HOLD state (MEDIUM confidence)
**Evidence**:
- Both P2 and P1 alerts mention checking "HOLD 原因" (HOLD reason)
- Alert suggests checking "当前 phase" (current phase)
- This is a designed behavior: reconciler enters HOLD when dependencies are unmet

**Needs investigation**: Logs/state to determine specific HOLD reason

#### 3. External dependency failure (MEDIUM confidence)
**Evidence**:
- P2 alert mentions checking "公网探针结果" (public probe results)
- P1 alert mentions "全部域名严格 TLS 与业务探针收敛" (all domains strict TLS and business probe convergence)
- Suggests external validation/probing is part of convergence criteria

**Cannot determine from alerts**:
- Which specific probes are failing
- Whether probes themselves are broken or domains are actually failing TLS

#### 4. Certificate issuance/renewal pipeline blocked (MEDIUM confidence)
**Evidence**:
- P1 alert mentions "签发确认、云端绑定" (issuance confirmation, cloud binding)
- Alert mentions "续期计划" (renewal plan)
- Suggests multi-step pipeline: issue → confirm → bind → validate

**Cannot determine from alerts**:
- Whether CA (Certificate Authority) is responding
- Whether cloud API calls are failing
- Renewal schedule details

### What We DON'T Know (requires investigation)

These critical details are NOT in the alert content:

- ❌ Current reconciler phase/status
- ❌ Specific HOLD reason (dependency name, error message)
- ❌ Certificate renewal plan state (next renewal, pending certs)
- ❌ Public probe actual results (which domains, which checks)
- ❌ Recent configuration changes
- ❌ Recent code deployments
- ❌ Reconciler pod status (running, crash-looping, etc.)
- ❌ Resource constraints (CPU, memory, disk)
- ❌ CA API health and rate limits

### READ-ONLY Diagnostic Commands

⚠️ **Gather context first. DO NOT restart or mutate anything yet.**

```bash
# 1. Check if reconciler is running
kubectl get pods -n cert-namespace -l app=cert-reconciler -o wide

# 2. Check reconciler logs for HOLD events (last 48h context)
kubectl logs -n cert-namespace deployment/cert-reconciler --tail=500 | grep -i "hold\|error\|failed"

# 3. View current certificate resource state
kubectl get certificates -n cert-namespace -o yaml > /tmp/certs-state.yaml
cat /tmp/certs-state.yaml | grep -A 5 "status:"

# 4. Check for recent events
kubectl get events -n cert-namespace --sort-by='.lastTimestamp' | tail -50

# 5. Verify reconciler can reach external dependencies
kubectl exec -n cert-namespace deployment/cert-reconciler -- curl -v https://ca-api.example.com/health
kubectl exec -n cert-namespace deployment/cert-reconciler -- curl -v https://probe-endpoint.example.com/status

# 6. Check if renewal schedule is accessible
kubectl exec -n cert-namespace deployment/cert-reconciler -- cat /config/renewal-schedule.yaml

# 7. Look for resource constraints
kubectl top pods -n cert-namespace
kubectl describe pod -n cert-namespace <pod-name> | grep -A 10 "Conditions:"
```

### Recommended Next Steps

1. **Verify reconciler is alive**:
   - Check pod status and restart count
   - If crash-looping, examine logs for panic/OOM

2. **Find the HOLD reason** (most likely root cause):
   - Search logs for "HOLD" events in the 48h window
   - Common HOLD reasons: CA API down, DNS propagation timeout, rate limit hit

3. **Check external dependencies**:
   - CA API health and rate limits
   - DNS propagation for domains requiring certificates
   - Cloud API (for certificate binding)

4. **Review recent changes**:
   - Config changes to renewal schedule
   - Code deployments to reconciler
   - Network policy or firewall changes blocking CA access

5. **Only after diagnosis, consider safe remediation**:
   - If HOLD is due to transient external issue: manual reconcile trigger
   - If reconciler is deadlocked: restart pod
   - If config is wrong: fix and redeploy
   - If CA rate-limited: wait or request increase

### Incident Severity Assessment

- **Priority**: P1 (per alert escalation)
- **Impact**: Certificate automation stuck for 48h
- **Risk**: Certificates may expire if not resolved before renewal deadline
- **Urgency**: High - investigate immediately, but gather diagnostics before acting

---

## Compression Stats

```bash
$ python3 bench/run_bench.py

🎯 Key Result: 99.3% token reduction
   (288 alerts → 1 page: 30,762 → 207 tokens)
```

The skill compressed 288 repetitive alerts into a 2-rule timeline, making it feasible for an AI agent to reason about the incident within its context window.

---

**Generated by 3am v0.1** | MIT © wangwu-30, 2026
