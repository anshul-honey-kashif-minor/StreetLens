import cv2
import easyocr
import numpy as np
from utils import logger
import numpy as np

class OCRProcessor:
    def __init__(self):
        logger.info("Initializing EasyOCR reader (English)...")
        self.reader = easyocr.Reader(['en'], gpu=False) 

    def preprocess_image(self, image_path):
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                raise ValueError(f"Could not load image at {image_path}")

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            width = int(gray.shape[1] * 1.5)
            height = int(gray.shape[0] * 1.5)
            resized = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

            denoised = cv2.bilateralFilter(resized, 9, 75, 75)

            kernel = np.array([[0, -1, 0],
                               [-1, 5,-1],
                               [0, -1, 0]])
            
            sharpened = cv2.filter2D(denoised, -1, kernel)

            contrast = cv2.convertScaleAbs(sharpened, alpha=1.5, beta=0)

            thresh = cv2.adaptiveThreshold(
                contrast,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )

            cv2.imwrite("debug_processed.png", thresh)

            return thresh
        except Exception as e:
            logger.error(f"Preprocessing failed for {image_path}: {e}")
            return None

    def extract_text(self, image_path):
        processed_img = self.preprocess_image(image_path)
        if processed_img is None:
            return []

        try:
            results = self.reader.readtext(
                processed_img,
                detail=1,
                paragraph=False
            )

            text_lines = [res[1].strip() for res in results if res[1].strip()]
            return text_lines
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return []