
import os
import shutil
import uuid

TEMP_FOLDER = "temp"

os.makedirs(TEMP_FOLDER, exist_ok=True)

def saveImageTemp(file) :
    unique_id = uuid.uuid4().hex
    extension = file.filename.split(".")[-1]

    filename = f"{TEMP_FOLDER}/{unique_id}.{extension}"

    with open(filename, "wb") as buffer :
        shutil.copyfileobj(file.file, buffer)

    return filename

def deleteTemp(file) :
    if os.path.exists(file) :
        os.remove(file)