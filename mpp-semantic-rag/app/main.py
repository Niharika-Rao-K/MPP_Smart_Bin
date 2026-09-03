from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import Base, engine
from app.database import models
from app.routes.deposit import router as deposit_router
from app.routes.bin import router as bin_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Recycling Bin RAG & Fusion Backend",
    version="1.0.0"
)

# Development origins only. Add your deployed PWA domain later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://solid-succotash-97w5vgqj54vr277wv-3000.app.github.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    deposit_router,
    prefix="/api/rag",
    tags=["RAG Deposits"]
)

app.include_router(
    bin_router,
    prefix="/api/bins",
    tags=["Bins"],
)

app.include_router(
    deposits_router,
    prefix="/api/deposits",
    tags=["Deposits"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Smart Recycling Bin Sensor Fusion API"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
