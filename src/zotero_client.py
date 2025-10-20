"""
Zotero API client for fetching user's research library.
"""
import os
from typing import List, Dict, Optional
from pyzotero import zotero
from dotenv import load_dotenv


class ZoteroClient:
    """Client for interacting with Zotero API."""

    def __init__(self, api_key: Optional[str] = None, user_id: Optional[str] = None,
                 library_type: str = "user", collection_id: Optional[str] = None):
        """
        Initialize Zotero client.

        Args:
            api_key: Zotero API key (or set ZOTERO_API_KEY env var)
            user_id: Zotero user ID (or set ZOTERO_USER_ID env var)
            library_type: Type of library (user or group)
            collection_id: Optional collection ID to filter items (or set ZOTERO_COLLECTION_ID env var)
        """
        load_dotenv()

        self.api_key = api_key or os.getenv("ZOTERO_API_KEY")
        self.user_id = user_id or os.getenv("ZOTERO_USER_ID")
        self.library_type = library_type or os.getenv("ZOTERO_LIBRARY_TYPE", "user")
        collection_input = collection_id or os.getenv("ZOTERO_COLLECTION_ID")

        if not self.api_key or not self.user_id:
            raise ValueError(
                "Zotero API key and user ID required. "
                "Set ZOTERO_API_KEY and ZOTERO_USER_ID environment variables."
            )

        self.zot = zotero.Zotero(self.user_id, self.library_type, self.api_key)

        # Resolve collection name to ID if needed
        if collection_input:
            # Check if it looks like an ID (8 alphanumeric chars) or a name
            if len(collection_input) == 8 and collection_input.isalnum():
                self.collection_id = collection_input
            else:
                # Try to find collection by name
                found_id = self.find_collection_by_name(collection_input)
                if found_id:
                    print(f"Resolved collection '{collection_input}' to ID: {found_id}")
                    self.collection_id = found_id
                else:
                    print(f"Warning: Could not find collection '{collection_input}'. Using entire library.")
                    self.collection_id = None
        else:
            self.collection_id = None

    def fetch_library(self, limit: Optional[int] = None, collection_id: Optional[str] = None) -> List[Dict]:
        """
        Fetch all items from Zotero library or a specific collection.

        Args:
            limit: Maximum number of items to fetch (None for all)
            collection_id: Optional collection ID to fetch from (overrides instance collection_id)

        Returns:
            List of paper metadata dictionaries
        """
        # Use provided collection_id, fall back to instance collection_id
        target_collection = collection_id or self.collection_id

        if target_collection:
            print(f"Fetching items from collection: {target_collection}")
            items = self.zot.everything(self.zot.collection_items(target_collection, limit=limit))
        else:
            items = self.zot.everything(self.zot.top(limit=limit))

        papers = []
        for item in items:
            paper = self._parse_item(item)
            if paper:
                papers.append(paper)

        return papers

    def _parse_item(self, item: Dict) -> Optional[Dict]:
        """
        Parse Zotero item into standardized paper format.

        Args:
            item: Raw Zotero item

        Returns:
            Standardized paper dictionary or None if not a paper
        """
        data = item.get('data', {})
        item_type = data.get('itemType', '')

        # Only process journal articles, conference papers, preprints
        valid_types = {'journalArticle', 'conferencePaper', 'preprint', 'report'}
        if item_type not in valid_types:
            return None

        # Extract key fields
        paper = {
            'title': data.get('title', ''),
            'abstract': data.get('abstractNote', ''),
            'authors': self._extract_authors(data.get('creators', [])),
            'year': data.get('date', '')[:4] if data.get('date') else None,
            'doi': data.get('DOI', ''),
            'url': data.get('url', ''),
            'publication': data.get('publicationTitle', ''),
            'item_type': item_type,
            'zotero_key': data.get('key', ''),
            'date_added': data.get('dateAdded', ''),
        }

        # Skip items without title
        if not paper['title']:
            return None

        return paper

    def _extract_authors(self, creators: List[Dict]) -> List[str]:
        """
        Extract author names from creators list.

        Args:
            creators: List of creator dictionaries

        Returns:
            List of author name strings
        """
        authors = []
        for creator in creators:
            if creator.get('creatorType') == 'author':
                first = creator.get('firstName', '')
                last = creator.get('lastName', '')
                name = f"{first} {last}".strip()
                if name:
                    authors.append(name)
        return authors

    def get_library_stats(self) -> Dict:
        """Get basic statistics about the library."""
        papers = self.fetch_library()

        return {
            'total_papers': len(papers),
            'papers_with_doi': sum(1 for p in papers if p.get('doi')),
            'papers_with_abstract': sum(1 for p in papers if p.get('abstract')),
            'unique_authors': len(set(
                author for p in papers for author in p.get('authors', [])
            ))
        }

    def list_collections(self) -> List[Dict]:
        """
        List all collections in the library.

        Returns:
            List of collection dictionaries with 'id', 'name', and 'num_items'
        """
        collections = self.zot.collections()

        collection_list = []
        for col in collections:
            col_data = col.get('data', {})
            collection_list.append({
                'id': col_data.get('key', ''),
                'name': col_data.get('name', ''),
                'num_items': self.zot.num_collectionitems(col_data.get('key', '')),
                'parent': col_data.get('parentCollection', None)
            })

        return collection_list

    def find_collection_by_name(self, name: str) -> Optional[str]:
        """
        Find a collection ID by its name.

        Args:
            name: Collection name (case-insensitive partial match)

        Returns:
            Collection ID if found, None otherwise
        """
        collections = self.list_collections()
        name_lower = name.lower()

        # Try exact match first
        for col in collections:
            if col['name'].lower() == name_lower:
                return col['id']

        # Try partial match
        for col in collections:
            if name_lower in col['name'].lower():
                return col['id']

        return None
