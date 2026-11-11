## Results
The 2 directories include result graphs of corresponding survey. Graphs corresponding to Survey 2 include 2 sub-graphs on each row, showcasing difference between 50 and 75 certainty levels.

# Results

This directory contains all finalized visual outputs generated from the survey analyses. The results are organized by survey version and visualization type, with each PDF aggregating multiple related plots for ease of inspection and comparison.

The figures in this directory are intended for **analysis, interpretation, and reporting** (e.g., papers, appendices, or presentations), rather than further preprocessing.

---

## Directory Structure

```text
results/
├── survey1/
│   ├── Barplots_survey1.pdf
│   ├── Boxplots_survey1.pdf
│   ├── Heatmap_survey1.pdf
│   ├── LinearPlots_survey1.pdf
│   └── README.md
├── survey2/
│   ├── Barplots_survey2.pdf
│   ├── Boxplots_survey2.pdf
│   ├── Heatmap_survey2.pdf
│   └── LinearPlots_survey1.pdf
└── README.md
```

Each `surveyX/` folder corresponds to a distinct survey instrument or experimental condition.

---

## General Notes

- Each **PDF file** contains plots for **8 individual surveys/questions**, grouped by visualization type.
- For **Survey 2**, figures include **two subplots per row**, enabling direct comparison between **50% and 75% certainty levels**.
- All plots reflect **post-cleaning, post-aggregation** data used in the final analysis.
- These are samples of different attributes/features compared against one another. The entire workflow must be run/configured for other graphs.

---

## Visualization Types

### 1. Bar Plots (`Barplots_*.pdf`)
**Purpose**
- Compare **average scores** across demographic groups.

**Sample dimensions shown**
- Race / ethnicity  
- Sexuality  
---

### 2. Heatmaps (`Heatmap_*.pdf`)
**Purpose**
- Display **mean scores** across intersecting demographic or socioeconomic variables.

**Sample dimensions shown**
- Division
- Family income

Color intensity reflects relative magnitude, enabling rapid visual comparison across groups.

---

### 3. Boxplots (`Boxplots_*.pdf`)
**Purpose**
- Visualize **score distributions** rather than just averages.

**Sample dimensions shown**
- Division
- Family income

Boxplots highlight variance, skew, and outliers, complementing the mean-based views in bar plots and heatmaps.

---

### 4. Linear Plots (`LinearPlots_*.pdf`)
**Purpose**
- Illustrate relationships between **continuous variables**.

****Sample dimensions shown**
- Mean score trends and **age correlations**, stratified by pregnancy status.

These plots help identify monotonic trends and interaction effects that may not appear in aggregated views.

---

## Reproducibility & Integrity

- All figures are generated programmatically from the analysis pipeline
- No manual editing of plots has been performed
- Results reflect synthetic or anonymized data consistent with ethical research standards

---

## Usage

These PDFs can be:
- Embedded directly into papers or appendices
- Referenced during exploratory analysis
- Used to validate modeling and survey design choices

For details on how these figures were generated, see the analysis and preprocessing directories in the main repository.
