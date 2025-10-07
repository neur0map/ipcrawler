# GitHub Actions Workflows

This directory contains automated workflows for the IPCrawler project.

## Rust Checks Workflow

The `rust-checks.yml` workflow provides automated code quality checks for Rust code.

### Features

- **Automated Formatting**: Checks code formatting with `rustfmt`
- **Linting**: Runs `clippy` to catch common mistakes and improve code quality
- **Auto-fix on PRs**: Automatically applies fixes and commits them to pull requests
- **Main Branch Protection**: Fails the build on main if issues are detected

### Jobs

#### 1. Format Check (`fmt`)

- Runs `cargo fmt -- --check` to verify code formatting
- **On Pull Requests**: Automatically runs `cargo fmt` and commits the fixes
- **On Main Branch**: Fails the workflow if formatting issues are found

#### 2. Clippy Lints (`clippy`)

- Runs `cargo clippy --all-targets --all-features -- -D warnings`
- All warnings are treated as errors to maintain code quality
- **On Pull Requests**: Automatically applies clippy fixes and commits them
- **On Main Branch**: Fails the workflow if lint issues are found
- Includes caching for faster builds (cargo registry, git index, and build artifacts)

### Triggers

The workflow runs on:
- Push events to the `main` branch
- Pull request events targeting the `main` branch

### How It Works

1. **On Pull Requests**:
   - Checks are run first
   - If checks fail, auto-fix is applied
   - Changes are automatically committed and pushed to the PR branch
   - Developers see the fixes in their PR automatically

2. **On Main Branch**:
   - Checks are run
   - If checks fail, the workflow fails (no auto-fix)
   - This ensures only properly formatted code is merged

### Benefits

- Reduces manual code review time
- Ensures consistent code style across the project
- Catches common issues early
- Automatically fixes issues in PRs
- Maintains high code quality standards
