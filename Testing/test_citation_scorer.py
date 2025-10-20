"""
Pytest tests for CitationScorer.
"""
import pytest
from unittest.mock import Mock, patch
import pickle
import os
from collections import defaultdict

from src.citation_scorer import CitationScorer


@pytest.mark.unit
class TestCitationScorerInit:
    """Tests for CitationScorer initialization."""

    def test_init(self, temp_cache_dir):
        """Test basic initialization."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)

        assert scorer.cache_dir == temp_cache_dir
        assert isinstance(scorer.citation_network, defaultdict)
        assert isinstance(scorer.openalex_id_map, dict)
        assert len(scorer.citation_network) == 0
        assert len(scorer.openalex_id_map) == 0


@pytest.mark.unit
class TestCacheParameterValidation:
    """Tests for citation network cache parameter validation."""

    def test_cache_loads_with_matching_params(self, temp_cache_dir, mock_citation_network):
        """Test cache loading when parameters match."""
        # Save cache
        cache_file = os.path.join(temp_cache_dir, 'citation_network.pkl')
        with open(cache_file, 'wb') as f:
            pickle.dump(mock_citation_network, f)

        # Mock client and papers
        mock_client = Mock()
        mock_papers = [{'title': f'Paper {i}'} for i in range(3)]

        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.build_library_network(
            mock_client,
            mock_papers,
            force_rebuild=False,
            max_citations=20
        )

        # Should load from cache
        assert dict(scorer.citation_network) == mock_citation_network['citation_network']
        mock_client.find_work_by_doi.assert_not_called()

    def test_cache_rebuilds_with_higher_citation_limit(self, temp_cache_dir, mock_citation_network):
        """Test cache rebuild when max_citations increases."""
        # Save cache with lower limits
        cache_data = mock_citation_network.copy()
        cache_data['build_params']['max_citations'] = 10

        cache_file = os.path.join(temp_cache_dir, 'citation_network.pkl')
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)

        # Mock client
        mock_client = Mock()
        mock_client.find_work_by_doi.return_value = None
        mock_client.find_work_by_title.return_value = None

        mock_papers = [{'title': 'Paper 1', 'doi': '10.1234/1'}]

        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.build_library_network(
            mock_client,
            mock_papers,
            force_rebuild=False,
            max_citations=25  # Higher than cached (10)
        )

        # Should rebuild (call API)
        assert mock_client.find_work_by_doi.called

    def test_cache_rebuilds_on_library_growth(self, temp_cache_dir, mock_citation_network):
        """Test cache rebuild when library grows significantly."""
        # Cache has 3 papers
        cache_file = os.path.join(temp_cache_dir, 'citation_network.pkl')
        with open(cache_file, 'wb') as f:
            pickle.dump(mock_citation_network, f)

        mock_client = Mock()
        mock_client.find_work_by_doi.return_value = None
        mock_client.find_work_by_title.return_value = None

        # Now have 10 papers (>10% growth), give them DOIs so API is called
        mock_papers = [{'title': f'Paper {i}', 'doi': f'10.1234/{i}'} for i in range(10)]

        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.build_library_network(
            mock_client,
            mock_papers,
            force_rebuild=False,
            max_citations=20
        )

        # Should rebuild due to library growth
        assert mock_client.find_work_by_doi.called

        # Verify new cache reflects larger library
        with open(cache_file, 'rb') as f:
            new_cache = pickle.load(f)
        assert new_cache['build_params']['num_papers'] == 10

    def test_old_cache_format_triggers_rebuild(self, temp_cache_dir):
        """Test that old cache without build_params triggers rebuild."""
        # Save old format cache (no build_params)
        old_cache = {
            'citation_network': {'W1': {'LIB1'}, 'W2': {'LIB2'}},
            'id_map': {}
        }

        cache_file = os.path.join(temp_cache_dir, 'citation_network.pkl')
        with open(cache_file, 'wb') as f:
            pickle.dump(old_cache, f)

        mock_client = Mock()
        mock_client.find_work_by_doi.return_value = None
        mock_client.find_work_by_title.return_value = None

        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.build_library_network(
            mock_client,
            [{'title': 'Paper', 'doi': '10.1234/test'}],
            force_rebuild=False,
            max_citations=20
        )

        # Should rebuild (old format)
        assert mock_client.find_work_by_doi.called

        # Verify new cache has build_params
        with open(cache_file, 'rb') as f:
            new_cache = pickle.load(f)
        assert 'build_params' in new_cache
        assert new_cache['build_params']['max_citations'] == 20


@pytest.mark.unit
class TestComputeCitationScores:
    """Tests for computing citation scores."""

    def test_compute_scores_basic(self, temp_cache_dir):
        """Test basic citation score computation with new scoring logic."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        # Map: citing_paper -> set of library papers it cites
        scorer.citation_network = defaultdict(set, {
            'W1': {'LIB1'},  # Cites 1 library paper
            'W2': {'LIB1', 'LIB2'},  # Cites 2 library papers
            'W3': {'LIB1', 'LIB2', 'LIB3'},  # Cites 3+ library papers
        })

        candidates = [
            {'openalex_id': 'W1', 'title': 'Cites 1'},
            {'openalex_id': 'W2', 'title': 'Cites 2'},
            {'openalex_id': 'W3', 'title': 'Cites 3+'},
            {'openalex_id': 'W999', 'title': 'Cites 0'},
            {'title': 'No OpenAlex ID'}
        ]

        results = scorer.compute_citation_scores(candidates)

        assert len(results) == 5
        assert results[0]['citation_score'] == 0.5  # Cites 1
        assert results[0]['library_papers_cited'] == 1
        assert results[1]['citation_score'] == 0.75  # Cites 2
        assert results[1]['library_papers_cited'] == 2
        assert results[2]['citation_score'] == 1.0  # Cites 3+
        assert results[2]['library_papers_cited'] == 3
        assert results[3]['citation_score'] == 0.0  # Cites 0
        assert results[3]['library_papers_cited'] == 0
        assert results[4]['citation_score'] == 0.0  # No ID
        assert results[4]['library_papers_cited'] == 0

    def test_compute_scores_no_network(self, temp_cache_dir):
        """Test error when network not built."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        candidates = [{'openalex_id': 'W1'}]

        with pytest.raises(ValueError, match="Citation network not built"):
            scorer.compute_citation_scores(candidates)

    def test_compute_scores_empty_candidates(self, temp_cache_dir):
        """Test with empty candidate list."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.citation_network = defaultdict(set, {'W1': {'LIB1'}})

        results = scorer.compute_citation_scores([])
        assert len(results) == 0


@pytest.mark.unit
class TestGetNetworkStats:
    """Tests for network statistics."""

    def test_get_stats(self, temp_cache_dir):
        """Test getting network statistics."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        # citation_network maps citing_paper -> set of library papers
        scorer.citation_network = defaultdict(set, {
            'W1': {'LIB1'},
            'W2': {'LIB2'},
            'W3': {'LIB1', 'LIB2'},
            'W4': {'LIB3'},
            'W5': {'LIB1'}
        })
        scorer.openalex_id_map = {'key1': 'LIB1', 'key2': 'LIB2'}

        stats = scorer.get_network_stats()

        assert stats['citing_papers'] == 5
        assert stats['library_papers_mapped'] == 2

    def test_get_stats_empty(self, temp_cache_dir):
        """Test statistics with empty network."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)

        stats = scorer.get_network_stats()

        assert stats['citing_papers'] == 0
        assert stats['library_papers_mapped'] == 0
