# Corall Testing Suite

Comprehensive pytest-based testing suite for the Corall paper recommendation engine.

## Overview

The testing suite uses **pytest** and includes unit tests for all core components:
- `OpenAlexClient` - API interactions and caching
- `CitationScorer` - Citation network building and scoring
- `SimilarityEngine` - Embedding generation and similarity computation
- `ZoteroClient` - Library fetching and parsing

## Installation

### Install pytest and dependencies

```bash
pip install pytest pytest-cov pytest-mock
```

Or add to `requirements.txt`:
```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1
```

## Running Tests

### Run all tests
```bash
# From project root
pytest Testing/

# With verbose output
pytest Testing/ -v

# With even more detail
pytest Testing/ -vv
```

### Run specific test file
```bash
pytest Testing/test_openalex_client.py
pytest Testing/test_citation_scorer.py
pytest Testing/test_similarity_engine.py
pytest Testing/test_zotero_client.py
```

### Run specific test class or function
```bash
# Run one test class
pytest Testing/test_openalex_client.py::TestJournalCaching

# Run one test function
pytest Testing/test_openalex_client.py::TestJournalCaching::test_journal_cache_save_and_load
```

### Run tests by marker
```bash
# Run only unit tests
pytest Testing/ -m unit

# Run only integration tests
pytest Testing/ -m integration

# Run only slow tests
pytest Testing/ -m slow

# Skip slow tests
pytest Testing/ -m "not slow"
```

## Coverage Reports

### Generate coverage report
```bash
# Terminal report
pytest Testing/ --cov=src --cov-report=term

# HTML report (more detailed)
pytest Testing/ --cov=src --cov-report=html

# Open HTML report
open Testing/htmlcov/index.html  # macOS
xdg-open Testing/htmlcov/index.html  # Linux
```

### Coverage with missing lines
```bash
pytest Testing/ --cov=src --cov-report=term-missing
```

## Test Organization

### Directory Structure
```
Testing/
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                     # Pytest configuration
├── test_openalex_client.py        # OpenAlex API tests
├── test_citation_scorer.py        # Citation scoring tests
├── test_similarity_engine.py      # Similarity computation tests
├── test_zotero_client.py          # Zotero integration tests
├── TESTING_README.md              # This file
├── exploration_notebook.ipynb     # Interactive exploration
└── Test_Data/                     # Test data (gitignored)
```

### Test Markers

Tests are organized with markers:

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (may call real APIs)
- `@pytest.mark.slow` - Slow tests (take >1 second)
- `@pytest.mark.api` - Tests that make actual API calls (not mocked)

## Fixtures

Shared fixtures are defined in `conftest.py`:

### Common Fixtures
- `temp_cache_dir` - Temporary directory for cache testing
- `mock_openalex_work` - Sample OpenAlex work data
- `mock_zotero_item` - Sample Zotero item data
- `sample_library_papers` - Sample library papers for testing
- `sample_candidate_papers` - Sample candidate papers
- `mock_citation_network` - Sample citation network data
- `mock_embeddings` - Sample embeddings (numpy arrays)
- `mock_journal_cache` - Sample journal cache data

### Using Fixtures

```python
def test_something(temp_cache_dir, mock_openalex_work):
    client = OpenAlexClient(cache_dir=temp_cache_dir)
    result = client._parse_work(mock_openalex_work)
    assert result['title'] == 'Sample Research Paper'
```

## Writing New Tests

### Test File Template

```python
"""
Pytest tests for YourComponent.
"""
import pytest
from unittest.mock import Mock, patch

from src.your_component import YourComponent


@pytest.mark.unit
class TestYourComponentInit:
    \"\"\"Tests for initialization.\"\"\"

    def test_init(self):
        \"\"\"Test basic initialization.\"\"\"
        component = YourComponent()
        assert component is not None


@pytest.mark.unit
class TestYourComponentMethod:
    \"\"\"Tests for specific method.\"\"\"

    def test_method_success(self):
        \"\"\"Test successful method call.\"\"\"
        component = YourComponent()
        result = component.method()
        assert result == expected_value

    def test_method_error(self):
        \"\"\"Test method error handling.\"\"\"
        component = YourComponent()
        with pytest.raises(ValueError):
            component.method(invalid_input)
```

### Testing Best Practices

1. **Use descriptive test names**
   - Good: `test_cache_rebuilds_with_higher_citation_limit`
   - Bad: `test_cache_1`

2. **One assertion per test** (when possible)
   - Makes failures easier to diagnose

3. **Use fixtures for setup**
   - Don't repeat setup code
   - Define reusable fixtures in `conftest.py`

4. **Mock external dependencies**
   - Use `@patch` for API calls
   - Use `Mock()` for complex objects

5. **Test edge cases**
   - Empty inputs
   - None values
   - Invalid data
   - Error conditions

6. **Group related tests in classes**
   - Better organization
   - Easier to run related tests together

## Mocking Examples

### Mock API calls
```python
@patch.object(OpenAlexClient, '_make_request')
def test_api_call(mock_request):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'results': []}
    mock_request.return_value = mock_response

    client = OpenAlexClient()
    results = client.get_citations('W123')
    assert len(results) == 0
```

### Mock file operations
```python
@patch('builtins.open', create=True)
def test_file_read(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = 'data'
    # Your test code here
```

### Mock environment variables
```python
@patch.dict(os.environ, {'VAR': 'value'})
def test_with_env():
    # Environment variable is set for this test
    pass
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: pytest Testing/ --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests not found

```bash
# Make sure you're in the project root
cd /path/to/Corall

# Run with test discovery
pytest Testing/ -v
```

### Import errors

```bash
# Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/Corall"

# Or run from project root
cd /path/to/Corall && pytest Testing/
```

### Mock not working

- Ensure you're patching the right location
- Use `@patch('module.where.used')` not `@patch('module.where.defined')`

### Fixture not found

- Check `conftest.py` is in the Testing directory
- Ensure fixture is defined before use
- Check fixture scope (function/class/module/session)

## Performance Tips

### Speed up tests

```bash
# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest Testing/ -n auto

# Run only failed tests
pytest Testing/ --lf

# Run tests that failed first, then others
pytest Testing/ --ff

# Stop after first failure
pytest Testing/ -x

# Stop after N failures
pytest Testing/ --maxfail=3
```

### Cache test results

```bash
# Use pytest cache
pytest Testing/ --cache-clear  # Clear cache
pytest Testing/ --cache-show   # Show cache contents
```

## Resources

- [Pytest documentation](https://docs.pytest.org/)
- [Pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Pytest markers](https://docs.pytest.org/en/stable/mark.html)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Run existing tests to ensure nothing breaks
3. Add new tests for your feature
4. Ensure coverage doesn't decrease
5. Document any new fixtures or markers

---

Happy testing! 🧪
