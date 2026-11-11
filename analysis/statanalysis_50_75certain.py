# Survey 2 (50% vs 75% certainty) analysis.
# Note: this is the approach with GCP / Google Colab.

import itertools

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
import statsmodels.formula.api as smf
from IPython.display import display
from patsy import dmatrix
from scipy.stats import norm
from statsmodels.stats.multitest import multipletests
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import make_scorer, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

# =========================
# Shared config
# =========================
QUESTIONS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
CERTAINTY_LEVELS = [50, 75]

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

FEATURE_LIST = [
    "GENDER", "RACETHN", "EDUCCAT5", "DIVISION", "MARITAL_ACS",
    "CHILDRENCAT", "CITIZEN_REC", "BORN_ACS", "AGE_INT",
    "HIV_STAT", "PREG_STAT", "NumChronicIllness",
    "FAMINC5", "CC_NUM", "FDSTMP_CPS",
    "SEXUALITY", "OWNGUN_GSS", "RELIGCAT", "Certainty",
]


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


def welch_50_vs_75(d, questions=QUESTIONS):
    """Print Welch t-test of 50% vs 75% certainty for each question."""
    for score in questions:
        data_50 = d.loc[d["Certainty"] == 50, score].dropna()
        data_75 = d.loc[d["Certainty"] == 75, score].dropna()
        if len(data_50) >= 2 and len(data_75) >= 2:
            t_stat, p_val = stats.ttest_ind(data_50, data_75, equal_var=False)
            print(f"{score} | t = {t_stat:.3f}, p = {p_val:.3e}")
        else:
            print(f"{score} | Not enough data for t-test.")


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

df = load_likert("data/survey2_results.csv")
# df columns: ProlificID, SyntheticPersonID, AttnCheck, Q1..Q8, Condition, Certainty
display(df.head())

# One row per SyntheticPersonID (mean over repeated ratings; Certainty is constant per profile)
df_avg = df.groupby("SyntheticPersonID")[QUESTIONS + ["Certainty"]].mean().reset_index()
print(df_avg.head())

# One row per (SyntheticPersonID, Condition)
grouped_df = (
    df.groupby(["SyntheticPersonID", "Condition"])[QUESTIONS + ["Certainty"]]
      .mean()
      .reset_index()
)
conditions = grouped_df["Condition"].unique()
certainties = sorted(grouped_df["Certainty"].unique())

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

# =========================
# Mean (95% CI) plots
# =========================
plt.rcParams.update(plt.rcParamsDefault)
question_labels = [CUSTOM_LABELS[q] for q in QUESTIONS]
x_q = np.arange(len(QUESTIONS))

# One plot per condition: x = question
for cond in conditions:
    cond_data = grouped_df[grouped_df["Condition"] == cond]
    stats_per_q = [ci95(cond_data[q]) for q in QUESTIONS]

    plt.figure(figsize=(10, 6))
    plt.errorbar(x_q, [m for m, _ in stats_per_q], yerr=[c for _, c in stats_per_q],
                 fmt="o", capsize=5, color="blue", ecolor="black")
    plt.xticks(x_q, question_labels, rotation=45, ha="right")
    plt.xlabel("Question")
    plt.ylabel("Mean Response")
    plt.title(f"Mean Response (95% CI) for Condition: {cond}")
    plt.tight_layout()
    plt.show()

# One plot per condition, 50% vs 75% side by side (saved as PDF)
# Force Type 1 outline fonts in PDF output
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"]

for cond in conditions:
    plt.figure(figsize=(8, 6))
    for i, cert in enumerate(certainties):
        subset = grouped_df[(grouped_df["Condition"] == cond) & (grouped_df["Certainty"] == cert)]
        stats_per_q = [ci95(subset[q]) for q in QUESTIONS]
        plt.errorbar(x_q + i * 0.1, [m for m, _ in stats_per_q], yerr=[c for _, c in stats_per_q],
                     fmt="o", capsize=5, label=f"Certainty = {cert}%")

    plt.xticks(x_q, question_labels, rotation=45, ha="right", fontsize=15)
    plt.yticks(fontsize=15)
    plt.xlabel("Scenario", fontsize=15)
    plt.ylabel("Mean Response", fontsize=15)
    plt.title(f"Mean Response (95% CI) by Certainty for Condition: {cond}", fontsize=15)
    plt.legend(fontsize=15)
    plt.tight_layout()
    plt.savefig(f"mean_response_{cond}.pdf", bbox_inches="tight")
    plt.show()

# One plot per question: x = (condition, certainty)
for question in QUESTIONS:
    means, ci_vals, x_labels = [], [], []
    for cond in conditions:
        for cert in certainties:
            subset = grouped_df.loc[
                (grouped_df["Condition"] == cond) & (grouped_df["Certainty"] == cert), question
            ]
            m, c = ci95(subset)
            means.append(m)
            ci_vals.append(c)
            x_labels.append(f"{cond}-{int(cert)}%")   # e.g. "Health-50%"

    x_positions = np.arange(len(means))
    plt.figure(figsize=(10, 6))
    plt.errorbar(x_positions, means, yerr=ci_vals, fmt="o", capsize=5, color="blue", ecolor="black")
    plt.xticks(x_positions, x_labels, rotation=45, ha="right")
    plt.xlabel("Condition - Certainty")
    plt.ylabel("Mean Response")
    plt.title(f"Mean {question} by Condition and Certainty (95% CI)")
    plt.tight_layout()
    plt.show()

