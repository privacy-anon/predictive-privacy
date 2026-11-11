# Preprocessing Pipeline

This directory contains preprocessing utilities for generating synthetic data, clustering population profiles, and producing survey-ready instruments. Together, these scripts support an end-to-end pipeline for simulating populations, grouping individuals into meaningful clusters, and translating those clusters into structured survey scenarios.

## Directory Structure

```text
preprocessing/
├── clustering.py
├── syntheticdata.py
└── survey_generation.py
```

## Overview of Components

### `syntheticdata.py`
Generates synthetic individual-level data from configurable distributions and constraints.

**Purpose**
- Create realistic, privacy-preserving synthetic populations
- Support controlled experimentation without using real participant data
- Enable downstream clustering and survey construction

**Key Functionality**
- Synthetic profile generation using parameterized feature distributions
- Support for demographic, behavioral, and contextual attributes
- Reproducible generation via random seeds
- Output formats compatible with clustering and survey pipelines
---

### `clustering.py`
Groups synthetic individuals into clusters representing distinct population segments.

**Purpose**
- Identify latent groupings in synthetic populations
- Reduce high-dimensional profiles into interpretable segments
- Support cluster-based survey design and analysis

**Key Functionality**
- Feature normalization and preprocessing
- Clustering algorithms (e.g., k-means or similar)
- Cluster evaluation and labeling
- Export of cluster assignments and centroids

---

### `survey_generation.py`
Transforms clustered synthetic profiles into survey-ready questions and scenarios.

**Purpose**
- Automatically generate survey instruments from population clusters
- Ensure consistency across survey conditions
- Enable large-scale, systematic survey deployment

**Key Functionality**
- Scenario and vignette construction from cluster attributes
- Question templating and randomization
- Support for multiple experimental conditions
- Export to survey platforms (e.g., CSVs suitable for Qualtrics)

---

## End-to-End Workflow

The preprocessing workflow looks like:

1. **Generate synthetic data**
   ```bash
   python syntheticdata.py
   ```

2. **Cluster synthetic profiles**
   ```bash
   python clustering.py
   ```

3. **Generate surveys from clusters**
   ```bash
   python survey_generation.py
   ```

Each stage consumes outputs from the previous step.

alized where possible
- Synthetic data does **not** correspond to real individuals

---

## Extending the Pipeline

You can extend this preprocessing pipeline by:
- Adding new synthetic attributes or distributions
- Swapping in alternative clustering algorithms
- Customizing survey templates or experimental conditions
- Integrating downstream modeling or statistical analysis
