"""
Pytest tests for CitationScorer.
"""
import pytest
from unittest.mock import Mock, patch
import pickle
import os

from src.citation_scorer import CitationScorer


@pytest.mark.unit
class TestCitationScorerInit:
    """Tests for CitationScorer initialization."""

    def test_init(self, temp_cache_dir):
        """Test basic initialization."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)

        assert scorer.cache_dir == temp_cache_dir
        assert isinstance(scorer.library_network, set)
        assert isinstance(scorer.openalex_id_map, dict)
        assert len(scorer.library_network) == 0
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
            max_citations=20,
            max_references=20
        )

        # Should load from cache
        assert scorer.library_network == mock_citation_network['network']
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
            max_citations=25,  # Higher than cached (10)
            max_references=20
        )

        # Should rebuild (call API)
        assert mock_client.find_work_by_doi.called

    def test_cache_rebuilds_with_higher_reference_limit(self, temp_cache_dir, mock_citation_network):
        """Test cache rebuild when max_references increases."""
        cache_data = mock_citation_network.copy()
        cache_data['build_params']['max_references'] = 10

        cache_file = os.path.join(temp_cache_dir, 'citation_network.pkl')
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)

        mock_client = Mock()
        mock_client.find_work_by_doi.return_value = None
        mock_client.find_work_by_title.return_value = None

        mock_papers = [{'title': 'Paper 1', 'doi': '10.1234/test'}]

        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.build_library_network(
            mock_client,
            mock_papers,
            force_rebuild=False,
            max_citations=20,
            max_references=25  # Higher than cached (10)
        )

        # Should have called API for the paper
        assert mock_client.find_work_by_doi.called

        # Verify new cache was saved with updated params
        with open(cache_file, 'rb') as f:
            new_cache = pickle.load(f)
        assert new_cache['build_params']['max_references'] == 25

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
            max_citations=20,
            max_references=20
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
            'network': {'W1', 'W2'},
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
            max_citations=20,
            max_references=20
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
        """Test basic citation score computation."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.library_network = {'W1', 'W2', 'W3'}

        candidates = [
            {'openalex_id': 'W1', 'title': 'In Network'},
            {'openalex_id': 'W999', 'title': 'Not In Network'},
            {'title': 'No OpenAlex ID'}
        ]

        results = scorer.compute_citation_scores(candidates)

        assert len(results) == 3
        assert results[0]['citation_score'] == 1.0
        assert results[0]['in_network'] is True
        assert results[1]['citation_score'] == 0.0
        assert results[1]['in_network'] is False
        assert results[2]['citation_score'] == 0.0
        assert results[2]['in_network'] is False

    def test_compute_scores_no_network(self, temp_cache_dir):
        """Test error when network not built."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        candidates = [{'openalex_id': 'W1'}]

        with pytest.raises(ValueError, match="Library network not built"):
            scorer.compute_citation_scores(candidates)

    def test_compute_scores_empty_candidates(self, temp_cache_dir):
        """Test with empty candidate list."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.library_network = {'W1'}

        results = scorer.compute_citation_scores([])
        assert len(results) == 0


@pytest.mark.unit
class TestComputeAdvancedCitationScores:
    """Tests for advanced citation score computation."""

    def test_compute_advanced_direct_match(self, temp_cache_dir):
        """Test advanced scoring with direct network match."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.library_network = {'W1', 'W2', 'W3'}

        mock_client = Mock()
        candidates = [{'openalex_id': 'W1', 'title': 'In Network'}]

        results = scorer.compute_advanced_citation_scores(
            mock_client,
            candidates,
            check_depth=1,
            max_citations=10,
            max_references=10
        )

        # Direct match gets score 1.0
        assert results[0]['citation_score'] == 1.0
        assert results[0]['network_connections'] == 1

        # Should not make API calls for direct match
        mock_client.get_citations.assert_not_called()
        mock_client.get_references.assert_not_called()

    def test_compute_advanced_indirect_connections(self, temp_cache_dir):
        """Test advanced scoring with indirect connections."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.library_network = {'W1', 'W2', 'W3'}

        mock_client = Mock()
        # Paper W999 cites W1 and W2 (both in network)
        mock_client.get_citations.return_value = [
            {'openalex_id': 'W1'},
            {'openalex_id': 'W100'}  # Not in network
        ]
        mock_client.get_references.return_value = [
            {'openalex_id': 'W2'},
            {'openalex_id': 'W101'}  # Not in network
        ]

        candidates = [{'openalex_id': 'W999', 'title': 'Candidate'}]

        results = scorer.compute_advanced_citation_scores(
            mock_client,
            candidates,
            check_depth=1,
            max_citations=10,
            max_references=10
        )

        # 2 connections (W1 and W2) = 0.2 score
        assert results[0]['network_connections'] == 2
        assert results[0]['citation_score'] == 0.2

    def test_compute_advanced_no_connections(self, temp_cache_dir):
        """Test advanced scoring with no connections."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.library_network = {'W1', 'W2'}

        mock_client = Mock()
        mock_client.get_citations.return_value = []
        mock_client.get_references.return_value = []

        candidates = [{'openalex_id': 'W999', 'title': 'Isolated Paper'}]

        results = scorer.compute_advanced_citation_scores(
            mock_client,
            candidates,
            check_depth=1,
            max_citations=10,
            max_references=10
        )

        assert results[0]['network_connections'] == 0
        assert results[0]['citation_score'] == 0.0

    def test_compute_advanced_score_capped(self, temp_cache_dir):
        """Test that advanced scores are capped at 0.8."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.library_network = {'W1', 'W2', 'W3'}

        mock_client = Mock()
        # Many connections
        mock_client.get_citations.return_value = [
            {'openalex_id': f'W{i}'} for i in range(1, 11)  # W1-W10
        ]
        mock_client.get_references.return_value = []

        candidates = [{'openalex_id': 'W999', 'title': 'Well Connected'}]

        results = scorer.compute_advanced_citation_scores(
            mock_client,
            candidates,
            check_depth=1,
            max_citations=20,
            max_references=20
        )

        # Max score is 0.8 for indirect matches
        assert results[0]['citation_score'] <= 0.8


@pytest.mark.unit
class TestGetNetworkStats:
    """Tests for network statistics."""

    def test_get_stats(self, temp_cache_dir):
        """Test getting network statistics."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)
        scorer.library_network = {'W1', 'W2', 'W3', 'W4', 'W5'}
        scorer.openalex_id_map = {'key1': 'W1', 'key2': 'W2'}

        stats = scorer.get_network_stats()

        assert stats['total_works'] == 5
        assert stats['library_papers_mapped'] == 2

    def test_get_stats_empty(self, temp_cache_dir):
        """Test statistics with empty network."""
        scorer = CitationScorer(cache_dir=temp_cache_dir)

        stats = scorer.get_network_stats()

        assert stats['total_works'] == 0
        assert stats['library_papers_mapped'] == 0
