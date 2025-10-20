"""
Pytest tests for SimilarityEngine.
"""
import pytest
from unittest.mock import Mock, patch
import numpy as np
import os

from src.similarity_engine import SimilarityEngine


@pytest.mark.unit
class TestSimilarityEngineInit:
    """Tests for SimilarityEngine initialization."""

    def test_init(self, temp_cache_dir):
        """Test basic initialization."""
        engine = SimilarityEngine(cache_dir=temp_cache_dir)

        assert engine.cache_dir == temp_cache_dir
        assert engine.model is None
        assert engine.library_embeddings is None
        assert engine.library_papers is None

    def test_init_custom_model(self, temp_cache_dir):
        """Test initialization with custom model name."""
        engine = SimilarityEngine(
            model_name="custom-model",
            cache_dir=temp_cache_dir
        )

        assert engine.model_name == "custom-model"


@pytest.mark.unit
class TestModelLoading:
    """Tests for model loading."""

    @patch('src.similarity_engine.SentenceTransformer')
    def test_load_model(self, mock_transformer, temp_cache_dir):
        """Test model loading."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        engine.load_model()

        assert engine.model is not None
        mock_transformer.assert_called_once_with(engine.model_name)

    @patch('src.similarity_engine.SentenceTransformer')
    def test_load_model_idempotent(self, mock_transformer, temp_cache_dir):
        """Test that loading model multiple times doesn't reload."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        engine.load_model()
        engine.load_model()

        # Should only load once
        assert mock_transformer.call_count == 1


@pytest.mark.unit
class TestBuildLibraryProfile:
    """Tests for building library embeddings."""

    @patch('src.similarity_engine.SentenceTransformer')
    def test_build_profile(self, mock_transformer, temp_cache_dir, sample_library_papers):
        """Test building library profile."""
        mock_model = Mock()
        mock_embeddings = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ])
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model

        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        engine.build_library_profile(sample_library_papers, force_rebuild=True)

        assert engine.library_embeddings is not None
        assert len(engine.library_embeddings) == 3
        assert len(engine.library_papers) == 3

    @patch('src.similarity_engine.SentenceTransformer')
    def test_build_profile_cache(self, mock_transformer, temp_cache_dir):
        """Test that library profile caching works."""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3]])
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model

        papers = [{'title': 'Test Paper', 'abstract': 'Test abstract'}]

        # Build first time
        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        engine.build_library_profile(papers, force_rebuild=True)
        first_encode_count = mock_model.encode.call_count

        # Create new engine and load from cache
        new_engine = SimilarityEngine(cache_dir=temp_cache_dir)
        new_engine.build_library_profile(papers, force_rebuild=False)

        # Should not encode again
        assert mock_model.encode.call_count == first_encode_count

    def test_build_profile_no_valid_papers(self, temp_cache_dir):
        """Test error when no valid papers."""
        papers = [{'author': 'John Doe'}]  # No title or abstract

        engine = SimilarityEngine(cache_dir=temp_cache_dir)

        with pytest.raises(ValueError, match="No papers with abstracts or titles"):
            engine.build_library_profile(papers)

    @patch('src.similarity_engine.SentenceTransformer')
    def test_build_profile_title_only(self, mock_transformer, temp_cache_dir):
        """Test building profile with title-only papers."""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2]])
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model

        papers = [{'title': 'Paper Title'}]  # No abstract

        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        engine.build_library_profile(papers, force_rebuild=True)

        assert len(engine.library_papers) == 1


@pytest.mark.unit
class TestComputeSimilarity:
    """Tests for computing similarity scores."""

    @patch('src.similarity_engine.SentenceTransformer')
    def test_compute_similarity(self, mock_transformer, temp_cache_dir, sample_library_papers):
        """Test similarity computation."""
        mock_model = Mock()

        # Library embeddings (3 papers)
        library_emb = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ])

        # Candidate embedding (similar to first paper)
        candidate_emb = np.array([[0.9, 0.1, 0.0]])

        mock_model.encode.side_effect = [library_emb, candidate_emb]
        mock_transformer.return_value = mock_model

        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        engine.library_papers = sample_library_papers
        engine.library_embeddings = library_emb
        engine.model = mock_model

        candidates = [{'title': 'Candidate', 'abstract': 'Test'}]
        results = engine.compute_similarity(candidates)

        assert len(results) == 1
        assert 'similarity_score' in results[0]
        assert 'most_similar_paper' in results[0]

        # Check that scores are Python floats (not numpy)
        assert isinstance(results[0]['similarity_score'], float)
        assert isinstance(results[0]['most_similar_paper']['similarity'], float)

    def test_compute_similarity_no_library(self, temp_cache_dir):
        """Test error when library not built."""
        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        candidates = [{'title': 'Test'}]

        with pytest.raises(ValueError, match="Library profile not built"):
            engine.compute_similarity(candidates)

    @patch('src.similarity_engine.SentenceTransformer')
    def test_compute_similarity_empty_candidates(self, mock_transformer, temp_cache_dir):
        """Test with empty candidate list."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        engine.library_embeddings = np.array([[0.1, 0.2]])
        engine.library_papers = [{'title': 'Paper'}]
        engine.model = mock_model

        results = engine.compute_similarity([])
        assert len(results) == 0

    @patch('src.similarity_engine.SentenceTransformer')
    def test_compute_similarity_no_text(self, mock_transformer, temp_cache_dir):
        """Test with candidates lacking title/abstract."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        engine.library_embeddings = np.array([[0.1, 0.2]])
        engine.library_papers = [{'title': 'Paper'}]
        engine.model = mock_model

        candidates = [{'author': 'John Doe'}]  # No title or abstract
        results = engine.compute_similarity(candidates)

        # Should return original candidates unchanged
        assert len(results) == 1


@pytest.mark.unit
class TestGetMostSimilarPapers:
    """Tests for finding most similar library papers."""

    @patch('src.similarity_engine.SentenceTransformer')
    def test_get_most_similar(self, mock_transformer, temp_cache_dir, sample_library_papers):
        """Test finding most similar papers."""
        mock_model = Mock()

        library_emb = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ])
        candidate_emb = np.array([[0.9, 0.1, 0.0]])

        mock_model.encode.return_value = candidate_emb
        mock_transformer.return_value = mock_model

        engine = SimilarityEngine(cache_dir=temp_cache_dir)
        engine.library_embeddings = library_emb
        engine.library_papers = sample_library_papers
        engine.model = mock_model

        paper = {'title': 'Test', 'abstract': 'Test abstract'}
        results = engine.get_most_similar_library_papers(paper, top_k=2)

        assert len(results) == 2
        assert 'similarity' in results[0]
        assert isinstance(results[0]['similarity'], float)

    def test_get_most_similar_no_library(self, temp_cache_dir):
        """Test error when library not built."""
        engine = SimilarityEngine(cache_dir=temp_cache_dir)

        with pytest.raises(ValueError, match="Library profile not built"):
            engine.get_most_similar_library_papers({'title': 'Test'})


