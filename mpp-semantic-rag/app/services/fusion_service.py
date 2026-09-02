from app.services.rag_client import evaluate_with_rag


def sensor_fusion(label: str, real_weight_g: float):
    if not label or not label.strip():
        return {
            "visual_label": label,
            "actual_weight_g": real_weight_g,
            "rag_result": {},
            "decision": "REJECTED",
            "action": "Reject item. No visual label was detected.",
            "hardware_route_signal": "R"
        }

    if real_weight_g <= 0:
        return {
            "visual_label": label,
            "actual_weight_g": real_weight_g,
            "rag_result": {},
            "decision": "REJECTED",
            "action": "Reject item. Invalid weight reading.",
            "hardware_route_signal": "R"
        }

    rag_result = evaluate_with_rag(
        label=label,
        real_weight_g=real_weight_g
    )

    final_decision = rag_result["final_decision"]

    return {
        "visual_label": label,
        "actual_weight_g": real_weight_g,
        "rag_result": rag_result,
        "decision": final_decision["status"],
        "action": final_decision["action"],
        "hardware_route_signal": final_decision["hardware_route_signal"],
        "reward_eligible": final_decision["reward_eligible"]
    }
