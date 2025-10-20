#!/usr/bin/env python3
"""
CLI for paper recommendation engine.
"""
import os
import sys
import json
from datetime import datetime
import click
from dotenv import load_dotenv

from src.recommender import PaperRecommender
from src.journal_lists import load_journals_from_file


@click.group()
def cli():
    """Paper Recommendation Engine - Get personalized research paper recommendations."""
    pass


@cli.command()
@click.option('--force', is_flag=True, help='Force rebuild of all caches')
@click.option('--max-papers', type=int, default=None, help='Limit number of library papers (for testing)')
@click.option('--collection-id', type=str, default=None, help='Use specific Zotero collection (ID or name)')
@click.option('--workers', type=int, default=5, help='Number of parallel workers (default: 5)')
def init(force, max_papers, collection_id, workers):
    """Initialize the recommendation engine by building profiles and networks."""
    load_dotenv()

    try:
        # Set collection ID if provided
        if collection_id:
            os.environ['ZOTERO_COLLECTION_ID'] = collection_id

        recommender = PaperRecommender()
        recommender.initialize(force_rebuild=force, max_papers=max_papers,
                             max_workers=workers)

        # Show stats
        stats = recommender.get_library_stats()
        click.echo("\n" + "="*60)
        click.echo("Library Statistics:")
        click.echo("="*60)
        click.echo(f"Total papers: {stats['library']['total_papers']}")
        click.echo(f"Papers with DOI: {stats['library']['papers_with_doi']}")
        click.echo(f"Papers with abstract: {stats['library']['papers_with_abstract']}")
        click.echo(f"Unique authors: {stats['library']['unique_authors']}")
        click.echo(f"Citation network size: {stats['citation_network']['total_works']} works")
        click.echo(f"Papers with embeddings: {stats['embeddings']['papers_with_embeddings']}")
        click.echo("="*60)

        click.echo("\nInitialization complete! You can now run recommendations.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--days', type=int, default=7, help='Days back to search for papers')
@click.option('--top', type=int, default=10, help='Number of recommendations to return')
@click.option('--citation-weight', type=float, default=0.3, help='Weight for citation score (0-1)')
@click.option('--similarity-weight', type=float, default=0.7, help='Weight for similarity score (0-1)')
@click.option('--min-citation', type=float, default=0.0, help='Minimum citation score threshold')
@click.option('--min-similarity', type=float, default=0.0, help='Minimum similarity score threshold')
@click.option('--explain', is_flag=True, help='Show detailed explanations for recommendations')
@click.option('--export', type=click.Path(), default=None, help='Export recommendations to JSON file')
@click.option('--filter-journals', is_flag=True, default=True, help='Filter by top biology/medicine journals (default: True)')
@click.option('--no-filter-journals', is_flag=True, help='Disable journal filtering')
@click.option('--custom-journals', type=str, default=None, help='Comma-separated list of custom journal names')
@click.option('--journal-file', type=click.Path(exists=True), default=None, help='Path to file containing journal names (one per line)')
@click.option('--collection-id', type=str, default=None, help='Use specific Zotero collection (ID or name)')
def recommend(days, top, citation_weight, similarity_weight, min_citation,
              min_similarity, explain, export, filter_journals, no_filter_journals, custom_journals, journal_file, collection_id):
    """Get paper recommendations based on your library."""
    load_dotenv()

    # Set collection ID if provided
    if collection_id:
        os.environ['ZOTERO_COLLECTION_ID'] = collection_id

    try:
        # Load recommender
        recommender = PaperRecommender()

        # Check if initialized
        cache_dir = ".cache"
        if not os.path.exists(os.path.join(cache_dir, "library_embeddings.pkl")):
            click.echo("Error: Recommender not initialized. Run 'recommend.py init' first.", err=True)
            sys.exit(1)

        # Load from cache
        click.echo("Loading recommendation engine...")
        recommender.library_papers = recommender.zotero.fetch_library()
        recommender.similarity.build_library_profile(recommender.library_papers)
        recommender.citation_scorer.build_library_network(
            recommender.openalex,
            recommender.library_papers
        )
        recommender.is_initialized = True

        # Prepare journal filtering options
        use_journal_filter = filter_journals and not no_filter_journals
        custom_journal_list = None

        # Load journals from file if provided
        if journal_file:
            click.echo(f"Loading journals from file: {journal_file}")
            custom_journal_list = load_journals_from_file(journal_file)
            click.echo(f"Loaded {len(custom_journal_list)} journals from file")
            use_journal_filter = True
        # Otherwise check for comma-separated list
        elif custom_journals:
            custom_journal_list = [j.strip() for j in custom_journals.split(',')]
            use_journal_filter = True

        # Get recommendations
        recommendations = recommender.get_recommendations(
            days_back=days,
            limit=top,
            citation_weight=citation_weight,
            similarity_weight=similarity_weight,
            min_citation_score=min_citation,
            min_similarity_score=min_similarity,
            use_journal_filter=use_journal_filter,
            custom_journals=custom_journal_list
        )

        if not recommendations:
            click.echo("No recommendations found. Try adjusting the parameters.")
            return

        # Display recommendations
        click.echo("\n" + "="*60)
        click.echo(f"Top {len(recommendations)} Recommendations")
        click.echo("="*60)

        for i, paper in enumerate(recommendations, 1):
            click.echo(f"\n{i}. {paper.get('title', 'Unknown Title')}")
            click.echo(f"   Score: {paper.get('combined_score', 0):.3f} "
                      f"(Citation: {paper.get('citation_score', 0):.3f}, "
                      f"Similarity: {paper.get('similarity_score', 0):.3f})")

            authors = paper.get('authors', [])
            if authors:
                # Format: First 2 authors ... Last 2 authors
                author_names = [a.get('name', '') for a in authors]
                if len(author_names) <= 4:
                    author_str = ', '.join(author_names)
                else:
                    first_two = ', '.join(author_names[:2])
                    last_two = ', '.join(author_names[-2:])
                    author_str = f"{first_two} ... {last_two}"
                click.echo(f"   Authors: {author_str}")

            # Show most similar paper from library
            most_similar = paper.get('most_similar_paper')
            if most_similar:
                similar_title = most_similar.get('title', 'Unknown')
                # Truncate to 60 characters
                if len(similar_title) > 60:
                    similar_title = similar_title[:60] + '...'
                similar_sim = most_similar.get('similarity', 0)
                click.echo(f"   Most similar to: \"{similar_title}\" (similarity: {similar_sim:.3f})")

            if paper.get('publication_date'):
                click.echo(f"   Published: {paper.get('publication_date')}")

            if paper.get('doi'):
                click.echo(f"   DOI: https://doi.org/{paper.get('doi')}")
            elif paper.get('url'):
                click.echo(f"   URL: {paper.get('url')}")

            if paper.get('open_access') and paper.get('pdf_url'):
                click.echo(f"   PDF: {paper.get('pdf_url')} (Open Access)")

            if explain:
                explanation = recommender.explain_recommendation(paper)
                click.echo(explanation)

        # Export if requested
        if export:
            with open(export, 'w') as f:
                json.dump(recommendations, f, indent=2, default=str)
            click.echo(f"\nRecommendations exported to {export}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
def stats():
    """Show statistics about your library and recommendation profiles."""
    load_dotenv()

    try:
        recommender = PaperRecommender()

        # Load from cache
        cache_dir = ".cache"
        if not os.path.exists(os.path.join(cache_dir, "library_embeddings.pkl")):
            click.echo("Error: Recommender not initialized. Run 'recommend.py init' first.", err=True)
            sys.exit(1)

        recommender.library_papers = recommender.zotero.fetch_library()
        recommender.similarity.build_library_profile(recommender.library_papers)
        recommender.citation_scorer.build_library_network(
            recommender.openalex,
            recommender.library_papers
        )
        recommender.is_initialized = True

        stats = recommender.get_library_stats()

        click.echo("\n" + "="*60)
        click.echo("Library Statistics")
        click.echo("="*60)
        click.echo(f"Total papers: {stats['library']['total_papers']}")
        click.echo(f"Papers with DOI: {stats['library']['papers_with_doi']}")
        click.echo(f"Papers with abstract: {stats['library']['papers_with_abstract']}")
        click.echo(f"Unique authors: {stats['library']['unique_authors']}")
        click.echo(f"\nCitation network size: {stats['citation_network']['total_works']} works")
        click.echo(f"Library papers mapped to OpenAlex: {stats['citation_network']['library_papers_mapped']}")
        click.echo(f"\nPapers with embeddings: {stats['embeddings']['papers_with_embeddings']}")
        click.echo("="*60)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def collections():
    """List all Zotero collections in your library."""
    load_dotenv()

    try:
        from src.zotero_client import ZoteroClient

        zotero_client = ZoteroClient()
        collections = zotero_client.list_collections()

        if not collections:
            click.echo("No collections found in your library.")
            return

        click.echo("\n" + "="*60)
        click.echo("Zotero Collections")
        click.echo("="*60)

        # Group by parent
        top_level = [c for c in collections if not c['parent']]
        children = [c for c in collections if c['parent']]

        for col in top_level:
            click.echo(f"\n{col['name']}")
            click.echo(f"  ID: {col['id']}")
            click.echo(f"  Items: {col['num_items']}")

            # Show children
            child_cols = [c for c in children if c['parent'] == col['id']]
            for child in child_cols:
                click.echo(f"  └─ {child['name']}")
                click.echo(f"     ID: {child['id']}")
                click.echo(f"     Items: {child['num_items']}")

        click.echo("\n" + "="*60)
        click.echo(f"\nTotal collections: {len(collections)}")
        click.echo("\nTo use a specific collection, add to your .env file:")
        click.echo("  ZOTERO_COLLECTION_ID=<collection_id>")
        click.echo("\nOr use the --collection-id option with init/recommend commands")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.option('--journals-only', is_flag=True, help='Clear only journal ID cache')
def clear_cache(confirm, journals_only):
    """Clear all cached data (embeddings, citation network, etc.)."""
    import shutil

    cache_dir = ".cache"

    if not os.path.exists(cache_dir):
        click.echo("No cache directory found. Nothing to clear.")
        return

    # Handle journals-only mode
    if journals_only:
        journal_cache_file = os.path.join(cache_dir, "journal_id_cache.pkl")
        if not os.path.exists(journal_cache_file):
            click.echo("No journal cache found. Nothing to clear.")
            return

        size = os.path.getsize(journal_cache_file)
        size_kb = size / 1024
        click.echo(f"\nJournal cache: {size_kb:.2f} KB")

        if not confirm:
            if not click.confirm('\nAre you sure you want to clear the journal cache?'):
                click.echo("Cache clearing cancelled.")
                return

        try:
            os.remove(journal_cache_file)
            click.echo("\n✓ Journal cache cleared successfully!")
        except Exception as e:
            click.echo(f"Error clearing journal cache: {e}", err=True)
            sys.exit(1)
        return

    # Check what's in the cache
    cache_files = []
    if os.path.exists(cache_dir):
        for item in os.listdir(cache_dir):
            cache_files.append(item)

    if not cache_files:
        click.echo("Cache directory is empty. Nothing to clear.")
        return

    # Show what will be deleted
    click.echo("\n" + "="*60)
    click.echo("Cache Contents:")
    click.echo("="*60)
    for f in cache_files:
        file_path = os.path.join(cache_dir, f)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            size_mb = size / (1024 * 1024)
            click.echo(f"  {f} ({size_mb:.2f} MB)")
        else:
            click.echo(f"  {f} (directory)")
    click.echo("="*60)

    # Confirm deletion
    if not confirm:
        if not click.confirm('\nAre you sure you want to delete all cached data?'):
            click.echo("Cache clearing cancelled.")
            return

    # Delete cache
    try:
        shutil.rmtree(cache_dir)
        os.makedirs(cache_dir)
        click.echo("\n✓ Cache cleared successfully!")
        click.echo("Run 'recommend.py init' to rebuild the cache.")
    except Exception as e:
        click.echo(f"Error clearing cache: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('output_file', type=click.Path())
@click.option('--days', type=int, default=7, help='Days back to search for papers')
@click.option('--top', type=int, default=20, help='Number of recommendations to export')
def export_bibtex(output_file, days, top):
    """Export recommendations as BibTeX for import into Zotero."""
    load_dotenv()

    try:
        # Load recommender
        recommender = PaperRecommender()

        cache_dir = ".cache"
        if not os.path.exists(os.path.join(cache_dir, "library_embeddings.pkl")):
            click.echo("Error: Recommender not initialized. Run 'recommend.py init' first.", err=True)
            sys.exit(1)

        click.echo("Loading recommendation engine...")
        recommender.library_papers = recommender.zotero.fetch_library()
        recommender.similarity.build_library_profile(recommender.library_papers)
        recommender.citation_scorer.build_library_network(
            recommender.openalex,
            recommender.library_papers
        )
        recommender.is_initialized = True

        # Get recommendations
        recommendations = recommender.get_recommendations(days_back=days, limit=top)

        if not recommendations:
            click.echo("No recommendations found.")
            return

        # Generate BibTeX
        with open(output_file, 'w') as f:
            for i, paper in enumerate(recommendations, 1):
                # Generate citation key
                first_author = paper.get('authors', [{}])[0].get('name', 'Unknown').split()[-1]
                year = paper.get('publication_year', 'XXXX')
                key = f"{first_author}{year}_{i}"

                f.write(f"@article{{{key},\n")
                f.write(f"  title = {{{paper.get('title', '')}}},\n")

                if paper.get('authors'):
                    author_str = ' and '.join([a.get('name', '') for a in paper.get('authors', [])])
                    f.write(f"  author = {{{author_str}}},\n")

                if paper.get('publication_year'):
                    f.write(f"  year = {{{paper.get('publication_year')}}},\n")

                if paper.get('doi'):
                    f.write(f"  doi = {{{paper.get('doi')}}},\n")

                if paper.get('url'):
                    f.write(f"  url = {{{paper.get('url')}}},\n")

                if paper.get('abstract'):
                    f.write(f"  abstract = {{{paper.get('abstract')}}},\n")

                f.write(f"  note = {{Recommended - Score: {paper.get('combined_score', 0):.3f}}}\n")
                f.write("}\n\n")

        click.echo(f"Exported {len(recommendations)} recommendations to {output_file}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
