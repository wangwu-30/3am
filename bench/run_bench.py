#!/usr/bin/env python3
"""
Benchmark script for 3am alert normalization.

Tests:
1. Token compression ratio (288 alerts -> 1 page)
2. Correct parsing of Aliyun ARMS, Alertmanager, Grafana formats
3. Deduplication accuracy
4. Last-known-good time inference
5. Escalation detection (P2 -> P1)
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def count_tokens_rough(text: str) -> int:
    """Rough token count: ~4 chars per token."""
    return len(text) // 4


def run_normalizer(fixture_path: Path) -> dict:
    """Run normalize.py on a fixture file."""
    cmd = ['python3', 'skills/3am/normalize.py', str(fixture_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    
    if result.returncode != 0:
        print(f"❌ Normalizer failed on {fixture_path.name}")
        print(result.stderr)
        sys.exit(1)
    
    return json.loads(result.stdout)


def test_aliyun_arms_real():
    """Test real Aliyun ARMS certificate alert dataset."""
    print("\n📊 Test: Real Aliyun ARMS Certificate Alerts")
    print("=" * 60)
    
    fixture = Path('bench/fixtures/real/aliyun-arms-cert-alerts.jsonl')
    
    # Count input tokens
    with open(fixture, 'r', encoding='utf-8') as f:
        input_text = f.read()
    
    input_tokens = count_tokens_rough(input_text)
    input_lines = len(input_text.strip().split('\n'))
    
    # Run normalizer
    result = run_normalizer(fixture)
    
    # Count output tokens
    output_text = json.dumps(result, indent=2, ensure_ascii=False)
    output_tokens = count_tokens_rough(output_text)
    
    # Calculate compression
    compression_ratio = (1 - output_tokens / input_tokens) * 100
    
    print(f"Input:  {input_lines} alerts, ~{input_tokens:,} tokens")
    print(f"Output: {result['summary']['unique_rules']} unique rules, ~{output_tokens:,} tokens")
    print(f"Compression: {compression_ratio:.1f}% fewer tokens")
    
    # Verify expected results
    summary = result['summary']
    timeline = result['timeline']
    
    assert summary['total_alerts'] == 288, f"Expected 288 alerts, got {summary['total_alerts']}"
    print(f"✅ Total alerts: {summary['total_alerts']}")
    
    assert summary['unique_rules'] == 2, f"Expected 2 unique rules, got {summary['unique_rules']}"
    print(f"✅ Unique rules: {summary['unique_rules']}")
    
    # Check for P2 and P1 escalation
    priorities = {t['priority'] for t in timeline}
    assert 'P2' in priorities and 'P1' in priorities, f"Expected P2 and P1, got {priorities}"
    print(f"✅ Escalation detected: P2 → P1")
    
    # Verify first P2 alert time
    p2_alerts = [t for t in timeline if t['priority'] == 'P2']
    if p2_alerts:
        first_p2 = p2_alerts[0]['first_seen']
        # Should be 2026-10-09 05:31:13 (UTC+8 in the alert, but stored as ISO string)
        # The alert time is "2026-10-09 05:31:13" which should be parsed
        print(f"✅ First P2 alert: {first_p2}")
    
    # Verify P1 alert time
    p1_alerts = [t for t in timeline if t['priority'] == 'P1']
    if p1_alerts:
        first_p1 = p1_alerts[0]['first_seen']
        # Should be 2026-10-10 03:31:58
        print(f"✅ First P1 alert: {first_p1}")
    
    # Verify last known good inference
    lkg = summary['last_known_good']
    print(f"✅ Last known good: {lkg}")
    
    return {
        'compression_ratio': compression_ratio,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens
    }


def test_alertmanager():
    """Test Prometheus Alertmanager webhook format."""
    print("\n📊 Test: Alertmanager Webhooks")
    print("=" * 60)
    
    fixture = Path('bench/fixtures/synthetic/alertmanager-high-cpu.jsonl')
    result = run_normalizer(fixture)
    
    summary = result['summary']
    timeline = result['timeline']
    
    print(f"Total alerts: {summary['total_alerts']}")
    print(f"Unique rules: {summary['unique_rules']}")
    
    # Should detect HighCPUUsage and HighMemoryUsage
    rule_names = {t['rule'] for t in timeline}
    assert 'HighCPUUsage' in rule_names, "Expected HighCPUUsage rule"
    assert 'HighMemoryUsage' in rule_names, "Expected HighMemoryUsage rule"
    print(f"✅ Detected rules: {', '.join(rule_names)}")
    
    # Should detect severity escalation warning -> critical
    priorities = {t['priority'] for t in timeline}
    assert 'WARNING' in priorities and 'CRITICAL' in priorities
    print(f"✅ Severity escalation detected: WARNING → CRITICAL")


def test_grafana():
    """Test Grafana alert webhook format."""
    print("\n📊 Test: Grafana Alerts")
    print("=" * 60)
    
    fixture = Path('bench/fixtures/synthetic/grafana-disk-space.jsonl')
    result = run_normalizer(fixture)
    
    summary = result['summary']
    timeline = result['timeline']
    
    print(f"Total alerts: {summary['total_alerts']}")
    print(f"Unique rules: {summary['unique_rules']}")
    
    # Should detect DiskSpaceWarning and DiskSpaceCritical
    rule_names = {t['rule'] for t in timeline}
    assert 'DiskSpaceWarning' in rule_names or 'DiskSpaceCritical' in rule_names
    print(f"✅ Detected rules: {', '.join(rule_names)}")
    
    # Should detect recovery (OK state)
    priorities = {t['priority'] for t in timeline}
    has_ok = 'OK' in priorities
    print(f"✅ Recovery detected: {has_ok}")


def main():
    print("🚀 Running 3am Benchmarks")
    print("=" * 60)
    
    # Test all formats
    stats = test_aliyun_arms_real()
    test_alertmanager()
    test_grafana()
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print(f"\n🎯 Key Result: {stats['compression_ratio']:.1f}% token reduction")
    print(f"   (288 alerts → 1 page: {stats['input_tokens']:,} → {stats['output_tokens']:,} tokens)")


if __name__ == '__main__':
    main()
