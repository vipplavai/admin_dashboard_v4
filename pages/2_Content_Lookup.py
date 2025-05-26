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

    content = db["Content"].find_one({"content_id": cid}) or {}
    qa      = db["QA_pairs"].find_one({"content_id": cid}) or {}
    audits  = list(db["audit_logs"].find({"content_id": cid, "length": "short"}))

    st.subheader("📄 Full Content")
    st.write(content.get("content_text", "—"))

    st.subheader("🧠 Short QA Pairs")
    for q in qa.get("questions", {}).get("short", []):
        st.markdown(f"> Q: {q['question']}  \n> A: {q['answer']}")

    st.subheader("👥 Reviewer Judgments")
    if audits:
        df = pd.DataFrame(audits)
        df["Reviewer"] = df["intern_id"]
        df["Judgment"] = df["judgment"]
        st.dataframe(df[["Reviewer", "question", "Judgment"]])
        st.metric("Fleiss Kappa",
                  compute_fleiss_kappa(df["judgment"].tolist()))
    else:
        st.info("No audits found.")

if __name__ == "__main__":
    show_content_lookup()
