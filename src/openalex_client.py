"""
OpenAlex API client for citation network and paper discovery.
"""
import os
import time
import pickle
import threading
from typing import List, Dict, Optional, Set
import requests
from dotenv import load_dotenv


class OpenAlexClient:
    """Client for interacting with OpenAlex API."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: Optional[str] = None, cache_dir: str = ".cache"):
        """
        Initialize OpenAlex client.

        Args:
            email: Email for polite pool (gets higher rate limits)
            cache_dir: Directory for caching journal mappings
        """
        load_dotenv()
        self.email = email or os.getenv("OPENALEX_EMAIL")
        self.session = requests.Session()
        self.cache_dir = cache_dir
        self.journal_cache_file = os.path.join(cache_dir, "journal_id_cache.pkl")
        self.journal_cache = self._load_journal_cache()

        # Rate limiting (10 req/sec is safe for polite pool)
        self.last_request_time = 0
        self.min_request_interval = 0.1  # seconds between requests
        self.rate_limit_lock = threading.Lock()  # Thread-safe rate limiting

        # Add email to headers for polite pool
        if self.email:
            self.session.headers.update({"User-Agent": f"mailto:{self.email}"})

    def _load_journal_cache(self) -> Dict[str, Dict]:
        """
        Load journal name-to-ID cache from disk.

        Returns:
            Dictionary mapping normalized journal names to source metadata
        """
        if os.path.exists(self.journal_cache_file):
            try:
                with open(self.journal_cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load journal cache: {e}")
                return {}
        return {}

    def _save_journal_cache(self):
        """Save journal cache to disk."""
        os.makedirs(self.cache_dir, exist_ok=True)
        try:
            with open(self.journal_cache_file, 'wb') as f:
                pickle.dump(self.journal_cache, f)
        except Exception as e:
            print(f"Warning: Could not save journal cache: {e}")

    def find_work_by_doi(self, doi: str) -> Optional[Dict]:
        """
        Find a work in OpenAlex by DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Work metadata or None if not found
        """
        if not doi:
            return None

        # Clean DOI
        doi = doi.strip().replace("https://doi.org/", "")

        url = f"{self.BASE_URL}/works/doi:{doi}"
        response = self._make_request(url)

        if response and response.status_code == 200:
            return self._parse_work(response.json())

        return None

    def find_work_by_title(self, title: str) -> Optional[Dict]:
        """
        Find a work in OpenAlex by title search.

        Args:
            title: Paper title

        Returns:
            Work metadata or None if not found
        """
        if not title:
            return None

        url = f"{self.BASE_URL}/works"
        params = {
            "filter": f"title.search:{title}",
            "per_page": 1
        }

        response = self._make_request(url, params=params)

        if response and response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if results:
                return self._parse_work(results[0])

        return None

    def get_citations(self, openalex_id: str, limit: int = 50) -> List[Dict]:
        """
        Get papers that cite this work.

        Optimized to fetch only IDs for network building (20-50x faster than full metadata).

        Args:
            openalex_id: OpenAlex work ID
            limit: Maximum number of citations to retrieve

        Returns:
            List of citing works with minimal metadata (openalex_id only)
        """
        url = f"{self.BASE_URL}/works"
        params = {
            "filter": f"cites:{openalex_id}",
            "per_page": min(limit, 200),
            "select": "id"  # Only fetch ID field for speed
        }

        response = self._make_request(url, params=params)

        if response and response.status_code == 200:
            data = response.json()
            # Return minimal dicts with just openalex_id (no need for full parsing)
            return [
                {'openalex_id': work.get('id', '').replace('https://openalex.org/', '')}
                for work in data.get('results', [])
            ]

        return []

    def get_references(self, openalex_id: str, limit: int = 50) -> List[Dict]:
        """
        Get papers cited by this work.

        Optimized to fetch only IDs for network building (20-50x faster than full metadata).

        Args:
            openalex_id: OpenAlex work ID
            limit: Maximum number of references to retrieve

        Returns:
            List of referenced works with minimal metadata (openalex_id only)
        """
        url = f"{self.BASE_URL}/works"
        params = {
            "filter": f"cited_by:{openalex_id}",
            "per_page": min(limit, 200),
            "select": "id"  # Only fetch ID field for speed
        }

        response = self._make_request(url, params=params)

        if response and response.status_code == 200:
            data = response.json()
            # Return minimal dicts with just openalex_id (no need for full parsing)
            return [
                {'openalex_id': work.get('id', '').replace('https://openalex.org/', '')}
                for work in data.get('results', [])
            ]

        return []

    def find_source_by_name(self, source_name: str) -> Optional[Dict]:
        """
        Find a source (journal/venue) in OpenAlex by name.
        Uses cache to avoid repeated API calls.

        Args:
            source_name: Name of journal/source

        Returns:
            Source metadata or None if not found
        """
        if not source_name:
            return None

        # Normalize name for cache lookup
        normalized_name = source_name.lower().strip()

        # Check cache first
        if normalized_name in self.journal_cache:
            return self.journal_cache[normalized_name]

        # Not in cache, fetch from API
        url = f"{self.BASE_URL}/sources"
        params = {
            "filter": f"display_name.search:{source_name}",
            "per_page": 1
        }

        response = self._make_request(url, params=params)

        if response and response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if results:
                source = results[0]
                source_data = {
                    'id': source.get('id', '').replace('https://openalex.org/', ''),
                    'display_name': source.get('display_name', ''),
                    'issn_l': source.get('issn_l', ''),
                    'issn': source.get('issn', []),
                    'type': source.get('type', '')
                }

                # Cache the result
                self.journal_cache[normalized_name] = source_data
                self._save_journal_cache()

                return source_data

        # Cache negative result to avoid repeated failed lookups
        self.journal_cache[normalized_name] = None
        self._save_journal_cache()

        return None

    def resolve_journal_ids(self, journal_names: List[str]) -> List[str]:
        """
        Resolve journal names to OpenAlex source IDs.
        Uses cache to avoid repeated API calls.

        Args:
            journal_names: List of journal names

        Returns:
            List of OpenAlex source IDs
        """
        source_ids = []
        cache_hits = 0
        api_calls = 0

        for name in journal_names:
            normalized_name = name.lower().strip()
            was_cached = normalized_name in self.journal_cache

            source = self.find_source_by_name(name)

            if source:
                source_ids.append(source['id'])
                cache_indicator = " (cached)" if was_cached else ""
                print(f"  Matched '{name}' -> {source['display_name']} ({source['id']}){cache_indicator}")
                if was_cached:
                    cache_hits += 1
                else:
                    api_calls += 1
            else:
                print(f"  Could not find source for '{name}'")

            # Only sleep if we made an API call
            if not was_cached:
                time.sleep(0.05)  # Be polite to API

        if cache_hits > 0:
            print(f"  Cache stats: {cache_hits} hits, {api_calls} API calls")

        return source_ids

    def search_recent_papers(self, from_date: str,
                            journal_ids: Optional[List[str]] = None,
                            limit: int = 100) -> List[Dict]:
        """
        Search for recent papers, optionally filtered by journals.
        Fetches ALL available papers using pagination (not limited to 200).

        Args:
            from_date: Date in YYYY-MM-DD format
            journal_ids: List of OpenAlex source IDs to filter by
            limit: Maximum number of papers to retrieve (None = all available)

        Returns:
            List of recent works
        """
        url = f"{self.BASE_URL}/works"

        filters = [f"from_publication_date:{from_date}"]

        if journal_ids:
            # Use OR logic for journals
            journal_filter = "|".join(journal_ids)
            filters.append(f"primary_location.source.id:{journal_filter}")

        print(f"  OpenAlex query: {url}")
        print(f"  Filters: {', '.join(filters)}")
        print(f"  Sort: publication_date:desc")

        # First request using cursor pagination (supports >10,000 results)
        params = {
            "filter": ",".join(filters),
            "sort": "publication_date:desc",
            "per_page": 200,  # Max per page
            "cursor": "*"  # Start cursor pagination
        }

        response = self._make_request(url, params=params)
        if not response or response.status_code != 200:
            return []

        data = response.json()
        total_results = data.get('meta', {}).get('count', 0)
        all_results = data.get('results', [])

        print(f"  Total papers available in OpenAlex: {total_results}")
        print(f"  Fetching papers via cursor pagination (supports >10,000 results)...")

        # Get next cursor from response
        next_cursor = data.get('meta', {}).get('next_cursor')
        page_count = 1

        # Continue fetching while cursor exists and we haven't hit limit
        while next_cursor and (limit is None or len(all_results) < limit):
            params['cursor'] = next_cursor
            response = self._make_request(url, params=params)

            if response and response.status_code == 200:
                page_data = response.json()
                page_results = page_data.get('results', [])
                all_results.extend(page_results)
                next_cursor = page_data.get('meta', {}).get('next_cursor')
                page_count += 1

                print(f"  Fetched page {page_count} ({len(page_results)} papers, total: {len(all_results)})")
                time.sleep(0.1)  # Be polite to API
            else:
                print(f"  Error fetching page {page_count}, stopping pagination")
                break

        print(f"  Total papers fetched: {len(all_results)}")

        # Parse and return
        parsed_results = [self._parse_work(work) for work in all_results]

        # Apply limit if specified
        if limit:
            parsed_results = parsed_results[:limit]
            print(f"  Limiting to {len(parsed_results)} papers")

        return parsed_results

    def _parse_work(self, work: Dict) -> Dict:
        """
        Parse OpenAlex work into standardized format.

        Args:
            work: Raw OpenAlex work object

        Returns:
            Standardized work dictionary
        """
        # Extract journal/source information
        primary_location = work.get('primary_location', {})
        source = primary_location.get('source', {}) if primary_location else {}
        journal = source.get('display_name', '') if source else ''

        return {
            'openalex_id': work.get('id', '').replace('https://openalex.org/', ''),
            'title': work.get('title', ''),
            'doi': work.get('doi', '').replace('https://doi.org/', '') if work.get('doi') else '',
            'publication_date': work.get('publication_date', ''),
            'publication_year': work.get('publication_year'),
            'journal': journal,
            'abstract': self._get_abstract(work),
            'authors': [
                {
                    'name': author.get('author', {}).get('display_name', ''),
                    'id': author.get('author', {}).get('id', '')
                }
                for author in work.get('authorships', [])
            ],
            'concepts': [
                {
                    'name': concept.get('display_name', ''),
                    'score': concept.get('score', 0)
                }
                for concept in work.get('concepts', [])
            ],
            'cited_by_count': work.get('cited_by_count', 0),
            'url': work.get('id', ''),
            'open_access': work.get('open_access', {}).get('is_oa', False),
            'pdf_url': work.get('open_access', {}).get('oa_url'),
        }

    def _get_abstract(self, work: Dict) -> str:
        """Extract abstract from work object."""
        abstract_inverted = work.get('abstract_inverted_index', {})

        if not abstract_inverted:
            return ''

        # Reconstruct abstract from inverted index
        words = {}
        for word, positions in abstract_inverted.items():
            for pos in positions:
                words[pos] = word

        return ' '.join(words[pos] for pos in sorted(words.keys()))

    def _make_request(self, url: str, params: Optional[Dict] = None, max_retries: int = 3) -> Optional[requests.Response]:
        """
        Make HTTP request with rate limiting, retry logic, and error handling.

        Args:
            url: Request URL
            params: Query parameters
            max_retries: Maximum number of retries for rate limit errors

        Returns:
            Response object or None on error
        """
        for attempt in range(max_retries):
            # Rate limiting: ensure minimum time between requests (thread-safe)
            with self.rate_limit_lock:
                elapsed = time.time() - self.last_request_time
                if elapsed < self.min_request_interval:
                    time.sleep(self.min_request_interval - elapsed)
                self.last_request_time = time.time()

            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                # Handle 429 (Too Many Requests) with exponential backoff
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt)  # 1s, 2s, 4s
                        print(f"Rate limit hit (429). Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Rate limit hit (429). Max retries exceeded.")
                        return None
                else:
                    print(f"HTTP error making request to {url}: {e}")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"Error making request to {url}: {e}")
                return None

        return None
