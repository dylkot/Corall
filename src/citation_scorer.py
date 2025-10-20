"""
Citation network scorer for computing paper relevance based on citation proximity.
"""
import os
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        # Maps citing_paper_id -> set of library_paper_ids it cites
        self.citation_network = defaultdict(set)
        self.openalex_id_map = {}

        os.makedirs(cache_dir, exist_ok=True)

    def build_library_network(self, openalex_client, library_papers: List[Dict],
                              force_rebuild: bool = False, max_papers: Optional[int] = None,
                              max_citations: Optional[int] = None,
                              max_workers: int = 5):
        """
        Build citation network from library papers using parallel processing.

        Fetches papers that cite library papers and tracks which library papers
        each citing paper references. This allows scoring based on how many
        library papers a candidate cites (1=0.5, 2=0.75, 3+=1.0).

        Uses multithreading to process multiple papers concurrently for 3-5x speedup.
        The rate limiter ensures we still respect OpenAlex API limits (10 req/sec).

        Args:
            openalex_client: OpenAlexClient instance (must be thread-safe)
            library_papers: List of library paper dictionaries
            force_rebuild: Force rebuilding even if cache exists
            max_papers: Maximum number of library papers to process (for testing)
            max_citations: Maximum number of citations to fetch per paper (None = fetch all)
            max_workers: Number of parallel worker threads (default: 5)
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
                cached_num_papers = cached_params.get('num_papers', 0)

                # Determine if we need to rebuild
                needs_rebuild = False
                rebuild_reasons = []

                # Check if requested limits are higher than cached
                # Handle None (fetch all) vs numeric limits
                # Note: cached_max_citations of 0 means old cache format without build_params, should rebuild
                if cached_max_citations == 0:
                    # Old cache format, trigger rebuild
                    needs_rebuild = True
                    rebuild_reasons.append("old cache format detected (no build params)")
                elif max_citations is None:
                    # Want to fetch all citations
                    if cached_max_citations is not None:
                        # Cache was built with a limit, need to rebuild to get all
                        needs_rebuild = True
                        rebuild_reasons.append(f"max_citations changed from {cached_max_citations} to unlimited")
                elif cached_max_citations is None:
                    # Cache has all citations, we're requesting limited - no rebuild needed
                    pass
                elif max_citations > cached_max_citations:
                    # Both are numbers, and we want more than what's cached
                    needs_rebuild = True
                    rebuild_reasons.append(f"max_citations increased ({cached_max_citations} -> {max_citations})")

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
                    self.citation_network = cache_data.get('citation_network', defaultdict(set))
                    self.openalex_id_map = cache_data['id_map']
                    print(f"Loaded citation network with {len(self.citation_network)} citing papers.")
                    max_cit_str = "unlimited" if cached_max_citations is None else str(cached_max_citations)
                    print(f"  Built with: max_citations={max_cit_str}, {cached_num_papers} papers")
                    return

        # Build new network with parallel processing
        print(f"Building citation network from library ({max_workers} workers)...")

        papers_to_process = library_papers[:max_papers] if max_papers else library_papers

        # Thread-safe collections
        network_lock = threading.Lock()
        id_map_lock = threading.Lock()

        def process_paper(paper_tuple):
            """Process a single library paper (find in OpenAlex and get its citations)."""
            i, paper = paper_tuple

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

                # Thread-safe ID map update
                paper_key = paper.get('zotero_key') or paper.get('title')
                with id_map_lock:
                    self.openalex_id_map[paper_key] = openalex_id

                # Get citations (papers that cite this library paper)
                print(f"  Found in OpenAlex: {openalex_id}")
                citations = openalex_client.get_citations(openalex_id, limit=max_citations)

                # Track which library paper each citing paper cites
                with network_lock:
                    for citing_work in citations:
                        citing_id = citing_work.get('openalex_id')
                        if citing_id:
                            # Map: citing_paper -> set of library papers it cites
                            self.citation_network[citing_id].add(openalex_id)

                print(f"  Added {len(citations)} citing papers")
                return (True, len(citations))
            else:
                print(f"  Not found in OpenAlex")
                return (False, 0)

        # Process papers in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all papers with their index
            futures = {
                executor.submit(process_paper, (i, paper)): i
                for i, paper in enumerate(papers_to_process)
            }

            # Wait for completion (futures complete as they finish)
            for future in as_completed(futures):
                try:
                    future.result()  # This will raise any exceptions from the worker
                except Exception as e:
                    print(f"Error processing paper: {e}")

        # Cache the network with build parameters
        print("Saving citation network to cache...")
        with open(cache_file, 'wb') as f:
            pickle.dump({
                'citation_network': dict(self.citation_network),  # Convert defaultdict to dict for pickling
                'id_map': self.openalex_id_map,
                'build_params': {
                    'max_citations': max_citations,
                    'num_papers': len(papers_to_process)
                }
            }, f)

        print(f"Citation network built with {len(self.citation_network)} citing papers.")
        max_cit_str = "unlimited" if max_citations is None else str(max_citations)
        print(f"  Parameters: max_citations={max_cit_str}, {len(papers_to_process)} papers, {max_workers} workers")

    def compute_citation_scores(self, candidate_papers: List[Dict]) -> List[Dict]:
        """
        Compute citation proximity scores for candidate papers.

        Scores based on how many library papers the candidate cites:
        - Cites 1 library paper: 0.5
        - Cites 2 library papers: 0.75
        - Cites 3+ library papers: 1.0
        - Cites 0 library papers: 0.0

        Args:
            candidate_papers: List of papers to score

        Returns:
            List of papers with added 'citation_score' and 'library_papers_cited' fields
        """
        if not self.citation_network:
            raise ValueError("Citation network not built. Call build_library_network first.")

        scored_papers = []

        for paper in candidate_papers:
            openalex_id = paper.get('openalex_id')

            if not openalex_id:
                # Skip papers without OpenAlex ID
                paper['citation_score'] = 0.0
                paper['library_papers_cited'] = 0
                scored_papers.append(paper)
                continue

            # Check how many library papers this candidate cites
            if openalex_id in self.citation_network:
                cited_library_papers = self.citation_network[openalex_id]
                num_cited = len(cited_library_papers)

                # Score based on number of library papers cited
                if num_cited >= 3:
                    score = 1.0
                elif num_cited == 2:
                    score = 0.75
                elif num_cited == 1:
                    score = 0.5
                else:
                    score = 0.0

                paper['library_papers_cited'] = num_cited
            else:
                score = 0.0
                paper['library_papers_cited'] = 0

            paper['citation_score'] = score
            scored_papers.append(paper)

        return scored_papers

    def get_network_stats(self) -> Dict:
        """Get statistics about the citation network."""
        return {
            'citing_papers': len(self.citation_network),
            'library_papers_mapped': len(self.openalex_id_map)
        }
