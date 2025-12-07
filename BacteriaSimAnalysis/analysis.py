import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# === 1. Load the table CSV ===
# NetLogo BehaviorSpace table has 6 metadata lines before the header.
# Skip them so pandas reads the actual column headers correctly.
df = pd.read_csv(
    "BacteriaSim-BR2-table.csv",
    skiprows=6
)

# === 2. Inspect ===
print(df.head())
print(df.columns)

# === 3. Summary stats ===
metrics = df.describe()
print(metrics)

# === 4. Group by run number ===
# Aggregate available columns from the BehaviorSpace table
run_summary = df.groupby("[run number]").agg({
    "total-patients": ["mean", "max", "min"],
    "total-discharged": ["sum", "mean"],
    "total-recovered": ["sum", "mean"],
    "patient-deaths": ["sum", "mean"],
    "total-mutations": ["sum", "max"],
    "ifelse-value any? bacteria [count bacteria with [carbapenem-resistant?] / count bacteria] [0]": ["mean", "max"]
})
print(run_summary)

# === 8. Export summaries for easier reading ===
# Save grouped summary and a sample of the raw table to Excel and CSV early
try:
    with pd.ExcelWriter("analysis-summary.xlsx", engine="openpyxl") as writer:
        run_summary.to_excel(writer, sheet_name="Run Summary")
        df.head(200).to_excel(writer, sheet_name="Sample (first 200)", index=False)
    print("Wrote Excel file: analysis-summary.xlsx")
except Exception as e:
    print(f"Excel export failed ({e}). Writing CSVs instead.")
    run_summary.to_csv("run_summary.csv")
    df.head(200).to_csv("table_sample.csv", index=False)
    print("Wrote CSVs: run_summary.csv, table_sample.csv")

# === 5. Mean trajectories over time (across runs) ===
# For each '[step]', compute mean of selected outcome categories
time_cols = [
    "total-discharged",
    "total-recovered",
    "patient-deaths",
    "successful-antibiotics",
    "sum [antibiotic-failures] of patients",
    "total-mutations",
]
time_cols = [c for c in time_cols if c in df.columns]

if "[step]" in df.columns and len(time_cols) > 0:
    mean_over_time = df.groupby("[step]")[time_cols].mean().reset_index()
    # Save a CSV snapshot for review
    mean_over_time.to_csv("mean_over_time.csv", index=False)

    plt.figure(figsize=(16, 10))
    for col in time_cols:
        sns.lineplot(data=mean_over_time, x="[step]", y=col, label=col)
    plt.title("Mean outcomes over time across runs")
    plt.xlabel("step")
    plt.ylabel("mean value")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig("plot_mean_over_time.png", dpi=200)
    plt.close()

# === 6. Compare runs ===
# Removed per request: trajectories by '[step]' and '[run number]'

# === 7. Input→Outcome relationships ===
# Define inputs that can influence outcomes
inputs = [
    "antibiotic-administration-period",
    "antibiotic-application",  # boolean true/false
    "antibiotic-strength-level",
    "cleaning-effectiveness",
    "cleaning-frequency"
]

# Define outcomes/reporters to evaluate
outcomes = [
    "total-discharged",
    "total-recovered",
    "patient-deaths",
    "successful-antibiotics",
    "sum [antibiotic-failures] of patients",
    "total-mutations",
    "ifelse-value any? bacteria [count bacteria with [carbapenem-resistant?] / count bacteria] [0]",
    "ifelse-value any? patients with [infected?] [mean[days-infected] of patients with [infected?]] [0]"
]

# Keep only columns that exist
inputs = [c for c in inputs if c in df.columns]
outcomes = [c for c in outcomes if c in df.columns]

# Convert boolean-like column to numeric (true/false -> 1/0) if present
for col in inputs:
    if df[col].dtype == object:
        if set(df[col].dropna().unique()) <= {"true", "false"}:
            df[col] = df[col].map({"true": 1, "false": 0}).astype(float)

"""
Compute correlations only where there is variability; constant columns yield NaN.
Also handle boolean-like inputs mapped to 1/0.
"""
# Drop zero-variance inputs/outcomes to avoid blank (NaN) boxes
inputs_var = [c for c in inputs if pd.to_numeric(df[c], errors="coerce").std() > 0]
outcomes_var = [c for c in outcomes if pd.to_numeric(df[c], errors="coerce").std() > 0]

