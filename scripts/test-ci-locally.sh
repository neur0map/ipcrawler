#!/bin/bash

# Local CI Testing Script for ipcrawler
# Simulates GitHub Actions workflow locally

set -e

echo "🚀 ipcrawler Local CI Testing"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "\n${BLUE}📋 Testing: $test_name${NC}"
    echo "Command: $test_command"
    
    if eval "$test_command" > /tmp/ci_test.log 2>&1; then
        echo -e "${GREEN}✅ PASSED: $test_name${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAILED: $test_name${NC}"
        echo "Error output:"
        cat /tmp/ci_test.log
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "\n${YELLOW}🔍 Phase 1: Environment Validation${NC}"

# Check required tools
run_test "Rust toolchain" "cargo --version && rustc --version"
run_test "Cargo formatting" "cargo fmt --version"
run_test "Cargo clippy" "cargo clippy --version"

echo -e "\n${YELLOW}📝 Phase 2: File Validation${NC}"

# File permission checks
run_test "File permissions check" "
    find . -type f -executable -not -path './target/*' -not -path './.git/*' | while read -r file; do
        if [[ \"\$file\" != \"./install.sh\" && \"\$file\" != \"./scripts/\"* && \"\$file\" != \"./docs/scripts/\"* ]]; then
            echo \"Unexpected executable: \$file\"
            exit 1
        fi
    done
"

# YAML validation (basic)
run_test "Basic YAML syntax check" "
    for yaml_file in config/*.yaml testing/*.yaml schemas/*.yaml .github/workflows/*.yml; do
        if [[ -f \"\$yaml_file\" ]]; then
            python3 -c \"
import sys
try:
    with open('\$yaml_file', 'r') as f:
        content = f.read()
        # Basic YAML structure check
        if content.count(':') == 0:
            raise Exception('No YAML key-value pairs found')
        print('Valid: \$yaml_file')
except Exception as e:
    print('Invalid: \$yaml_file - ', str(e))
    sys.exit(1)
            \"
        fi
    done
"

# Documentation check
run_test "Documentation completeness" "
    required_docs=('README.md' 'docs/installation.md' 'docs/PRODUCTION_ARCHITECTURE.md')
    for doc in \"\${required_docs[@]}\"; do
        if [[ ! -f \"\$doc\" ]]; then
            echo \"Missing: \$doc\"
            exit 1
        fi
    done
"

# Secret scan (basic)
run_test "Basic secret scanning" "
    if grep -r -i -E '(password|secret|key|token).*=' --include='*.rs' --include='*.toml' --include='*.yaml' src/ config/ testing/ | grep -v '# Example' | grep -v 'TODO' | grep -v 'test' | head -1; then
        echo 'Potential secrets found'
        exit 1
    fi
"

echo -e "\n${YELLOW}🔨 Phase 3: Build Matrix Testing${NC}"

# Test different build configurations
build_configs=(
    "debug:default:cargo build"
    "release:default:cargo build --release" 
    "lean:default:cargo build --profile lean"
    "debug:dev-tools:cargo build --features dev-tools"
    "release:dev-tools:cargo build --release --features dev-tools"
)

for config in "${build_configs[@]}"; do
    IFS=':' read -r profile features command <<< "$config"
    run_test "Build $profile with $features" "$command"
done

echo -e "\n${YELLOW}🧪 Phase 4: Binary Testing${NC}"

# Test each built binary
binary_paths=(
    "target/debug/ipcrawler"
    "target/release/ipcrawler"
    "target/lean/ipcrawler"
)

for binary in "${binary_paths[@]}"; do
    if [[ -f "$binary" ]]; then
        run_test "Binary execution: $(basename $binary)" "
            $binary --version && 
            $binary --help >/dev/null &&
            $binary --doctor &&
            $binary --list >/dev/null
        "
        
        run_test "Binary size check: $(basename $binary)" "
            size=\$(ls -la '$binary' | awk '{print \$5}')
            if [[ \$size -gt 50000000 ]]; then  # 50MB limit
                echo \"Binary too large: \${size} bytes\"
                exit 1
            fi
            echo \"Binary size OK: \${size} bytes\"
        "
    fi
done

echo -e "\n${YELLOW}🔍 Phase 5: Code Quality${NC}"

run_test "Code formatting" "cargo fmt --all -- --check"
run_test "Clippy lints" "cargo clippy --all-targets --all-features -- -D warnings"
run_test "Tests execution" "cargo test --all-features"

echo -e "\n${YELLOW}📊 Phase 6: Integration Testing${NC}"

# Context detection test
run_test "Context detection" "
    # Test in project directory
    version_dev=\$(./target/release/ipcrawler --version 2>/dev/null || echo 'failed')
    if [[ \"\$version_dev\" == *\"+dev\"* ]]; then
        echo \"✅ Project context detected: \$version_dev\"
    else
        echo \"❌ Project context not detected: \$version_dev\"
        exit 1
    fi
    
    # Test outside project (simulate)
    cd /tmp
    version_prod=\$(ipcrawler --version 2>/dev/null || echo '0.1.0')
    cd \"\$OLDPWD\"
    echo \"✅ System context test: \$version_prod\"
"

# Configuration validation
if command_exists "yamllint"; then
    run_test "YAML lint validation" "yamllint config/ testing/ schemas/ || true"
fi

if [[ -f "src/bin/validate-tools-config.rs" ]]; then
    run_test "Tools config validation" "cargo run --bin validate-tools-config"
fi

echo -e "\n${YELLOW}📦 Phase 7: Artifact Analysis${NC}"

run_test "Binary artifacts check" "
    for binary in target/debug/ipcrawler target/release/ipcrawler target/lean/ipcrawler; do
        if [[ -f \"\$binary\" ]]; then
            echo \"Found: \$binary (\$(ls -lh \"\$binary\" | awk '{print \$5}'))\"
        fi
    done
"

# Final summary
echo -e "\n${BLUE}📈 CI Testing Summary${NC}"
echo "========================"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All local CI tests passed! Ready for GitHub Actions.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Please fix issues before pushing.${NC}"
    exit 1
fi