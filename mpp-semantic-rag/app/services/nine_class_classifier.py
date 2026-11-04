import json
from functools import lru_cache
from pathlib import Path

import torch
from PIL import Image, ImageFile
from torch import nn
from torchvision import models, transforms


ImageFile.LOAD_TRUNCATED_IMAGES = True

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODEL_DIR / "best_nine_item_model.pth"
CLASSES_PATH = MODEL_DIR / "nine_item_classes.json"

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
    """Load the trained nine-class model once per process."""

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Nine-item model not found: {MODEL_PATH}"
        )

    if not CLASSES_PATH.is_file():
        raise FileNotFoundError(
            f"Nine-item class list not found: {CLASSES_PATH}"
        )

    with CLASSES_PATH.open("r", encoding="utf-8") as file:
        classes = json.load(file)

    if not isinstance(classes, list) or len(classes) != 9:
        raise ValueError("The nine-item class list must contain nine classes.")

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
        weights_only=True,
    )

    checkpoint_classes = checkpoint.get("classes")

    if checkpoint_classes != classes:
        raise ValueError(
            "The checkpoint classes do not match nine_item_classes.json."
        )

    if checkpoint.get("architecture") != "mobilenet_v3_small":
        raise ValueError("Unexpected model architecture in checkpoint.")

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
    """Classify an image and return its predicted class and confidence."""

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
