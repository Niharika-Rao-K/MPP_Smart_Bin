def calculate_reward(weight_g: float, rag_result: dict) -> float:
    metadata = rag_result.get("metadata", {})

    resale_rate_per_kg = float(
        metadata.get("resale_rate_per_kg", 0)
    )

    quality_factor = float(
        metadata.get("quality_factor", 1.0)
    )

    # Tune this value based on your token-economy design.
    token_conversion_factor = 1.0

    reward = (
        (weight_g / 1000)
        * resale_rate_per_kg
        * quality_factor
        * token_conversion_factor
    )

    return round(max(reward, 0), 2)
