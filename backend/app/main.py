"""FastAPI application entry."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import API_PREFIX
from app.api.routes import router

app = FastAPI(title="PDF to PPT API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}
