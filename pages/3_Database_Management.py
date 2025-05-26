# pages/3_Database_Management.py
import streamlit as st
import json
from utils import get_db

# Load your JSON once at startup
@st.cache_data
def load_all_content():
    with open("data.json", "r", encoding="utf-8") as f:
        return json.load(f)

db = get_db()
content_col = db["Content"]
audit_col   = db["audit_logs"]
qa_col      = db["QA_pairs"]
done_col    = db["completed_content"]
final_col   = db["Final_audit_logs"]

st.title("🛠 Database Management")

# --- Inject Content ---
st.subheader("📥 Inject Content from JSON")
all_content = load_all_content()

c1, c2 = st.columns(2)
start_id = c1.number_input("Start content_id", min_value=0, step=1, value=0)
end_id   = c2.number_input("End content_id",   min_value=0, step=1, value=0)

if st.button("▶️ Inject Range"):
    if start_id > end_id:
        st.error("Start must be ≤ End.")
    else:
        to_insert = [
            doc for doc in all_content
            if start_id <= doc.get("content_id", -1) <= end_id
        ]
        if not to_insert:
            st.warning("No records found in that range.")
        else:
            for rec in to_insert:
                content_col.replace_one(
                    {"content_id": rec["content_id"]},
                    {"content_id": rec["content_id"],
                     "content_text": rec["content_text"]},
                    upsert=True
                )
            st.success(f"Injected {len(to_insert)} records.")

# --- Archive Completed Content ---
st.subheader("🚚 Archive Completed Content (≥5 reviews)")
# count how many are ready:
pipeline = [
    {"$group": {"_id": "$content_id", "interns": {"$addToSet": "$intern_id"}}},
    {"$addFields": {"count": {"$size": "$interns"}}},
    {"$match": {"count": {"$eq": 5}}}
]
num_ready = len(list(audit_col.aggregate(pipeline)))
st.info(f"{num_ready} content items are ready to archive.")

if st.button("🗄 Archive Now", disabled=(num_ready < 5)):
    with st.spinner("Archiving…"):
        completed_ids = [doc["_id"] for doc in audit_col.aggregate(pipeline)]
        for cid in completed_ids:
            # move content → completed_content
            doc = content_col.find_one({"content_id": cid})
            if doc:
                done_col.replace_one({"content_id": cid}, doc, upsert=True)
                content_col.delete_one({"content_id": cid})
            # move audit_logs → final
            logs = list(audit_col.find({"content_id": cid}))
            if logs:
                final_col.insert_many(logs)
                audit_col.delete_many({"content_id": cid})
            # delete QA templates
            qa_col.delete_many({"content_id": cid})
        st.success(f"Archived {len(completed_ids)} items.")
