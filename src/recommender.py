"""
Main recommendation engine that combines citation and content similarity.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import numpy as np

from .zotero_client import ZoteroClient
from .openalex_client import OpenAlexClient
from .similarity_engine import SimilarityEngine
from .citation_scorer import CitationScorer
from .journal_lists import TOP_BIOLOGY_MEDICINE_JOURNALS


class PaperRecommender:
    """Main recommendation engine combining multiple signals."""

    def __init__(self, zotero_api_key: Optional[str] = None,
                 zotero_user_id: Optional[str] = None,
                 openalex_email: Optional[str] = None,
                 cache_dir: str = ".cache"):
        """
        Initialize recommender.

        Args:
            zotero_api_key: Zotero API key
            zotero_user_id: Zotero user ID
            openalex_email: Email for OpenAlex polite pool
            cache_dir: Cache directory
        """
        self.zotero = ZoteroClient(zotero_api_key, zotero_user_id)
        self.openalex = OpenAlexClient(openalex_email)
        self.similarity = SimilarityEngine(cache_dir=cache_dir)
        self.citation_scorer = CitationScorer(cache_dir=cache_dir)

        self.library_papers = None
        self.is_initialized = False

    def initialize(self, force_rebuild: bool = False, max_papers: Optional[int] = None,
                   max_workers: int = 5):
        """
        Initialize the recommender by building profiles and networks.

        Args:
            force_rebuild: Force rebuilding caches
            max_papers: Maximum number of library papers to process (for testing)
            max_workers: Number of parallel workers for citation network (default: 5)
        """
        print("="*60)
        print("Initializing Paper Recommendation Engine")
        print("="*60)

        # Fetch library
        print("\n1. Fetching Zotero library...")
        self.library_papers = self.zotero.fetch_library()
        print(f"   Found {len(self.library_papers)} papers in library")

        if max_papers:
            self.library_papers = self.library_papers[:max_papers]
            print(f"   Limited to {len(self.library_papers)} papers for testing")

        # Build similarity profile
        print("\n2. Building content similarity profile...")
        self.similarity.build_library_profile(self.library_papers, force_rebuild=force_rebuild)

        # Build citation network (uses parallel processing)
        print("\n3. Building citation network...")
        self.citation_scorer.build_library_network(
            self.openalex,
            self.library_papers,
            force_rebuild=force_rebuild,
            max_papers=max_papers,
            max_workers=max_workers
        )

        self.is_initialized = True
        print("\n" + "="*60)
        print("Initialization complete!")
        print("="*60)

    def get_top_journals(self, top_n: int = 30) -> List[str]:
        """
        Get the most frequent journals from the user's library.

        Args:
            top_n: Number of top journals to return

        Returns:
            List of journal names sorted by frequency
        """
        if not self.library_papers:
            return []

        from collections import Counter

        # Extract journals
        journals = []
        for paper in self.library_papers:
            pub = paper.get('publication')
            if pub and pub.strip():
                journals.append(pub.strip())

        # Count and rank
        journal_counts = Counter(journals)
        top_journals = [journal for journal, _ in journal_counts.most_common(top_n)]

        return top_journals

    def get_recommendations(self, days_back: int = 7, limit: int = 20,
                           min_citation_score: float = 0.0,
                           min_similarity_score: float = 0.0,
                           citation_weight: float = 0.3,
                           similarity_weight: float = 0.7,
                           deep_citation_check: bool = False,
                           use_journal_filter: bool = False,
                           custom_journals: Optional[List[str]] = None,
                           max_workers: int = 5) -> List[Dict]:
        """
        Get paper recommendations.

        Args:
            days_back: How many days back to search for papers
            limit: Maximum number of recommendations to return
            min_citation_score: Minimum citation score threshold
            min_similarity_score: Minimum similarity score threshold
            citation_weight: Weight for citation score (0-1)
            similarity_weight: Weight for similarity score (0-1)
            deep_citation_check: Use deeper citation network analysis
            use_journal_filter: Filter by journals from your library
            custom_journals: Custom list of journal names to filter by (overrides auto-detection)
            max_workers: Number of parallel workers for deep citation check (default: 5)

        Returns:
            List of recommended papers sorted by combined score
        """
        if not self.is_initialized:
            raise ValueError("Recommender not initialized. Call initialize() first.")

        print("\n" + "="*60)
        print("Generating Recommendations")
        print("="*60)

        # Calculate date range
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        print(f"\nSearching for papers published since {from_date}...")

        # Prepare journal filter if requested
        journal_ids = None
        if use_journal_filter or custom_journals:
            print("\nPreparing journal filter...")

            # Determine which journals to use
            if custom_journals:
                journals_to_use = custom_journals
                print(f"Using {len(custom_journals)} custom journals")
            else:
                # Use default top 50 biology/medicine journals
                journals_to_use = TOP_BIOLOGY_MEDICINE_JOURNALS
                print(f"Using default list of {len(journals_to_use)} top biology/medicine journals")
                print(f"Including: Nature, Science, Cell, NEJM, The Lancet, and more...")

            # Resolve journal names to OpenAlex source IDs
            print("Resolving journal names to OpenAlex IDs...")
            journal_ids = self.openalex.resolve_journal_ids(journals_to_use)
            print(f"Successfully resolved {len(journal_ids)} journal IDs")

        # Search for recent papers
        print(f"\nSearching OpenAlex for recent papers...")
        print(f"  Date filter: from {from_date} onwards")
        print(f"  Journal filter: {len(journal_ids) if journal_ids else 0} journals")

        candidate_papers = self.openalex.search_recent_papers(
            from_date=from_date,
            journal_ids=journal_ids,  # Apply journal filter if available
            limit=None  # Fetch ALL papers, no limit
        )
        print(f"Found {len(candidate_papers)} candidate papers from OpenAlex")

        # Show date distribution
        if candidate_papers:
            dates = [p.get('publication_date', '') for p in candidate_papers if p.get('publication_date')]
            if dates:
                print(f"  Date range in results: {min(dates)} to {max(dates)}")
                from collections import Counter
                date_counts = Counter(dates)
                print(f"  Papers per date (top 5): {date_counts.most_common(5)}")

        if not candidate_papers:
            print("No candidate papers found.")
            return []

        # Compute similarity scores
        print("\nComputing content similarity scores...")
        candidate_papers = self.similarity.compute_similarity(candidate_papers)

        # Show similarity score distribution
        sim_scores = [p.get('similarity_score', 0) for p in candidate_papers]
        if sim_scores:
            print(f"  Similarity scores - min: {min(sim_scores):.3f}, max: {max(sim_scores):.3f}, avg: {sum(sim_scores)/len(sim_scores):.3f}")

        # Compute citation scores
        print("\nComputing citation network scores...")
        if deep_citation_check:
            candidate_papers = self.citation_scorer.compute_advanced_citation_scores(
                self.openalex,
                candidate_papers,
                check_depth=1,
                max_workers=max_workers
            )
        else:
            candidate_papers = self.citation_scorer.compute_citation_scores(candidate_papers)

        # Show citation score distribution
        cit_scores = [p.get('citation_score', 0) for p in candidate_papers]
        if cit_scores:
            print(f"  Citation scores - min: {min(cit_scores):.3f}, max: {max(cit_scores):.3f}, avg: {sum(cit_scores)/len(cit_scores):.3f}")

        # Filter and rank
        print("\nRanking papers...")
        recommendations = []

        for paper in candidate_papers:
            citation_score = paper.get('citation_score', 0)
            similarity_score = paper.get('similarity_score', 0)

            # Apply thresholds
            if citation_score < min_citation_score or similarity_score < min_similarity_score:
                continue

            # Compute combined score
            combined_score = (
                citation_weight * citation_score +
                similarity_weight * similarity_score
            )

            paper['combined_score'] = combined_score
            recommendations.append(paper)

        # Sort by combined score
        recommendations.sort(key=lambda x: x['combined_score'], reverse=True)

        print(f"\nBefore limit: {len(recommendations)} papers passed filters")
        print(f"  Min thresholds - citation: {min_citation_score}, similarity: {min_similarity_score}")

        # Return top N
        top_recommendations = recommendations[:limit]

        # Show top recommendations summary
        print(f"\nReturning top {len(top_recommendations)} recommendations")
        if top_recommendations:
            print(f"  Top combined score: {top_recommendations[0].get('combined_score', 0):.3f}")
            print(f"  Bottom combined score: {top_recommendations[-1].get('combined_score', 0):.3f}")
            top_dates = [p.get('publication_date', '') for p in top_recommendations if p.get('publication_date')]
            if top_dates:
                print(f"  Date range: {min(top_dates)} to {max(top_dates)}")

        print("="*60)

        return top_recommendations

    def explain_recommendation(self, paper: Dict) -> str:
        """
        Generate explanation for why a paper was recommended.

        Args:
            paper: Recommended paper dictionary

        Returns:
            Human-readable explanation string
        """
        title = paper.get('title', 'Unknown')
        citation_score = paper.get('citation_score', 0)
        similarity_score = paper.get('similarity_score', 0)
        combined_score = paper.get('combined_score', 0)

        explanation = f"\nPaper: {title}\n"
        explanation += f"Combined Score: {combined_score:.3f}\n"
        explanation += f"  - Citation Network Score: {citation_score:.3f}\n"
        explanation += f"  - Content Similarity Score: {similarity_score:.3f}\n"

        # Add network info
        if paper.get('in_network'):
            explanation += "  - This paper is directly connected to your library\n"
        elif paper.get('network_connections', 0) > 0:
            explanation += f"  - This paper has {paper['network_connections']} connections to your library\n"

        # Add most similar library papers
        if hasattr(self.similarity, 'library_papers') and self.similarity.library_papers:
            similar_papers = self.similarity.get_most_similar_library_papers(paper, top_k=2)
            if similar_papers:
                explanation += "  - Most similar to your papers:\n"
                for sim_paper in similar_papers:
                    explanation += f"    * {sim_paper.get('title', '')[:60]}... (similarity: {sim_paper['similarity']:.3f})\n"

        return explanation

    def get_library_stats(self) -> Dict:
        """Get statistics about the library and profiles."""
        stats = {
            'library': self.zotero.get_library_stats(),
            'citation_network': self.citation_scorer.get_network_stats(),
        }

        if self.similarity.library_papers:
            stats['embeddings'] = {
                'papers_with_embeddings': len(self.similarity.library_papers)
            }

        return stats
