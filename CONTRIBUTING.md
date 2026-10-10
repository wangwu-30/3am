# Contributing to 3am

感谢你对 3am 的兴趣！我们欢迎各种形式的贡献。

## 如何贡献

### 添加新的告警源支持

如果你想添加对新告警系统的支持（如 Tencent Cloud CLS、PagerDuty、Datadog 等），请遵循以下步骤：

#### 1. 添加解析器函数

在 `skills/3am/normalize.py` 中添加新的解析器函数：

```python
def parse_your_alert_source(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Your Alert Source format."""
    
    # Extract alert fields
    rule_name = alert.get('alert_name', 'Unknown')
    content = alert.get('message', '')
    
    # Extract threshold if present (e.g., ">2h", "超过30分钟")
    threshold_hours = extract_threshold_hours(rule_name, content)
    
    return {
        'timestamp': alert.get('timestamp', ''),  # ISO 8601 format
        'priority': alert.get('severity', 'P3').upper(),  # P1/P2/P3/CRITICAL/WARNING
        'rule': rule_name,
        'cluster': alert.get('cluster'),  # Optional
        'content': content,
        'source': 'your-source-name',
        'threshold_hours': threshold_hours  # Optional, for last-known-good inference
    }
```

#### 2. 在 `normalize_alert()` 中注册解析器

在 `normalize_alert()` 函数中添加检测逻辑：

```python
def normalize_alert(alert: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect format and normalize alert."""
    
    # ... existing parsers ...
    
    # Your Alert Source format
    elif 'your_unique_field' in alert:
        return [parse_your_alert_source(alert)]
    
    else:
        raise ValueError(f"Unknown alert format: {alert.keys()}")
```

#### 3. 添加测试 fixture

在 `bench/fixtures/synthetic/` 创建测试数据文件（JSONL 格式）：

```bash
# bench/fixtures/synthetic/your-source-alerts.jsonl
{"alert_name": "HighCPU", "severity": "warning", "timestamp": "2026-10-10T10:00:00Z", "message": "CPU >80% for 5min"}
{"alert_name": "HighCPU", "severity": "critical", "timestamp": "2026-10-10T10:15:00Z", "message": "CPU >90% for 10min"}
```

#### 4. 添加基准测试

在 `bench/run_bench.py` 中添加测试函数：

```python
def test_your_source():
    """Test Your Alert Source format."""
    print("\n📊 Test: Your Alert Source")
    print("=" * 60)
    
    fixture = Path('bench/fixtures/synthetic/your-source-alerts.jsonl')
    result = run_normalizer(fixture)
    
    summary = result['summary']
    timeline = result['timeline']
    
    print(f"Total alerts: {summary['total_alerts']}")
    print(f"Unique rules: {summary['unique_rules']}")
    
    # Add assertions
    assert summary['total_alerts'] > 0
    rule_names = {t['rule'] for t in timeline}
    assert 'HighCPU' in rule_names
    print(f"✅ Detected rules: {', '.join(rule_names)}")

# Add to main()
def main():
    # ... existing tests ...
    test_your_source()
```

#### 5. 更新文档

- 在 `README.md` 的 "Supported Alert Sources" 表格中添加新的告警源
- 在 `skills/3am/SKILL.md` 的 "Supported Alert Sources" 章节中添加

#### 6. 提交 PR

- Fork 本仓库
- 创建特性分支：`git checkout -b feature/add-your-source`
- 提交更改：`git commit -m "feat: add Your Source alert parser"`
- 推送到你的 fork：`git push origin feature/add-your-source`
- 开启 Pull Request

---

## Good First Issues

以下是一些适合新贡献者的任务：

### 1. 添加 Tencent Cloud CLS 支持

**目标**：支持腾讯云日志服务 (CLS) 的告警格式

**需要做什么**：
- 研究 CLS 告警 webhook/邮件格式
- 添加 `parse_tencent_cls()` 解析器
- 支持中文告警内容
- 提取阈值信息（如"连续3分钟超过阈值"）
- 添加测试 fixture 和基准断言

**难度**：⭐⭐ 中等

**参考**：参考 `parse_aliyun_arms_email()` 的实现

---

### 2. 添加 PagerDuty 支持

**目标**：支持 PagerDuty webhook 格式

**需要做什么**：
- 解析 PagerDuty incident webhook JSON
- 提取 urgency (high/low) → priority (P1/P2)
- 提取 incident key, service, summary
- 支持 triggered/acknowledged/resolved 状态
- 添加测试 fixture 和基准断言

**难度**：⭐ 简单

**资源**：[PagerDuty Webhook 文档](https://developer.pagerduty.com/docs/ZG9jOjExMDI5NTgx-overview)

---

### 3. 添加 Datadog 支持

**目标**：支持 Datadog 告警 webhook 格式

**需要做什么**：
- 解析 Datadog monitor alert webhook
- 提取 alert_type, priority, title, body
- 支持 monitor query 中的阈值提取
- 处理 recovered 状态
- 添加测试 fixture 和基准断言

**难度**：⭐⭐ 中等

**资源**：[Datadog Webhook 文档](https://docs.datadoghq.com/integrations/webhooks/)

---

### 4. 添加 Aliyun SLS 支持

**目标**：支持阿里云 SLS (Simple Log Service) 日志查询结果

**需要做什么**：
- 解析 SLS 日志查询导出的 JSON 格式
- 从日志内容中提取告警级别和规则名
- 支持结构化日志和非结构化日志
- 添加去重逻辑（SLS 日志可能包含很多重复条目）
- 添加测试 fixture 和基准断言

**难度**：⭐⭐⭐ 较难

**原因**：SLS 日志格式比告警更灵活，需要更智能的解析

---

## 开发指南

### 运行测试

```bash
# 运行完整基准测试
python3 bench/run_bench.py

# 测试单个 fixture
python3 skills/3am/normalize.py bench/fixtures/synthetic/your-source.jsonl | jq .
```

### 代码风格

- 遵循 PEP 8
- 使用类型提示 (type hints)
- 保持函数简短、单一职责
- 添加有意义的注释和文档字符串

### 提交信息格式

```
<type>: <subject>

<body>
```

类型：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 重构
- `chore`: 构建/工具链更新

例子：
```
feat: add PagerDuty webhook parser

- Parse PagerDuty incident webhook JSON
- Map urgency to priority levels
- Extract incident key and service
- Add synthetic test fixture
```

---

## 报告 Bug

如果你发现了 bug，请开启一个 [GitHub Issue](https://github.com/wangwu-30/3am/issues) 并包含：

- 问题描述
- 重现步骤
- 预期行为 vs. 实际行为
- 告警数据样例（请务必脱敏！）
- 你的环境（Python 版本、操作系统）

---

## 需要帮助？

- 查看 [README.md](README.md) 了解项目概览
- 阅读 [skills/3am/SKILL.md](skills/3am/SKILL.md) 了解技能使用方式
- 查看 [demo/example-analysis.md](demo/example-analysis.md) 了解输出示例
- 在 [GitHub Discussions](https://github.com/wangwu-30/3am/discussions) 提问

---

## 行为准则

请保持友好、尊重和建设性。我们欢迎所有背景的贡献者！

---

**感谢你帮助 3am 变得更好！** 🎉
