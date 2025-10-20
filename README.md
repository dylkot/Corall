# Corall - Research Paper Recommendation Engine

A lightweight, personalized research paper recommendation system that learns from your Zotero library and uses citation networks + content similarity to suggest relevant new papers.

## Features

- **Citation Network Analysis**: Builds a citation graph around your library using OpenAlex API
- **Content Similarity**: Uses lightweight sentence transformers to match paper abstracts semantically
- **Hybrid Ranking**: Combines both signals for better recommendations
- **Zotero Integration**: Syncs directly with your Zotero library (full library or specific collections)
- **CLI Tool**: Simple command-line interface for on-demand recommendations
- **Smart Caching**: Avoids re-processing by caching embeddings and citation networks
- **BibTeX Export**: Export recommendations directly for import into Zotero

## How It Works

1. **Profile Building**: Fetches your Zotero library and builds:
   - Semantic embeddings of paper abstracts using sentence-transformers
   - Citation network graph from OpenAlex (papers citing/cited by your library)

2. **Discovery**: Searches OpenAlex for recent papers matching your research interests

3. **Scoring**: Ranks papers using:
   - **Citation proximity**: How close are they to papers you've read?
   - **Content similarity**: Do their abstracts match your interests?

4. **Recommendations**: Returns top-ranked papers with explanations

## Setup

### Prerequisites

- Python 3.8+
- Zotero account with API access
- (Optional) OpenAlex account for higher rate limits

### Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your credentials:

Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
ZOTERO_API_KEY=your_api_key_here
ZOTERO_USER_ID=your_user_id_here
ZOTERO_LIBRARY_TYPE=user
OPENALEX_EMAIL=your_email@example.com
```

#### Getting Zotero API Credentials

1. Go to https://www.zotero.org/settings/keys
2. Create a new API key with read access to your library
3. Your User ID is shown on the same page

#### Using a Specific Zotero Collection (Optional)

By default, Corall uses your entire Zotero library. To use only a specific collection/folder:

1. **List your collections**:
   ```bash
   python recommend.py collections
   ```

2. **Set collection in .env file**:
   ```env
   ZOTERO_COLLECTION_ID=ABC12345
   ```

   Or use collection name instead of ID:
   ```env
   ZOTERO_COLLECTION_ID=Machine Learning Papers
   ```

3. **Or specify when running commands**:
   ```bash
   python recommend.py init --collection-id "Machine Learning Papers"
   python recommend.py recommend --collection-id ABC12345
   ```

This is useful if you maintain separate collections for different research topics.

#### OpenAlex Email (Optional)

Adding your email gets you into OpenAlex's "polite pool" with higher rate limits. No registration required.

## Usage

### Initialize the System

First, build your recommendation profile (this takes a few minutes):

```bash
python recommend.py init
```

This will:
- Fetch your Zotero library
- Build semantic embeddings for all papers
- Construct citation network from OpenAlex
- Cache everything for fast future queries

To force rebuild all caches:
```bash
python recommend.py init --force
```

### Clear Cache

To clear all cached data (embeddings, citation network, etc.):
```bash
python recommend.py clear-cache
```

This will show you what's in the cache and ask for confirmation before deleting. To skip confirmation:
```bash
python recommend.py clear-cache --confirm
```

After clearing the cache, you'll need to run `init` again to rebuild it.

### Get Recommendations

Get top 10 papers from the last 7 days:
```bash
python recommend.py recommend
```

#### Options

```bash
# Get top 20 papers from last 14 days
python recommend.py recommend --days 14 --top 20

# Adjust scoring weights (citation vs similarity)
python recommend.py recommend --citation-weight 0.5 --similarity-weight 0.5

# Set minimum thresholds
python recommend.py recommend --min-citation 0.2 --min-similarity 0.4

# Use deeper citation network analysis (slower but more accurate)
python recommend.py recommend --deep

# Show detailed explanations
python recommend.py recommend --explain

# Export to JSON
python recommend.py recommend --export recommendations.json
```

### View Statistics

See stats about your library and recommendation profiles:
```bash
python recommend.py stats
```

### Export to BibTeX

Export recommendations as BibTeX for import into Zotero:
```bash
python recommend.py export-bibtex recommendations.bib --days 7 --top 20
```

Then import `recommendations.bib` into Zotero.

## Example Output

```
Top 10 Recommendations
============================================================

