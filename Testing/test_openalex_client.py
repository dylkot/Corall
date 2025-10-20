"""
Pytest tests for OpenAlexClient.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pickle
import os

from src.openalex_client import OpenAlexClient


@pytest.mark.unit
class TestOpenAlexClientInit:
    """Tests for OpenAlexClient initialization."""

    def test_init_basic(self, temp_cache_dir):
        """Test basic client initialization."""
        client = OpenAlexClient(cache_dir=temp_cache_dir)

        assert client.session is not None
        assert client.cache_dir == temp_cache_dir
        assert isinstance(client.journal_cache, dict)
        assert len(client.journal_cache) == 0

    def test_init_with_email(self, temp_cache_dir):
        """Test initialization with email for polite pool."""
        client = OpenAlexClient(email="test@example.com", cache_dir=temp_cache_dir)

        assert "mailto:test@example.com" in client.session.headers['User-Agent']


@pytest.mark.unit
class TestJournalCaching:
    """Tests for journal name-to-ID caching."""

    def test_journal_cache_save_and_load(self, temp_cache_dir, mock_journal_cache):
        """Test journal cache persistence."""
        # Create client and populate cache
        client = OpenAlexClient(cache_dir=temp_cache_dir)
        client.journal_cache = mock_journal_cache
        client._save_journal_cache()

        # Create new client and verify cache loaded
        new_client = OpenAlexClient(cache_dir=temp_cache_dir)
        assert new_client.journal_cache == mock_journal_cache

    def test_empty_cache_loading(self, temp_cache_dir):
        """Test loading when no cache exists."""
        client = OpenAlexClient(cache_dir=temp_cache_dir)
        assert client.journal_cache == {}

    @patch.object(OpenAlexClient, '_make_request')
    def test_find_source_caching(self, mock_request, temp_cache_dir):
        """Test that journal lookups are cached."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [{
                'id': 'https://openalex.org/S123',
                'display_name': 'Nature',
                'issn_l': '0028-0836',
                'issn': ['0028-0836'],
                'type': 'journal'
            }]
        }
        mock_request.return_value = mock_response

        client = OpenAlexClient(cache_dir=temp_cache_dir)

        # First call - should hit API
        result1 = client.find_source_by_name('Nature')
        assert mock_request.call_count == 1
        assert result1['id'] == 'S123'

        # Second call - should use cache
        result2 = client.find_source_by_name('Nature')
        assert mock_request.call_count == 1  # No additional call
        assert result2 == result1

        # Case insensitive - should also use cache
        result3 = client.find_source_by_name('NATURE')
        assert mock_request.call_count == 1
        assert result3 == result1


