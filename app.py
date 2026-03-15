from fastapi import FastAPI, UploadFile, File
from service.save_image import saveImageTemp

app = FastAPI()

@app.get("/health-check")
def health() :
    return {"message" : "API Working"}


@app.post("/image-analyzer")
def image_analyzer(file : UploadFile = File(...)) :
    filename = saveImageTemp(file)
    return {
        "saved_path" : filename
    }