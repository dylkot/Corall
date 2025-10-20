# Testing Directory

This directory contains tools for exploring and analyzing how the Corall recommendation engine works.

## Contents

### Notebooks

- **`exploration_notebook.ipynb`** - Interactive exploration of the recommendation engine
  - Load papers from Zotero
  - Compute similarity matrices
  - Build citation networks
  - Analyze recommendation scores
  - Visualize results

### Data Directory

- **`Test_Data/`** - Generated data files (excluded from git)
  - All analysis outputs are saved here
  - Not tracked in version control to save space
  - Created automatically when running the notebook

## Setup

### 1. Install Jupyter

If you don't have Jupyter installed:

```bash
pip install jupyter notebook
```

Or if using conda:

```bash
conda install jupyter notebook
```

### 2. Install Additional Dependencies

The notebook uses some visualization libraries:

```bash
pip install matplotlib seaborn pandas
```

Or add to your main requirements.txt:
```
matplotlib>=3.5.0
seaborn>=0.12.0
pandas>=1.5.0
```

### 3. Configure Zotero

Make sure your `.env` file is configured with Zotero credentials:

```env
ZOTERO_API_KEY=your_api_key
ZOTERO_USER_ID=your_user_id
ZOTERO_LIBRARY_TYPE=user
```

## Usage

### Start Jupyter Notebook

From the Corall root directory:

```bash
jupyter notebook Testing/exploration_notebook.ipynb
```

Or from the Testing directory:

```bash
cd Testing
jupyter notebook exploration_notebook.ipynb
```

### Run the Analysis

The notebook is organized in sections:

1. **Setup** - Import libraries and initialize
2. **Load Papers** - Fetch your Zotero library
3. **Similarity Matrix** - Compute pairwise similarities
4. **Citation Network** - Build network from OpenAlex
5. **Test Recommendations** - Score candidate papers
6. **Analyze Results** - Find patterns and insights
7. **Summary Report** - Complete analysis summary

Run cells sequentially (Shift+Enter) or use "Run All" from the Cell menu.

## Generated Files

When you run the notebook, it creates these files in `Test_Data/`:

| File | Description | Size |
|------|-------------|------|
| `library_papers.pkl` | Your Zotero papers | ~1-5 MB |
| `similarity_matrix.npy` | NxN similarity matrix | ~1-10 MB |
| `similarity_matrix_heatmap.png` | Heatmap visualization | ~1 MB |
| `similarity_distribution.png` | Score distribution plot | ~200 KB |
| `citation_network.pkl` | Citation network data | ~100 KB-1 MB |
| `citation_stats.json` | Network statistics | ~1 KB |
| `test_recommendations.pkl` | Scored candidates | ~1-5 MB |
| `score_distributions.png` | Score visualizations | ~500 KB |
| `analysis_summary.json` | Summary statistics | ~1 KB |

**Total estimated size:** 5-25 MB (depends on library size)

## What You'll Learn

### Similarity Analysis

- How papers in your library relate to each other
- Distribution of similarity scores
- Clusters of related papers
- Embedding quality assessment

### Citation Network

- Size of your citation network
- Coverage of OpenAlex mapping
- Network expansion factor
- Papers with high connectivity

### Recommendation Scores

- Distribution of combined, citation, and similarity scores
- Correlation between citation and content similarity
- Which library papers are most frequently matched
- Score thresholds for filtering

## Tips

### Performance

- **First run:** Takes 10-30 minutes depending on library size
- **Similarity matrix:** O(N²) computation, slow for large libraries (>500 papers)
- **Citation network:** Limited by OpenAlex API rate limits
- **Tip:** Use a smaller test collection first

### Memory

- Large libraries (>1000 papers) may require significant RAM
- Similarity matrix for 1000 papers ≈ 8 MB (numpy array)
- Consider using a subset for initial testing

### Customization

You can modify the notebook to:
- Use specific Zotero collections
- Adjust number of test candidates
- Change scoring weights
- Add custom visualizations
- Export results in different formats

## Troubleshooting

### "Module not found" errors

Make sure you're running from the Testing directory or the parent directory is in your Python path.

### OpenAlex rate limit errors

- Add `OPENALEX_EMAIL` to your `.env` file for higher limits
- Add delays between requests if needed
- Reduce the number of papers being processed

### Out of memory errors

- Reduce library size using Zotero collections
- Limit the number of test candidates
- Process in batches

### Jupyter not starting

```bash
# Try this if jupyter notebook doesn't work
python -m jupyter notebook Testing/exploration_notebook.ipynb
```

## Example Workflow

```bash
# 1. Navigate to Corall directory
cd /path/to/Corall

# 2. Activate your environment (if using venv)
source venv/bin/activate  # or: conda activate corall

# 3. Start Jupyter
jupyter notebook Testing/exploration_notebook.ipynb

# 4. Run all cells in the notebook

# 5. Check Test_Data/ for generated files
ls -lh Testing/Test_Data/

# 6. View visualizations
open Testing/Test_Data/similarity_matrix_heatmap.png
open Testing/Test_Data/score_distributions.png
```

## Future Enhancements

Potential additions to this testing framework:

- Network visualization (graph of citation relationships)
- Dimensionality reduction (t-SNE, UMAP) of embeddings
- Topic modeling on library papers
- A/B testing different recommendation parameters
- Temporal analysis of recommendation quality
- Comparative analysis across collections

## Notes

- **Test_Data/** is excluded from git (see `.gitignore`)
- Delete `Test_Data/` contents to start fresh
- Notebook creates all required directories automatically
- Safe to re-run multiple times (overwrites previous results)

---

Happy exploring! 🔬
