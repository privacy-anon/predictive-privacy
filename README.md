# Predictive Privacy

This repository contains code and data to implement the **Predictive Privacy** experiment: an end-to-end framework for quantifying informational privacy harm. The pipeline combines synthetic data generation, unsupervised clustering, human harm scoring via surveys, and supervised machine learning to predict perceived privacy harm under different disclosure scenarios.

> **Note**  
> These scripts were originally developed using **Google Colab and GCP**. Depending on your cloud provider and your organization’s RBAC / authorization policies, you may need to modify authentication, storage paths, or credential handling.

---

## Table of Contents

- [Background](#background)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Workflow](#workflow)
  - [1. Synthetic Data Generation](#1-synthetic-data-generation)
  - [2. Clustering](#2-clustering)
  - [3. Survey Generation & Scoring](#3-survey-generation--scoring)
  - [4. Statistical Analysis & Model Training](#4-statistical-analysis--model-training)
  - [5. Results](#5-results)
- [Data & Privacy](#data--privacy)
- [Notes & Caveats](#notes--caveats)
- [License](#license)

---

## Background

As data-driven systems increasingly collect, infer, and share personal information across corporations, data brokers, and governments, understanding **how much harm such disclosures cause** has become critical.

**Predictive Privacy** aims to operationalize informational privacy harm by:
1. Generating realistic, privacy-preserving synthetic individuals.
2. Clustering individuals to identify common archetypes.
3. Collecting human harm judgments for disclosure scenarios at varying inference accuracies.
4. Training supervised models to predict harm for unseen profiles.

The resulting framework is intended to support **empirical, policy-relevant assessments of privacy injury**, rather than speculative or purely doctrinal claims.

---

## Repository Structure

```text
├── analysis/                             # Statistical analysis & modeling
│   ├── statanalysis_100Certain.py        # Survey 1: 100% certainty
│   └── statanalysis_50_75Certain.py      # Survey 2: 50% vs 75% certainty
│
├── data/                                 # Aggregated survey outputs (no demographics)
│   ├── survey1_results.csv
│   └── survey2_results.csv
│
├── preprocessing/                        # Data preparation & survey setup
│   ├── syntheticdata.py                  # Synthetic profile generation
│   ├── clustering.py                     # Clustering of synthetic profiles
│   └── survey_generation.py              # Survey construction & export
│
├── results/                              # Example plots and figures
│   ├── survey1/
│   │   ├── barplots_survey1.pdf
│   │   ├── boxplots_survey1.pdf
│   │   ├── heatmap_survey1.pdf
│   │   └── linearplots_survey1.pdf
│   └── survey2/
│       ├── barplots_survey2.pdf
│       ├── boxplots_survey2.pdf
│       ├── heatmap_survey2.pdf
│       └── linearplots_survey2.pdf
│
└── README.md                             # Project overview
```

---

## Prerequisites

- Python 3.8+
- Jupyter Notebook, Google Colab, or a cloud-connected IDE
- Core Python libraries:
  - `pandas`, `numpy`, `scikit-learn`, `scipy`
  - `matplotlib`, `seaborn`
  - `requests`, `gspread` (for survey / Google Sheets integration)

---

## Workflow

### 1. Synthetic Data Generation

**Script:** `preprocessing/syntheticdata.py`

**Purpose**  
Generate a synthetic population with sensitive attributes using privacy-preserving techniques.

**Steps**

1. Email [info@pewresearch.org](mailto:info@pewresearch.org) for access to download the PEW Research synthetic US population dataset from here:  
   https://www.pewresearch.org/methods/2018/01/26/appendix-b-synthetic-population-dataset/
2. Run `syntheticdata.py` to add additional attributes and produce a synthetic population.

---

### 2. Clustering

**Script:** `preprocessing/clustering.py`

**Purpose**  
Identify clusters of similar individuals based on sensitive attribute profiles.

**Steps**
1. Load the synthetic dataset.
2. Perform preprocessing (encoding, scaling).
3. Run clustering (e.g., K-Means, hierarchical).
4. Export clustered profiles for survey sampling.

---

### 3. Survey Generation & Scoring

**Script:** `preprocessing/survey_generation.py`

**Purpose**  
Prepare survey instruments and collect human harm ratings.

**Steps**
1. Sample representative profiles from each cluster.
2. Generate survey prompts describing disclosure scenarios at:
   - 100% certainty
   - 75% certainty
   - 50% certainty
3. Export survey responses (aggregated outputs are stored in `data/`).

---

### 4. Statistical Analysis & Model Training

**Scripts:**  
- `analysis/statanalysis_100Certain.py`  
- `analysis/statanalysis_50_75Certain.py`

These scripts:
- Preprocess survey responses
- Run statistical comparisons across conditions and certainty levels
- Generate plots and summary statistics
- Optionally train supervised models to **impute missing harm scores** for synthetic profiles

---

### 5. Results

**Folder:** `results/`

Contains example plots generated by the analysis scripts. These files are **illustrative only**; outputs will differ if surveys are rerun or synthetic datasets are regenerated.

---

## Data & Privacy

This repository **does not include** Prolific demographic exports or merged datasets containing sensitive participant information.

Any public use of this code should exclude:
- Prolific demographic exports
- merged datasets with demographic attributes
- identifiers that could re-link participants

Only aggregate, non-identifying summaries should be shared.

---

## Notes & Caveats

- Supervised learning is used primarily as an **imputation mechanism**, not as a causal model.
- Current evaluation focuses on training-time metrics; users seeking generalization guarantees should add held-out test splits.
- For Survey 2, missing certainty values are currently assigned randomly (50 or 75) for modeling convenience; alternative treatments may be preferable.

---

## License

This project is licensed under the [MIT License](LICENSE).

**Repository / code owners:** Anonymous

