from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import Base, engine
from app.database import models
from app.routes.deposit import router as deposit_router
from app.routes.deposits import router as deposits_router
from app.routes.bin import router as bin_router
from app.routes.leaderboard import router as leaderboard_router
from app.routes.auth import router as auth_router
from app.routes.sensor import router as sensor_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Recycling Bin RAG & Fusion Backend",
    version="1.0.0"
)
origins = [
    "https://mpp-smart-bin-mpp-admin-dashboard-v-pearl.vercel.app",
]

print("CORS DEBUG - loaded file:", __file__)
print("CORS DEBUG - allowed origins:", repr(origins))

# Development origins only. Add your deployed PWA domain later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

app.include_router(
    leaderboard_router,
    prefix="/api/leaderboard",
    tags=["Leaderboard"],
)

app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"],
)

app.include_router(
    sensor_router,
    prefix="/api/sensor",
    tags=["Sensor Readings"],
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
