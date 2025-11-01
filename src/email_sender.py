"""
Email sending functionality for search results.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class EmailSender:
    """Simple email sender using SMTP."""

    def __init__(self):
        """Initialize email sender from environment variables."""
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('SMTP_FROM_EMAIL', self.smtp_username)

    def is_configured(self) -> bool:
        """Check if email is configured."""
        return bool(self.smtp_username and self.smtp_password)

    def send_search_results(self, to_email: str, results: List[Dict], 
                           search_params: Dict) -> bool:
        """
        Send search results via email.

        Args:
            to_email: Recipient email address
            results: List of paper recommendation dictionaries
            search_params: Dictionary of search parameters used

        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            raise ValueError("Email not configured. Set SMTP_USERNAME and SMTP_PASSWORD in .env")

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Corall Paper Recommendations ({len(results)} papers)'
        msg['From'] = self.from_email
        msg['To'] = to_email

        # Create HTML content
        html_body = self._format_results_html(results, search_params)
        text_body = self._format_results_text(results, search_params)

        # Attach both plain text and HTML versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')

        msg.attach(part1)
        msg.attach(part2)

        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            raise

    def _format_results_html(self, results: List[Dict], search_params: Dict) -> str:
        """Format results as HTML email."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                h1 {{ color: #667eea; }}
                .paper {{ margin: 20px 0; padding: 15px; border-left: 4px solid #667eea; background: #f8f9fa; }}
                .paper-title {{ font-size: 1.2em; font-weight: bold; color: #667eea; margin-bottom: 10px; }}
                .paper-title a {{ text-decoration: none; color: #667eea; }}
                .paper-meta {{ color: #666; font-size: 0.9em; margin: 10px 0; }}
                .paper-scores {{ margin: 10px 0; }}
                .score {{ display: inline-block; margin-right: 15px; }}
                .badge {{ display: inline-block; padding: 3px 8px; background: #d4edda; color: #155724; border-radius: 3px; font-size: 0.85em; }}
                .abstract {{ margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <h1>🔬 Corall Paper Recommendations</h1>
            <p><strong>Search Parameters:</strong></p>
            <ul>
                <li>Days back: {search_params.get('days', 'N/A')}</li>
                <li>Number of results: {search_params.get('top', 'N/A')}</li>
                <li>Citation weight: {search_params.get('citation_weight', 'N/A')}</li>
                <li>Similarity weight: {search_params.get('similarity_weight', 'N/A')}</li>
            </ul>
            <hr>
            <h2>Recommended Papers ({len(results)})</h2>
        """

        for i, paper in enumerate(results, 1):
            title = paper.get('title', 'Unknown Title')
            doi = paper.get('doi', '')
            url = paper.get('url', f'https://doi.org/{doi}' if doi else '')
            
            authors = paper.get('authors', [])
            author_names = ', '.join([a.get('name', '') for a in authors[:3]])
            if len(authors) > 3:
                author_names += f' ... and {len(authors) - 3} more'
            
            date = paper.get('publication_date', 'Unknown')
            journal = paper.get('journal', 'Unknown')
            
            combined_score = paper.get('combined_score', 0)
            citation_score = paper.get('citation_score', 0)
            similarity_score = paper.get('similarity_score', 0)
            
            abstract = paper.get('abstract', '')
            abstract_preview = abstract[:300] + '...' if len(abstract) > 300 else abstract
            
            html += f"""
            <div class="paper">
                <div class="paper-title">
                    {i}. {f'<a href="{url}">{title}</a>' if url else title}
                </div>
                <div class="paper-meta">
                    <strong>Authors:</strong> {author_names if author_names else 'Unknown'}<br>
                    <strong>Published:</strong> {date}<br>
                    <strong>Journal:</strong> {journal}
                    {f'<span class="badge">Open Access</span>' if paper.get('open_access') else ''}
                </div>
                <div class="paper-scores">
                    <span class="score"><strong>Combined:</strong> {combined_score:.3f}</span>
                    <span class="score"><strong>Citation:</strong> {citation_score:.3f}</span>
                    <span class="score"><strong>Similarity:</strong> {similarity_score:.3f}</span>
                </div>
            """

            if abstract:
                html += f"""
                <div class="abstract">
                    <strong>Abstract:</strong> {abstract_preview}
                </div>
                """

            if doi:
                html += f'<div style="margin-top: 10px;"><a href="https://doi.org/{doi}">View on DOI</a></div>'
            
            html += "</div>"

        html += """
            <hr>
            <p style="color: #666; font-size: 0.9em;">
                Generated by Corall Paper Recommendation System<br>
                <a href="http://127.0.0.1:5000">Open Corall Interface</a>
            </p>
        </body>
        </html>
        """
        return html

    def _format_results_text(self, results: List[Dict], search_params: Dict) -> str:
        """Format results as plain text email."""
        text = f"""
Corall Paper Recommendations
============================

Search Parameters:
- Days back: {search_params.get('days', 'N/A')}
- Number of results: {search_params.get('top', 'N/A')}
- Citation weight: {search_params.get('citation_weight', 'N/A')}
- Similarity weight: {search_params.get('similarity_weight', 'N/A')}

Recommended Papers ({len(results)})
===================================
"""
        for i, paper in enumerate(results, 1):
            title = paper.get('title', 'Unknown Title')
            doi = paper.get('doi', '')
            
            authors = paper.get('authors', [])
            author_names = ', '.join([a.get('name', '') for a in authors[:3]])
            if len(authors) > 3:
                author_names += f' ... and {len(authors) - 3} more'
            
            date = paper.get('publication_date', 'Unknown')
            journal = paper.get('journal', 'Unknown')
            
            combined_score = paper.get('combined_score', 0)
            citation_score = paper.get('citation_score', 0)
            similarity_score = paper.get('similarity_score', 0)
            
            abstract = paper.get('abstract', '')
            abstract_preview = abstract[:300] + '...' if len(abstract) > 300 else abstract
            
            text += f"""
{i}. {title}
   Authors: {author_names if author_names else 'Unknown'}
   Published: {date}
   Journal: {journal}
   Scores: Combined={combined_score:.3f}, Citation={citation_score:.3f}, Similarity={similarity_score:.3f}
"""
            if doi:
                text += f"   DOI: https://doi.org/{doi}\n"
            
            if abstract:
                text += f"   Abstract: {abstract_preview}\n"
            
            text += "\n"

        text += """
---
Generated by Corall Paper Recommendation System
"""
        return text

