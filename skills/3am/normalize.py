#!/usr/bin/env python3
"""
3am Alert Normalizer - Convert messy alerts into a compact timeline.

Supports:
- Aliyun ARMS/CloudMonitor alert emails (Chinese text)
- Prometheus Alertmanager webhook JSON
- Grafana alert webhook JSON
"""

import json
import sys
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple

# UTC+8 timezone for Aliyun alerts
UTC_PLUS_8 = timezone(timedelta(hours=8))


def extract_threshold_hours(rule_name: str, content: str) -> Optional[int]:
    """
    Extract threshold hours from rule name or content.
    
    Examples:
    - "超过26小时未成功收敛" -> 26
    - ">48h without convergence" -> 48
    - "for >2h" -> 2
    """
    text = rule_name + ' ' + content
    
    # Chinese patterns: 超过N小时, >N小时, >=N小时
    cn_match = re.search(r'(?:超过|[>>=]+)\s*(\d+)\s*(?:小时|h)', text)
    if cn_match:
        return int(cn_match.group(1))
    
    # English patterns: >Nh, for Nh, >N hours, >=N hours
    en_match = re.search(r'[>>=]+\s*(\d+)\s*h(?:ours?)?', text, re.IGNORECASE)
    if en_match:
        return int(en_match.group(1))
    
    # "for N hours/h"
    for_match = re.search(r'for\s+(\d+)\s*h(?:ours?)?', text, re.IGNORECASE)
    if for_match:
        return int(for_match.group(1))
    
    return None