@pytest.mark.unit
class TestFindWorkByDOI:
    """Tests for finding works by DOI."""

    @patch.object(OpenAlexClient, '_make_request')
    def test_find_work_success(self, mock_request, temp_cache_dir, mock_openalex_work):
        """Test successful work lookup by DOI."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_openalex_work
        mock_request.return_value = mock_response

        client = OpenAlexClient(cache_dir=temp_cache_dir)
        result = client.find_work_by_doi('10.1234/sample')

        assert result is not None
        assert result['openalex_id'] == 'W123456'
        assert result['title'] == 'Sample Research Paper'
        assert result['doi'] == '10.1234/sample'

    @patch.object(OpenAlexClient, '_make_request')
    def test_find_work_not_found(self, mock_request, temp_cache_dir):
        """Test work lookup with invalid DOI."""
        mock_request.return_value = None

        client = OpenAlexClient(cache_dir=temp_cache_dir)
        result = client.find_work_by_doi('invalid-doi')

        assert result is None

    def test_find_work_empty_doi(self, temp_cache_dir):
        """Test with empty DOI."""
        client = OpenAlexClient(cache_dir=temp_cache_dir)
        result = client.find_work_by_doi('')
        assert result is None


@pytest.mark.unit
class TestCitationsAndReferences:
    """Tests for getting citations and references."""

    @patch.object(OpenAlexClient, '_make_request')
    def test_get_citations(self, mock_request, temp_cache_dir):
        """Test getting citations for a work."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'id': 'https://openalex.org/W1', 'title': 'Citing Paper 1'},
                {'id': 'https://openalex.org/W2', 'title': 'Citing Paper 2'}
            ]
        }
        mock_request.return_value = mock_response

        client = OpenAlexClient(cache_dir=temp_cache_dir)
        results = client.get_citations('W123', limit=10)

        assert len(results) == 2
        assert results[0]['openalex_id'] == 'W1'
        assert results[1]['openalex_id'] == 'W2'

    @patch.object(OpenAlexClient, '_make_request')
    def test_get_references(self, mock_request, temp_cache_dir):
        """Test getting references for a work."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'id': 'https://openalex.org/W3', 'title': 'Reference 1'}
            ]
        }
        mock_request.return_value = mock_response

        client = OpenAlexClient(cache_dir=temp_cache_dir)
        results = client.get_references('W123', limit=10)

        assert len(results) == 1
        assert results[0]['openalex_id'] == 'W3'


@pytest.mark.unit
class TestWorkParsing:
    """Tests for parsing OpenAlex work data."""

    def test_parse_complete_work(self, temp_cache_dir, mock_openalex_work):
        """Test parsing a complete work with all fields."""
        client = OpenAlexClient(cache_dir=temp_cache_dir)
        parsed = client._parse_work(mock_openalex_work)

        assert parsed['openalex_id'] == 'W123456'
        assert parsed['title'] == 'Sample Research Paper'
        assert parsed['doi'] == '10.1234/sample'
        assert parsed['publication_year'] == 2024
        assert parsed['journal'] == 'Nature'
        assert len(parsed['authors']) == 2
        assert parsed['authors'][0]['name'] == 'John Doe'
        assert len(parsed['concepts']) == 2
        assert parsed['cited_by_count'] == 42
        assert parsed['open_access'] is True
        assert parsed['abstract'] == 'This is a sample abstract'

    def test_parse_minimal_work(self, temp_cache_dir):
        """Test parsing minimal work with few fields."""
        minimal_work = {
            'id': 'https://openalex.org/W999',
            'title': 'Minimal Paper'
        }

        client = OpenAlexClient(cache_dir=temp_cache_dir)
        parsed = client._parse_work(minimal_work)

        assert parsed['openalex_id'] == 'W999'
        assert parsed['title'] == 'Minimal Paper'
        assert parsed['doi'] == ''
        assert parsed['abstract'] == ''
        assert len(parsed['authors']) == 0

    def test_abstract_reconstruction(self, temp_cache_dir):
        """Test abstract reconstruction from inverted index."""
        work = {
            'abstract_inverted_index': {
                'This': [0],
                'is': [1, 5],
                'a': [2],
                'test': [3],
                'that': [4],
                'working': [6]
            }
        }

        client = OpenAlexClient(cache_dir=temp_cache_dir)
        abstract = client._get_abstract(work)

        assert abstract == 'This is a test that is working'

    def test_empty_abstract(self, temp_cache_dir):
        """Test handling of empty abstract."""
        work = {'abstract_inverted_index': {}}

        client = OpenAlexClient(cache_dir=temp_cache_dir)
        abstract = client._get_abstract(work)

        assert abstract == ''


@pytest.mark.unit
class TestResolveJournalIds:
    """Tests for journal name resolution."""

    @patch.object(OpenAlexClient, 'find_source_by_name')
    def test_resolve_multiple_journals(self, mock_find_source, temp_cache_dir):
        """Test resolving multiple journal names."""
        mock_find_source.side_effect = [
            {'id': 'S1', 'display_name': 'Nature'},
            {'id': 'S2', 'display_name': 'Science'},
            None  # Not found
        ]

        client = OpenAlexClient(cache_dir=temp_cache_dir)
        journal_names = ['Nature', 'Science', 'Unknown Journal']

        result = client.resolve_journal_ids(journal_names)

        assert len(result) == 2
        assert 'S1' in result
        assert 'S2' in result

    @patch.object(OpenAlexClient, 'find_source_by_name')
    def test_resolve_empty_list(self, mock_find_source, temp_cache_dir):
        """Test with empty journal list."""
        client = OpenAlexClient(cache_dir=temp_cache_dir)
        result = client.resolve_journal_ids([])

        assert result == []
        mock_find_source.assert_not_called()
