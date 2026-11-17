#!/bin/bash
# Script to run Odoo 17 verification tests

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Odoo 17 AsyncOdooUI Test Suite ===${NC}\n"

# Check if environment variables are set
if [ -z "$ODOO_URL" ]; then
    echo -e "${RED}Error: ODOO_URL not set${NC}"
    echo "Usage:"
    echo "  export ODOO_URL='https://integration.cc1.vn'"
    echo "  export ODOO_USER='username'"
    echo "  export ODOO_PASSWORD='password'"
    echo "  export ODOO_DB='database'"
    echo "  ./run_odoo17_tests.sh"
    exit 1
fi

if [ -z "$ODOO_USER" ]; then
    echo -e "${RED}Error: ODOO_USER not set${NC}"
    exit 1
fi

if [ -z "$ODOO_PASSWORD" ]; then
    echo -e "${RED}Error: ODOO_PASSWORD not set${NC}"
    exit 1
fi

# Set defaults
ODOO_DB=${ODOO_DB:-"test"}
ODOO_VERSION=${ODOO_VERSION:-17}
HEADLESS=${HEADLESS:-"false"}
SLOW_MO=${SLOW_MO:-0}

# Print configuration
echo "Configuration:"
echo "  URL:      $ODOO_URL"
echo "  User:     $ODOO_USER"
echo "  Database: $ODOO_DB"
echo "  Version:  $ODOO_VERSION"
echo "  Headless: $HEADLESS"
echo "  Slow-Mo:  ${SLOW_MO}ms"
echo ""

# Export for pytest
export ODOO_URL
export ODOO_USER
export ODOO_PASSWORD
export ODOO_DB
export ODOO_VERSION
export HEADLESS
export SLOW_MO

# Determine which tests to run
if [ "$1" == "all" ]; then
    echo -e "${GREEN}Running ALL tests...${NC}\n"
    pytest tests/test_verify_odoo17_functions.py -v --tb=short
elif [ "$1" == "quick" ]; then
    echo -e "${GREEN}Running quick smoke tests...${NC}\n"
    pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Navigation -v --tb=short
    pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_AppNavigation -v --tb=short
elif [ "$1" == "forms" ]; then
    echo -e "${GREEN}Running form tests...${NC}\n"
    pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions -v --tb=short
    pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations -v --tb=short
elif [ "$1" == "list" ]; then
    echo -e "${GREEN}Running list view tests...${NC}\n"
    pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_ListViewOperations -v --tb=short
elif [ "$1" == "modals" ]; then
    echo -e "${GREEN}Running modal & notification tests...${NC}\n"
    pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Modals -v --tb=short
    pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Notifications -v --tb=short
else
    # Default: run specific problematic tests
    echo -e "${GREEN}Running key tests that need Odoo 17 fixes...${NC}\n"
    echo "Test groups:"
    echo "  - Navigation (basic)"
    echo "  - Form Actions (button clicks)"
    echo "  - Field Operations (get/set)"
    echo "  - List View (searching, pagination)"
    echo ""

    pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Navigation \
            tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_AppNavigation \
            tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions \
            tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations \
            tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_ListViewOperations \
            -v --tb=short
fi

echo ""
echo -e "${GREEN}=== Test Run Complete ===${NC}"
echo ""
echo "Notes:"
echo "  - Review the detailed issue document at:"
echo "    /private/tmp/claude-501/-Users-mac-Documents-Code/.../ODOO17_FIXES_NEEDED.md"
echo ""
echo "  - To see details, use: pytest -vvs"
echo "  - To stop on first failure: pytest -x"
echo "  - To show print statements: pytest -s"


