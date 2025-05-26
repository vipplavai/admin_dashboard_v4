# utils.py
import streamlit as st
from pymongo import MongoClient
from statsmodels.stats.inter_rater import fleiss_kappa
import numpy as np
import pandas as pd
from datetime import datetime

@st.cache_resource
def get_db():
    client = MongoClient(st.secrets["mongo_uri"])
    return client["Tel_QA"]

def compute_fleiss_kappa(judgments: list[str]) -> float:
    cnt = {"Correct": judgments.count("Correct"),
           "Incorrect": judgments.count("Incorrect")}
    mat = np.array([[cnt["Correct"], cnt["Incorrect"]]])
    try:
        k = fleiss_kappa(mat)
    except:
        k = np.nan
    # perfect agreement edge‐cases
    if np.isnan(k) and (mat[0,0] in (0,5) or mat[0,1] in (0,5)):
        k = 1.0
    return round(k, 4)

def parse_timestamp(ts) -> datetime:
    # if ts is string, parse; if datetime, return
    if isinstance(ts, str):
        return pd.to_datetime(ts, utc=True).to_pydatetime()
    return ts
