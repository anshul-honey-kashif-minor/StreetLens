import cv2
import os
from pathlib import Path

from dotenv import load_dotenv

from utils import logger

try:
    import google.genai as genai
    from google.genai import types
except ImportError:  # pragma: no cover - depends on optional runtime dependency
    genai = None
    types = None

# Get absolute path to current file → then go to project root
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

class OCRProcessor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if genai is None:
            logger.warning("google-genai is not installed; Gemini OCR will be unavailable.")
            self.client = None
        elif not api_key:
            logger.warning("GEMINI_API_KEY not set; Gemini OCR will be unavailable.")
            self.client = None
        else:
            logger.info("Initializing Google Gemini Vision API...")
            self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def preprocess_image(self, image_path):
        """Resize very large inputs before sending them to Gemini."""
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Could not load image at {image_path}")

            height, width = image.shape[:2]
            if max(height, width) > 4096:
                scale = 4096 / max(height, width)
                image = cv2.resize(
                    image,
                    (int(width * scale), int(height * scale)),
                    interpolation=cv2.INTER_CUBIC,
                )

            logger.info(f"Image preprocessed for Gemini: {image.shape}")
            return image
        except Exception as exc:
            logger.error(f"Preprocessing failed for {image_path}: {exc}")
            return None

    def extract_text(self, image_path):
        """Extract text using Gemini Vision and return normalized OCR metadata."""
        try:
            if self.client is None or types is None:
                return {
                    "text_lines": [],
                    "line_metadata": [],
                    "quality_score": 0.0,
                    "error": "Gemini OCR is unavailable. Check the dependency and API key.",
                }

            processed_img = self.preprocess_image(image_path)
            if processed_img is None:
                return {
                    "text_lines": [],
                    "line_metadata": [],
                    "quality_score": 0.0,
                    "error": "Could not preprocess the image for Gemini OCR.",
                }

            success, encoded_img = cv2.imencode(
                ".jpg",
                processed_img,
                [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            )

            if not success:
                logger.error(f"Could not encode processed image: {image_path}")
                return {
                    "text_lines": [],
                    "line_metadata": [],
                    "quality_score": 0.0,
                    "error": "Could not encode the image for Gemini OCR.",
                }

            logger.info(f"Encoded image for Gemini: {len(encoded_img.tobytes())} bytes")

            # Call Gemini API with new syntax (using self.client)
            message = (
                "Extract all visible text from this storefront image. "
                "Return only the detected text lines, one per line."
            )
            
            # ✅ Use client.models.generate_content instead of model.generate_content
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(
                                data=encoded_img.tobytes(),
                                mime_type="image/jpeg",
                            ),
                            types.Part.from_text(message),
                        ],
                    )
                ]
            )

            if response and response.text:
                text_lines = [line.strip() for line in response.text.split('\n') if line.strip()]
                logger.info(f"Extracted {len(text_lines)} lines using Gemini API")
                return {
                    "text_lines": text_lines,
                    "line_metadata": [
                        {
                            "text": line,
                            "confidence": 0.85,
                            "prominence": max(len(line), 1) * 100,
                            "variant": "gemini",
                            "y_center": float(index),
                            "x_min": 0,
                        }
                        for index, line in enumerate(text_lines)
                    ],
                    "quality_score": float(sum(len(line) for line in text_lines)),
                    "error": None,
                }

            logger.warning("No text extracted from Gemini API")
            return {
                "text_lines": [],
                "line_metadata": [],
                "quality_score": 0.0,
                "error": "Gemini returned no text for this image.",
            }

        except Exception as exc:
            logger.error(f"Gemini OCR failed for {image_path}: {exc}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "text_lines": [],
                "line_metadata": [],
                "quality_score": 0.0,
                "error": str(exc),
            }
