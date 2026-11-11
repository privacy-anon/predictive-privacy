# Analysis

This directory contains all scripts used for **statistical analysis and experimental evaluation** of survey responses. These scripts operate on cleaned survey data (e.g., from Prolific) and produce the aggregated statistics and figures that appear in the `results/` directory.

---

## Directory Structure

```text
analysis/
├── prolific_script.py
├── statanalysis_100certain.py
├── statanalysis_50_75certain.py
└── README.md
```

---

## Script Overview

### `prolific_script.py`
**Purpose**
- Preprocess and clean raw survey data exported from **Prolific**
- Standardize formats for downstream statistical analysis

**Script workflow**
- Load raw Prolific CSV exports
- Filter invalid or incomplete responses
- Handle attention checks and exclusion criteria
- Normalize demographic and response fields
- Export cleaned datasets for analysis scripts

**Output**
- Cleaned CSV or DataFrame-ready datasets
- Consistent schema across survey versions

---

### `statanalysis_100certain.py`
**Purpose**
- Perform statistical analysis for surveys conducted under **100% certainty** conditions

**Script workflow**
- Aggregate survey responses by demographic variables
- Compute summary statistics (means, distributions, correlations)
- Run statistical comparisons and tests
- Generate analysis-ready outputs used for plotting

---

### `statanalysis_50_75certain.py`
**Purpose**
- Perform comparative statistical analysis across **50% vs. 75% certainty** conditions

**Script workflow**
- Parallel analysis of two certainty levels
- Side-by-side aggregation and comparison
- Prepare data structures for paired visualizations
- Support within-row subplot comparisons in results figures

---

## Statistical Integrity

- All analyses are scripted and reproducible
- No manual post-hoc data manipulation
- Analyses are run consistently across survey versions and conditions
- Scripts are designed to be rerunnable with new data drops

---

## Notes on Interpretation

- The `100certain` analysis establishes baseline effects
- The `50_75certain` analysis evaluates robustness and uncertainty sensitivity
- Distributional analyses complement mean-based comparisons

Together, these scripts support both **exploratory** and **confirmatory** analysis.

---

## Extending the Analysis

You may extend this directory by:
- Adding additional certainty levels (if relevant to your survey designs)
- Introducing new demographic stratifications
- Incorporating regression or mixed-effects models
- Exporting statistical tables for papers or appendices
