import os


def classify_image(image_path: str) -> dict:
    """Run the classifier selected by WASTE_CLASSIFIER_MODEL.

    Defaults to the eight-class waste classifier.
    Set WASTE_CLASSIFIER_MODEL=nine to use the previous
    nine-class backup classifier.
    """

    selected_model = os.getenv(
        "WASTE_CLASSIFIER_MODEL",
        "eight",
    ).strip().lower()

    if selected_model == "nine":
        from app.services.nine_class_classifier import (
            classify_image as selected_classifier,
        )

    elif selected_model == "eight":
        from app.services.eight_class_classifier import (
            classify_image as selected_classifier,
        )

    else:
        raise ValueError(
            "Invalid WASTE_CLASSIFIER_MODEL setting. "
            "Use 'nine' or 'eight'."
        )

    return selected_classifier(image_path)