def parse_aliyun_arms_email(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Aliyun ARMS alert email format."""
    body = alert.get('body', '')
    
    # Extract priority (P1/P2/P3/P4)
    priority_match = re.search(r'发生(P\d)告警', body)
    priority = priority_match.group(1) if priority_match else 'P3'
    
    # Extract alert name
    name_match = re.search(r'告警名称：(.+?)(?:集群名称|通知策略|告警时间|$)', body)
    alert_name = name_match.group(1).strip() if name_match else alert.get('subject', 'Unknown')
    
    # Extract cluster name
    cluster_match = re.search(r'集群名称：(.+?)(?:通知策略|告警时间|$)', body)
    cluster = cluster_match.group(1).strip() if cluster_match else None
    
    # Extract alert time (use the time from alert content, or fallback to received time)
    time_match = re.search(r'告警时间：(.+?)(?:告警内容|$)', body)
    if time_match:
        alert_time_str = time_match.group(1).strip()
        # Parse format like "2026-10-09 05:31:13" (UTC+8 local time)
        try:
            # Parse as naive datetime, then localize to UTC+8
            alert_time_local = datetime.strptime(alert_time_str, '%Y-%m-%d %H:%M:%S')
            alert_time_utc8 = alert_time_local.replace(tzinfo=UTC_PLUS_8)
            # Convert to UTC for internal storage
            alert_time_utc = alert_time_utc8.astimezone(timezone.utc)
            timestamp = alert_time_utc.isoformat()
        except:
            timestamp = alert.get('received_at_utc')
    else:
        timestamp = alert.get('received_at_utc')
    
    # Extract alert content
    content_match = re.search(r'告警内容：\s*(.+?)(?:\[详情链接\]|$)', body, re.DOTALL)
    content = content_match.group(1).strip() if content_match else ''
    
    # Extract threshold for last-known-good inference
    threshold_hours = extract_threshold_hours(alert_name, content)
    
    return {
        'timestamp': timestamp,
        'priority': priority,
        'rule': alert_name,
        'cluster': cluster,
        'content': content,
        'source': 'aliyun-arms',
        'threshold_hours': threshold_hours
    }


def parse_alertmanager_webhook(alert: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Prometheus Alertmanager webhook format."""
    normalized = []
    
    for a in alert.get('alerts', []):
        labels = a.get('labels', {})
        annotations = a.get('annotations', {})
        
        rule_name = labels.get('alertname', 'Unknown')
        content = annotations.get('summary', annotations.get('description', ''))
        threshold_hours = extract_threshold_hours(rule_name, content)
        
        normalized.append({
            'timestamp': a.get('startsAt', ''),
            'priority': labels.get('severity', 'warning').upper(),
            'rule': rule_name,
            'cluster': labels.get('cluster') or labels.get('namespace'),
            'content': content,
            'source': 'alertmanager',
            'threshold_hours': threshold_hours
        })
    
    return normalized


def parse_grafana_webhook(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Grafana alert webhook format."""
    state = alert.get('state', 'alerting')
    
    # Map Grafana state to priority
    priority_map = {
        'alerting': 'P2',
        'ok': 'OK',
        'no_data': 'P3',
        'paused': 'INFO'
    }
    
    rule_name = alert.get('ruleName', alert.get('title', 'Unknown'))
    content = alert.get('message', '')
    threshold_hours = extract_threshold_hours(rule_name, content)
    
    return {
        'timestamp': alert.get('time', ''),
        'priority': priority_map.get(state, 'P3'),
        'rule': rule_name,
        'cluster': alert.get('evalMatches', [{}])[0].get('tags', {}).get('cluster') if alert.get('evalMatches') else None,
        'content': content,
        'source': 'grafana',
        'threshold_hours': threshold_hours
    }


def normalize_alert(alert: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect format and normalize alert."""
    # Aliyun ARMS email format
    if 'subject' in alert and 'body' in alert and '告警' in alert.get('body', ''):
        return [parse_aliyun_arms_email(alert)]
    
    # Alertmanager webhook format
    elif 'alerts' in alert:
        return parse_alertmanager_webhook(alert)
    
    # Grafana webhook format
    elif 'state' in alert and ('ruleName' in alert or 'title' in alert):
        return [parse_grafana_webhook(alert)]
    
    else:
        raise ValueError(f"Unknown alert format: {alert.keys()}")


def deduplicate_alerts(alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deduplicate repeated alerts and build a compact timeline."""
    
    # Group by rule + priority + cluster
    groups = defaultdict(list)
    for alert in alerts:
        key = (alert['rule'], alert['priority'], alert.get('cluster', 'default'))
        groups[key].append(alert)
    
    timeline = []
    
    for (rule, priority, cluster), group in sorted(groups.items()):
        # Sort by timestamp
        group.sort(key=lambda x: x['timestamp'])
        
        first_alert = group[0]
        last_alert = group[-1]
        count = len(group)
        
        timeline.append({
            'rule': rule,
            'priority': priority,
            'cluster': cluster if cluster != 'default' else None,
            'count': count,
            'first_seen': first_alert['timestamp'],
            'last_seen': last_alert['timestamp'],
            'content': first_alert['content'],
            'source': first_alert['source'],
            'threshold_hours': first_alert.get('threshold_hours')
        })
    
    # Sort timeline by first occurrence
    timeline.sort(key=lambda x: x['first_seen'])
    
    # Infer last known good time using thresholds
    last_known_good, inference_method, evidence = infer_last_known_good(timeline)
    
    return {
        'summary': {
            'total_alerts': len(alerts),
            'unique_rules': len(timeline),
            'last_known_good': last_known_good,
            'last_known_good_method': inference_method,
            'last_known_good_evidence': evidence
        },
        'timeline': timeline
    }


def infer_last_known_good(timeline: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Infer last known good time from threshold-based rules.
    
    Returns:
        (last_known_good_time, inference_method, evidence_list)
    """
    if not timeline:
        return None, None, []
    
    # Try to infer from threshold rules
    threshold_inferences = []
    evidence = []
    
    for entry in timeline:
        threshold_hours = entry.get('threshold_hours')
        if threshold_hours is not None:
            first_fire = entry['first_seen']
            try:
                first_fire_dt = datetime.fromisoformat(first_fire.replace('Z', '+00:00'))
                last_good_dt = first_fire_dt - timedelta(hours=threshold_hours)
                last_good_iso = last_good_dt.isoformat()
                
                threshold_inferences.append(last_good_dt)
                
                # Format evidence with explicit timezone offset
                if first_fire_dt.tzinfo and first_fire_dt.tzinfo.utcoffset(None):
                    offset = first_fire_dt.tzinfo.utcoffset(None)
                    offset_hours = int(offset.total_seconds() // 3600)
                    if offset_hours == 0:
                        tz_str = "UTC"
                    else:
                        tz_str = f"UTC{offset_hours:+d}"
                else:
                    tz_str = "UTC"
                
                evidence.append(
                    f"Rule '{entry['rule']}' (threshold: {threshold_hours}h) first fired at "
                    f"{first_fire_dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_str} "
                    f"→ last good ≈ {last_good_dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_str}"
                )
            except Exception:
                pass
    
    if threshold_inferences:
        # Check if multiple rules agree (within 1 hour tolerance)
        avg_time = threshold_inferences[0]
        agreement = all(
            abs((t - avg_time).total_seconds()) < 3600
            for t in threshold_inferences
        )
        
        if len(threshold_inferences) > 1 and agreement:
            method = f"threshold_cross_check_{len(threshold_inferences)}_rules_agree"
        else:
            method = "threshold_single_rule"
        
        return avg_time.isoformat(), method, evidence
    
    # Fallback: use earliest alert time as upper bound
    earliest = min(entry['first_seen'] for entry in timeline)
    evidence.append(f"No threshold found; using earliest alert as upper bound: {earliest}")
    return earliest, "first_alert_upper_bound", evidence


def main():
    if len(sys.argv) < 2:
        print("Usage: normalize.py <alerts.jsonl>", file=sys.stderr)
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    alerts = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                alert = json.loads(line)
                normalized = normalize_alert(alert)
                alerts.extend(normalized)
            except Exception as e:
                print(f"Warning: Failed to parse line {line_num}: {e}", file=sys.stderr)
    
    result = deduplicate_alerts(alerts)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
