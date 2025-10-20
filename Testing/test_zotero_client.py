"""
Pytest tests for ZoteroClient.
"""
import pytest
from unittest.mock import Mock, patch
import os

from src.zotero_client import ZoteroClient


@pytest.mark.unit
class TestZoteroClientInit:
    """Tests for ZoteroClient initialization."""

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_init_success(self, mock_zotero):
        """Test successful initialization."""
        mock_zot = Mock()
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()

        assert client.zot is not None
        assert client.api_key == 'test_key'
        assert client.user_id == 'test_user'
        assert client.library_type == 'user'
        mock_zotero.assert_called_once_with('test_user', 'user', 'test_key')

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.zotero_client.load_dotenv')
    def test_init_missing_credentials(self, mock_load_dotenv):
        """Test initialization with missing credentials."""
        # Mock load_dotenv to do nothing (prevent loading from .env file)
        mock_load_dotenv.return_value = None

        with pytest.raises(ValueError, match="API key and user ID required"):
            ZoteroClient()

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': '',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    def test_init_empty_user_id(self):
        """Test initialization with empty user ID."""
        with pytest.raises(ValueError):
            ZoteroClient()


@pytest.mark.unit
class TestParseItem:
    """Tests for parsing Zotero items."""

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_parse_journal_article(self, mock_zotero):
        """Test parsing a journal article."""
        mock_zot = Mock()
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()

        item = {
            'data': {
                'itemType': 'journalArticle',
                'title': 'Sample Paper',
                'abstractNote': 'This is a sample abstract.',
                'DOI': '10.1234/sample',
                'date': '2024-02-20',
                'publicationTitle': 'Journal of Test Studies',
                'key': 'ABC123',
                'creators': [
                    {'creatorType': 'author', 'firstName': 'Alice', 'lastName': 'Johnson'},
                    {'creatorType': 'author', 'firstName': 'Bob', 'lastName': 'Williams'}
                ]
            }
        }

        parsed = client._parse_item(item)

        assert parsed is not None
        assert parsed['title'] == 'Sample Paper'
        assert parsed['doi'] == '10.1234/sample'
        assert 'sample abstract' in parsed['abstract']
        assert parsed['year'] == '2024'
        assert parsed['publication'] == 'Journal of Test Studies'
        assert parsed['zotero_key'] == 'ABC123'
        assert len(parsed['authors']) == 2
        assert 'Alice Johnson' in parsed['authors']
        assert 'Bob Williams' in parsed['authors']

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_parse_invalid_type(self, mock_zotero):
        """Test parsing non-article item (should return None)."""
        mock_zot = Mock()
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()

        # Book item (not in valid_types)
        item = {
            'data': {
                'itemType': 'book',
                'title': 'Test Book'
            }
        }

        parsed = client._parse_item(item)
        assert parsed is None

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_parse_no_title(self, mock_zotero):
        """Test parsing item without title (should return None)."""
        mock_zot = Mock()
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()

        item = {
            'data': {
                'itemType': 'journalArticle',
                'title': ''
            }
        }

        parsed = client._parse_item(item)
        assert parsed is None

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_parse_date_formats(self, mock_zotero):
        """Test parsing different date formats."""
        mock_zot = Mock()
        mock_zotero.return_value = mock_zot
        client = ZoteroClient()

        # Full date
        item1 = {
            'data': {
                'itemType': 'journalArticle',
                'title': 'Paper 1',
                'date': '2024-05-15'
            }
        }
        assert client._parse_item(item1)['year'] == '2024'

        # Year only
        item2 = {
            'data': {
                'itemType': 'journalArticle',
                'title': 'Paper 2',
                'date': '2023'
            }
        }
        assert client._parse_item(item2)['year'] == '2023'

        # No date
        item3 = {
            'data': {
                'itemType': 'journalArticle',
                'title': 'Paper 3'
            }
        }
        assert client._parse_item(item3)['year'] is None


@pytest.mark.unit
class TestExtractAuthors:
    """Tests for author extraction."""

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_extract_authors(self, mock_zotero):
        """Test extracting author names."""
        mock_zot = Mock()
        mock_zotero.return_value = mock_zot
        client = ZoteroClient()

        creators = [
            {'creatorType': 'author', 'firstName': 'John', 'lastName': 'Doe'},
            {'creatorType': 'author', 'firstName': 'Jane', 'lastName': 'Smith'},
            {'creatorType': 'editor', 'firstName': 'Bob', 'lastName': 'Editor'}  # Not an author
        ]

        authors = client._extract_authors(creators)

        assert len(authors) == 2
        assert 'John Doe' in authors
        assert 'Jane Smith' in authors
        assert 'Bob Editor' not in authors


