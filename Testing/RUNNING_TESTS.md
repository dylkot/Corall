# How to Run Tests

## Quick Start

From the project root directory:

```bash
# Run all tests with coverage (recommended)
./run_tests.sh

# Or run directly with pytest
python -m pytest Testing/
```

## The Recommended Test Command

The most general and useful command for testing the package is:

```bash
python -m pytest Testing/ --cov=src --cov-report=term --cov-report=html -v
```

### Command Breakdown

Let's break down each part:

#### `python -m pytest`
- Runs pytest as a Python module (more reliable than just `pytest`)
- Ensures correct Python environment is used
- Works consistently across different setups

#### `Testing/`
- Specifies the directory containing test files
- Pytest will discover all `test_*.py` files in this directory
- Follows the naming convention in `pytest.ini`

#### `--cov=src`
- Measures code coverage for the `src/` directory
- Shows which lines of your source code are tested
- Helps identify untested code paths

#### `--cov-report=term`
- Displays coverage summary in the terminal
- Shows percentage coverage for each module
- Quick overview of test coverage

#### `--cov-report=html`
- Generates detailed HTML coverage report
- Saved to `Testing/htmlcov/index.html`
- Interactive browser view with line-by-line coverage
- Highlights which specific lines are/aren't covered

#### `-v` (optional but recommended)
- Verbose output
- Shows individual test names as they run
- Makes it easier to identify which test failed
- Can use `-vv` for even more detail

## Using the Test Runner Script

The `run_tests.sh` script provides convenient shortcuts:

```bash
# Standard run (with coverage)
./run_tests.sh

# Quick run (no coverage, faster)
./run_tests.sh -q

# Verbose output
./run_tests.sh -v

# Fast mode (parallel execution)
./run_tests.sh -f

# Show help
./run_tests.sh -h
```

## Common Testing Scenarios

### 1. Development Workflow
When actively developing, run tests frequently:

```bash
# Quick feedback loop (no coverage)
python -m pytest Testing/ -v

# Or
./run_tests.sh -q
```

### 2. Before Committing
Run full test suite with coverage:

```bash
# Full test suite
./run_tests.sh

# View coverage report
open Testing/htmlcov/index.html  # macOS
```

### 3. Run Specific Tests
Test only what you're working on:

```bash
# Single test file
python -m pytest Testing/test_openalex_client.py -v

# Single test class
python -m pytest Testing/test_openalex_client.py::TestJournalCaching -v

# Single test function
python -m pytest Testing/test_openalex_client.py::TestJournalCaching::test_journal_cache_save_and_load -v
```

### 4. Run by Test Marker
Use markers to run specific test categories:

```bash
# Only unit tests (fast)
python -m pytest Testing/ -m unit -v

# Skip slow tests
python -m pytest Testing/ -m "not slow" -v

# Only integration tests
python -m pytest Testing/ -m integration -v
```

### 5. Debug Failed Tests
Get detailed output for debugging:

```bash
# Stop at first failure
python -m pytest Testing/ -x -v

# Show local variables on failure
python -m pytest Testing/ -l -v

# Show print statements
python -m pytest Testing/ -s -v

# Detailed traceback
python -m pytest Testing/ --tb=long -v
```

### 6. Check Coverage
Focus on improving coverage:

```bash
# Show missing line numbers
python -m pytest Testing/ --cov=src --cov-report=term-missing

# Coverage for specific module
python -m pytest Testing/ --cov=src.openalex_client --cov-report=term
```

### 7. Continuous Integration
For CI/CD pipelines:

```bash
# CI-friendly output
python -m pytest Testing/ --cov=src --cov-report=xml -v

# With JUnit XML for test reports
python -m pytest Testing/ --cov=src --junitxml=test-results.xml
```

## Understanding Test Output

### Success Output
```
============================= test session starts ==============================
collected 45 items

Testing/test_openalex_client.py::TestOpenAlexClientInit::test_init_basic PASSED
Testing/test_openalex_client.py::TestOpenAlexClientInit::test_init_with_email PASSED
...

============================== 45 passed in 2.34s ===============================
```

### Coverage Report
```
Name                               Stmts   Miss  Cover
------------------------------------------------------
src/openalex_client.py               150     10    93%
src/citation_scorer.py               120      5    96%
src/similarity_engine.py             100      8    92%
src/zotero_client.py                  80      3    96%
------------------------------------------------------
TOTAL                                450     26    94%
```

### Failure Output
```
FAILED Testing/test_openalex_client.py::TestJournalCaching::test_find_source_caching
    AssertionError: assert 2 == 1
    Expected mock to be called once, but was called 2 times
```

## Pytest Configuration

All pytest settings are in `Testing/pytest.ini`:

- Test discovery patterns
- Default command-line options
- Test markers
- Output formatting

Modify this file to change default behavior.

## Tips for Effective Testing

1. **Run tests often during development**
   - Catch bugs early
   - Faster feedback loop

2. **Use coverage to find gaps**
   - Aim for >80% coverage
   - Focus on critical paths first

3. **Keep tests fast**
   - Mock external API calls
   - Use fixtures for setup
   - Run full suite less frequently

4. **Read test names to understand behavior**
   - Tests serve as documentation
   - Good test names explain expected behavior

5. **Fix failing tests immediately**
   - Don't accumulate technical debt
   - Failing tests lose value quickly

## Troubleshooting

### "No module named pytest"
```bash
pip install pytest pytest-cov pytest-mock
```

### "Import errors in tests"
```bash
# Make sure you're in project root
cd /path/to/Corall
python -m pytest Testing/
```

### "Tests not discovered"
```bash
# Check pytest.ini is in Testing/ directory
# Ensure test files match pattern: test_*.py
```

### "Coverage not working"
```bash
pip install pytest-cov
python -m pytest Testing/ --cov=src
```

## Additional Resources

- Run `./run_tests.sh -h` for script options
- See `Testing/TESTING_README.md` for comprehensive documentation
- Check `Testing/pytest.ini` for configuration details
