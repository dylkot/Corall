# Journal Filtering Guide

## Overview

Corall now supports filtering recommendations by specific journals. This helps you focus on papers from journals most relevant to your research.

## Your Custom Journal List

Your personalized journal list is in `my_journals.txt`. This includes:

- **Core journals you specified**: bioRxiv, Nature, Science, Cell
- **Arthritis & Rheumatology journals**: Multiple variants to catch different naming conventions
- **Top journals from your library**: Based on what you already cite (Nature family, Cell family, etc.)
- **Immunology journals**: Immunity, Journal of Immunology, Frontiers in Immunology, etc.
- **Clinical journals**: NEJM, JAMA, The Lancet, Blood
- **Genomics/Computational**: Genome Biology, Nucleic Acids Research, Bioinformatics

## Usage

### Use Your Custom Journal List (Recommended)

```bash
python recommend.py recommend --journal-file my_journals.txt
```

This searches only the 40 journals in your custom list.

### Use Default Top 50 Biology/Medicine Journals

```bash
python recommend.py recommend
```

Uses the built-in curated list of 49 top-tier journals (enabled by default).

### Disable Journal Filtering

```bash
python recommend.py recommend --no-filter-journals
```

Searches all journals in OpenAlex (slower, less focused).

### Use Custom Journals via Command Line

```bash
python recommend.py recommend --custom-journals "Nature,Science,Cell,Blood"
```

Specify journals directly without a file.

## Editing Your Journal List

Edit `my_journals.txt` to customize:

1. Open the file in any text editor
2. Add/remove journal names (one per line)
3. Lines starting with `#` are comments
4. Empty lines are ignored

Example:
```
# My favorite journals
Nature
Science
Cell

# Specialty journals
Arthritis & Rheumatology
Nature Immunology
```

## Performance Benefits

Journal filtering provides:

- **Faster searches**: Fewer candidate papers to process
- **Higher quality**: Only papers from journals you trust
- **Better relevance**: Aligned with your research field

## Test Results

Your custom journal list successfully:
- ✅ Loaded 40 journals from file
- ✅ Resolved 37 journal IDs in OpenAlex (3 couldn't be matched due to naming variations)
- ✅ Found 200 candidate papers from your specified journals
- ✅ Generated relevant recommendations

## Troubleshooting

**Journal not found**: Some journal abbreviations may not match OpenAlex exactly. Try:
- Full journal name: "Arthritis & Rheumatology" instead of "Arthritis Rheum."
- Check OpenAlex for the exact name at https://openalex.org

**Too few results**:
- Increase search period: `--days 30` or `--days 60`
- Add more journals to your list
- Use `--no-filter-journals` temporarily

## Combined with Other Filters

You can combine journal filtering with other options:

```bash
# Search last 14 days in your journals, get top 20
python recommend.py recommend --journal-file my_journals.txt --days 14 --top 20

# With detailed explanations
python recommend.py recommend --journal-file my_journals.txt --explain

# Export to JSON
python recommend.py recommend --journal-file my_journals.txt --export results.json
```
