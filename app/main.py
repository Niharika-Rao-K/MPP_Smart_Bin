from fastapi import FastAPI

from app.routes.deposit import router as deposit_router


app = FastAPI(
    title="Reflow-Net Backend",
    description="Backend API for Reflow-Net Smart Waste Segregation System",
    version="1.0"
)


@app.get("/")
def home():
    return {
        "message": "Reflow-Net Backend Running"
    }


app.include_router(deposit_router)