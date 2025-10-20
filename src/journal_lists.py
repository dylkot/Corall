"""
Curated lists of journals for filtering recommendations.
"""
import os
from typing import List

# Top 50 high-impact journals in Biology and Medicine
# Based on impact factor and field reputation
TOP_BIOLOGY_MEDICINE_JOURNALS = [
    # Top-tier multidisciplinary
    "Nature",
    "Science",
    "Cell",
    "The New England Journal of Medicine",
    "The Lancet",
    "JAMA",
    "Nature Medicine",
    "Nature Biotechnology",
    "Nature Genetics",
    "Nature Immunology",
    "Nature Cell Biology",
    "Nature Structural & Molecular Biology",
    "Nature Microbiology",
    "Nature Neuroscience",
    "Nature Methods",
    "Nature Reviews Immunology",
    "Nature Reviews Genetics",
    "Nature Reviews Molecular Cell Biology",
    "Nature Reviews Cancer",
    "Nature Reviews Drug Discovery",
    "Nature Communications",
    "Science Translational Medicine",
    "Science Immunology",
    "Science Advances",

    # Top-tier specialized journals
    "Cell Stem Cell",
    "Cell Metabolism",
    "Cancer Cell",
    "Immunity",
    "Molecular Cell",
    "Developmental Cell",
    "Cell Reports",
    "Cancer Discovery",
    "Blood",
    "Journal of Clinical Investigation",
    "Journal of Experimental Medicine",
    "PNAS",  # Proceedings of the National Academy of Sciences
    "eLife",
    "EMBO Journal",
    "Genome Research",
    "Genome Biology",
    "Nucleic Acids Research",
    "PLoS Biology",
    "Cell Systems",
    "Trends in Immunology",
    "Annual Review of Immunology",

    # High-impact clinical and translational
    "The Lancet Oncology",
    "JAMA Oncology",
    "Annals of Internal Medicine",
    "BMJ",  # British Medical Journal
]

# Extended list for broader coverage (100+ journals)
EXTENDED_BIOLOGY_MEDICINE_JOURNALS = TOP_BIOLOGY_MEDICINE_JOURNALS + [
    # Additional high-quality journals
    "Journal of Immunology",
    "Frontiers in Immunology",
    "Nature Reviews Microbiology",
    "Nature Protocols",
    "Cell Host & Microbe",
    "Trends in Cell Biology",
    "Trends in Genetics",
    "Molecular Systems Biology",
    "Nature Chemical Biology",
    "Science Signaling",
    "JCI Insight",
    "PLoS Genetics",
    "PLoS Pathogens",
    "mBio",
    "PLOS Medicine",
    "Clinical Cancer Research",
    "Journal of Clinical Oncology",
    "Leukemia",
    "Genes & Development",
    "Molecular and Cellular Biology",
    "Journal of Biological Chemistry",
    "Cell Death & Differentiation",
    "Autophagy",
    "Oncogene",
    "Nature Reviews Clinical Oncology",
    "Trends in Molecular Medicine",
    "Gastroenterology",
    "Hepatology",
    "Circulation",
    "Circulation Research",
    "Journal of the American College of Cardiology",
    "European Heart Journal",
    "Diabetes",
    "Diabetologia",
    "Kidney International",
    "Journal of Neuroscience",
    "Neuron",
    "Brain",
    "Acta Neuropathologica",
    "Arthritis & Rheumatology",
    "Annals of the Rheumatic Diseases",
    "Gut",
    "Journal of Allergy and Clinical Immunology",
    "American Journal of Respiratory and Critical Care Medicine",
    "Chest",
    "Journal of Infectious Diseases",
    "Clinical Infectious Diseases",
    "The Lancet Infectious Diseases",
    "Journal of Virology",
    "mSystems",
    "Microbiome",
    "Cell Chemical Biology",
]


def load_journals_from_file(file_path: str) -> List[str]:
    """
    Load journal names from a text file.

    Args:
        file_path: Path to file containing journal names (one per line)

    Returns:
        List of journal names

    Format:
        - One journal name per line
        - Lines starting with # are treated as comments
        - Empty lines are ignored
        - Leading/trailing whitespace is stripped
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Journal list file not found: {file_path}")

    journals = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Strip whitespace
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            journals.append(line)

    return journals
