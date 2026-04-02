from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

app = FastAPI(title="Data Pipeline Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_processed_csv(filename: str) -> list[dict]:
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {filename}")

    df = pd.read_csv(file_path)
    return df.to_dict(orient="records")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/revenue")
def get_revenue() -> list[dict]:
    return read_processed_csv("monthly_revenue.csv")


@app.get("/api/top-customers")
def get_top_customers() -> list[dict]:
    return read_processed_csv("top_customers.csv")


@app.get("/api/categories")
def get_categories() -> list[dict]:
    return read_processed_csv("category_performance.csv")


@app.get("/api/regions")
def get_regions() -> list[dict]:
    return read_processed_csv("regional_analysis.csv")
