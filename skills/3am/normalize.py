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
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any


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
        # Parse format like "2026-10-09 05:31:13"
        try:
            alert_time = datetime.strptime(alert_time_str, '%Y-%m-%d %H:%M:%S')
            timestamp = alert_time.isoformat() + 'Z'
        except:
            timestamp = alert.get('received_at_utc')
    else:
        timestamp = alert.get('received_at_utc')
    
    # Extract alert content
    content_match = re.search(r'告警内容：\s*(.+?)(?:\[详情链接\]|$)', body, re.DOTALL)
    content = content_match.group(1).strip() if content_match else ''
    
    return {
        'timestamp': timestamp,
        'priority': priority,
        'rule': alert_name,
        'cluster': cluster,
        'content': content,
        'source': 'aliyun-arms'
    }


def parse_alertmanager_webhook(alert: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Prometheus Alertmanager webhook format."""
    normalized = []
    
    for a in alert.get('alerts', []):
        labels = a.get('labels', {})
        annotations = a.get('annotations', {})
        
        normalized.append({
            'timestamp': a.get('startsAt', ''),
            'priority': labels.get('severity', 'warning').upper(),
            'rule': labels.get('alertname', 'Unknown'),
            'cluster': labels.get('cluster') or labels.get('namespace'),
            'content': annotations.get('summary', annotations.get('description', '')),
            'source': 'alertmanager'
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
    
    return {
        'timestamp': alert.get('time', ''),
        'priority': priority_map.get(state, 'P3'),
        'rule': alert.get('ruleName', alert.get('title', 'Unknown')),
        'cluster': alert.get('evalMatches', [{}])[0].get('tags', {}).get('cluster') if alert.get('evalMatches') else None,
        'content': alert.get('message', ''),
        'source': 'grafana'
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
    all_timestamps = []
    
    for (rule, priority, cluster), group in sorted(groups.items()):
        # Sort by timestamp
        group.sort(key=lambda x: x['timestamp'])
        
        first_alert = group[0]
        last_alert = group[-1]
        count = len(group)
        
        all_timestamps.extend([a['timestamp'] for a in group])
        
        timeline.append({
            'rule': rule,
            'priority': priority,
            'cluster': cluster if cluster != 'default' else None,
            'count': count,
            'first_seen': first_alert['timestamp'],
            'last_seen': last_alert['timestamp'],
            'content': first_alert['content'],
            'source': first_alert['source']
        })
    
    # Sort timeline by first occurrence
    timeline.sort(key=lambda x: x['first_seen'])
    
    # Find last known good time (earliest alert time)
    if timeline:
        earliest = min(all_timestamps)
        last_known_good = earliest
    else:
        last_known_good = None
    
    return {
        'summary': {
            'total_alerts': len(alerts),
            'unique_rules': len(timeline),
            'last_known_good': last_known_good,
        },
        'timeline': timeline
    }


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
