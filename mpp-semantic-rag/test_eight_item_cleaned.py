import json
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parent
# Independent eight-class test dataset.
TEST_DIR = Path(r"D:\Downloads\trash_cam\trash_cam\test_photos_8class")

# Eight-class candidate model and class list.
MODEL_PATH = ROOT / "app" / "models" / "candidate_eight_item_cleaned_model.pth"
CLASSES_PATH = ROOT / "app" / "models" / "candidate_eight_item_cleaned_classes.json"
REPORT_PATH = ROOT / "app" / "models" / "candidate_eight_item_cleaned_test_results.json"
EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".jfif", ".avif",
    ".bmp", ".tif", ".tiff", ".ppm", ".pgm"
}

if not MODEL_PATH.is_file():
    raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
if not CLASSES_PATH.is_file():
    raise FileNotFoundError(f"Class list not found: {CLASSES_PATH}")
if not TEST_DIR.is_dir():
    raise FileNotFoundError(f"Test folder not found: {TEST_DIR}")

with CLASSES_PATH.open("r", encoding="utf-8") as f:
    classes = json.load(f)

device = torch.device("cpu")

checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=True)
if checkpoint.get("architecture") != "mobilenet_v3_small":
    raise ValueError("Unexpected model architecture in checkpoint.")
if checkpoint.get("classes") != classes:
    raise ValueError("Checkpoint classes do not match candidate_eight_item_cleaned_classes.json.")

model = models.mobilenet_v3_small(weights=None)
model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(classes))
model.load_state_dict(checkpoint["model_state_dict"])
model.to(device)
model.eval()

transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

results = []
skipped = []

for class_dir in sorted(p for p in TEST_DIR.iterdir() if p.is_dir()):
    expected = class_dir.name
    if expected not in classes:
        print(f"Skipping folder not in model classes: {expected}")
        continue

    for path in sorted(class_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue

        try:
            with Image.open(path) as image:
                image = image.convert("RGB")
                tensor = transform(image).unsqueeze(0).to(device)

            with torch.inference_mode():
                logits = model(tensor)
                probabilities = torch.softmax(logits, dim=1)[0]
                confidence, predicted_index = probabilities.max(dim=0)

            predicted = classes[predicted_index.item()]
            confidence_pct = round(confidence.item() * 100, 2)
            correct = predicted == expected

            results.append({
                "file": str(path.relative_to(TEST_DIR)),
                "expected": expected,
                "predicted": predicted,
                "confidence_percent": confidence_pct,
                "correct": correct,
            })

            status = "CORRECT" if correct else "WRONG"
            print(
                f"{status:7} | expected={expected:20} | "
                f"predicted={predicted:20} | confidence={confidence_pct:6.2f}% "
                f"| {path.name}"
            )
        except Exception as exc:
            skipped.append({
                "file": str(path.relative_to(TEST_DIR)),
                "error": str(exc),
            })
            print(f"SKIPPED | {path.name} | {exc}")

total = len(results)
correct_count = sum(item["correct"] for item in results)
accuracy = round(correct_count / total * 100, 2) if total else 0.0

report = {
    "model": str(MODEL_PATH),
    "classes": classes,
    "test_images_evaluated": total,
    "correct": correct_count,
    "incorrect": total - correct_count,
    "accuracy_percent": accuracy,
    "skipped_images": skipped,
    "results": results,
}

with REPORT_PATH.open("w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("\n--- TEST SUMMARY ---")
print(f"Images evaluated: {total}")
print(f"Correct: {correct_count}")
print(f"Incorrect: {total - correct_count}")
print(f"Test accuracy: {accuracy:.2f}%")
print(f"Skipped images: {len(skipped)}")
print(f"Report saved: {REPORT_PATH}")


