import cv2
import easyocr
import numpy as np
from utils import logger

class OCRProcessor:
    def __init__(self):
        logger.info("Initializing EasyOCR reader (English)...")
        # Load model into memory once
        self.reader = easyocr.Reader(['en'], gpu=False) 

    def preprocess_image(self, image_path):
        """Preprocesses the image for better OCR accuracy."""
        try:
            # Read image
            img = cv2.imread(str(image_path))
            if img is None:
                raise ValueError(f"Could not load image at {image_path}")

            # 1. Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 2. Resize (scale up by 1.5x to improve small text clarity)
            width = int(gray.shape[1] * 1.5)
            height = int(gray.shape[0] * 1.5)
            resized = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

            # 3. Remove noise (Bilateral Filter preserves edges)
            denoised = cv2.bilateralFilter(resized, 9, 75, 75)

            # 4. Adaptive Thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            return thresh
        except Exception as e:
            logger.error(f"Preprocessing failed for {image_path}: {e}")
            return None

    def extract_text(self, image_path):
        """Runs OCR on the preprocessed image and returns clean text lines."""
        processed_img = self.preprocess_image(image_path)
        if processed_img is None:
            return []

        try:
            # Extract text
            results = self.reader.readtext(processed_img)
            # results format: [(bounding_box, text, confidence), ...]
            text_lines = [res[1].strip() for res in results if res[1].strip()]
            return text_lines
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return []