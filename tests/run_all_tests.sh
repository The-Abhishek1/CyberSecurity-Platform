#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  🧪 ENTERPRISE TEST SUITE LAUNCHER${NC}"
echo -e "${BLUE}==================================================${NC}"

# Get the absolute path of the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo -e "${YELLOW}Project root: ${PROJECT_ROOT}${NC}"

# Set Python path to include project root
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"
echo -e "${YELLOW}PYTHONPATH set to: ${PYTHONPATH}${NC}"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found${NC}"
    exit 1
fi

# Create menu
show_menu() {
    echo -e "\n${YELLOW}Select test option:${NC}"
    echo "1) Run All Tests (Unit + Integration + Performance)"
    echo "2) Run Unit Tests Only (Simple Runner)"
    echo "3) Run Integration Tests Only (Simple Runner)"
    echo "4) Run Performance Tests Only (Simple Runner)"
    echo "5) Run Specific Test (Simple Runner)"
    echo "6) Run with pytest (All Tests)"
    echo "7) Fix Test Structure (Create __init__.py files)"
    echo "8) Exit"
    echo -n "Choice (1-8): "
}

# Run specific test with simple runner
run_specific_test() {
    echo -e "\n${YELLOW}Available test modules:${NC}"
    echo "UNIT TESTS:"
    echo "  1) Adaptive Scanner"
    echo "  2) Auto Scaler"
    echo "  3) API Gateway"
    echo "  4) Data Masking"
    echo "  5) Vulnerability Predictor"
    echo "  6) Tool Recommender"
    echo "  7) Tenant Manager"
    echo "  8) Billing"
    echo "INTEGRATION TESTS:"
    echo "  9) Full Workflow"
    echo "PERFORMANCE TESTS:"
    echo " 10) Load Scaling"
    echo -n "Select test (1-10): "
    read test_choice
    
    case $test_choice in
        1) module="tests.unit.autonomous.test_adaptive_scanner" ;;
        2) module="tests.unit.autonomous.test_auto_scaler" ;;
        3) module="tests.unit.gateway.test_api_gateway" ;;
        4) module="tests.unit.governance.test_masking" ;;
        5) module="tests.unit.predictive.test_vulnerability_predictor" ;;
        6) module="tests.unit.recommendation.test_tool_recommender" ;;
        7) module="tests.unit.tenant.test_tenant_manager" ;;
        8) module="tests.unit.tenant.test_billing" ;;
        9) module="tests.integration.test_full_workflow" ;;
        10) module="tests.performance.test_load_scaling" ;;
        *) echo -e "${RED}Invalid choice${NC}"; return ;;
    esac
    
    echo -e "\n${GREEN}Running ${module}...${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
    
    python3 -c "
import asyncio
import sys
sys.path.insert(0, '${PROJECT_ROOT}')
try:
    module = __import__('${module}', fromlist=['manual_test'])
    if hasattr(module, 'manual_test'):
        asyncio.run(module.manual_test())
    else:
        print(f'❌ No manual_test function found')
except Exception as e:
    print(f'❌ Error: {e}')
"
}

# Run tests by category
run_category() {
    category=$1
    echo -e "\n${GREEN}Running ${category} tests...${NC}"
    
    python3 -c "
import asyncio
import sys
sys.path.insert(0, '${PROJECT_ROOT}')
from run_all_tests import TestRunner

async def run_category():
    runner = TestRunner()
    await runner.run_category('${category}')
    if runner.failed_tests:
        sys.exit(1)

asyncio.run(run_category())
"
}

# Fix test structure
fix_structure() {
    echo -e "\n${GREEN}Fixing test structure...${NC}"
    
    cd "${PROJECT_ROOT}"
    
    # Create __init__.py files
    touch tests/__init__.py
    touch tests/unit/__init__.py
    touch tests/unit/autonomous/__init__.py
    touch tests/unit/gateway/__init__.py
    touch tests/unit/governance/__init__.py
    touch tests/unit/predictive/__init__.py
    touch tests/unit/recommendation/__init__.py
    touch tests/unit/tenant/__init__.py
    touch tests/integration/__init__.py
    touch tests/performance/__init__.py
    
    # Rename file if it exists with old name
    if [ -f tests/unit/recommendation/test_tool_remmender.py ]; then
        mv tests/unit/recommendation/test_tool_remmender.py tests/unit/recommendation/test_tool_recommender.py
        echo -e "${GREEN}✅ Renamed test_tool_remmender.py to test_tool_recommender.py${NC}"
    fi
    
    echo -e "${GREEN}✅ Test structure fixed!${NC}"
}

# Main loop
while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            echo -e "\n${GREEN}Running all tests with simple runner...${NC}"
            python3 "${PROJECT_ROOT}/run_all_tests.py"
            ;;
        2)
            run_category "unit"
            ;;
        3)
            run_category "integration"
            ;;
        4)
            run_category "performance"
            ;;
        5)
            run_specific_test
            ;;
        6)
            echo -e "\n${GREEN}Running all tests with pytest...${NC}"
            cd "${PROJECT_ROOT}"
            python3 -m pytest tests/ -v
            ;;
        7)
            fix_structure
            ;;
        8)
            echo -e "\n${BLUE}Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid choice${NC}"
            ;;
    esac
    
    echo -e "\n${YELLOW}Press Enter to continue...${NC}"
    read
done