# Compute Pearson correlations between inputs and outcomes (matrix shape: inputs x outcomes)
corr_io = pd.DataFrame(index=inputs_var, columns=outcomes_var, dtype=float)
for i in inputs_var:
    for o in outcomes_var:
        corr_io.loc[i, o] = pd.to_numeric(df[i], errors="coerce").corr(
            pd.to_numeric(df[o], errors="coerce")
        )

print("\nInput→Outcome correlation (Pearson):")
print(corr_io)

# Export the input→outcome correlation table to Excel/CSV
try:
    with pd.ExcelWriter("analysis-summary.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        corr_io.to_excel(writer, sheet_name="Input→Outcome (corr)")
    print("Appended correlation sheet to Excel: analysis-summary.xlsx")
except Exception as e:
    print(f"Append to Excel failed ({e}). Writing CSV as fallback.")
    corr_io.to_csv("input_outcome_correlations.csv")
    print("Wrote CSV: input_outcome_correlations.csv")

# Optional visualization: heatmap for input→outcome correlations
plt.figure(figsize=(18, 12))
mask = corr_io.isna()
# Build annotation: show numeric values, 'N/A' where NaN
annot = corr_io.round(2).astype(str)
annot = annot.mask(mask, other="N/A")

"""Use full variable names on axes to avoid ambiguity."""
corr_plot = corr_io.copy()
annot.index = corr_plot.index
annot.columns = corr_plot.columns
mask.index = corr_plot.index
mask.columns = corr_plot.columns

ax = sns.heatmap(
    corr_plot.astype(float),
    annot=annot,
    fmt="",
    cmap="coolwarm",
    cbar_kws={"shrink":0.6},
    mask=mask
)
ax.set_title("Input→Outcome Correlations (Pearson)")
ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")
ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
plt.subplots_adjust(bottom=0.3, left=0.25)
plt.savefig("plot_input_outcome_correlations.png", dpi=250, bbox_inches="tight")
plt.close()

# === 9. Pivoted summaries by parameter levels ===
# Define outcome metrics to summarize
metrics_to_summarize = [
    "patient-deaths",
    "total-recovered",
    "total-discharged",
    "successful-antibiotics",
    "sum [antibiotic-failures] of patients",
    "total-mutations",
    "ifelse-value any? bacteria [count bacteria with [carbapenem-resistant?] / count bacteria] [0]",
    "ifelse-value any? patients with [infected?] [mean[days-infected] of patients with [infected?]] [0]"
]
metrics_to_summarize = [m for m in metrics_to_summarize if m in df.columns]

# 9a. Pivot: strength-level × cleaning-effectiveness
if {"antibiotic-strength-level", "cleaning-effectiveness"} <= set(df.columns):
    pivot_strength_cleaning = df.pivot_table(
        index="antibiotic-strength-level",
        columns="cleaning-effectiveness",
        values=metrics_to_summarize,
        aggfunc="mean"
    )
    try:
        with pd.ExcelWriter("analysis-summary.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            pivot_strength_cleaning.to_excel(writer, sheet_name="Strength x Cleaning")
    except Exception:
        pivot_strength_cleaning.to_csv("pivot_strength_cleaning.csv")

# 9b. Pivot: administration-period
if "antibiotic-administration-period" in df.columns:
    pivot_period = df.groupby("antibiotic-administration-period")[metrics_to_summarize].mean()
    try:
        with pd.ExcelWriter("analysis-summary.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            pivot_period.to_excel(writer, sheet_name="Admin Period")
    except Exception:
        pivot_period.to_csv("pivot_admin_period.csv")

# 9c. Pivot: total-patients (add rates)
if "total-patients" in df.columns:
    df_rates = df.copy()
    for rate_col, numerator in [
        ("mortality-rate", "patient-deaths"),
        ("recovery-rate", "total-recovered"),
        ("discharge-rate", "total-discharged")
    ]:
        if numerator in df_rates.columns:
            df_rates[rate_col] = df_rates[numerator] / df_rates["total-patients"].replace(0, pd.NA)

    rate_cols = [c for c in ["mortality-rate", "recovery-rate", "discharge-rate"] if c in df_rates.columns]
    pivot_total_patients = df_rates.groupby("total-patients")[metrics_to_summarize + rate_cols].mean()
    try:
        with pd.ExcelWriter("analysis-summary.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            pivot_total_patients.to_excel(writer, sheet_name="Total Patients (rates)")
    except Exception:
        pivot_total_patients.to_csv("pivot_total_patients_rates.csv")
