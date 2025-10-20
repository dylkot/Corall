#!/bin/bash
#
# Test runner for Corall
#
# Usage:
#   ./run_tests.sh              # Run all tests with coverage
#   ./run_tests.sh -q           # Quick run (no coverage)
#   ./run_tests.sh -v           # Verbose output
#   ./run_tests.sh -f           # Fast (parallel execution)
#   ./run_tests.sh -h           # Show help

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default options
COVERAGE=true
VERBOSE=""
PARALLEL=""

# Parse arguments
while getopts "qvfh" opt; do
  case $opt in
    q)
      COVERAGE=false
      echo -e "${YELLOW}Running quick tests (no coverage)${NC}"
      ;;
    v)
      VERBOSE="-vv"
      echo -e "${YELLOW}Running with verbose output${NC}"
      ;;
    f)
      PARALLEL="-n auto"
      echo -e "${YELLOW}Running tests in parallel${NC}"
      ;;
    h)
      echo "Usage: $0 [-q] [-v] [-f] [-h]"
      echo "  -q  Quick mode (no coverage)"
      echo "  -v  Verbose output"
      echo "  -f  Fast mode (parallel execution, requires pytest-xdist)"
      echo "  -h  Show this help"
      exit 0
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

echo -e "${GREEN}Running Corall test suite...${NC}\n"

# Build the pytest command
PYTEST_CMD="python -m pytest Testing/"

# Add options
if [ "$COVERAGE" = true ]; then
  PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=term --cov-report=html"
fi

if [ -n "$VERBOSE" ]; then
  PYTEST_CMD="$PYTEST_CMD $VERBOSE"
fi

if [ -n "$PARALLEL" ]; then
  PYTEST_CMD="$PYTEST_CMD $PARALLEL"
fi

# Run tests
echo "Command: $PYTEST_CMD"
echo ""
$PYTEST_CMD

# Show coverage report location if generated
if [ "$COVERAGE" = true ]; then
  echo ""
  echo -e "${GREEN}HTML coverage report generated at: Testing/htmlcov/index.html${NC}"
fi
