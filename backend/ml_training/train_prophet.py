"""Train Facebook Prophet time-series models per H3 cell for outage forecasting."""
import argparse
import json
import os
import pickle


def load_cell_timeseries(db_url: str, h3_index: str | None) -> dict[str, object]:
    from sqlalchemy import create_engine, text
    import pandas as pd

    engine = create_engine(db_url)
    query = text("""
        SELECT
            h3_index,
            DATE_TRUNC('day', reported_at) AS ds,
            COUNT(*) AS y
        FROM outage_reports
        WHERE verified = true
          AND (:h3_index IS NULL OR h3_index = :h3_index)
        GROUP BY h3_index, DATE_TRUNC('day', reported_at)
        ORDER BY h3_index, ds
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"h3_index": h3_index})

    cells = {}
    for cell, group in df.groupby("h3_index"):
        cells[cell] = group[["ds", "y"]].reset_index(drop=True)
    return cells


def train_cell(h3_index: str, df, output_dir: str) -> dict:
    from prophet import Prophet

    if len(df) < 30:
        return {"h3_index": h3_index, "skipped": True, "reason": f"Only {len(df)} days of data"}

    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
    )
    m.fit(df)

    future = m.make_future_dataframe(periods=30)
    forecast = m.predict(future)
    tail = forecast.tail(30)

    cell_dir = os.path.join(output_dir, h3_index[:4])  # shard by first 4 chars
    os.makedirs(cell_dir, exist_ok=True)
    with open(os.path.join(cell_dir, f"{h3_index}.pkl"), "wb") as f:
        pickle.dump(m, f)

    return {
        "h3_index": h3_index,
        "skipped": False,
        "forecast_30d_mean": round(float(tail["yhat"].mean()), 3),
        "forecast_30d_max": round(float(tail["yhat_upper"].max()), 3),
    }


def train_all(db_url: str, output_dir: str, h3_index: str | None = None) -> None:
    print("Loading time-series data...")
    cells = load_cell_timeseries(db_url, h3_index)
    if not cells:
        print("No data found.")
        return

    print(f"Training Prophet models for {len(cells)} cells...")
    results = []
    for i, (cell, df) in enumerate(cells.items(), 1):
        result = train_cell(cell, df, output_dir)
        results.append(result)
        if i % 10 == 0:
            print(f"  {i}/{len(cells)} cells processed")

    summary = {
        "total_cells": len(cells),
        "trained": sum(1 for r in results if not r.get("skipped")),
        "skipped": sum(1 for r in results if r.get("skipped")),
    }
    print(f"Done: {summary}")
    with open(os.path.join(output_dir, "prophet_summary.json"), "w") as f:
        json.dump({"summary": summary, "cells": results}, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--output-dir", default="models/prophet/")
    parser.add_argument("--h3-index", default=None, help="Train for single cell (omit for all)")
    args = parser.parse_args()
    train_all(args.db_url, args.output_dir, args.h3_index)