@pytest.mark.unit
class TestCollections:
    """Tests for collection operations."""

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_list_collections(self, mock_zotero):
        """Test listing all collections."""
        mock_zot = Mock()
        mock_collections = [
            {'data': {'key': 'COL1', 'name': 'My Papers'}},
            {'data': {'key': 'COL2', 'name': 'Research'}}
        ]
        mock_zot.collections.return_value = mock_collections
        mock_zot.num_collectionitems.return_value = 5
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()
        collections = client.list_collections()

        assert len(collections) == 2
        assert collections[0]['id'] == 'COL1'
        assert collections[0]['name'] == 'My Papers'
        assert collections[1]['id'] == 'COL2'
        assert collections[1]['name'] == 'Research'

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_find_collection_by_name_exact(self, mock_zotero):
        """Test finding collection by exact name."""
        mock_zot = Mock()
        mock_collections = [
            {'data': {'key': 'COL1', 'name': 'My Papers'}},
            {'data': {'key': 'COL2', 'name': 'Other Papers'}}
        ]
        mock_zot.collections.return_value = mock_collections
        mock_zot.num_collectionitems.return_value = 5
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()
        result = client.find_collection_by_name('My Papers')

        assert result == 'COL1'

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_find_collection_case_insensitive(self, mock_zotero):
        """Test case-insensitive collection lookup."""
        mock_zot = Mock()
        mock_collections = [
            {'data': {'key': 'COL1', 'name': 'My Papers'}}
        ]
        mock_zot.collections.return_value = mock_collections
        mock_zot.num_collectionitems.return_value = 5
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()
        result = client.find_collection_by_name('my papers')

        assert result == 'COL1'

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_find_collection_partial_match(self, mock_zotero):
        """Test partial match collection lookup."""
        mock_zot = Mock()
        mock_collections = [
            {'data': {'key': 'COL1', 'name': 'My Research Papers'}}
        ]
        mock_zot.collections.return_value = mock_collections
        mock_zot.num_collectionitems.return_value = 5
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()
        result = client.find_collection_by_name('Research')

        assert result == 'COL1'

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_find_collection_not_found(self, mock_zotero):
        """Test collection not found."""
        mock_zot = Mock()
        mock_collections = [
            {'data': {'key': 'COL1', 'name': 'My Papers'}}
        ]
        mock_zot.collections.return_value = mock_collections
        mock_zot.num_collectionitems.return_value = 5
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()
        result = client.find_collection_by_name('Nonexistent')

        assert result is None


@pytest.mark.unit
class TestLibraryStats:
    """Tests for library statistics."""

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_get_stats(self, mock_zotero):
        """Test getting library statistics."""
        mock_zot = Mock()
        mock_items = [
            {
                'data': {
                    'itemType': 'journalArticle',
                    'title': 'Paper 1',
                    'DOI': '10.1234/1',
                    'abstractNote': 'Abstract 1',
                    'creators': [
                        {'creatorType': 'author', 'firstName': 'John', 'lastName': 'Doe'}
                    ]
                }
            },
            {
                'data': {
                    'itemType': 'journalArticle',
                    'title': 'Paper 2',
                    'creators': [
                        {'creatorType': 'author', 'firstName': 'Jane', 'lastName': 'Smith'},
                        {'creatorType': 'author', 'firstName': 'John', 'lastName': 'Doe'}  # Duplicate
                    ]
                }
            }
        ]
        mock_zot.everything.return_value = mock_items
        mock_zot.top.return_value = mock_items
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()
        stats = client.get_library_stats()

        assert stats['total_papers'] == 2
        assert stats['papers_with_doi'] == 1
        assert stats['papers_with_abstract'] == 1
        assert stats['unique_authors'] == 2  # John Doe and Jane Smith

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_get_stats_empty_library(self, mock_zotero):
        """Test statistics with empty library."""
        mock_zot = Mock()
        mock_zot.everything.return_value = []
        mock_zot.top.return_value = []
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()
        stats = client.get_library_stats()

        assert stats['total_papers'] == 0
        assert stats['papers_with_doi'] == 0
        assert stats['unique_authors'] == 0


@pytest.mark.unit
class TestFetchLibrary:
    """Tests for fetching library items."""

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_fetch_library_all(self, mock_zotero):
        """Test fetching all library items."""
        mock_zot = Mock()
        mock_items = [
            {'data': {'itemType': 'journalArticle', 'title': 'Paper 1'}},
            {'data': {'itemType': 'journalArticle', 'title': 'Paper 2'}}
        ]
        mock_zot.everything.return_value = mock_items
        mock_zot.top.return_value = mock_items
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()
        items = client.fetch_library()

        assert len(items) == 2
        mock_zot.top.assert_called_once()

    @patch.dict(os.environ, {
        'ZOTERO_API_KEY': 'test_key',
        'ZOTERO_USER_ID': 'test_user',
        'ZOTERO_LIBRARY_TYPE': 'user'
    })
    @patch('src.zotero_client.zotero.Zotero')
    def test_fetch_library_with_collection(self, mock_zotero):
        """Test fetching items from specific collection."""
        mock_zot = Mock()
        mock_items = [
            {'data': {'itemType': 'journalArticle', 'title': 'Paper 1'}}
        ]
        mock_zot.everything.return_value = mock_items
        mock_zot.collection_items.return_value = mock_items
        mock_zotero.return_value = mock_zot

        client = ZoteroClient()
        items = client.fetch_library(collection_id='COL123')

        assert len(items) == 1
        mock_zot.collection_items.assert_called_once_with('COL123', limit=None)
