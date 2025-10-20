"""
Citation network scorer for computing paper relevance based on citation proximity.
"""
import os
import pickle
from typing import List, Dict, Set, Optional
from collections import defaultdict


class CitationScorer:
    """Scorer for computing citation network proximity."""

    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize citation scorer.

        Args:
            cache_dir: Directory for caching citation networks
        """
        self.cache_dir = cache_dir
        self.library_network = set()
        self.openalex_id_map = {}

        os.makedirs(cache_dir, exist_ok=True)

    def build_library_network(self, openalex_client, library_papers: List[Dict],
                              force_rebuild: bool = False, max_papers: Optional[int] = None,
                              max_citations: int = 20, max_references: int = 20):
        """
        Build citation network from library papers.

        Args:
            openalex_client: OpenAlexClient instance
            library_papers: List of library paper dictionaries
            force_rebuild: Force rebuilding even if cache exists
            max_papers: Maximum number of library papers to process (for testing)
            max_citations: Maximum number of citations to fetch per paper (default: 20)
            max_references: Maximum number of references to fetch per paper (default: 20)
        """
        cache_file = os.path.join(self.cache_dir, "citation_network.pkl")

        # Try to load from cache
        if not force_rebuild and os.path.exists(cache_file):
            print("Loading citation network from cache...")
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)

                # Check if cache has parameter metadata
                cached_params = cache_data.get('build_params', {})
                cached_max_citations = cached_params.get('max_citations', 0)
                cached_max_references = cached_params.get('max_references', 0)
                cached_num_papers = cached_params.get('num_papers', 0)

                # Determine if we need to rebuild
                needs_rebuild = False
                rebuild_reasons = []

                # Check if requested limits are higher than cached
                if max_citations > cached_max_citations:
                    needs_rebuild = True
                    rebuild_reasons.append(f"max_citations increased ({cached_max_citations} -> {max_citations})")

                if max_references > cached_max_references:
                    needs_rebuild = True
                    rebuild_reasons.append(f"max_references increased ({cached_max_references} -> {max_references})")

                # Check if library has grown significantly (more than 10% or 5 papers)
                current_num_papers = len(library_papers[:max_papers] if max_papers else library_papers)
                if current_num_papers > cached_num_papers + max(5, cached_num_papers * 0.1):
                    needs_rebuild = True
                    rebuild_reasons.append(f"library grew significantly ({cached_num_papers} -> {current_num_papers} papers)")

                if needs_rebuild:
                    print(f"Cache exists but needs rebuild:")
                    for reason in rebuild_reasons:
                        print(f"  - {reason}")
                    print("Rebuilding citation network...")
                else:
                    self.library_network = cache_data['network']
                    self.openalex_id_map = cache_data['id_map']
                    print(f"Loaded network with {len(self.library_network)} works.")
                    print(f"  Built with: max_citations={cached_max_citations}, max_references={cached_max_references}, {cached_num_papers} papers")
                    return

        # Build new network
        print("Building citation network from library...")

        papers_to_process = library_papers[:max_papers] if max_papers else library_papers

        for i, paper in enumerate(papers_to_process):
            print(f"Processing paper {i+1}/{len(papers_to_process)}: {paper.get('title', '')[:60]}...")

            # Try to find paper in OpenAlex
            openalex_work = None

            # First try DOI
            if paper.get('doi'):
                openalex_work = openalex_client.find_work_by_doi(paper['doi'])

            # Fallback to title search
            if not openalex_work and paper.get('title'):
                openalex_work = openalex_client.find_work_by_title(paper['title'])

            if openalex_work:
                openalex_id = openalex_work['openalex_id']
                self.library_network.add(openalex_id)

                # Store mapping
                paper_key = paper.get('zotero_key') or paper.get('title')
                self.openalex_id_map[paper_key] = openalex_id

                # Get citations and references
                print(f"  Found in OpenAlex: {openalex_id}")
                citations = openalex_client.get_citations(openalex_id, limit=max_citations)
                references = openalex_client.get_references(openalex_id, limit=max_references)

                # Add to network
                for work in citations + references:
                    if work.get('openalex_id'):
                        self.library_network.add(work['openalex_id'])

                print(f"  Added {len(citations)} citations and {len(references)} references")
            else:
                print(f"  Not found in OpenAlex")

        # Cache the network with build parameters
        print("Saving citation network to cache...")
        with open(cache_file, 'wb') as f:
            pickle.dump({
                'network': self.library_network,
                'id_map': self.openalex_id_map,
                'build_params': {
                    'max_citations': max_citations,
                    'max_references': max_references,
                    'num_papers': len(papers_to_process)
                }
            }, f)

        print(f"Citation network built with {len(self.library_network)} works.")
        print(f"  Parameters: max_citations={max_citations}, max_references={max_references}, {len(papers_to_process)} papers")

    def compute_citation_scores(self, candidate_papers: List[Dict]) -> List[Dict]:
        """
        Compute citation proximity scores for candidate papers.

        Args:
            candidate_papers: List of papers to score

        Returns:
            List of papers with added 'citation_score' field
        """
        if not self.library_network:
            raise ValueError("Library network not built. Call build_library_network first.")

        scored_papers = []

        for paper in candidate_papers:
            openalex_id = paper.get('openalex_id')

            if not openalex_id:
                # Skip papers without OpenAlex ID
                paper['citation_score'] = 0.0
                paper['in_network'] = False
                scored_papers.append(paper)
                continue

            # Check if paper is in network
            if openalex_id in self.library_network:
                score = 1.0
                in_network = True
            else:
                score = 0.0
                in_network = False

            paper['citation_score'] = score
            paper['in_network'] = in_network
            scored_papers.append(paper)

        return scored_papers

    def compute_advanced_citation_scores(self, openalex_client, candidate_papers: List[Dict],
                                        check_depth: int = 1, max_citations: int = 10,
                                        max_references: int = 10) -> List[Dict]:
        """
        Compute citation scores with deeper network analysis.

        Args:
            openalex_client: OpenAlexClient instance
            candidate_papers: List of papers to score
            check_depth: How deep to check citations (1 = direct, 2 = second-degree)
            max_citations: Maximum number of citations to fetch per paper (default: 10)
            max_references: Maximum number of references to fetch per paper (default: 10)

        Returns:
            List of papers with citation scores
        """
        if not self.library_network:
            raise ValueError("Library network not built.")

        scored_papers = []

        for i, paper in enumerate(candidate_papers):
            print(f"Scoring citation network for paper {i+1}/{len(candidate_papers)}...")

            openalex_id = paper.get('openalex_id')

            if not openalex_id:
                paper['citation_score'] = 0.0
                paper['network_connections'] = 0
                scored_papers.append(paper)
                continue

            # Direct match
            if openalex_id in self.library_network:
                paper['citation_score'] = 1.0
                paper['network_connections'] = 1
                scored_papers.append(paper)
                continue

            # Check citations and references
            connections = 0

            if check_depth >= 1:
                # Get paper's citations and references
                citations = openalex_client.get_citations(openalex_id, limit=max_citations)
                references = openalex_client.get_references(openalex_id, limit=max_references)

                # Count connections to library network
                for work in citations + references:
                    work_id = work.get('openalex_id')
                    if work_id and work_id in self.library_network:
                        connections += 1

            # Compute score based on connections
            # Score ranges from 0 to 0.8 (direct match is 1.0)
            score = min(0.8, connections * 0.1)

            paper['citation_score'] = score
            paper['network_connections'] = connections
            scored_papers.append(paper)

        return scored_papers

    def get_network_stats(self) -> Dict:
        """Get statistics about the citation network."""
        return {
            'total_works': len(self.library_network),
            'library_papers_mapped': len(self.openalex_id_map)
        }
