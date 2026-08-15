import os
import shutil


UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def save_uploaded_file(upload_file):

    file_path = os.path.join(
        UPLOAD_FOLDER,
        upload_file.filename
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return file_path