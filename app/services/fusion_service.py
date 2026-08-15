from app.services.rag_client import evaluate_with_rag


def sensor_fusion(label: str, real_weight_g: float):

    rag_result = evaluate_with_rag(
        label,
        real_weight_g
    )

    final_decision = rag_result["final_decision"]

    return {
        "visual_label": label,
        "actual_weight_g": real_weight_g,
        "rag_result": rag_result,
        "decision": final_decision["status"],
        "action": final_decision["action"],
        "hardware_route_signal": final_decision["hardware_route_signal"]
    }