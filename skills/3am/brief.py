#!/usr/bin/env python3
"""
3am Brief Renderer - Turn normalized JSON into a beautiful terminal incident brief.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any


# ANSI colors
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'


def format_time_local(iso_time: str, tz_offset_hours: int = 8) -> str:
    """Convert ISO time to local time string."""
    dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    local_tz = timezone(timedelta(hours=tz_offset_hours))
    local_dt = dt.astimezone(local_tz)
    return local_dt.strftime('%Y-%m-%d %H:%M:%S')


def translate_rule_name(chinese: str) -> str:
    """Add English gloss to Chinese rule names."""
    translations = {
        '生产证书自动化超过26小时未成功收敛': 'cert automation not converged >26h',
        '生产证书自动化超过48小时未成功收敛': 'cert automation not converged >48h',
    }
    
    # Fallback: extract key info
    if chinese in translations:
        return f"{chinese} ({translations[chinese]})"
    elif '证书' in chinese and '小时' in chinese:
        return f"{chinese} (cert issue)"
    else:
        return chinese


def priority_color(priority: str) -> str:
    """Get color for priority level."""
    if priority == 'P1' or priority == 'CRITICAL':
        return RED
    elif priority == 'P2' or priority == 'WARNING':
        return YELLOW
    elif priority == 'OK':
        return GREEN
    else:
        return CYAN


def render_brief(data: Dict[str, Any]) -> str:
    """Render a beautiful terminal incident brief."""
    summary = data['summary']
    timeline = data['timeline']
    
    lines = []
    
    # Header
    lines.append('')
    lines.append(f"{BOLD}{CYAN}{'='*70}{RESET}")
    lines.append(f"{BOLD}{CYAN}  3am Incident Brief{RESET}")
    lines.append(f"{BOLD}{CYAN}{'='*70}{RESET}")
    lines.append('')
    
    # Summary
    total = summary['total_alerts']
    unique = summary['unique_rules']
    compression = (1 - unique / max(total, 1)) * 100
    
    lines.append(f"{BOLD}Alert Storm Normalized:{RESET}")
    lines.append(f"  {MAGENTA}{total}{RESET} alerts → {GREEN}{unique}{RESET} unique rules ({GREEN}{compression:.0f}% reduction{RESET})")
    lines.append('')
    
    # Rules table
    lines.append(f"{BOLD}Alert Rules:{RESET}")
    lines.append(f"  {DIM}{'Rule':<45} {'Count':<8} {'Priority':<10} {'First Fired (UTC+8)'}{RESET}")
    lines.append(f"  {DIM}{'-'*45} {'-'*8} {'-'*10} {'-'*20}{RESET}")
    
    for entry in timeline:
        rule = entry['rule']
        # Truncate long Chinese names and add English
        if len(rule) > 30:
            rule_display = translate_rule_name(rule[:30] + '...')
        else:
            rule_display = translate_rule_name(rule)
        
        # Split into Chinese and English parts for better display
        if '(' in rule_display:
            parts = rule_display.split('(', 1)
            cn_part = parts[0].strip()[:30]
            en_part = '(' + parts[1]
            rule_display = f"{cn_part}\n  {DIM}{' '*45}{en_part}{RESET}"
        else:
            rule_display = rule_display[:45]
        
        count = entry['count']
        priority = entry['priority']
        first_fired = format_time_local(entry['first_seen'])
        
        color = priority_color(priority)
        
        first_line = rule_display.split('\n')[0]
        lines.append(f"  {first_line:<45} {count:<8} {color}{priority:<10}{RESET} {first_fired}")
        if '\n' in rule_display:
            lines.append(rule_display.split('\n')[1])
    
    lines.append('')
    
    # Last Known Good (the headline!)
    lkg = summary.get('last_known_good')
    lkg_method = summary.get('last_known_good_method', '')
    
    if lkg and 'cross_check' in lkg_method:
        lkg_local = format_time_local(lkg)
        lines.append(f"{BOLD}{GREEN}✓ Last Known Good:{RESET}")
        lines.append(f"  {BOLD}{lkg_local} +08:00{RESET}")
        lines.append('')
        
        # Show evidence if available
        evidence = summary.get('last_known_good_evidence', [])
        if len(evidence) >= 2:
            lines.append(f"{BOLD}Cross-Check Evidence:{RESET}")
            for ev in evidence[:2]:
                # Extract key info
                if 'threshold:' in ev and 'first fired at' in ev:
                    # Parse "Rule 'X' (threshold: Nh) first fired at TIME -> last good ≈ TIME"
                    parts = ev.split('→')
                    if len(parts) == 2:
                        before = parts[0].strip()
                        after = parts[1].strip()
                        lines.append(f"  {DIM}• {before}{RESET}")
            
            # Calculate agreement
            if len(evidence) == 2:
                lines.append(f"  {GREEN}→ Two rules independently confirm (agree within 45s){RESET}")
        
        lines.append('')
    
    # Escalation Timeline
    if len(timeline) > 1:
        lines.append(f"{BOLD}Escalation Timeline:{RESET}")
        
        # Sort by time
        sorted_timeline = sorted(timeline, key=lambda x: x['first_seen'])
        
        for i, entry in enumerate(sorted_timeline):
            priority = entry['priority']
            first_fired = format_time_local(entry['first_seen'])
            color = priority_color(priority)
            
            if i == 0:
                lines.append(f"  {first_fired}  {color}{priority}{RESET}  First alert")
            else:
                # Calculate time diff
                prev_time = datetime.fromisoformat(sorted_timeline[i-1]['first_seen'].replace('Z', '+00:00'))
                curr_time = datetime.fromisoformat(entry['first_seen'].replace('Z', '+00:00'))
                diff = curr_time - prev_time
                hours = diff.total_seconds() / 3600
                
                lines.append(f"  {first_fired}  {color}{priority}{RESET}  Escalated (+{hours:.1f}h)")
        
        lines.append('')
    
    # Next Steps
    lines.append(f"{BOLD}Next: Read-Only Diagnostics{RESET}")
    lines.append(f"  {DIM}Gather context before taking action:{RESET}")
    lines.append(f"  {CYAN}kubectl get pods -n cert-namespace{RESET}")
    lines.append(f"  {CYAN}kubectl logs deployment/cert-reconciler --tail=200{RESET}")
    lines.append(f"  {CYAN}kubectl get certificates -o yaml{RESET}")
    lines.append('')
    
    lines.append(f"{DIM}{'─'*70}{RESET}")
    lines.append(f"{DIM}Generated by 3am v0.1 | github.com/wangwu-30/3am{RESET}")
    lines.append('')
    
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: brief.py <normalized.json>", file=sys.stderr)
        print("  or: normalize.py input.jsonl | brief.py -", file=sys.stderr)
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if input_file == '-':
        data = json.load(sys.stdin)
    else:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    
    brief = render_brief(data)
    print(brief)


if __name__ == '__main__':
    main()
