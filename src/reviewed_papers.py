"""
Storage and management for reviewed papers.
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional


class ReviewedPapersManager:
    """Manages the list of papers that have been reviewed by the user."""

    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize reviewed papers manager.

        Args:
            cache_dir: Directory for storing reviewed papers JSON
        """
        self.cache_dir = cache_dir
        self.storage_file = os.path.join(cache_dir, "reviewed_papers.json")
        os.makedirs(cache_dir, exist_ok=True)

    def _load_reviewed_papers(self) -> Dict:
        """Load reviewed papers from JSON file."""
        if not os.path.exists(self.storage_file):
            return {}

        try:
            with open(self.storage_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupted, return empty dict
            return {}

    def _save_reviewed_papers(self, reviewed_papers: Dict):
        """Save reviewed papers to JSON file."""
        with open(self.storage_file, 'w') as f:
            json.dump(reviewed_papers, f, indent=2)

    def mark_as_reviewed(self, paper_id: str, paper_data: Optional[Dict] = None):
        """
        Mark a paper as reviewed.

        Args:
            paper_id: Unique identifier for the paper (DOI or OpenAlex ID)
            paper_data: Optional paper metadata (title, authors, etc.)
        """
        reviewed_papers = self._load_reviewed_papers()

        # Store paper with review timestamp
        reviewed_papers[paper_id] = {
            'reviewed_date': datetime.now().isoformat(),
            'paper_data': paper_data or {}
        }

        self._save_reviewed_papers(reviewed_papers)

    def is_reviewed(self, paper_id: str) -> bool:
        """
        Check if a paper has been reviewed.

        Args:
            paper_id: Unique identifier for the paper (DOI or OpenAlex ID)

        Returns:
            True if paper has been reviewed, False otherwise
        """
        reviewed_papers = self._load_reviewed_papers()
        return paper_id in reviewed_papers

    def get_all_reviewed(self) -> List[Dict]:
        """
        Get all reviewed papers with their metadata.

        Returns:
            List of reviewed papers with review dates
        """
        reviewed_papers = self._load_reviewed_papers()

        result = []
        for paper_id, data in reviewed_papers.items():
            paper_info = data.get('paper_data', {})
            paper_info['paper_id'] = paper_id
            paper_info['reviewed_date'] = data.get('reviewed_date')
            result.append(paper_info)

        # Sort by review date (most recent first)
        result.sort(key=lambda x: x.get('reviewed_date', ''), reverse=True)

        return result

    def clear_all(self):
        """Clear all reviewed papers."""
        if os.path.exists(self.storage_file):
            os.remove(self.storage_file)

    def get_stats(self) -> Dict:
        """Get statistics about reviewed papers."""
        reviewed_papers = self._load_reviewed_papers()
        return {
            'total_reviewed': len(reviewed_papers)
        }
