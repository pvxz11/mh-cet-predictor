from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import os

app = FastAPI(title="MH-CET College Predictor")

# Allow frontend (same origin or localhost dev) to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── load data once at startup ─────────
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "colleges.csv")
df = pd.read_csv(CSV_PATH)

# Normalise column names (strip spaces)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
df["category"]    = df["category"].str.strip().str.upper()
df["gender"]      = df["gender"].str.strip().str.capitalize()
df["district"]    = df["district"].str.strip().str.title()
df["branch"]      = df["branch"].str.strip()
df["college_name"]= df["college_name"].str.strip()

# ── helper: get unique dropdown values for the frontend ───────────
@app.get("/meta")
def get_meta():
    return {
        "categories": sorted(df["category"].dropna().unique().tolist()),
        "districts":  sorted(df["district"].dropna().unique().tolist()),
        "branches":   sorted(df["branch"].dropna().unique().tolist()),
        "years":      sorted(df["year"].dropna().unique().astype(int).tolist(), reverse=True),
    }

# ── main prediction endpoint ─
@app.get("/predict")
def predict(
    percentile: float = Query(..., ge=0, le=100, description="Your CET percentile"),
    category:   str   = Query(..., description="e.g. OPEN, OBC, SC, ST, EWS, TFWS"),
    gender:     str   = Query(..., description="Male, Female, or ALL"),
    district:   str   = Query(None, description="Filter by district (optional)"),
    branch:     str   = Query(None, description="Filter by branch keyword (optional)"),
    cap_round:  int   = Query(1,    description="CAP Round number (1, 2, or 3)"),
    year:       int   = Query(2024, description="Year of cutoff data"),
    buffer:     float = Query(2.0,  description="Show colleges within this many percentile points above your score too"),
):
    """
    Returns colleges where closing cutoff <= your percentile + small buffer.
    Gender filter: if a college row has gender='ALL' it always matches.
    """
    gender_norm   = gender.strip().capitalize()
    category_norm = category.strip().upper()

    mask = (
        (df["category"]          == category_norm) &
        (df["cutoff_percentile"] <= percentile + buffer) &
        (df["cap_round"]         == cap_round) &
        (df["year"]              == year) &
        (df["gender"].isin([gender_norm, "All"]))  # 'All' rows match everyone
    )

    filtered = df[mask].copy()

    # optional filters
    if district:
        filtered = filtered[filtered["district"].str.lower() == district.strip().lower()]
    if branch:
        filtered = filtered[filtered["branch"].str.lower().str.contains(branch.strip().lower())]

    # safe = cutoff clearly below your score  |  possible = cutoff within buffer
    def safety(cutoff):
        if cutoff <= percentile - 3:
            return "safe"
        elif cutoff <= percentile:
            return "good"
        else:
            return "stretch"

    filtered["chance"] = filtered["cutoff_percentile"].apply(safety)

    result = (
        filtered
        .sort_values("cutoff_percentile", ascending=False)
        [["college_name", "branch", "district", "category", "gender",
          "cutoff_percentile", "cap_round", "year", "chance"]]
        .to_dict(orient="records")
    )

    return {
        "input": {
            "percentile": percentile,
            "category":   category_norm,
            "gender":     gender_norm,
            "cap_round":  cap_round,
        },
        "count":   len(result),
        "results": result,
    }

# ── serve the frontend static files ─
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
