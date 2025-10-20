# Corall Web Interface

A simple web-based interface for the Corall paper recommendation system.

## Features

- **Initialize System**: Build your recommendation profile from your Zotero library
- **Adjust Search Parameters**:
  - Time window (1-365 days)
  - Number of results (1-50)
  - Journal filtering (default list, custom list, or no filter)
  - Citation and similarity weights
- **View Results**:
  - Paper titles with clickable DOI links
  - Author information
  - Publication dates
  - Open access indicators and PDF links
  - Visual score breakdown (Combined, Citation, Similarity)
  - Abstract previews

## Quick Start

1. **Start the web server:**

```bash
python app.py
```

The server will start on `http://127.0.0.1:5000`

2. **Open your browser:**

Navigate to `http://127.0.0.1:5000`

3. **Initialize the system:**

Click the "Initialize System" button. This will:
- Fetch your Zotero library
- Build semantic embeddings
- Create citation network
- Cache everything for future use

**Note:** First initialization takes 5-15 minutes depending on your library size.

4. **Search for papers:**

- Set your desired time window (default: 7 days)
- Choose journal filtering option
- Adjust scoring weights if desired
- Click "Get Recommendations"

## Journal Filtering Options

### Default Top 50 Journals
Uses the built-in curated list of 49 high-impact biology/medicine journals.

### Custom List
Enter your own journals, one per line. For example:
```
Nature
Science
Cell
Blood
Arthritis & Rheumatology
```

### No Filter
Searches all journals in OpenAlex (slower, less focused).

## Understanding the Scores

Each recommended paper shows three scores:

1. **Combined Score**: Weighted combination of citation and similarity scores
   - Default: 30% citation + 70% similarity
   - You can adjust these weights in the interface

2. **Citation Score**:
   - 1.0 = Paper is in your citation network
   - 0.0 = No citation connection to your library
   - Measures how connected the paper is to papers you've read

3. **Similarity Score**:
   - 0.0-1.0 = Semantic similarity to your library
   - Based on abstract/title similarity using AI embeddings
   - Measures how topically relevant the paper is

## API Endpoints

The web interface uses these REST API endpoints:

- `GET /api/status` - Check initialization status
- `POST /api/initialize` - Initialize the recommendation system
- `POST /api/recommend` - Get paper recommendations
- `GET /api/journals/default` - Get default journal list
- `GET /api/journals/library` - Get journals from your library

## Troubleshooting

### Server won't start
- Make sure Flask is installed: `pip install flask flask-cors`
- Check that port 5000 isn't already in use

### "System not initialized" error
- Click the "Initialize System" button first
- Wait for initialization to complete

### No results found
- Try increasing the time window (e.g., 14 or 30 days)
- Reduce or disable journal filtering
- Check that your Zotero library is accessible

### Initialization fails
- Verify your `.env` file has correct Zotero credentials
- Check your internet connection
- Look at the terminal output for specific error messages

## Architecture

```
┌─────────────┐
│   Browser   │
│  (Frontend) │
└──────┬──────┘
       │ HTTP/JSON
       │
┌──────▼──────┐
│   Flask     │
│   (app.py)  │
└──────┬──────┘
       │
       ├─► PaperRecommender
       ├─► ZoteroClient
       ├─► OpenAlexClient
       └─► SimilarityEngine
```

The web interface is a thin layer over the existing CLI functionality, making all features accessible through a browser.

## Development

To modify the interface:

- **Backend**: Edit `app.py`
- **Frontend**: Edit `templates/index.html`
- **Styling**: CSS is embedded in the HTML `<style>` tag
- **JavaScript**: JavaScript is embedded at the bottom of the HTML

The interface uses:
- Flask for the web server
- jQuery for AJAX requests
- Vanilla JavaScript for UI interactions
- CSS3 for styling with gradient themes

## Production Considerations

This is a **development interface** for local use. For production deployment:

1. Use a production WSGI server (e.g., Gunicorn)
2. Add authentication/authorization
3. Set `debug=False` in `app.py`
4. Use environment variables for configuration
5. Add proper error logging
6. Consider adding request rate limiting

## Next Steps

Potential enhancements:
- Save/load custom journal lists
- Export results to BibTeX
- Bookmark/favorite papers
- Email digest functionality
- Visualization of citation networks
- Advanced filtering options
