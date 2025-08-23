#!/bin/bash

# GitHub Actions Workflow Validation Script
# Uses GitHub CLI to validate and test workflow

set -e

echo "🔍 GitHub Actions Workflow Validation"
echo "====================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Not in a git repository${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Checking GitHub CLI authentication...${NC}"
if ! gh auth status > /dev/null 2>&1; then
    echo -e "${RED}❌ GitHub CLI not authenticated. Run: gh auth login${NC}"
    exit 1
fi
echo -e "${GREEN}✅ GitHub CLI authenticated${NC}"

echo -e "\n${YELLOW}📝 Validating workflow files...${NC}"

# Check if workflow file exists
WORKFLOW_FILE=".github/workflows/ci.yml"
if [[ ! -f "$WORKFLOW_FILE" ]]; then
    echo -e "${RED}❌ Workflow file not found: $WORKFLOW_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Workflow file found: $WORKFLOW_FILE${NC}"

# Basic YAML syntax check
echo -e "\n${YELLOW}🔍 Basic YAML syntax validation...${NC}"
if python3 -c "
import sys
try:
    with open('$WORKFLOW_FILE', 'r') as f:
        content = f.read()
        # Check for basic GitHub Actions structure
        required_keys = ['name:', 'on:', 'jobs:']
        for key in required_keys:
            if key not in content:
                raise Exception(f'Missing required key: {key}')
        print('✅ Basic workflow structure valid')
except Exception as e:
    print(f'❌ Workflow structure error: {e}')
    sys.exit(1)
"; then
    echo -e "${GREEN}✅ Workflow structure validation passed${NC}"
else
    echo -e "${RED}❌ Workflow structure validation failed${NC}"
    exit 1
fi

# Check if we can list workflows (requires repo to be on GitHub)
echo -e "\n${YELLOW}📋 Checking GitHub repository workflows...${NC}"
if gh workflow list > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Repository found on GitHub${NC}"
    echo "Available workflows:"
    gh workflow list
    
    # If we have workflows, we can potentially trigger them
    echo -e "\n${YELLOW}ℹ️  You can manually trigger workflows with:${NC}"
    echo "   gh workflow run ci.yml"
    echo "   gh run list  # to see run history"
    echo "   gh run view <run-id>  # to see specific run details"
    
else
    echo -e "${YELLOW}⚠️  Repository not found on GitHub or no workflows available${NC}"
    echo "This is normal for local testing. Push to GitHub to see workflows."
fi

echo -e "\n${YELLOW}📊 Workflow analysis:${NC}"

# Count jobs in workflow
job_count=$(grep -c "^  [a-zA-Z][a-zA-Z0-9_-]*:" "$WORKFLOW_FILE" || echo "0")
echo "  Jobs defined: $job_count"

# List job names
echo "  Job names:"
grep "^  [a-zA-Z][a-zA-Z0-9_-]*:" "$WORKFLOW_FILE" | sed 's/://' | sed 's/^/    - /'

# Check for matrix builds
if grep -q "strategy:" "$WORKFLOW_FILE"; then
    echo -e "${GREEN}  ✅ Matrix builds configured${NC}"
else
    echo -e "${YELLOW}  ⚠️  No matrix builds found${NC}"
fi

# Check for caching
if grep -q "actions/cache" "$WORKFLOW_FILE"; then
    echo -e "${GREEN}  ✅ Caching configured${NC}"
else
    echo -e "${YELLOW}  ⚠️  No caching configured${NC}"
fi

# Check for artifact uploads
if grep -q "actions/upload-artifact" "$WORKFLOW_FILE"; then
    echo -e "${GREEN}  ✅ Artifact uploads configured${NC}"
else
    echo -e "${YELLOW}  ⚠️  No artifact uploads configured${NC}"
fi

echo -e "\n${GREEN}✅ Workflow validation completed${NC}"

echo -e "\n${YELLOW}💡 Next steps:${NC}"
echo "1. Run local CI tests: ./scripts/test-ci-locally.sh"
echo "2. Commit and push to trigger GitHub Actions"
echo "3. Monitor with: gh run list --workflow=ci.yml"
echo "4. View logs with: gh run view <run-id>"