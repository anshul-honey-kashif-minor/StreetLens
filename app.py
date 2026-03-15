from fastapi import FastAPI, UploadFile, File
from service.save_image import saveImageTemp, deleteTemp
from service.ocr_service import process_image

app = FastAPI()

@app.get("/health-check")
def health() :
    return {"message" : "API Working"}


@app.post("/image-analyzer")
def image_analyzer(file : UploadFile = File(...)) :
    filename = saveImageTemp(file)

    result = process_image(filename)

    deleteTemp(filename)

    return result