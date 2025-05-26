# pages/2_Content_Lookup.py
import streamlit as st
import pandas as pd
from utils import get_db, compute_fleiss_kappa

def show_content_lookup():
    st.title("🔎 Content Lookup")
    db = get_db()

    cid_input = st.text_input("Content ID")
    if not cid_input:
        return

    try:
        cid = int(cid_input)
    except ValueError:
        st.error("Please enter a valid integer ID.")
        return

    # Fetch content (active or archived)
    content = (
        db["Content"].find_one({"content_id": cid})
        or db["completed_content"].find_one({"content_id": cid})
        or {}
    )

    # Fetch QA templates
    qa = db["QA_pairs"].find_one({"content_id": cid}) or {}

    # Merge live + final audits
    audits_active = list(db["audit_logs"].find({
        "content_id": cid, "length": "short"
    }))
    audits_final = list(db["Final_audit_logs"].find({
        "content_id": cid, "length": "short"
    }))
    audits = audits_active + audits_final

    # Display content & QAs
    st.subheader("📄 Full Content")
    st.write(content.get("content_text", "—"))

    st.subheader("🧠 Short QA Pairs")
    for q in qa.get("questions", {}).get("short", []):
        st.markdown(f"> Q: {q['question']}  \n> A: {q['answer']}")

    # Reviewer judgments, grouped & sorted
    st.subheader("👥 Reviewer Judgments")
    if audits:
        # build DataFrame and parse timestamps
        df = pd.DataFrame(audits)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        # sort by intern then time
        df = df.sort_values(["intern_id", "timestamp"])

        # display per‐reviewer
        for intern, group in df.groupby("intern_id"):
            with st.expander(f"👤 Reviewer: {intern}", expanded=True):
                display_df = group[["timestamp", "question", "judgment"]].rename(
                    columns={"timestamp": "Time", "judgment": "Judgment"}
                )
                st.table(display_df)

        # overall agreement
        all_judgments = df["judgment"].tolist()
        st.metric("Fleiss Kappa", compute_fleiss_kappa(all_judgments))
    else:
        st.info("No audits found.")

if __name__ == "__main__":
    show_content_lookup()
