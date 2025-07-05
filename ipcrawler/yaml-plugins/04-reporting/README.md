# Reporting Plugin Status

## markdown-report.yaml.disabled

The YAML reporting plugin has been disabled to prevent conflicts with the built-in automatic report generation system.

### Why Disabled?

1. **Duplicate Reports**: Both systems generate `report.md` files, causing overwrites
2. **Timing Issues**: YAML plugin runs during normal plugin execution, may execute before `parsed.yaml` files exist
3. **Scope Mismatch**: Built-in system is per-target, YAML plugin processes all targets
4. **Reliability**: Built-in system handles edge cases (timeout, interruption) better

### Current Report Generation

The built-in system automatically generates reports in three scenarios:
- **Normal completion**: Target scans complete successfully
- **Timeout**: Target exceeds configured time limit  
- **Interruption**: User presses Ctrl+C

Reports are generated via the 4-phase pipeline:
1. **Raw logs** → `results/{target}/scans/*.log`
2. **Parsed YAML** → `results/{target}/parsed.yaml` 
3. **Validation** → Pydantic schema validation
4. **Markdown report** → `results/{target}/report.md`

### Re-enabling the Plugin

To re-enable the YAML plugin (not recommended):
```bash
mv markdown-report.yaml.disabled markdown-report.yaml
```

However, this will cause conflicts with the built-in system and is not recommended.