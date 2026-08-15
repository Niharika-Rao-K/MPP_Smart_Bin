from pydantic import BaseModel


class DepositResponse(BaseModel):
    message: str
    image_filename: str
    predicted_label: str
    confidence: float
    weight_received: float
    status: str