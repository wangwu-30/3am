# Real Production Data (Redacted)

## aliyun-arms-cert-alerts.jsonl

- **Source**: Aliyun ARMS production monitoring
- **Incident**: Certificate reconciler convergence failure
- **Duration**: 2026-10-08 to 2026-10-10
- **Alert count**: 288 emails (deduplicated to 2 unique rules)
- **Severity escalation**: P2 (>26h) → P1 (>48h)
- **Status**: Owner-approved and fully redacted (no sensitive data)

### Expected Findings

When analyzed by the 3am skill, the incident brief should show:

- **Last known good**: ≈ 2026-10-08 03:30 UTC+8 (26 hours before first P2 alert)
- **First alert**: 2026-10-09 05:31:13 UTC+8 (P2 severity)
- **Escalation**: 2026-10-10 03:31:58 UTC+8 (P1 severity, 48 hours after last convergence)
- **Alert frequency**: ~10 minutes (typical ARMS re-notification interval)
- **Recovery**: None observed in this dataset

### Data Privacy

All sensitive information has been redacted:
- Internal domain names → `example.com`
- VPC IDs → `vpc-xxxxxxxxxxxxxxxx`
- Console URLs → `console.example.com`
- Email addresses → `oncall@example.com`, `monitor@monitor.cloud-provider.example`

The alert structure, timing, and Chinese content are preserved to test real-world parsing.
