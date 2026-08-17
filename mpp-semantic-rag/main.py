from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional

app = FastAPI(title="Smart Bin RAG API")

# Enable CORS for all origins (required for GitHub Codespaces forwarded ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler: Ensures CORS headers are present even when a 500 error occurs
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
    )

@app.get("/")
async def root():
    return {"status": "online", "service": "Smart Bin Semantic RAG Engine"}

@app.post("/api/rag/evaluate")
async def evaluate_sensor_fusion(
    label: str = Form(...),
    real_weight_g: float = Form(...),
    wallet_address: str = Form(""),
    image: Optional[UploadFile] = File(None)
):
    try:
        # Read uploaded image bytes if present
        image_bytes = None
        if image:
            image_bytes = await image.read()

        # Place your ChromaDB lookup and sensor fusion logic here

        return {
            "predicted_label": label,
            "stable_weight_g": real_weight_g,
            "hardware_route_signal": "M",
            "fusion_result": {
                "decision": "VERIFIED_CLEAN",
                "action": "Accept item. Route to METAL bin."
            },
            "web3_reward": {
                "tokens_minted": 10
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
