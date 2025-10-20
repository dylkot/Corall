"""
Content similarity engine using sentence transformers for paper embeddings.
"""
import os
import pickle
from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine


class SimilarityEngine:
    """Engine for computing semantic similarity between papers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: str = ".cache"):
        """
        Initialize similarity engine.

        Args:
            model_name: Name of sentence-transformers model to use
            cache_dir: Directory for caching embeddings
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model = None
        self.library_embeddings = None
        self.library_papers = None

        os.makedirs(cache_dir, exist_ok=True)

    def load_model(self):
        """Load the sentence transformer model."""
        if self.model is None:
            print(f"Loading embedding model: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            print("Model loaded successfully.")

    def build_library_profile(self, papers: List[Dict], force_rebuild: bool = False):
        """
        Build embeddings for user's library papers.

        Args:
            papers: List of paper dictionaries
            force_rebuild: Force rebuilding even if cache exists
        """
        cache_file = os.path.join(self.cache_dir, "library_embeddings.pkl")

        # Try to load from cache
        if not force_rebuild and os.path.exists(cache_file):
            print("Loading library embeddings from cache...")
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
                self.library_embeddings = cache_data['embeddings']
                self.library_papers = cache_data['papers']
                print(f"Loaded embeddings for {len(self.library_papers)} papers.")
                return

        # Build new embeddings
        self.load_model()

        # Filter papers with abstracts or titles
        valid_papers = [
            p for p in papers
            if p.get('abstract') or p.get('title')
        ]

        if not valid_papers:
            raise ValueError("No papers with abstracts or titles found in library.")

        print(f"Building embeddings for {len(valid_papers)} papers...")

        # Create text representations
        texts = []
        for paper in valid_papers:
            # Combine title and abstract for better representation
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')

            if abstract:
                text = f"{title}. {abstract}"
            else:
                text = title

            texts.append(text)

        # Generate embeddings
        self.library_embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32
        )

        self.library_papers = valid_papers

        # Cache the results
        print("Saving embeddings to cache...")
        with open(cache_file, 'wb') as f:
            pickle.dump({
                'embeddings': self.library_embeddings,
                'papers': self.library_papers
            }, f)

        print("Library profile built successfully.")

    def compute_similarity(self, candidate_papers: List[Dict]) -> List[Dict]:
        """
        Compute similarity scores for candidate papers against library.

        Args:
            candidate_papers: List of papers to score

        Returns:
            List of papers with added 'similarity_score' field
        """
        if self.library_embeddings is None:
            raise ValueError("Library profile not built. Call build_library_profile first.")

        self.load_model()

        # Filter candidates with text
        valid_candidates = [
            p for p in candidate_papers
            if p.get('abstract') or p.get('title')
        ]

        if not valid_candidates:
            return candidate_papers

        # Create text representations
        texts = []
        for paper in valid_candidates:
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')

            if abstract:
                text = f"{title}. {abstract}"
            else:
                text = title

            texts.append(text)

        # Generate embeddings for candidates
        candidate_embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            batch_size=32
        )

        # Compute similarity scores
        scored_papers = []
        for i, paper in enumerate(valid_candidates):
            candidate_emb = candidate_embeddings[i]

            # Compute similarity to all library papers
            similarities = []
            for j, lib_emb in enumerate(self.library_embeddings):
                # Cosine similarity (1 - cosine distance)
                sim = 1 - cosine(candidate_emb, lib_emb)
                similarities.append((sim, j))

            # Sort by similarity
            similarities.sort(reverse=True, key=lambda x: x[0])

            # Use max similarity to any library paper
            max_similarity = similarities[0][0]
            most_similar_idx = similarities[0][1]

            # Also compute average of top-k similarities
            top_k = min(5, len(similarities))
            avg_top_similarity = np.mean([sim for sim, _ in similarities[:top_k]])

            paper['similarity_score'] = float(max_similarity)
            paper['avg_top_similarity'] = float(avg_top_similarity)

            # Store most similar library paper
            most_similar_paper = self.library_papers[most_similar_idx]
            paper['most_similar_paper'] = {
                'title': most_similar_paper.get('title', 'Unknown'),
                'authors': most_similar_paper.get('authors', []),
                'year': most_similar_paper.get('year', ''),
                'similarity': float(max_similarity)
            }

            scored_papers.append(paper)

        return scored_papers

    def get_most_similar_library_papers(self, paper: Dict, top_k: int = 3) -> List[Dict]:
        """
        Find most similar papers from library for a given paper.

        Args:
            paper: Paper to compare
            top_k: Number of similar papers to return

        Returns:
            List of most similar library papers
        """
        if self.library_embeddings is None:
            raise ValueError("Library profile not built.")

        self.load_model()

        # Create text representation
        title = paper.get('title', '')
        abstract = paper.get('abstract', '')
        text = f"{title}. {abstract}" if abstract else title

        # Generate embedding
        paper_emb = self.model.encode([text])[0]

        # Compute similarities
        similarities = []
        for i, lib_emb in enumerate(self.library_embeddings):
            sim = 1 - cosine(paper_emb, lib_emb)
            similarities.append((sim, i))

        # Get top-k
        similarities.sort(reverse=True)
        top_papers = []

        for sim, idx in similarities[:top_k]:
            lib_paper = self.library_papers[idx].copy()
            lib_paper['similarity'] = float(sim)
            top_papers.append(lib_paper)

        return top_papers

    def extract_key_concepts(self) -> List[str]:
        """
        Extract key concepts/topics from library using OpenAlex concepts.

        Returns:
            List of key concept names
        """
        if not self.library_papers:
            return []

        # Aggregate concepts from all papers
        concept_counts = {}

        for paper in self.library_papers:
            concepts = paper.get('concepts', [])
            for concept in concepts:
                name = concept.get('name')
                score = concept.get('score', 0)

                if name:
                    if name not in concept_counts:
                        concept_counts[name] = {'count': 0, 'total_score': 0}

                    concept_counts[name]['count'] += 1
                    concept_counts[name]['total_score'] += score

        # Rank by frequency and average score
        ranked_concepts = []
        for name, data in concept_counts.items():
            avg_score = data['total_score'] / data['count']
            rank_score = data['count'] * avg_score
            ranked_concepts.append((name, rank_score))

        ranked_concepts.sort(key=lambda x: x[1], reverse=True)

        # Return top concepts
        return [name for name, _ in ranked_concepts[:20]]
