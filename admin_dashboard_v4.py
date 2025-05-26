# admin_dashboard_v4.py

import streamlit as st
from pymongo import MongoClient
import pandas as pd
import numpy as np
from statsmodels.stats.inter_rater import fleiss_kappa
from collections import defaultdict, Counter
from datetime import datetime

# === CONFIG ===
st.set_page_config(page_title="JNANA Admin Dashboard v4", layout="wide")
st.title("📊 JNANA Admin Dashboard v4")

# === MongoDB Connection ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["Tel_QA"]

# === Collections ===
collections = {
    "Content": db["Content"],
    "Completed Content": db["completed_content"],
    "QA Pairs": db["QA_pairs"],
    "Audit Logs": db["audit_logs"],
    "Final Audit Logs": db["Final_audit_logs"],
    "Doubt Logs": db["doubt_logs"],
    "Skipped Logs": db["skipped_logs"],
}

# === Load DataFrames ===
dfs = {
    name: pd.DataFrame(list(col.find({}, {"_id": 0})))
    for name, col in collections.items()
}

# Parse timestamps
for df in dfs.values():
    if "timestamp" in df.columns and not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

# === Unique Content IDs across all collections ===
all_cids = set()
for name, col in collections.items():
    if name in [
        "Content", "Completed Content", "QA Pairs",
        "Audit Logs", "Final Audit Logs", "Doubt Logs", "Skipped Logs"
    ]:
        all_cids |= set(col.distinct("content_id"))
total_content_count = len(all_cids)

# === QA-Pair Universe ===
# Defined = total_content_count * 6 (6 QA pairs per content)
defined_pairs_count = total_content_count * 6

# Touched = distinct (content_id, qa_index) across logs
touched_sets = set()
for log in ["Audit Logs", "Final Audit Logs", "Doubt Logs"]:
    df = dfs[log]
    if "qa_index" in df.columns:
        touched_sets |= set(zip(df["content_id"], df["qa_index"]))
touched_pairs_count = len(touched_sets)

# === Review Coverage ===
logs_df = pd.concat([dfs["Audit Logs"], dfs["Final Audit Logs"]], ignore_index=True)
intern_counts = logs_df.groupby("content_id")["intern_id"].nunique().to_dict()
fully_reviewed = sum(1 for cnt in intern_counts.values() if cnt == 5)
pending = total_content_count - fully_reviewed
coverage_pct = (fully_reviewed / total_content_count * 100) if total_content_count else 0

# === Doubts & Skips ===
doubt_df = dfs["Doubt Logs"]
skip_df = dfs["Skipped Logs"]
total_doubts = len(doubt_df)
unique_doubt_pairs = len(doubt_df.drop_duplicates(["content_id", "qa_index"]))
total_skips = len(skip_df)
unique_skipped_content = skip_df["content_id"].nunique()

# === Fleiss' Kappa ===
pairwise = defaultdict(lambda: defaultdict(list))
for _, row in logs_df.iterrows():
    if row["judgment"] in ("Correct", "Incorrect"):
        pairwise[row["content_id"]][row["qa_index"]].append(row["judgment"])
kappa_scores = []
for qdict in pairwise.values():
    for judgs in qdict.values():
        if len(judgs) == 5:
            cnt = Counter(judgs)
            matrix = np.array([[cnt["Correct"], cnt["Incorrect"]]])
            try:
                k = fleiss_kappa(matrix)
            except:
                k = np.nan
            if np.isnan(k) and (matrix[0,0] in (0,5) or matrix[0,1] in (0,5)):
                k = 1.0
            if not np.isnan(k):
                kappa_scores.append(k)
valid_pairs = len(kappa_scores)
avg_kappa = round(np.mean(kappa_scores), 4) if kappa_scores else 0.0
ge_08_count = sum(1 for k in kappa_scores if k >= 0.8)
eq_1_count = sum(1 for k in kappa_scores if k == 1.0)

# === DASHBOARD LAYOUT ===

# 1. Top-Line Overview
st.subheader("📦 Top‐Line Overview")
o1, o2, o3, o4 = st.columns(4)
o1.metric("Total Content Items", total_content_count)
o2.metric("Fully Reviewed (== 5)", fully_reviewed)
o3.metric("Pending (<5)", pending)
o4.metric("Coverage (%)", f"{coverage_pct:.1f}%")

# 2. QA-Pair Universe
st.subheader("🔢 QA-Pair Universe")
q1, q2 = st.columns(2)
q1.metric("Defined QA Pairs", defined_pairs_count)
q2.metric("Touched QA Pairs", touched_pairs_count)

# 3. Doubt & Skip Summary
st.subheader("📝 Doubt & Skip Summary")
d1, d2, d3, d4 = st.columns(4)
d1.metric("Total Doubts", total_doubts)
d2.metric("Unique Doubt Pairs", unique_doubt_pairs)
d3.metric("Total Skips", total_skips)
d4.metric("Unique Skipped Content", unique_skipped_content)

# 4. Inter-Rater Agreement
st.subheader("📉 Inter-Rater Agreement (κ)")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Valid QA Pairs", valid_pairs)
k2.metric("Avg. Fleiss’ κ", f"{avg_kappa:.4f}")
k3.metric("Pairs κ ≥ 0.8", ge_08_count)
k4.metric("Pairs κ = 1.0", eq_1_count)

# 5. Download Logs
st.subheader("✅ Download Logs")
st.markdown("Select date range to export raw logs:")
from_col, to_col = st.columns(2)
start_date = from_col.date_input("📅 From", value=pd.Timestamp.utcnow().date())
end_date = to_col.date_input("📅 To", value=pd.Timestamp.utcnow().date())

if start_date > end_date:
    st.warning("‘From’ must be before or equal to ‘To’.")
else:
    def filter_by_date(df):
        if df.empty or "timestamp" not in df.columns:
            return df
        return df[
            (df["timestamp"].dt.date >= start_date) &
            (df["timestamp"].dt.date <= end_date)
        ]

    for name in ["Audit Logs", "Final Audit Logs", "Doubt Logs", "Skipped Logs"]:
        df = dfs[name]
        df_filt = filter_by_date(df)
        st.download_button(
            f"⬇️ Download {name}",
            df_filt.to_csv(index=False).encode("utf-8"),
            file_name=f"{name.replace(' ', '_').lower()}_{start_date}_to_{end_date}.csv",
            mime="text/csv",
        )

