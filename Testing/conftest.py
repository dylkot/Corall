"""
Pytest configuration and shared fixtures for Corall testing suite.
"""
import pytest
import tempfile
import shutil
import os
import sys
import pickle
import numpy as np
from unittest.mock import Mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_openalex_work():
    """Sample OpenAlex work data."""
    return {
        'id': 'https://openalex.org/W123456',
        'title': 'Sample Research Paper',
        'doi': 'https://doi.org/10.1234/sample',
        'publication_date': '2024-01-15',
        'publication_year': 2024,
        'primary_location': {
            'source': {
                'display_name': 'Nature'
            }
        },
        'authorships': [
            {
                'author': {
                    'display_name': 'John Doe',
                    'id': 'https://openalex.org/A1'
                }
            },
            {
                'author': {
                    'display_name': 'Jane Smith',
                    'id': 'https://openalex.org/A2'
                }
            }
        ],
        'concepts': [
            {'display_name': 'Biology', 'score': 0.9},
            {'display_name': 'Genetics', 'score': 0.8}
        ],
        'cited_by_count': 42,
        'open_access': {
            'is_oa': True,
            'oa_url': 'https://example.com/paper.pdf'
        },
        'abstract_inverted_index': {
            'This': [0],
            'is': [1],
            'a': [2],
            'sample': [3],
            'abstract': [4]
        }
    }


@pytest.fixture
def mock_zotero_item():
    """Sample Zotero item data."""
    return {
        'key': 'ABC123XYZ',
        'version': 1,
        'data': {
            'itemType': 'journalArticle',
            'title': 'Sample Paper from Zotero',
            'DOI': '10.1234/zotero',
            'abstractNote': 'This is a sample abstract from Zotero library.',
            'date': '2024-02-20',
            'publicationTitle': 'Journal of Test Studies',
            'creators': [
                {
                    'creatorType': 'author',
                    'firstName': 'Alice',
                    'lastName': 'Johnson'
                },
                {
                    'creatorType': 'author',
                    'firstName': 'Bob',
                    'lastName': 'Williams'
                }
            ],
            'tags': [
                {'tag': 'machine learning'},
                {'tag': 'biology'}
            ]
        }
    }


@pytest.fixture
def sample_library_papers():
    """Sample library papers for testing."""
    return [
        {
            'title': 'Paper 1: Machine Learning in Biology',
            'abstract': 'This paper discusses machine learning applications in biological research.',
            'doi': '10.1234/paper1',
            'year': '2023',
            'authors': ['Alice Johnson', 'Bob Smith'],
            'journal': 'Nature',
            'zotero_key': 'KEY1'
        },
        {
            'title': 'Paper 2: Genomic Analysis Methods',
            'abstract': 'Novel methods for genomic data analysis and interpretation.',
            'doi': '10.1234/paper2',
            'year': '2023',
            'authors': ['Charlie Brown', 'Diana Prince'],
            'journal': 'Science',
            'zotero_key': 'KEY2'
        },
        {
            'title': 'Paper 3: Protein Structure Prediction',
            'abstract': 'Advanced techniques for predicting protein structures.',
            'doi': '10.1234/paper3',
            'year': '2024',
            'authors': ['Eve Wilson'],
            'journal': 'Cell',
            'zotero_key': 'KEY3'
        }
    ]


@pytest.fixture
def sample_candidate_papers():
    """Sample candidate papers for recommendation testing."""
    return [
        {
            'title': 'New ML Applications in Biology',
            'abstract': 'Exploring new machine learning methods for biological data.',
            'openalex_id': 'W1001',
            'doi': '10.5678/candidate1',
            'publication_date': '2024-10-01',
            'authors': [{'name': 'New Author 1'}]
        },
        {
            'title': 'Genomic Data Processing',
            'abstract': 'Efficient processing pipelines for large genomic datasets.',
            'openalex_id': 'W1002',
            'doi': '10.5678/candidate2',
            'publication_date': '2024-10-05',
            'authors': [{'name': 'New Author 2'}]
        }
    ]


@pytest.fixture
def mock_citation_network():
    """Sample citation network data."""
    return {
        'network': {'W123', 'W456', 'W789', 'W1001'},
        'id_map': {
            'KEY1': 'W123',
            'KEY2': 'W456',
            'KEY3': 'W789'
        },
        'build_params': {
            'max_citations': 20,
            'max_references': 20,
            'num_papers': 3
        }
    }


@pytest.fixture
def mock_embeddings():
    """Sample embeddings for similarity testing."""
    return np.array([
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
        [0.9, 0.1, 0.2, 0.3]
    ])


@pytest.fixture
def mock_journal_cache():
    """Sample journal cache data."""
    return {
        'nature': {
            'id': 'S137773608',
            'display_name': 'Nature',
            'issn_l': '0028-0836',
            'issn': ['0028-0836', '1476-4687'],
            'type': 'journal'
        },
        'science': {
            'id': 'S3880285',
            'display_name': 'Science',
            'issn_l': '0036-8075',
            'issn': ['0036-8075', '1095-9203'],
            'type': 'journal'
        }
    }
