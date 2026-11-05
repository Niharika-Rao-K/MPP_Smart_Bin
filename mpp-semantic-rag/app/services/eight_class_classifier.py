import json
from functools import lru_cache
from pathlib import Path

import torch
from PIL import Image, ImageFile
from torch import nn
from torchvision import models, transforms

ImageFile.LOAD_TRUNCATED_IMAGES = True

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODEL_DIR / "candidate_eight_item_cleaned_model.pth"
CLASSES_PATH = MODEL_DIR / "candidate_eight_item_cleaned_classes.json"

DEVICE = torch.device("cpu")

IMAGE_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


@lru_cache(maxsize=1)
def get_classifier():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Eight-class model not found: {MODEL_PATH}"
        )

    if not CLASSES_PATH.is_file():
        raise FileNotFoundError(
            f"Eight-class labels not found: {CLASSES_PATH}"
        )

    with CLASSES_PATH.open("r", encoding="utf-8") as file:
        classes = json.load(file)

    if not isinstance(classes, list) or len(classes) != 8:
        raise ValueError(
            "Expected exactly eight class labels."
        )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
        weights_only=True,
    )

    if checkpoint.get("classes") != classes:
        raise ValueError(
            "Class labels do not match the model checkpoint."
        )

    if checkpoint.get("architecture") != "mobilenet_v3_small":
        raise ValueError(
            "Unexpected model architecture."
        )

    model = models.mobilenet_v3_small(weights=None)

    model.classifier[3] = nn.Linear(
        model.classifier[3].in_features,
        len(classes),
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(DEVICE)
    model.eval()

    return model, classes


def classify_image(image_path: str) -> dict:
    model, classes = get_classifier()

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        tensor = IMAGE_TRANSFORM(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        logits = model(tensor)[0]
        probabilities = torch.softmax(logits, dim=0)
        best_index = int(probabilities.argmax())

    return {
        "label": classes[best_index],
        "confidence": float(probabilities[best_index]),
        "class_probabilities": {
            label: float(probabilities[index])
            for index, label in enumerate(classes)
        },
    }
