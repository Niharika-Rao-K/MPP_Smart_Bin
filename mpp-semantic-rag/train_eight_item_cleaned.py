import json
import random
import time
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import datasets, transforms, models
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT = Path(__file__).resolve().parent

# Separate eight-class training dataset.
DATA_DIR = Path(r"D:\Downloads\trash_cam\trash_cam\training_8class_cleaned")

# Actual backend model directory.
MODEL_DIR = ROOT / "app" / "models"

# Separate eight-class candidate files.
OUTPUT_MODEL = MODEL_DIR / "candidate_eight_item_cleaned_model.pth"
OUTPUT_CLASSES = MODEL_DIR / "candidate_eight_item_cleaned_classes.json"
OUTPUT_REPORT = MODEL_DIR / "candidate_eight_item_cleaned_training_report.json"

SEED = 42
EPOCHS = 15
BATCH_SIZE = 8
PATIENCE = 5

random.seed(SEED)
torch.manual_seed(SEED)

if not DATA_DIR.is_dir():
    raise FileNotFoundError(f"Training folder not found: {DATA_DIR}")

train_transform = transforms.Compose([
    transforms.Resize((240, 240)),
    transforms.RandomResizedCrop(224, scale=(0.80, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ColorJitter(
        brightness=0.15, contrast=0.15, saturation=0.10
    ),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

val_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".jfif", ".avif",
    ".bmp", ".tif", ".tiff", ".ppm", ".pgm"
}

def is_supported_image(path):
    if Path(path).suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except Exception as exc:
        print(f"Skipping unreadable image: {path} ({exc})")
        return False

base_dataset = datasets.ImageFolder(
    DATA_DIR,
    is_valid_file=is_supported_image
)
print(f"Total usable images loaded: {len(base_dataset.samples)}")
print("Images per class:")
for class_name, class_index in base_dataset.class_to_idx.items():
    count = sum(1 for _, label in base_dataset.samples if label == class_index)
    print(f"  {class_name}: {count}")
classes = base_dataset.classes

if len(classes) != 8:
    raise ValueError(
        f"Expected 8 class folders, found {len(classes)}: {classes}"
    )

class_counts = {
    name: sum(1 for _, label in base_dataset.samples
              if label == index)
    for index, name in enumerate(classes)
}

print("Discovered classes and image counts:")
for name, count in class_counts.items():
    print(f"  {name}: {count}")

for name, count in class_counts.items():
    if count < 5:
        raise ValueError(
            f"Class '{name}' has only {count} images. "
            "Add at least 5 images before training."
        )

rng = random.Random(SEED)
train_indices = []
val_indices = []

for class_index, class_name in enumerate(classes):
    indices = [
        i for i, (_, label) in enumerate(base_dataset.samples)
        if label == class_index
    ]
    rng.shuffle(indices)

    val_count = max(1, round(len(indices) * 0.20))
    val_indices.extend(indices[:val_count])
    train_indices.extend(indices[val_count:])

class ImageSubset(Dataset):
    def __init__(self, base, indices, transform):
        self.base = base
        self.indices = indices
        self.transform = transform

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        image_index = self.indices[index]
        path, label = self.base.samples[image_index]

        with Image.open(path) as im:
            image = im.convert("RGB")

        return self.transform(image), label

train_dataset = ImageSubset(
    base_dataset, train_indices, train_transform
)
val_dataset = ImageSubset(
    base_dataset, val_indices, val_transform
)

train_loader = DataLoader(
    train_dataset, batch_size=BATCH_SIZE,
    shuffle=True, num_workers=0
)
val_loader = DataLoader(
    val_dataset, batch_size=BATCH_SIZE,
    shuffle=False, num_workers=0
)

print(f"\nClasses: {classes}")
print(f"Training images: {len(train_dataset)}")
print(f"Validation images: {len(val_dataset)}")
print("Device: CPU")
print("Loading pretrained MobileNetV3-Small...")

MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Stop if pretrained weights cannot be downloaded.
model = models.mobilenet_v3_small(
    weights=models.MobileNet_V3_Small_Weights.DEFAULT
)
model.classifier[3] = nn.Linear(
    model.classifier[3].in_features, len(classes)
)

for parameter in model.features.parameters():
    parameter.requires_grad = False

device = torch.device("cpu")
model.to(device)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(
    model.classifier.parameters(),
    lr=0.001,
    weight_decay=0.0001
)

best_val_loss = float("inf")
best_val_accuracy = 0.0
epochs_without_improvement = 0
history = []

for epoch in range(1, EPOCHS + 1):
    start = time.time()
    model.train()
    train_loss_sum = 0.0
    train_correct = 0
    train_total = 0

    for images, labels in train_loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        train_loss_sum += loss.item() * labels.size(0)
        train_correct += (
            outputs.argmax(1) == labels
        ).sum().item()
        train_total += labels.size(0)

    model.eval()
    val_loss_sum = 0.0
    val_correct = 0
    val_total = 0

    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            val_loss_sum += loss.item() * labels.size(0)
            val_correct += (
                outputs.argmax(1) == labels
            ).sum().item()
            val_total += labels.size(0)

    train_loss = train_loss_sum / train_total
    train_accuracy = train_correct / train_total
    val_loss = val_loss_sum / val_total
    val_accuracy = val_correct / val_total

    history.append({
        "epoch": epoch,
        "train_loss": round(train_loss, 4),
        "train_accuracy": round(train_accuracy, 4),
        "val_loss": round(val_loss, 4),
        "val_accuracy": round(val_accuracy, 4),
    })

    print(
        f"Epoch {epoch:02d}/{EPOCHS} | "
        f"train loss {train_loss:.3f} | "
        f"train acc {train_accuracy:.1%} | "
        f"val loss {val_loss:.3f} | "
        f"val acc {val_accuracy:.1%} | "
        f"{time.time() - start:.0f}s"
    )

    if val_loss < best_val_loss:
        best_val_loss = val_loss
        best_val_accuracy = val_accuracy
        epochs_without_improvement = 0

        torch.save({
            "model_state_dict": model.state_dict(),
            "classes": classes,
            "architecture": "mobilenet_v3_small",
            "input_size": 224,
            "seed": SEED,
        }, OUTPUT_MODEL)
    else:
        epochs_without_improvement += 1

    if epochs_without_improvement >= PATIENCE:
        print(f"Early stopping after epoch {epoch}.")
        break

with OUTPUT_CLASSES.open("w", encoding="utf-8") as f:
    json.dump(classes, f, indent=2)

report = {
    "dataset": str(DATA_DIR),
    "class_counts": class_counts,
    "train_images": len(train_dataset),
    "validation_images": len(val_dataset),
    "best_validation_loss": best_val_loss,
    "validation_accuracy_at_best_loss": best_val_accuracy,
    "history": history,
    "warning": (
        "Small dataset. Validation results may be optimistic if "
        "similar images or the same physical objects appear in "
        "both splits. Test with independent photos before deployment."
    ),
}

with OUTPUT_REPORT.open("w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("\nTraining finished.")
print(f"Model: {OUTPUT_MODEL}")
print(f"Class list: {OUTPUT_CLASSES}")
print(f"Report: {OUTPUT_REPORT}")
print(f"Best validation loss: {best_val_loss:.4f}")
print(
    "Validation accuracy at best loss: "
    f"{best_val_accuracy:.1%}"
)
