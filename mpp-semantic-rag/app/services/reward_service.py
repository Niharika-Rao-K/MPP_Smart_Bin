def calculate_reward(weight_g: float, rag_result: dict) -> float:
    """
    Calculate $RECYCLE reward from measured weight and
    the reference recycling rate retrieved by RAG.

    Reward is calculated only when the RAG decision marks
    the item as reward eligible.
    """

    if weight_g <= 0:
        return 0.0

    final_decision = rag_result.get(
        "final_decision",
        {}
    )

    if not final_decision.get(
        "reward_eligible",
        False
    ):
        return 0.0

    metadata = rag_result.get(
        "metadata",
        {}
    )

    rate_inr_per_kg = metadata.get(
        "rate_inr_per_kg",
        0
    )

    try:
        rate_inr_per_kg = float(
            rate_inr_per_kg
        )
    except (TypeError, ValueError):
        return 0.0

    if rate_inr_per_kg <= 0:
        return 0.0

    token_conversion_factor = 1.0

    weight_kg = weight_g / 1000.0

    material_value_inr = (
        weight_kg * rate_inr_per_kg
    )

    reward = (
        material_value_inr
        * token_conversion_factor
    )

    return round(
        max(reward, 0.0),
        2
    )