# 50% vs 75% within each condition (observed participant data)
for cond in ["Health", "Control"]:
    print(f"\n=== Condition: {cond} ===")
    welch_50_vs_75(grouped_df[grouped_df["Condition"] == cond])

# =========================
# Participant demographics (Prolific export)
# =========================
df_responses = load_likert("data/survey2_results.csv")
df_prolific = pd.read_csv("data/prolific_export_survey2.csv")  # Note: this data has to come from your own surveys

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
demo_ttests.to_csv("t-tests_survey2.csv", index=False)

# =========================
# Mixed-effects model: Condition × Certainty × Recipient
# =========================
grouped_cert = (
    df.groupby(["SyntheticPersonID", "Condition", "Certainty"])[QUESTIONS]
      .mean()
      .reset_index()
)
long_df = grouped_cert.melt(
    id_vars=["SyntheticPersonID", "Condition", "Certainty"], value_vars=QUESTIONS,
    var_name="Question", value_name="Response",
).dropna(subset=["Response"])

# Categorical baselines: Control, 50%, Q1
long_df["Question"] = pd.Categorical(long_df["Question"], categories=QUESTIONS)
long_df["Certainty_cat"] = pd.Categorical(long_df["Certainty"], categories=CERTAINTY_LEVELS, ordered=True)
if "Control" in long_df["Condition"].unique():
    long_df["Condition"] = pd.Categorical(long_df["Condition"], categories=["Control", "Health"])
display(long_df.head())

mres = smf.mixedlm(
    "Response ~ Condition * Certainty_cat * Question",
    data=long_df, groups=long_df["SyntheticPersonID"],
).fit(reml=True, method="lbfgs")
print(mres.summary())

# Use ONLY the fixed-effect covariance (cov_params also includes the random-effect variance)
fe_names = list(mres.fe_params.index)
V_fe = mres.cov_params().loc[fe_names, fe_names].to_numpy()
z = norm.ppf(0.975)

conds = (list(long_df["Condition"].cat.categories)
         if isinstance(long_df["Condition"].dtype, pd.CategoricalDtype)
         else sorted(long_df["Condition"].unique()))

# Newer statsmodels versions don't keep `design_info` on model.data,
# so design rows are rebuilt from the fitted formula's right-hand side.
FIXED_RHS = mres.model.formula.split("~", 1)[1].strip()


def make_grid(rows):
    g = pd.DataFrame(rows)
    g["Condition"] = pd.Categorical(g["Condition"], categories=conds)
    g["Certainty_cat"] = pd.Categorical(g["Certainty_cat"], categories=CERTAINTY_LEVELS, ordered=True)
    g["Question"] = pd.Categorical(g["Question"], categories=QUESTIONS)
    return g


def fe_design(frame):
    """Fixed-effects design matrix for `frame`, columns aligned to mres.fe_params."""
    X = dmatrix(FIXED_RHS, frame, return_type="dataframe")
    missing = set(fe_names) - set(X.columns)
    if missing:
        raise ValueError(f"Design columns don't match model coefficients: {sorted(missing)}")
    return X[fe_names].to_numpy()


# Predicted means + 95% CI (delta method, fixed effects only)
predicted_means = make_grid([
    {"Condition": c, "Certainty_cat": cert, "Question": q}
    for c in conds for cert in CERTAINTY_LEVELS for q in QUESTIONS
])
X = fe_design(predicted_means)
predicted_means["pred_mean"] = X @ mres.fe_params.to_numpy()
se = np.sqrt(np.einsum("ij,jk,ik->i", X, V_fe, X))
predicted_means["ci_low"] = predicted_means["pred_mean"] - z * se
predicted_means["ci_high"] = predicted_means["pred_mean"] + z * se
display(predicted_means)

# Recipient-specific marginal effect of certainty (75 − 50) within each condition & question
beta = mres.fe_params.to_numpy()
rows = []
for c in conds:
    for q in QUESTIONS:
        X50 = fe_design(make_grid([{"Condition": c, "Certainty_cat": 50, "Question": q}]))[0]
        X75 = fe_design(make_grid([{"Condition": c, "Certainty_cat": 75, "Question": q}]))[0]
        mu50, mu75 = float(X50 @ beta), float(X75 @ beta)
        dX = X75 - X50
        se_diff = float(np.sqrt(dX @ V_fe @ dX))
        ame = mu75 - mu50
        rows.append({
            "Condition": c, "Question": q, "Mean_50": mu50, "Mean_75": mu75,
            "AME_75_minus_50": ame, "CI_low": ame - z * se_diff, "CI_high": ame + z * se_diff,
        })

recipient_ame = pd.DataFrame(rows)
recipient_ame["Recipient"] = recipient_ame["Question"].map(CUSTOM_LABELS)
print("\nRecipient-specific marginal effects (75% − 50%):")
display(recipient_ame)

