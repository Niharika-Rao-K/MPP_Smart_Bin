import requests


# Niharika's RAG API
RAG_API_URL = "http://127.0.0.1:8001/api/rag/evaluate"


def evaluate_with_rag(label: str, real_weight_g: float):

    payload = {
        "label": label,
        "real_weight_g": real_weight_g
    }

    response = requests.post(
        RAG_API_URL,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    return response.json()