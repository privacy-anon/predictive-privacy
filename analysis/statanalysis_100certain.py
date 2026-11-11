# Survey 1 (100% certainty) analysis.
# Note: this is the approach with GCP / Google Colab.

import glob
import itertools
import subprocess

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from IPython.display import display
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages
from patsy import dmatrix
from scipy.stats import chi2, norm
from statsmodels.formula.api import ols
from statsmodels.stats.multitest import multipletests
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

# =========================
# Shared config
# =========================
QUESTIONS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]

LIKERT_MAPPING = {
    "Not at all harmful": 1,
    "Slightly harmful": 2,
    "Moderately harmful": 3,
    "Very harmful": 4,
    "Extremely harmful": 5,
}

# Question code -> recipient label
CUSTOM_LABELS = {
    "Q1": "Hackers/Cybercriminals",
    "Q2": "Government",
    "Q3": "Corporations",
    "Q4": "Employer/Colleagues",
    "Q5": "Family",
    "Q6": "Close Friends",
    "Q7": "Acquaintances",
    "Q8": "Publicly Available",
}

INCOME_LEVELS = [
    "Less than $20K",
    "$20K to less than $40K",
    "$40K to less than $75K",
    "$75K to less than $150K",
    "$150K or more",
]
INCOME_SHORT_LABELS = ["<$20K", "$20–40K", "$40–75K", "$75–150K", "$150K+"]

FEATURE_LIST = [
    "GENDER", "RACETHN", "EDUCCAT5", "DIVISION", "MARITAL_ACS",
    "CHILDRENCAT", "CITIZEN_REC", "BORN_ACS", "AGE_INT",
    "HIV_STAT", "PREG_STAT", "NumChronicIllness",
    "FAMINC5", "CC_NUM", "FDSTMP_CPS",
    "SEXUALITY", "OWNGUN_GSS", "RELIGCAT",
]

# Journal (OUP) figure style. sns.set_theme() resets rcParams, so font
# settings must be passed through rc= rather than set beforehand.
JOC_RC = {
    "pdf.fonttype": 42, "ps.fonttype": 42,     # TrueType, not Type 3
    "font.family": "Arial",
    "font.size": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.6, "lines.linewidth": 1.0,
}


def load_likert(path):
    """Read a survey CSV and map Likert text in Q1..Q8 to 1..5."""
    d = pd.read_csv(path)
    for col in QUESTIONS:
        if col in d.columns:
            # to_numeric: newer pandas keeps object dtype after replace()
            d[col] = pd.to_numeric(d[col].replace(LIKERT_MAPPING), errors="coerce")
    return d


def ci95(values):
    """Mean and 95% t-based CI half-width for a 1-D array/Series."""
    values = pd.Series(values).dropna()
    n = len(values)
    if n <= 1:
        return values.mean(), 0.0
    se = values.std() / np.sqrt(n)
    return values.mean(), stats.t.ppf(1 - 0.025, df=n - 1) * se


def sig_stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"


def pairwise_ttests_by(df, group_col, questions=QUESTIONS):
    """Print Welch t-tests between every pair of levels of `group_col`, per question."""
    for score in questions:
        print(f"\n=== T-test Results for {score} ===")
        print(f"Comparisons by {group_col}:")
        groups = df[group_col].dropna().unique()
        for g1, g2 in itertools.combinations(groups, 2):
            data1 = df.loc[df[group_col] == g1, score].dropna()
            data2 = df.loc[df[group_col] == g2, score].dropna()
            if len(data1) >= 2 and len(data2) >= 2:
                t_stat, p_val = stats.ttest_ind(data1, data2, equal_var=False)
                print(f"  {g1} vs {g2}: t = {t_stat:.3f}, p = {p_val:.3e}")
            else:
                print(f"  {g1} vs {g2}: Not enough data.")


# =========================
# Load data
# =========================
from google.colab import auth, drive
import gspread
from oauth2client.service_account import ServiceAccountCredentials

auth.authenticate_user()

scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

spreadsheet_url = ""  # insert sheet URL
sheet = client.open_by_url(spreadsheet_url)
df_synthetic = pd.DataFrame(sheet.get_worksheet(0).get_all_records())
display(df_synthetic.head())

drive.mount("/content/drive")

df = load_likert("data/survey1_results.csv")
# df columns: ProlificID, SyntheticPersonID, AttnCheck, Q1..Q8, Condition

# One row per SyntheticPersonID (mean over repeated ratings)
df_avg = df.groupby("SyntheticPersonID")[QUESTIONS].mean().reset_index()
df_avg["avg_harm"] = df_avg[QUESTIONS].mean(axis=1)
print(df_avg.head())

# One row per (SyntheticPersonID, Condition)
grouped_df = (
    df.groupby(["SyntheticPersonID", "Condition"])[QUESTIONS]
      .mean()
      .reset_index()
)
conditions = grouped_df["Condition"].unique()

# =========================
# Pairwise Welch t-tests across conditions (Bonferroni)
# =========================
results = []
for question in QUESTIONS:
    for cond1, cond2 in itertools.combinations(conditions, 2):
        group1 = grouped_df.loc[grouped_df["Condition"] == cond1, question].dropna()
        group2 = grouped_df.loc[grouped_df["Condition"] == cond2, question].dropna()
        t_stat, p_val = stats.ttest_ind(group1, group2, equal_var=False)
        results.append((question, cond1, cond2, t_stat, p_val))