# Overall average marginal effect of certainty: predict every observation at 50 and at 75
df_50 = long_df.copy()
df_75 = long_df.copy()
df_50["Certainty_cat"] = pd.Categorical([50] * len(df_50), categories=CERTAINTY_LEVELS, ordered=True)
df_75["Certainty_cat"] = pd.Categorical([75] * len(df_75), categories=CERTAINTY_LEVELS, ordered=True)
pred_50 = np.asarray(mres.predict(df_50))
pred_75 = np.asarray(mres.predict(df_75))
ame_certainty = np.mean(pred_75 - pred_50)

# Bootstrap CI
rng = np.random.default_rng(0)
boot = []
for _ in range(1000):
    idx = rng.choice(len(pred_50), len(pred_50), replace=True)
    boot.append(np.mean(pred_75[idx] - pred_50[idx]))
ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])
print(f"AME of certainty (75 − 50): {ame_certainty:.3f}  95% CI [{ci_lo:.3f}, {ci_hi:.3f}]")

"""## Supervised ML"""

# Join synthetic profiles with observed ratings; unrated profiles get 0 (imputed below)
df_merged = pd.merge(df_synthetic, df_avg, how="left",
                     left_on="id", right_on="SyntheticPersonID", suffixes=("", "_drop"))
df_final = df_merged.drop(columns=[c for c in df_merged.columns if c.endswith("_drop")])
df_final = df_final.fillna(0)
print(df_final.head())

# Unrated profiles have no certainty: randomly assign 50 or 75
no_cert = df_final["Certainty"] == 0
df_final.loc[no_cert, "Certainty"] = np.random.choice(CERTAINTY_LEVELS, size=no_cert.sum())


def make_encoder():
    return OneHotEncoder(sparse_output=False, handle_unknown="ignore", drop="first")


def evaluate_model(model_name, model, X_train, y_train):
    model.fit(X_train, y_train)
    y_train_pred = model.predict(X_train)
    print(f"Model: {model_name}")
    print(f"MSE on training data: {mean_squared_error(y_train, y_train_pred)}")
    print(f"R^2 on training data: {r2_score(y_train, y_train_pred)}\n")


# Model comparison on Q1
train_data = df_final[df_final["Q1"] > 0]
X_train_encoded = make_encoder().fit_transform(train_data[FEATURE_LIST].astype(str))
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

    best_model = DecisionTreeRegressor(max_depth=30, max_features=None, min_samples_leaf=4,
                                       min_samples_split=5, random_state=42)
    best_model.fit(X_train_encoded, y_train_scaled)

    X_predict_encoded = onehot_encoder.transform(predict_data[FEATURE_LIST].astype(str))
    predicted_scores = scaler.inverse_transform(
        best_model.predict(X_predict_encoded).reshape(-1, 1)
    ).flatten()
    df_final.loc[df_final[q] == 0, q] = predicted_scores
    print(df_final.head())

df_final = df_final.drop(columns=["SyntheticPersonID"])
display(df_final.head())

# 10-fold CV MAE of the imputation model, on observed (non-imputed) values only
mae_scorer = make_scorer(mean_absolute_error, greater_is_better=False)
results = []
for q in QUESTIONS:
    data = df_final[df_final[q] > 0].copy()
    X = data[FEATURE_LIST]
    y = data[q]

    pipeline = Pipeline([
        ("prep", ColumnTransformer(
            transformers=[("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), X.columns)]
        )),
        ("model", DecisionTreeRegressor(max_depth=30, min_samples_leaf=4,
                                        min_samples_split=5, random_state=42)),
    ])
    cv_mae = cross_val_score(pipeline, X, y, cv=KFold(n_splits=10, shuffle=True, random_state=42),
                             scoring=mae_scorer)
    results.append({"Question": q, "MAE_mean": -cv_mae.mean(), "MAE_sd": cv_mae.std()})

cv_mae_df = pd.DataFrame(results)
display(cv_mae_df)

"""## Graphs"""

palette = sns.color_palette("Set2")
df_by_cert = {cert: df_final[df_final["Certainty"] == cert] for cert in CERTAINTY_LEVELS}

for score_type in QUESTIONS:
    # Side-by-side subplots: Certainty = 50 | Certainty = 75
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    for ax, cert in zip(axes, CERTAINTY_LEVELS):
        medians = df_by_cert[cert].groupby(["RACETHN", "SEXUALITY"])[score_type].median().reset_index()
        sns.barplot(x="RACETHN", y=score_type, hue="SEXUALITY", data=medians, palette=palette, ax=ax)
        ax.set_title(f"{score_type} (Certainty = {cert}%)")
        ax.set_xlabel("Race/Ethnicity")
        ax.set_ylabel("Median Score")
        ax.tick_params(axis="x", rotation=45)
        ax.legend(title="Sexuality")

    plt.suptitle(f"Comparison of Certainty Levels for {score_type}", fontsize=14)
    plt.tight_layout()
    plt.show()

"""Does certainty of 50 vs 75 produce significantly diff harm scores? In almost all cases, it does."""

welch_50_vs_75(df_final)
