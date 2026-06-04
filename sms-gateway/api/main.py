from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import send, status, webhook, inbound

app = FastAPI(title="Blackout Predictor SMS Gateway", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(send.router)
app.include_router(status.router)
app.include_router(webhook.router)
app.include_router(inbound.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "sms-gateway"}
