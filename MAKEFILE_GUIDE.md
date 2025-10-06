# Makefile Quick Reference

## 🚀 First Time User? Start Here!

```bash
# Complete setup in one command
make setup
```

This will:
1. ✓ Check dependencies (Rust, Docker, Ollama)
2. ✓ Install Rust packages
3. ✓ Build optimized binary
4. ✓ Create system-wide symlink
5. ✓ Run interactive setup wizard
6. ✓ Start Qdrant database

---

## 📋 Most Common Commands

### For Development
```bash
make build-release    # Build optimized version
make symlink          # Create symlink to binary
make rebuild          # Clean and rebuild
```

### For Daily Use
```bash
make verify          # Check everything is working
make docker-up       # Start database
make docker-down     # Stop database
```

---

## 🔧 Understanding the Symlink

**What it does:**
- Creates a link: `/usr/local/bin/ipcrawler` → `your-project/target/release/ipcrawler`
- Lets you type `ipcrawler` from anywhere
- **Automatically uses new builds** (no reinstall needed!)

**Workflow:**
```bash
# Make changes to code
make build-release    # Build new version
ipcrawler --help      # Already uses new binary! ✨
```

**Alternative (copy install):**
```bash
make install          # Copies binary instead of linking
# After code changes, must reinstall:
make build-release
make install          # Required to update
```

---

## 📖 All Commands

### Help
| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make info` | Show project information |

### Quick Start
| Command | Description |
|---------|-------------|
| `make setup` | Complete initial setup |

### Building
| Command | Description |
|---------|-------------|
| `make build` | Build debug version (faster, larger) |
| `make build-release` | Build release version (slower, optimized) |
| `make rebuild` | Clean and rebuild |
| `make clean` | Remove build artifacts |

### Installation
| Command | Description |
|---------|-------------|
| `make symlink` | Create symlink (recommended for dev) |
| `make install` | Copy binary to /usr/local/bin |
| `make uninstall` | Remove installed binary |
| `make reinstall` | Uninstall + symlink |

### Configuration
| Command | Description |
|---------|-------------|
| `make wizard` | Run interactive setup |
| `make config` | Show current configuration |
| `make config-dir` | Open configuration directory |

### Docker Services
| Command | Description |
|---------|-------------|
| `make docker-up` | Start Qdrant database |
| `make docker-down` | Stop Qdrant database |
| `make docker-status` | Check service status |
| `make docker-logs` | Show Qdrant logs |

### Testing & Verification
| Command | Description |
|---------|-------------|
| `make test` | Run all tests |
| `make test-verbose` | Run tests with output |
| `make verify` | Verify complete setup |

### Development
| Command | Description |
|---------|-------------|
| `make dev` | Auto-rebuild on changes |
| `make run` | Build and run debug |
| `make run-release` | Build and run release |
| `make fmt` | Format code |
| `make lint` | Run linter |
| `make check` | Quick compile check |

### Maintenance
| Command | Description |
|---------|-------------|
| `make update` | Update and rebuild project |
| `make clean-all` | Clean build + docker volumes |
| `make reset` | Reset everything |

---

## 💡 Common Workflows

### After Making Code Changes
```bash
make build-release
# That's it! Symlink automatically uses new binary
ipcrawler --version
```

### Starting Fresh Development Session
```bash
make docker-up       # Start database
make verify          # Check everything works
# Start coding...
```

### Deploying to New Machine
```bash
git clone <repo>
cd ipcrawler
make setup           # Does everything
```

### Updating from Git
```bash
make update          # Pulls changes + rebuilds
```

### Troubleshooting
```bash
make verify          # Shows what's wrong
make clean-all       # Nuclear option
make setup           # Start fresh
```

---

## 🎯 Examples

### Pass Arguments to Binary
```bash
make run ARGS="scan --help"
make run-release ARGS="query 'show vulnerabilities'"
```

### Development Workflow
```bash
# Terminal 1: Auto-rebuild on changes
make dev

# Terminal 2: Start database
make docker-up

# Terminal 3: Watch logs
make docker-logs
```

### Production Build
```bash
make lint            # Check code quality
make test            # Run tests
make build-release   # Build optimized
make verify          # Verify everything
```

---

## ⚠️ Requirements

- **Rust/Cargo**: Install from https://rustup.rs
- **Docker** (optional): For Qdrant database
- **Ollama** (optional): For local LLM models
- **sudo**: For system-wide installation

Check requirements:
```bash
make check-deps
```

---

## 🔍 Verification Checklist

Run `make verify` to check:
- [x] Binary exists
- [x] Installed correctly
- [x] Configuration present
- [x] Qdrant running
- [x] Ollama running (optional)

---

## 🆘 Quick Fixes

**"Permission denied"**
```bash
sudo make symlink
```

**"Binary not found"**
```bash
make build-release
```

**"Qdrant not running"**
```bash
make docker-up
```

**"Config missing"**
```bash
make wizard
```

**Start completely fresh:**
```bash
make reset
make setup
```

---

## 📝 Notes

- **Symlink vs Install**: Symlink is better for development (no reinstall needed)
- **Debug vs Release**: Release is 10x faster but takes longer to build
- **Docker Compose**: Auto-created if missing
- **Configuration**: Stored in `~/.config/ipcrawler/`
- **API Keys**: Stored in system keychain (secure)

---

**Need help?** Run `make help` for a quick reference!
