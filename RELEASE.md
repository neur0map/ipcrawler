# Release and Installation Guide

This document explains how to release new versions of ipcrawler and how users can install the binary.

## For Maintainers: Creating Releases

### Stable Releases

Stable releases are triggered by creating and pushing version tags:

```bash
# Update version in Cargo.toml first
git commit -am "Bump version to v1.0.0"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

This will:
1. Trigger the `release.yml` workflow
2. Build binaries for all supported platforms
3. Create a GitHub release with the binaries attached
4. Generate SHA256 checksums

### Unstable Builds

Unstable builds are automatically created on every push to the `main` branch:

- No manual action required
- Binaries are automatically built and attached to the `unstable` release tag
- The unstable release is continuously updated with the latest commit
- Each build includes metadata (commit SHA, date, branch)

### Supported Platforms

Both stable and unstable releases support:

- **Linux**: x86_64 (glibc and musl)
- **macOS**: x86_64 (Intel) and aarch64 (Apple Silicon)
- **Windows**: x86_64

## For Users: Installation

### Quick Install (Stable)

Install the latest stable release:

```bash
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash
```

### Install Unstable Build

Install the latest unstable build from the main branch:

```bash
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash -s -- --unstable
```

### Install Specific Version

Install a specific version:

```bash
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash -s -- --version v1.0.0
```

### Custom Installation Directory

Install to a custom directory:

```bash
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash -s -- --dir /usr/local/bin
```

### Manual Installation

1. Go to the [Releases page](https://github.com/neur0map/ipcrawler/releases)
2. Download the appropriate binary for your platform:
   - Linux: `ipcrawler-linux-x86_64.tar.gz` or `ipcrawler-linux-x86_64-musl.tar.gz`
   - macOS Intel: `ipcrawler-macos-x86_64.tar.gz`
   - macOS Apple Silicon: `ipcrawler-macos-aarch64.tar.gz`
   - Windows: `ipcrawler-windows-x86_64.exe.zip`
3. Extract the archive and move the binary to a directory in your PATH

### Verify Installation

After installation, verify it works:

```bash
ipcrawler --version
ipcrawler --help
```

## Installation Script Options

The `install.sh` script supports the following options:

| Option | Description |
|--------|-------------|
| `--unstable` | Install the latest unstable build |
| `--version VERSION` | Install a specific version (e.g., v1.0.0) |
| `--dir DIR` | Installation directory (default: ~/.local/bin) |
| `--force` | Force reinstall even if already installed |
| `-h, --help` | Show help message |

## Troubleshooting

### Binary not in PATH

If you see "command not found" after installation, add the installation directory to your PATH:

```bash
# For bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# For zsh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Platform not supported

If your platform is not supported, you can build from source:

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
cargo build --release
# Binary will be at target/release/ipcrawler
```

### Download fails

If the download fails:
1. Check your internet connection
2. Verify the release exists on the [Releases page](https://github.com/neur0map/ipcrawler/releases)
3. Try downloading manually from GitHub

## CI/CD Workflows

### CI Workflow

Runs on every pull request and push to main:
- Tests on Linux, macOS, and Windows
- Format checking with rustfmt
- Linting with clippy

### Release Workflow

Triggered by version tags (v*.*.*):
- Builds optimized binaries for all platforms
- Strips debug symbols to reduce binary size
- Creates GitHub release with binaries
- Generates SHA256 checksums

### Unstable Workflow

Triggered on every push to main:
- Builds binaries with commit metadata
- Updates the `unstable` release tag
- Provides latest development builds
- Artifacts retained for 30 days