1. Deep Learning for Protein Structure Prediction
   Score: 0.856 (Citation: 0.700, Similarity: 0.924)
   Authors: John Smith, Jane Doe ... Robert Johnson, Sarah Williams
   Most similar to: "AlphaFold: Accurate protein structure prediction" (similarity: 0.924)
   Published: 2024-10-15
   DOI: https://doi.org/10.1234/example
   PDF: https://arxiv.org/pdf/... (Open Access)

2. Novel Approaches to Gene Expression Analysis
   Score: 0.823 (Citation: 0.600, Similarity: 0.915)
   ...
```

## Configuration

You can customize default settings in `.env`:

```env
DEFAULT_DAYS_BACK=7
DEFAULT_TOP_N=10
CACHE_DIR=.cache
```

Or use the `config.example.json` as a template.

## How the Scoring Works

Each paper gets two scores:

1. **Citation Score** (0-1):
   - 1.0 if the paper is directly in your citation network
   - 0.0-0.8 based on number of connections to your network
   - 0.0 if no connections found

2. **Similarity Score** (0-1):
   - Computed using cosine similarity between paper embeddings
   - Based on semantic similarity of abstracts
   - Uses the maximum similarity to any paper in your library

**Combined Score** = `citation_weight × citation_score + similarity_weight × similarity_score`

Default weights: 30% citation, 70% similarity

## Performance

- **First initialization**: 5-15 minutes for a library of ~200 papers
- **Subsequent recommendations**: 1-3 minutes (uses cached data)
- **Memory usage**: ~500MB (model + embeddings)
- **Model size**: ~80MB (all-MiniLM-L6-v2)

## Caching

All data is cached in `.cache/` directory:
- `library_embeddings.pkl`: Paper embeddings
- `citation_network.pkl`: Citation graph data

To rebuild caches, use `--force` flag with `init` command.

## Troubleshooting

### "Recommender not initialized"
Run `python recommend.py init` first.

### Rate limiting from OpenAlex
Add your email to `.env` as `OPENALEX_EMAIL` for higher limits.

### No recommendations found
Try:
- Increasing `--days` to search further back
- Lowering thresholds: `--min-citation 0 --min-similarity 0`
- Using `--deep` for better citation network analysis

### Papers not matching to OpenAlex
Some papers may not be in OpenAlex, especially very recent preprints. The system will still use content similarity for these.

## Architecture

```
Corall/
├── src/
│   ├── zotero_client.py      # Zotero API integration
│   ├── openalex_client.py    # OpenAlex API client
│   ├── similarity_engine.py   # Content similarity with embeddings
│   ├── citation_scorer.py     # Citation network scoring
│   └── recommender.py         # Main recommendation engine
├── recommend.py               # CLI interface
├── requirements.txt           # Python dependencies
├── .env                       # Your credentials (create from .env.example)
└── .cache/                    # Cached data (auto-generated)
```

## Tech Stack

- **pyzotero**: Zotero API client
- **sentence-transformers**: Semantic embeddings (all-MiniLM-L6-v2)
- **OpenAlex API**: Citation network and paper metadata
- **click**: CLI framework
- **numpy/scipy**: Similarity computations

## Limitations

- Requires papers to have abstracts for best content similarity
- OpenAlex coverage may vary by field (excellent for STEM, good for others)
- Citation network analysis is limited to what's indexed in OpenAlex
- Recommendations are only as good as your library profile

## Future Enhancements

Potential additions:
- Author network analysis
- Topic modeling for better concept extraction
- Support for other reference managers (Mendeley, Papers)
- Web dashboard interface
- Automated email digests
- Fine-tuning on user feedback

## License

MIT License - feel free to modify and extend!

## Contributing

Contributions welcome! Some ideas:
- Add support for other reference managers
- Improve scoring algorithms
- Add visualization of citation networks
- Build a web interface

## Credits

Built with:
- [OpenAlex](https://openalex.org/) - Open citation and publication data
- [Zotero](https://www.zotero.org/) - Reference management
- [Sentence Transformers](https://www.sbert.net/) - Semantic embeddings

## Support

For issues or questions, please open an issue on GitHub.