condition_ttests = pd.DataFrame(
    results, columns=["Question", "Condition1", "Condition2", "t_stat", "p_value"]
)
condition_ttests["p_adjusted"] = multipletests(condition_ttests["p_value"], method="bonferroni")[1]
print("Separate t-test results for each question (with Bonferroni correction):")
print(condition_ttests)

"""In summary, based on your adjusted p‑values, significant differences exist between:

*   Financial vs. Health
*   Financial vs. Sensitive
*   Health vs. Sensitive
*   Control vs. Sensitive.


Financial vs. Control and Health vs. Control do not show significant differences after adjustment.
"""

# =========================
# Mean (95% CI) plots
# =========================
question_labels = [CUSTOM_LABELS[q] for q in QUESTIONS]

# One plot per condition: x = question
for cond in conditions:
    cond_data = grouped_df[grouped_df["Condition"] == cond]
    stats_per_q = [ci95(cond_data[q]) for q in QUESTIONS]
    x_positions = np.arange(len(QUESTIONS))

    plt.figure(figsize=(10, 6))
    plt.errorbar(x_positions, [m for m, _ in stats_per_q], yerr=[c for _, c in stats_per_q],
                 fmt="o", capsize=5, color="blue", ecolor="black")
    plt.xticks(x_positions, question_labels, rotation=45, ha="right")
    plt.xlabel("Question")
    plt.ylabel("Mean Response")
    plt.title(f"Mean Response (95% CI) for Condition: {cond}")
    plt.tight_layout()
    plt.show()

# One plot per question: x = condition
for question in QUESTIONS:
    stats_per_c = [
        ci95(grouped_df.loc[grouped_df["Condition"] == cond, question]) for cond in conditions
    ]
    x_positions = np.arange(len(conditions))

    plt.figure(figsize=(8, 6))
    plt.errorbar(x_positions, [m for m, _ in stats_per_c], yerr=[c for _, c in stats_per_c],
                 fmt="o", capsize=5, color="blue", ecolor="black")
    plt.xticks(x_positions, conditions, rotation=45, ha="right")
    plt.xlabel("Condition")
    plt.ylabel("Mean Response")
    plt.title(f"Mean {question} by Condition (95% CI)")
    plt.tight_layout()
    plt.show()

# =========================
# Harm summary by condition × question
# =========================
harm_summary = (
    grouped_df.groupby("Condition")[QUESTIONS]
    .mean()
    .T
    .sort_values(by="Health", ascending=False)
)
print(harm_summary)

harm_summary.plot(kind="bar", figsize=(10, 6))
plt.ylabel("Mean harm rating (1–5)")
plt.title("Mean Harm Ratings by Condition and Question")
plt.legend(title="Condition")
plt.tight_layout()
plt.show()

plt.figure(figsize=(8, 6))
sns.heatmap(harm_summary, annot=True, cmap="Blues", fmt=".2f")
plt.title("Mean Harm Ratings (1–5)")
plt.ylabel("Question")
plt.xlabel("Condition")
plt.tight_layout()
plt.show()

# =========================
# Sensitive vs Health: Welch t, Cohen's d, Holm
# =========================
results = []
for q in QUESTIONS:
    scores_s = grouped_df.loc[grouped_df["Condition"] == "Sensitive", q].dropna()
    scores_h = grouped_df.loc[grouped_df["Condition"] == "Health", q].dropna()

    mean_s, sd_s = scores_s.mean(), scores_s.std()
    mean_h, sd_h = scores_h.mean(), scores_h.std()
    t, p = stats.ttest_ind(scores_s, scores_h, equal_var=False)

    mean_diff = mean_s - mean_h                       # Sensitive - Health
    pooled_sd = np.sqrt((sd_s**2 + sd_h**2) / 2)
    cohens_d = mean_diff / pooled_sd if pooled_sd > 0 else np.nan

    results.append([q, f"{mean_s:.2f} ({sd_s:.2f})", f"{mean_h:.2f} ({sd_h:.2f})",
                    mean_diff, t, p, cohens_d])

sensitive_vs_health = pd.DataFrame(
    results,
    columns=["Question", "Sensitive Mean (SD)", "Health Mean (SD)", "MeanDiff", "t", "p", "Cohen's d"],
)
sensitive_vs_health["p_adjusted"] = multipletests(sensitive_vs_health["p"], method="holm")[1]
sensitive_vs_health["p_adjusted_fmt"] = sensitive_vs_health["p_adjusted"].apply(lambda x: f"{x:.3g}")
sensitive_vs_health["significant"] = sensitive_vs_health["p_adjusted"] < 0.05
sensitive_vs_health = sensitive_vs_health.round(
    {"MeanDiff": 2, "t": 2, "p": 3, "p_adjusted": 3, "Cohen's d": 2}
)
print(sensitive_vs_health)

# =========================
# Participant demographics (Prolific export)
# =========================
df_responses = load_likert("data/survey1_results.csv")
df_prolific = pd.read_csv("data/prolific_export.csv")  # Note: this has to come from your own surveys
display(df_prolific.head())

merged_df = pd.merge(df_responses, df_prolific,
                     left_on="ProlificID", right_on="Participant id", how="inner")
print("Merged DataFrame:")
print(merged_df.head())

demographics = [
    "Age", "Sex", "Ethnicity simplified", "Country of residence",
    "Nationality", "Language", "Student status", "Employment status",
]


def demographic_table(d, column):
    counts = d[column].value_counts(dropna=False)
    percents = d[column].value_counts(normalize=True, dropna=False) * 100
    return pd.DataFrame({"Count": counts, "Percent (%)": percents.round(2)})


df_prolific = df_prolific.replace("CONSENT_REVOKED", pd.NA)
for col in demographics:
    print(f"\n===== {col} =====")
    print(demographic_table(df_prolific, col))

