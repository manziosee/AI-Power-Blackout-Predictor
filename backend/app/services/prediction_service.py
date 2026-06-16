import httpx


async def request_prediction(h3_index: str, weather_features: dict) -> dict:
    """Call the ML engine microservice to get a prediction for a single H3 cell."""
    payload = {"h3_index": h3_index, "features": weather_features}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post("http://ml-engine:8002/predict", json=payload)
        resp.raise_for_status()
        return resp.json()


async def batch_predict_region(region_model: str, cells: list[dict]) -> list[dict]:
    """Request batch predictions for a full region."""
    payload = {"region_model": region_model, "cells": cells}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post("http://ml-engine:8002/predict/batch", json=payload)
        resp.raise_for_status()
        return resp.json()
