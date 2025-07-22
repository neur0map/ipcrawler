# Contributing to IPCrawler

Thank you for your interest in contributing to IPCrawler! We love your input! We want to make contributing to this project as easy and transparent as possible.

## 🚀 Quick Start

1. **Fork the repo** and create your branch from `main`
2. **Make your changes** and test them
3. **Submit a pull request** with a clear description

That's it! We'll review your PR and provide feedback.

## 💡 Ways to Contribute

### 1. Report Bugs 🐛
Found a bug? [Open an issue](https://github.com/neur0map/ipcrawler/issues/new) with:
- A clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version)

### 2. Suggest Features ✨
Have an idea? [Create a feature request](https://github.com/neur0map/ipcrawler/issues/new) with:
- Problem it solves
- Proposed solution
- Any alternatives considered

### 3. Add Wordlists 📝
Know a great wordlist for a specific technology? Add it to our SmartList rules:
```python
# In src/core/scorer/rules.py
{
    "name": "Your Technology",
    "port": 443,
    "service": "https",
    "wordlist": "your-tech-paths.txt",
    "confidence": "HIGH"
}
```

### 4. Enhance Port Database 🔍
Our port intelligence database is constantly evolving! Help us improve detection:
```python
# In database/ports/enhanced_ports.json
{
    "port": 8089,
    "services": ["splunkd", "splunk-api"],
    "technologies": ["Splunk Enterprise", "Splunk Universal Forwarder"],
    "common_paths": ["/en-US/app/", "/servicesNS/", "/services/"],
    "detection_patterns": ["X-Splunk-Version", "splunkd"]
}
```
**Every new port mapping helps thousands of security professionals!**

### 5. Improve Documentation 📚
- Fix typos
- Add examples
- Clarify confusing sections
- Translate to other languages

### 6. Write Code 💻
- Fix bugs
- Add features
- Improve performance
- Add tests

## 🛠️ Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/ipcrawler.git
cd ipcrawler

# 2. Create a branch
git checkout -b feature/your-feature-name

# 3. Install dependencies
pip install -r requirements.txt --break-system-packages

# 4. Make your changes
# ... edit files ...

# 5. Test your changes
python ipcrawler.py --audit  # Run audit to verify rules
python ipcrawler.py 192.168.1.1  # Test scanning

# 6. Commit with a descriptive message
git add .
git commit -m "Add: support for detecting GraphQL endpoints"

# 7. Push and create PR
git push origin feature/your-feature-name
```

## 📋 Pull Request Guidelines

### PR Title Format
Use these prefixes:
- `Add:` New feature or wordlist
- `Fix:` Bug fix
- `Update:` Updating existing features
- `Docs:` Documentation only
- `Test:` Adding tests
- `Refactor:` Code restructuring

### PR Checklist
- [ ] Code follows project style
- [ ] Tests pass (if applicable)
- [ ] Documentation updated (if needed)
- [ ] PR has descriptive title
- [ ] Changes are focused and minimal

## 🎯 Code Guidelines

### Python Style
```python
# Good: Clear, simple, documented
def analyze_service(port: int, service: str) -> List[str]:
    """Analyze service and return wordlist recommendations."""
    if not service:
        return []
    
    # Your logic here
    return recommendations

# Avoid: Complex one-liners, missing types
def analyze(p,s): return [] if not s else [w for w in get_wl() if match(w,s)]
```

### Adding New Workflows
1. Create directory: `workflows/your_workflow/`
2. Inherit from `BaseWorkflow`
3. Implement required methods:
```python
class YourWorkflow(BaseWorkflow):
    async def execute(self, context):
        # Your scanning logic
        pass
```

### Testing Changes
Before submitting:
```bash
# Run the audit system
python ipcrawler.py --audit

# Test with a real target
python ipcrawler.py scanme.nmap.org

# Check for syntax errors
python -m py_compile ipcrawler.py
```

## 🤝 Community Guidelines

### Be Respectful
- Constructive feedback only
- Help newcomers
- Celebrate diversity

### Be Clear
- Write descriptive commit messages
- Comment complex code
- Document your changes

### Be Focused
- One feature per PR
- Keep changes minimal
- Test before submitting

## 🏆 Recognition

Contributors will be:
- Added to README credits
- Mentioned in release notes
- Given credit in commit history

## ❓ Questions?

- **General questions**: Open a [discussion](https://github.com/neur0map/ipcrawler/discussions)
- **Bug reports**: Create an [issue](https://github.com/neur0map/ipcrawler/issues)
- **Security issues**: Email security@ipcrawler.io

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License with attribution requirements as specified in our [LICENSE](LICENSE) file.

---

<div align="center">

**Thank you for making IPCrawler better! 🎉**

Every contribution, no matter how small, makes a difference.

</div>