# Pairwise t-tests per question by participant demographic (Bonferroni)
demographic_vars = ["Sex", "Ethnicity simplified", "Country of residence", "Language", "Employment status"]

results = []
for demo in demographic_vars:
    groups = merged_df[demo].dropna().unique()
    if len(groups) < 2:
        continue
    for question in QUESTIONS:
        for group1, group2 in itertools.combinations(groups, 2):
            data1 = merged_df.loc[merged_df[demo] == group1, question].dropna()
            data2 = merged_df.loc[merged_df[demo] == group2, question].dropna()
            if len(data1) >= 2 and len(data2) >= 2:
                t_stat, p_val = stats.ttest_ind(data1, data2, equal_var=False)
            else:
                t_stat, p_val = np.nan, np.nan
            results.append((demo, question, group1, group2, t_stat, p_val))

demo_ttests = pd.DataFrame(
    results, columns=["Demographic", "Question", "Group1", "Group2", "t_stat", "p_value"]
)
valid = demo_ttests["p_value"].notna()
demo_ttests.loc[valid, "p_adjusted"] = multipletests(demo_ttests.loc[valid, "p_value"], method="bonferroni")[1]
print("Pairwise t-test results for each question by demographic variable:")
print(demo_ttests)
demo_ttests.to_csv("t-tests.csv", index=False)

"""## Supervised ML"""

# Join synthetic profiles with observed ratings; unrated profiles get 0 (imputed below)
df_merged = pd.merge(df_synthetic, df_avg, how="left",
                     left_on="id", right_on="SyntheticPersonID", suffixes=("", "_drop"))
df_final = df_merged.drop(columns=[c for c in df_merged.columns if c.endswith("_drop")])
df_final[QUESTIONS] = df_final[QUESTIONS].fillna(0)
print(df_final.head())

# Add Condition back into df_final (majority vote if a profile was shown in several)
cond_map = grouped_df[["SyntheticPersonID", "Condition"]].dropna().drop_duplicates()
dupes = cond_map["SyntheticPersonID"][cond_map["SyntheticPersonID"].duplicated()].unique()
if len(dupes) > 0:
    print(f"WARNING: {len(dupes)} SyntheticPersonIDs appear in multiple conditions. Using majority vote.")
    cond_map = (
        grouped_df[["SyntheticPersonID", "Condition"]]
        .dropna()
        .groupby("SyntheticPersonID")["Condition"]
        .agg(lambda s: s.value_counts().idxmax())
        .reset_index()
    )

df_final = df_final.drop(columns=["SyntheticPersonID"]).merge(
    cond_map, left_on="id", right_on="SyntheticPersonID", how="left"
)
print(df_final["Condition"].value_counts(dropna=False))

# =========================
# Survey 1 — PRE analysis (observed participant data only)
# =========================
recipient_labels = {
    "Q1": "Hackers / Cybercriminals",
    "Q2": "Government",
    "Q3": "Corporations",
    "Q4": "Employer / Colleagues",
    "Q5": "Family",
    "Q6": "Close Friends",
    "Q7": "Acquaintances",
    "Q8": "Publicly Available",
}

