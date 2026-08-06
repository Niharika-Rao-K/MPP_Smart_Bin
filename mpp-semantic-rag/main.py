from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import evaluate_similarity, evaluate_weight_anomaly

app = FastAPI(
    title="MPP Core Semantic Intelligence Layer",
    description="ChromaDB RAG Foundations & Mathematical Rule Engine"
)

# Enable CORS for your React Dashboard UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema contract for Anusha's sensor fusion pipeline 
class FusionRequest(BaseModel):
    label: str
    real_weight_g: float

@app.post("/api/rag/evaluate")
def evaluate_sensor_fusion(payload: FusionRequest):
    """
    Executes a semantic fallback check followed by physical weight verification.
    Maps outcomes explicitly to Plastic Wrapper, Metal Waste, or E-Waste compartments.
    """
    # 1. Step A: Perform vector database lookup
    match_data = evaluate_similarity(payload.label)
    if not match_data:
        raise HTTPException(status_code=404, detail="No semantic mapping profile found.")
        
    # 2. Step B: Extract parameters and pass into your mathematical rule engine
    weight_assessment = evaluate_weight_anomaly(
        ideal_weight=match_data["ideal_weight_g"],
        real_weight=payload.real_weight_g,
        error_margin=match_data["error_margin_g"]
    )
    
    # 3. Step C: Map the material category to your exact physical hardware routing signals
    material_type = match_data["material"]
    validation_status = weight_assessment["status"]
    
    if validation_status == "Valid":
        if material_type == "Plastic Wrapper":
            hardware_signal = "W"  # W for Wrapper Compartment
        elif material_type == "Metal Waste":
            hardware_signal = "M"  # M for Metal Waste Compartment
        elif material_type == "E-Waste":
            hardware_signal = "E"  # E for E-Waste Compartment
        else:
            hardware_signal = "R"  # Fallback reject if material mismatch occurs
    else:
        # If the item is Contaminated or Underweight, send it to the Reject tray
        hardware_signal = "R"
    
    # 4. Step D: Combine the results into a single comprehensive decision payload
    return {
        "semantic_match": match_data,
        "validation_check": weight_assessment,
        "final_decision": {
            "status": validation_status,
            "action": weight_assessment["action"],
            "hardware_route_signal": hardware_signal
        }
    }