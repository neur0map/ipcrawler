# Code Quality System

This repository includes a comprehensive code quality checking system designed to catch common issues, especially template variable formatting problems like `{{}}` vs `{}` in plugins.

## Features

### 🔍 Automated Checks

1. **Python Syntax Validation** - Critical syntax errors that prevent code execution
2. **Template Variable Check** - Detects `{variable}` vs `{{variable}}` issues in plugins  
3. **Control Flow Validation** - Checks for unclosed loops, break/continue outside loops, return outside functions
4. **Advanced Linting** - Uses flake8, pyflakes and bandit for code quality and security
5. **Async/Await Pattern Check** - Detects missing `await` and blocking calls in async functions
6. **TOML/Makefile Validation** - Ensures configuration files are valid
7. **Package Vulnerability Scanning** - Checks for known security issues in dependencies

### 🚨 Priority System

**Plugins are checked first** - The system prioritizes plugin files since they're critical for tool functionality.

**Smart Error Classification:**
- ❌ **Critical Errors**: Syntax errors, undefined variables, critical linting issues
- ⚠️ **Warnings**: Security issues, package vulnerabilities, style warnings
- ✅ **Success**: All checks passed

### 📢 Discord Notifications

Rich Discord notifications include:
- 📁 **Modified Files**: Clear list of changed files with proper formatting
- 🔍 **Analysis Results**: Detailed breakdown of any issues found
- 🎯 **Status Colors**: Green (success), Yellow (warnings), Red (failures)
- 🔗 **GitHub Integration**: Direct links to commits and workflow runs

## Setup

### 1. GitHub Secrets

Add your Discord webhook URL as a repository secret:

```
Settings → Secrets and variables → Actions → New repository secret
Name: DISCORD_WEBHOOK_URL
Value: https://discord.com/api/webhooks/your-webhook-url
```

### 2. Pre-commit Hooks (Optional)

Install pre-commit hooks for local development:

```bash
pip install pre-commit
pre-commit install
```

This will run basic checks before each commit to catch issues early.

## Workflow Triggers

The workflow runs on:
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`

## Common Issues & Solutions

### Template Variable Errors

❌ **Wrong**: `f'curl {port}/endpoint'` 
✅ **Correct**: `f'curl {{port}}/endpoint'`

The system specifically looks for:
- `F821 undefined name` errors in flake8 output
- Single brace patterns in f-strings within plugin files

### Control Flow Issues

❌ **Wrong**: 
```python
def some_function():
    if condition:
        for item in items:
            if something:
                break  # This is fine
    break  # ❌ Error: break outside loop
```

✅ **Correct**:
```python
def some_function():
    for item in items:
        if condition:
            break  # ✅ break inside loop
    return result  # ✅ return inside function
```

### Async/Await Issues

❌ **Wrong**: 
```python
async def run(self, service):
    service.execute('command')  # Missing await
    time.sleep(5)  # Blocking call in async function
```

✅ **Correct**:
```python
async def run(self, service):
    await service.execute('command')  # ✅ Proper await
    await asyncio.sleep(5)  # ✅ Async sleep
```

### False Positive Prevention

The system is designed to minimize false positives:
- Only reports high-severity security issues
- Focuses on critical syntax and undefined variable errors
- Excludes style-only issues that don't affect functionality
- Smart pattern matching for template variable issues

### File Structure

```
.github/
├── workflows/
│   └── code-quality-check.yml    # Main workflow
└── CODE_QUALITY.md               # This documentation

.pre-commit-config.yaml            # Local pre-commit hooks
```

## Discord Notification Format

### 🎯 Modern Design Features

- **Smart File Type Emojis**: 🐍 Python, ⚙️ TOML, 📋 YAML, 📖 Markdown, 🔨 Makefile
- **Branch-Specific Emojis**: 🚀 main, ⚡ develop, 🌿 feature branches
- **Color-Coded Status**: Modern green/yellow/red color scheme
- **Contextual Explanations**: Each error type includes helpful context
- **File Count Management**: Shows count and truncates long lists
- **HTTP Status Verification**: Confirms delivery success

### ✅ Success Notification:
```
✨ Code Quality: All Checks Passed

🚀 Branch: main
👤 Author: username  
🔗 Commit: abc123d
⚡ Trigger: push

📁 Changed Files (3)
🐍 ipcrawler/plugins.py
⚙️ config.toml
📖 README.md

🔍 Quality Analysis
🎯 Perfect Quality Score!

All systems green: Your code passes all quality checks with flying colors.

✅ Validated:
• 🐍 Python syntax & structure
• 🔧 Template variables ({{}}} formatting)
• 🔄 Control flow (loops, functions)
• 🔍 Code quality & style  
• ⚙️ Configuration files
• 🛡️ Security vulnerabilities

Ready for production deployment!
```

### 🚨 Error Notification:
```
🚨 Code Quality: Critical Issues

🚀 Branch: main
👤 Author: username
🔗 Commit: abc123d  
⚡ Trigger: push

📁 Changed Files (2)
🐍 spring-boot-actuator.py
🐍 whatweb.py

🔍 Quality Analysis
📊 Quality Report: 2 critical error(s) 1 warning(s)

> 🔥 Critical Syntax Errors
> These prevent the code from running and must be fixed immediately.
```python
spring-boot-actuator.py:66:62: F821 undefined name 'port'
whatweb.py:48:35: F821 undefined name 'hostname'
```

> 🔧 Template & Control Flow Issues  
> Problems with {{}} formatting or loop/function structure.
```python
plugin.py: Line 45: break outside loop
main.py: Missing 'await' before service.execute()
```

> ⚠️ Code Quality Warnings
> Non-critical issues worth reviewing.
```
Potential blocking calls in async function
```
```

### ⚠️ Warning Notification:
```
⚠️ Code Quality: Issues Found

📊 Quality Report: 1 warning(s)

> 🛡️ Security Advisories
> Potential security vulnerabilities in dependencies.
```bash
Package 'requests' has known vulnerability CVE-2023-xxxxx
```
```

## Integration with Development Workflow

1. **Local Development**: Use pre-commit hooks to catch issues early
2. **Pull Requests**: Automatic checking prevents broken code from merging
3. **Main Branch**: Continuous monitoring ensures code quality
4. **Discord Alerts**: Team stays informed about code quality status

## Customization

Edit `.github/workflows/code-quality-check.yml` to:
- Add custom linting rules
- Modify Discord notification format
- Change trigger conditions
- Add additional file types for validation

## Troubleshooting

**Common Issues:**

1. **Workflow not running**: Check branch names match workflow triggers
2. **Discord not working**: Verify `DISCORD_WEBHOOK_URL` secret is set correctly  
3. **False positives**: Review the specific error patterns and adjust accordingly
4. **Template variable issues**: Use `{{variable}}` in plugin f-strings, not `{variable}`

**Getting Help:**

Check the Actions tab in GitHub for detailed logs of each step in the workflow.