missing = [c for c in ["SyntheticPersonID", "Condition"] + QUESTIONS if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns in df: {missing}")

# Rows with no condition cannot be used in condition analysis
df_pre = df.dropna(subset=["Condition"]).copy()
print("Condition counts (PRE):")
print(df_pre["Condition"].value_counts())

# Long form, averaged per SyntheticPersonID × Condition
grouped = df_pre.groupby(["SyntheticPersonID", "Condition"], as_index=False)[QUESTIONS].mean()
long_pre = grouped.melt(
    id_vars=["SyntheticPersonID", "Condition"], value_vars=QUESTIONS,
    var_name="Question", value_name="Response",
).dropna(subset=["Response"])
long_pre["Condition"] = long_pre["Condition"].astype("category")
long_pre["Question"] = pd.Categorical(long_pre["Question"], categories=QUESTIONS, ordered=True)

# Mixed-effects model: random intercept per SyntheticPersonID, Condition × Recipient fixed effects
mres_pre = smf.mixedlm(
    "Response ~ C(Condition) * C(Question)", data=long_pre, groups=long_pre["SyntheticPersonID"]
).fit(reml=True, method="lbfgs")
print("converged:", getattr(mres_pre, "converged", None))
print("any NaN fe_params:", mres_pre.fe_params.isna().any())
print("any NaN cov_params:", np.isnan(mres_pre.cov_params().values).any())
print("min/max fe_params:", np.nanmin(mres_pre.fe_params.values), np.nanmax(mres_pre.fe_params.values))
print("first 10 fe_params:\n", mres_pre.fe_params.head(10))
print("random effect var:\n", mres_pre.cov_re)
print(mres_pre.summary())

# Newer statsmodels versions don't keep `design_info` on model.data,
# so design rows are rebuilt from the fitted formula's right-hand side.
FALLBACK_RHS = "C(Condition) * C(Question)"


def _fixed_effects_rhs(mres, fallback=FALLBACK_RHS):
    formula = getattr(mres.model, "formula", None)
    if isinstance(formula, str) and "~" in formula:
        return formula.split("~", 1)[1].strip()
    return fallback


def _fe_design(mres, frame):
    """Fixed-effects design matrix for `frame`, columns aligned to mres.fe_params."""
    X = dmatrix(_fixed_effects_rhs(mres), frame, return_type="dataframe")
    fe_names = mres.fe_params.index
    missing = set(fe_names) - set(X.columns)
    if missing:
        raise ValueError(f"Design columns don't match model coefficients: {sorted(missing)}")
    return X[fe_names]


# Predicted means + 95% CI (fixed effects only)
conditions_order = list(long_pre["Condition"].cat.categories)
if "Control" not in conditions_order:
    raise ValueError(f"'Control' not found in Condition categories: {conditions_order}")

grid = pd.DataFrame([(c, q) for c in conditions_order for q in QUESTIONS],
                    columns=["Condition", "Question"])
# Keep ALL levels in fitting order so patsy produces identical dummy columns
grid["Condition"] = pd.Categorical(grid["Condition"], categories=conditions_order)
grid["Question"] = pd.Categorical(grid["Question"], categories=QUESTIONS, ordered=True)

fe_names = mres_pre.fe_params.index
X = _fe_design(mres_pre, grid).values
V = mres_pre.cov_params().loc[fe_names, fe_names].values
pred = X @ mres_pre.fe_params.values
se = np.sqrt(np.einsum("ij,jk,ik->i", X, V, X))
z = norm.ppf(0.975)

pre_means = grid.copy()
pre_means["PredMean"] = pred
pre_means["CI_Low"] = pred - z * se
pre_means["CI_High"] = pred + z * se
pre_means["Recipient"] = pre_means["Question"].astype(str).map(recipient_labels)
pre_means = pre_means.sort_values(["Condition", "Question"]).reset_index(drop=True)
display(pre_means)

# -------------------------
# Omnibus Wald tests on MixedLM fixed effects:
#   Condition main effect, Question main effect, Condition × Question interaction
# -------------------------


def _wald_test_terms_mixedlm(mres, term_prefixes, term_name):
    """
    Wald chi-square test for a set of fixed-effect coefficients in a fitted MixedLM result.
    Main effects: coefficient names starting with any prefix and containing no ':'.
    Interaction:  names of the form C(Condition)[T.X]:C(Question)[T.Qy].
    """
    fe = mres.fe_params
    names = fe.index.tolist()

    if term_name == "Condition × Question":
        sel = [n for n in names if n.startswith("C(Condition)[T.") and ":C(Question)[T." in n]
    else:
        sel = [n for n in names if any(n.startswith(p) for p in term_prefixes) and ":" not in n]

    if len(sel) == 0:
        raise ValueError(f"No coefficients found for term '{term_name}'. Check coding / names.")

    beta = fe.loc[sel].values
    Vsel = mres.cov_params().loc[sel, sel].values
    stat = float(beta @ np.linalg.solve(Vsel, beta))   # beta' V^{-1} beta
    df_ = len(sel)
    return {"Term": term_name, "Chi2": stat, "df": df_, "p_value": float(chi2.sf(stat, df_)), "n_coefs": df_}


omnibus_table = pd.DataFrame([
    _wald_test_terms_mixedlm(mres_pre, ["C(Condition)[T."], "Condition"),
    _wald_test_terms_mixedlm(mres_pre, ["C(Question)[T."], "Recipient (Question)"),
    _wald_test_terms_mixedlm(mres_pre, [], "Condition × Question"),
])
omnibus_table["p_value_fmt"] = omnibus_table["p_value"].map(lambda x: f"{x:.3g}")
display(omnibus_table[["Term", "Chi2", "df", "p_value_fmt", "n_coefs"]])

# -------------------------
# Effect sizes vs Control (3 conditions × 8 questions = 24 rows):
#   Δ mean (model-based), 95% CI, Cohen's d (pooled SD of person-level means)
# -------------------------


def contrast_vs_control_table(mres, grouped_profile_df, conditions_order, questions,
                              recipient_labels, control_label="Control", alpha=0.05):
    fe_names = mres.fe_params.index
    V = mres.cov_params().loc[fe_names, fe_names].values
    beta = mres.fe_params.loc[fe_names].values
    z = norm.ppf(1 - alpha / 2)

    def design_row(cond, q):
        row = pd.DataFrame({
            "Condition": pd.Categorical([cond], categories=conditions_order),
            "Question": pd.Categorical([q], categories=questions, ordered=True),
        })
        return _fe_design(mres, row).values.reshape(-1)

    out_rows = []
    for q in questions:
        ctrl_vals = grouped_profile_df.loc[grouped_profile_df["Condition"] == control_label, q].dropna().values
        n0 = len(ctrl_vals)
        s0 = np.std(ctrl_vals, ddof=1) if n0 > 1 else np.nan
        X_ctl = design_row(control_label, q)

        for c in [c for c in conditions_order if c != control_label]:
            cond_vals = grouped_profile_df.loc[grouped_profile_df["Condition"] == c, q].dropna().values
            n1 = len(cond_vals)
            s1 = np.std(cond_vals, ddof=1) if n1 > 1 else np.nan

            L = design_row(c, q) - X_ctl          # (c, q) − (Control, q)
            diff = float(L @ beta)
            se = float(np.sqrt(L @ V @ L))

            if n0 > 1 and n1 > 1 and np.isfinite(s0) and np.isfinite(s1):
                sp = np.sqrt(((n0 - 1) * s0**2 + (n1 - 1) * s1**2) / (n0 + n1 - 2))
                d = diff / sp if sp > 0 else np.nan
            else:
                d = np.nan

            out_rows.append({
                "Condition": c, "Question": q, "Recipient": recipient_labels.get(q, q),
                "Delta_vs_Control": diff, "CI_Low": diff - z * se, "CI_High": diff + z * se,
                "SE": se, "Cohens_d": d, "n_cond": n1, "n_control": n0,
            })

    return pd.DataFrame(out_rows).sort_values(["Condition", "Question"]).reset_index(drop=True)


effect_table = contrast_vs_control_table(
    mres=mres_pre, grouped_profile_df=grouped, conditions_order=conditions_order,
    questions=QUESTIONS, recipient_labels=recipient_labels, control_label="Control",
)

# Wald z p-values (from unrounded Δ/SE) + Holm across the 24 contrasts
effect_table["z"] = effect_table["Delta_vs_Control"] / effect_table["SE"]
effect_table["p_value"] = 2 * norm.sf(np.abs(effect_table["z"].values))
effect_table["p_holm"] = multipletests(effect_table["p_value"], method="holm")[1]
effect_table["p_holm_fmt"] = effect_table["p_holm"].map(lambda x: f"{x:.3g}")

# Round for display only (after all calculations)
for col in ["Delta_vs_Control", "CI_Low", "CI_High", "SE", "Cohens_d", "z"]:
    effect_table[col] = effect_table[col].round(3)

display(effect_table[["Condition", "Question", "Recipient", "Delta_vs_Control",
                      "CI_Low", "CI_High", "Cohens_d", "p_holm_fmt", "n_cond", "n_control"]])

# Top-k largest absolute deltas (for main text)
topk = (
    effect_table.assign(abs_delta=lambda d: d["Delta_vs_Control"].abs())
    .sort_values("abs_delta", ascending=False)
    .head(8)
    .drop(columns="abs_delta")
)
print("Top deltas vs Control (by |Δ|):")
display(topk[["Condition", "Question", "Recipient", "Delta_vs_Control",
              "CI_Low", "CI_High", "Cohens_d", "p_holm_fmt"]])

# =========================
# Imputation of unrated profiles (decision tree)
# =========================


def make_encoder():
    return OneHotEncoder(sparse_output=False, handle_unknown="ignore", drop="first")


def make_best_tree(random_state=42):
    return DecisionTreeRegressor(max_depth=30, max_features=None, min_samples_leaf=4,
                                 min_samples_split=5, random_state=random_state)


def evaluate_model(model_name, model, X_train, y_train):
    model.fit(X_train, y_train)
    y_train_pred = model.predict(X_train)
    print(f"Model: {model_name}")
    print(f"MSE on training data: {mean_squared_error(y_train, y_train_pred)}")
    print(f"R^2 on training data: {r2_score(y_train, y_train_pred)}\n")


# Model comparison on Q1
train_data = df_final[df_final["Q1"] > 0]
onehot_encoder = make_encoder()
X_train_encoded = onehot_encoder.fit_transform(train_data[FEATURE_LIST].astype(str))
y_train_scaled = StandardScaler().fit_transform(train_data[["Q1"]]).flatten()

models = [
    ("RandomForest", RandomForestRegressor(n_estimators=100)),
    ("GradientBoosting", GradientBoostingRegressor()),
    ("LinearRegression", LinearRegression()),
    ("Ridge", Ridge()),
    ("Lasso", Lasso()),
    ("DecisionTree", DecisionTreeRegressor()),
    ("SVR", SVR()),
]
for name, model in models:
    evaluate_model(name, model, X_train_encoded, y_train_scaled)

# Impute each question with the tuned decision tree
for q in QUESTIONS:
    train_data = df_final[df_final[q] > 0]
    predict_data = df_final[df_final[q] == 0]

    onehot_encoder = make_encoder()
    X_train_encoded = onehot_encoder.fit_transform(train_data[FEATURE_LIST].astype(str))
    scaler = StandardScaler()
    y_train_scaled = scaler.fit_transform(train_data[[q]]).flatten()

    evaluate_model("DecisionTree", DecisionTreeRegressor(), X_train_encoded, y_train_scaled)

    best_model = make_best_tree()
    best_model.fit(X_train_encoded, y_train_scaled)

    X_predict_encoded = onehot_encoder.transform(predict_data[FEATURE_LIST].astype(str))
    predicted_scores = scaler.inverse_transform(
        best_model.predict(X_predict_encoded).reshape(-1, 1)
    ).flatten()
    df_final.loc[df_final[q] == 0, q] = predicted_scores
    print(df_final.head())


def cv_mae_for_imputation(df, feature_list, questions, n_splits=10, random_state=42):
    """10-fold CV MAE of the imputation model, on observed values only."""
    results = []
    for q in questions:
        data = df[df[q] > 0].copy()
        X = data[feature_list].astype(str)
        y = data[q].values.reshape(-1, 1)

        fold_maes = []
        for train_idx, test_idx in KFold(n_splits=n_splits, shuffle=True, random_state=random_state).split(X):
            encoder = make_encoder()                    # fit on TRAIN only
            X_train_enc = encoder.fit_transform(X.iloc[train_idx])
            X_test_enc = encoder.transform(X.iloc[test_idx])

            scaler = StandardScaler()
            y_train_scaled = scaler.fit_transform(y[train_idx]).ravel()

            model = make_best_tree(random_state)
            model.fit(X_train_enc, y_train_scaled)
            y_pred = scaler.inverse_transform(model.predict(X_test_enc).reshape(-1, 1)).ravel()
            fold_maes.append(mean_absolute_error(y[test_idx].ravel(), y_pred))

        results.append({"Question": q, "MAE_Mean": np.mean(fold_maes),
                        "MAE_SD": np.std(fold_maes), "n_observed": len(data)})
    return pd.DataFrame(results)


mae_table = cv_mae_for_imputation(df_final, FEATURE_LIST, QUESTIONS, n_splits=10)
display(mae_table)

df_final = df_final.drop(columns=["SyntheticPersonID", "avg_harm"], errors="ignore")
display(df_final.head())

"""# Participant Graphs"""

sns.set_theme(style="whitegrid")


def plot_responses(df, question, demographic, kind="bar", show=True):
    """
    Visualize responses for one question by a demographic group.
    kind : {'bar', 'violin', 'box'}
    """
    plt.figure(figsize=(10, 5))
    if kind == "bar":
        sns.barplot(data=df, x=demographic, y=question, errorbar="sd", palette="muted")
    elif kind == "violin":
        sns.violinplot(data=df, x=demographic, y=question, inner="quartile", palette="Set3")
    elif kind == "box":
        sns.boxplot(data=df, x=demographic, y=question, palette="Set2")
    plt.title(f"{question} responses by {demographic}")
    plt.ylabel("Likert Score")
    plt.xlabel(demographic)
    plt.ylim(1, 5)  # 1–5 Likert scale
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    if show:
        plt.show()


plot_responses(merged_df, question="Q5", demographic="Ethnicity simplified", kind="violin")

# All questions × demographics as violins, into one PDF
output_path = "survey_plots.pdf"
with PdfPages(output_path) as pdf:
    for q in QUESTIONS:
        for demo in demographic_vars:
            plot_responses(merged_df, q, demo, kind="violin", show=False)
            pdf.savefig()
            plt.close()
print(f"PDF saved to {output_path}")

"""for JOC"""

# Install Microsoft core fonts (includes Arial) in Colab, accepting the licence non-interactively
subprocess.run(
    "echo 'ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true' "
    "| debconf-set-selections && apt-get -qq install -y ttf-mscorefonts-installer > /dev/null",
    shell=True, check=True,
)
# Register the new fonts with matplotlib without restarting the runtime
for f in glob.glob("/usr/share/fonts/truetype/msttcorefonts/*.ttf"):
    font_manager.fontManager.addfont(f)
print(font_manager.findfont("Arial", fallback_to_default=False))

# Fig 1: Q6 by ethnicity (mean ± 95% CI)
sns.set_theme(style="whitegrid", rc={
    **JOC_RC,
    "axes.edgecolor": "black",
    "grid.linewidth": 0.4, "grid.color": "0.85",  # >= 0.25 pt, light grey
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
})
font_manager.findfont("Arial", fallback_to_default=False)  # fail if Arial missing

question = "Q6"
plot_df = merged_df[merged_df["Ethnicity simplified"] != "DATA_EXPIRED"]

# Single-column print size (~3.4 in); check against \columnwidth
fig, ax = plt.subplots(figsize=(3.4, 2.6), constrained_layout=True)
sns.barplot(
    data=plot_df, x="Ethnicity simplified", y=question,
    estimator="mean", errorbar=("ci", 95),
    color="white", edgecolor="black", linewidth=0.6,
    err_kws={"linewidth": 0.8, "color": "black"}, capsize=0.15, ax=ax,
)
# No title: it goes in the LaTeX caption
ax.set_xlabel("Ethnicity")
ax.set_ylabel("Average harm rating")
ax.set_ylim(1, 5)
plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
ax.grid(axis="x", visible=False)           # horizontal gridlines only

# No bbox_inches='tight', so the PDF stays exactly 3.4 x 2.6 in
fig.savefig("fig1.pdf")
fig.savefig("fig1.eps", format="eps")
plt.show()

"""## Graphs"""

sns.set_theme(style="whitegrid")
palette = sns.color_palette("Set2")

for i, score_type in enumerate(QUESTIONS, start=1):
    medians = df_final.groupby(["RACETHN", "SEXUALITY"])[score_type].median().reset_index()
    plt.figure(figsize=(12, 8))
    sns.barplot(x="RACETHN", y=score_type, hue="SEXUALITY", data=medians, palette=palette)
    plt.title(f"Average Scores by Race/Ethnicity and Sexuality for Question {i}")
    plt.xlabel("Race/Ethnicity")
    plt.ylabel("Average Score")
    plt.xticks(rotation=45)
    plt.legend(title="Sexuality")
    plt.tight_layout()
    plt.show()

"""Does sexuality / HIV status / income impact harm?"""

pairwise_ttests_by(df_final, "SEXUALITY")
pairwise_ttests_by(df_final, "HIV_STAT")
pairwise_ttests_by(df_final, "FAMINC5")

# =========================
# Income × Division
# =========================


def income_means(df, score, mask_zeros=True):
    """Mean of `score` by DIVISION × FAMINC5, columns in income order."""
    d = df.copy()
    if mask_zeros:
        d.loc[d[score] == 0, score] = np.nan   # 0 was a placeholder for missing

    # Stop if any income value doesn't match a canonical level; otherwise
    # pd.Categorical turns it into NaN and that column silently goes blank
    unknown = set(d["FAMINC5"].dropna().unique()) - set(INCOME_LEVELS)
    if unknown:
        raise ValueError(f"Unrecognised FAMINC5 values: {unknown}")

    d["FAMINC5"] = pd.Categorical(d["FAMINC5"], categories=INCOME_LEVELS, ordered=True)
    return (d.groupby(["DIVISION", "FAMINC5"], observed=False)[score]
              .mean()
              .unstack()
              .reindex(columns=INCOME_LEVELS))


def plot_heatmap_per_question(
    df, questions, mask_zeros=True, save=False, outdir=".",
    title_fontsize=12, label_fontsize=11, tick_fontsize=10.5,
    figsize=(8, 6), dpi=100, save_dpi=300,
):
    """Heatmap of mean value by Division × Family Income, one per question."""
    sns.set_theme(style="white")
    for score in questions:
        means = income_means(df, score, mask_zeros=mask_zeros)

        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        sns.heatmap(means, annot=True, fmt=".2f", cmap="Greys", cbar=False, ax=ax,
                    annot_kws={"size": tick_fontsize}, linewidths=0.5, linecolor="lightgray")
        ax.set_title(f"{score}: Mean by Division × Family Income", fontsize=title_fontsize, pad=10)
        ax.set_xlabel("Family Income", fontsize=label_fontsize)
        ax.set_ylabel("Division", fontsize=label_fontsize)
        ax.set_xticklabels(INCOME_SHORT_LABELS, rotation=30, ha="right", fontsize=tick_fontsize)
        ax.tick_params(axis="y", labelsize=tick_fontsize)
        plt.tight_layout()

        if save:
            base = f"{outdir}/Heatmap_{score}"
            plt.savefig(f"{base}.pdf", bbox_inches="tight", dpi=save_dpi)
            plt.savefig(f"{base}.png", bbox_inches="tight", dpi=save_dpi)
            print(f"Saved {base}.pdf / .png")
        plt.show()


plot_heatmap_per_question(df_final, QUESTIONS, save=True)

# Income vs harm: means, Spearman trend, pairwise t-tests
df_copy = df_final.copy()
for q in QUESTIONS:
    df_copy.loc[df_copy[q] == 0, q] = np.nan
df_copy["FAMINC5"] = pd.Categorical(df_copy["FAMINC5"], categories=INCOME_LEVELS, ordered=True)
df_copy["income_rank"] = df_copy["FAMINC5"].cat.codes

print("Mean harm score by income bracket")
print("=" * 75)
print(df_copy.groupby("FAMINC5", observed=False)[QUESTIONS].mean().round(3).to_string())

print("\n\nSpearman correlation: income rank vs harm score")
print("=" * 75)
for q in QUESTIONS:
    sub = df_copy.loc[df_copy["income_rank"] >= 0, ["income_rank", q]].dropna()
    r, p = stats.spearmanr(sub["income_rank"], sub[q])
    print(f"  {q}: r = {r:+.3f}, p = {p:.3e}  {sig_stars(p)}")

print("\n\nPairwise t-tests by income group")
print("=" * 75)
for q in QUESTIONS:
    print(f"\n{q}")
    groups = {lvl: df_copy.loc[df_copy["FAMINC5"] == lvl, q].dropna().values for lvl in INCOME_LEVELS}
    for g1, g2 in itertools.combinations(INCOME_LEVELS, 2):
        t, p = stats.ttest_ind(groups[g1], groups[g2], equal_var=False)
        m1, m2 = np.nanmean(groups[g1]), np.nanmean(groups[g2])
        print(f"  {g1} vs {g2}: t={t:+.3f}, p={p:.3e}  {sig_stars(p)}  (means: {m1:.3f} vs {m2:.3f})")

"""for JOC"""

# Fig 3: Q5 and Q8 by Division × Family Income, shared colour scale
sns.set_theme(style="white", rc=JOC_RC)
font_manager.findfont("Arial", fallback_to_default=False)  # fail if Arial missing

fig3_questions = ["Q5", "Q8"]
tables = [income_means(df_final, q) for q in fig3_questions]

# One colour scale for both panels so shading is comparable
vmin = min(np.nanmin(t.to_numpy()) for t in tables)
vmax = max(np.nanmax(t.to_numpy()) for t in tables)

# Double-column print size (~6.9 in); check against \textwidth
fig, axes = plt.subplots(1, 3, figsize=(6.9, 3.4), constrained_layout=True,
                         gridspec_kw={"width_ratios": [1, 1, 0.05]})

for i, (ax, table, tag) in enumerate(zip(axes[:2], tables, ["(a)", "(b)"])):
    sns.heatmap(
        table, annot=True, fmt=".2f",
        annot_kws={"fontsize": 7},       # value labels: meaning not colour-only
        cmap="cividis",                  # colour-blind safe, no pale yellow end
        vmin=vmin, vmax=vmax, linewidths=0.5, linecolor="white",
        cbar=(i == 1), cbar_ax=axes[2] if i == 1 else None,
        cbar_kws={"label": "Mean harm rating"}, ax=ax,
    )
    ax.set_xticklabels(INCOME_SHORT_LABELS)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
    ax.set_xlabel("Family income")
    ax.text(0.0, 1.02, tag, transform=ax.transAxes, fontweight="bold", ha="left", va="bottom")

# Division names only on the left panel
axes[0].set_ylabel("Division")
plt.setp(axes[0].get_yticklabels(), rotation=0)
axes[1].set_ylabel("")
axes[1].set_yticklabels([])
axes[1].tick_params(axis="y", length=0)

cbar = axes[1].collections[0].colorbar
cbar.ax.tick_params(labelsize=7, width=0.6)
cbar.outline.set_linewidth(0.6)

# No bbox_inches='tight', so the PDF stays exactly 6.9 x 3.4 in
fig.savefig("fig3.pdf")
fig.savefig("fig3.eps", format="eps")
plt.show()

sns.set_theme(style="whitegrid")
for score_type in QUESTIONS:
    plt.figure(figsize=(12, 6))
    sns.boxplot(x="DIVISION", y=score_type, hue="FAMINC5", data=df_final)
    plt.title(f"Distribution of {score_type} by Division and Family Income")
    plt.xlabel("Division")
    plt.ylabel(score_type)
    plt.legend(title="Family Income")
    plt.xticks(rotation=45)
    plt.show()

"""Does race impact harm?"""

races = df_final["RACETHN"].dropna().unique()
results = []
for score_type in QUESTIONS:
    for race1, race2 in itertools.combinations(races, 2):
        group1 = df_final.loc[df_final["RACETHN"] == race1, score_type].dropna()
        group2 = df_final.loc[df_final["RACETHN"] == race2, score_type].dropna()

        t, p = stats.ttest_ind(group1, group2)
        mean1, mean2 = group1.mean(), group2.mean()
        d = (mean2 - mean1) / pd.concat([group1, group2]).std()

        results.append({
            "Question": score_type, "Group 1": race1, "Group 2": race2,
            "Mean (Group 1)": round(mean1, 3), "Mean (Group 2)": round(mean2, 3),
            "Mean Diff": round(mean2 - mean1, 3), "t": round(t, 3), "p_raw": p,
            "Cohen's d": round(d, 3),
        })
race_ttests = pd.DataFrame(results)

# Holm-Bonferroni correction per question
corrected = []
for q in QUESTIONS:
    subset = race_ttests[race_ttests["Question"] == q].copy()
    reject, p_adj, _, _ = multipletests(subset["p_raw"], method="holm")
    subset["p_adjusted"] = p_adj.round(6)
    subset["significant"] = reject
    corrected.append(subset)
race_ttests_corrected = pd.concat(corrected).drop(columns="p_raw")

# Show only significant results
print(race_ttests_corrected[race_ttests_corrected["significant"]].to_string())

# =========================
# Two-way ANOVAs
# =========================
for q in QUESTIONS:
    formula = f"{q} ~ C(HIV_STAT)*C(GENDER) + C(HIV_STAT)*C(RACETHN) + C(HIV_STAT)*C(SEXUALITY)"
    print(f"ANOVA for {q} (HIV status interactions):")
    print(sm.stats.anova_lm(ols(formula, data=df_final).fit(), typ=2))
    print("\n")

for q in QUESTIONS:
    formula = f"{q} ~ C(PREG_STAT)*C(OWNGUN_GSS) + C(PREG_STAT)*C(EDUCCAT5) + C(PREG_STAT)*C(AGE_INT)"
    print(f"ANOVA for {q} (Pregnancy):")
    print(sm.stats.anova_lm(ols(formula, data=df_final).fit(), typ=2))
    print("\n")

# =========================
# Pregnancy status
# =========================
for score_type in QUESTIONS:
    medians = df_final.groupby(["AGE", "PREG_STAT"])[score_type].median().reset_index()
    sns.lmplot(x="AGE", y=score_type, data=medians, hue="PREG_STAT",
               height=6, aspect=1.5, legend_out=True)
    plt.title(f"Mean Question {score_type[1:]} vs. Age colored by Pregnancy Status")
    plt.xlabel("Age")
    plt.ylabel(score_type)
    plt.xlim(16, 40)
    plt.subplots_adjust(top=0.9)
    plt.show()

pairwise_ttests_by(df_final, "PREG_STAT")

preg_means = df_final.groupby("PREG_STAT")[QUESTIONS].mean()

# Raw means
sns.set_theme(style="white")
plt.figure(figsize=(10, 3))
sns.heatmap(preg_means, annot=True, fmt=".2f", cmap="YlOrRd", linewidths=0.5,
            cbar_kws={"label": "Mean Harm Rating"}, vmin=1, vmax=5)
plt.title("Mean Perceived Harm by Pregnancy Status and Scenario")
plt.xlabel("Scenario")
plt.ylabel("Pregnancy Status")
plt.tight_layout()
plt.savefig("pregnancy_heatmap.pdf", bbox_inches="tight")
plt.show()

"""for JOC"""

# Fig 2: deviation from each scenario's mean, by pregnancy status
sns.set_theme(style="white", rc=JOC_RC)   # "white": no gridlines over the heatmap
font_manager.findfont("Arial", fallback_to_default=False)  # fail if Arial missing

preg_deviation = (preg_means
                  .subtract(preg_means.mean(axis=0), axis=1)
                  .rename(columns=CUSTOM_LABELS))

# Symmetric colour limits that cover all the data (a fixed ±0.2
# would clip any larger deviation without warning)
lim = max(np.ceil(np.abs(preg_deviation.to_numpy()).max() * 20) / 20, 0.2)

# Colour-blind-safe blue-orange diverging map, centred on 0
cmap = sns.diverging_palette(250, 30, s=80, l=55, as_cmap=True)

# Double-column print size (~6.9 in); check against \textwidth
fig, ax = plt.subplots(figsize=(6.9, 2.4), constrained_layout=True)
sns.heatmap(
    preg_deviation, annot=True, fmt=".2f",
    annot_kws={"fontsize": 7},           # value labels: meaning not colour-only
    cmap=cmap, center=0, vmin=-lim, vmax=lim,
    linewidths=0.5, linecolor="white",
    cbar_kws={"label": "Deviation from scenario mean"}, ax=ax,
)
# No title: it goes in the LaTeX caption
ax.set_xlabel("Scenario")
ax.set_ylabel("Pregnancy status")
plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
plt.setp(ax.get_yticklabels(), rotation=0)

cbar = ax.collections[0].colorbar
cbar.ax.tick_params(labelsize=7, width=0.6)
cbar.outline.set_linewidth(0.6)

# No bbox_inches='tight', so the PDF stays exactly 6.9 x 2.4 in
fig.savefig("fig2.pdf")
fig.savefig("fig2.eps", format="eps")
plt.show()
