from utils import logger
from ocr_module import OCRProcessor
from extractor import InformationExtractor
from classifier import ShopClassifier
import os

ocr_processor = OCRProcessor()
extractor = InformationExtractor()
classifier = ShopClassifier()

valid_extensions = {'.jpg', '.jpeg', '.png'}

def process_image(image_path) :
    logger.info(f"Processing: {os.path.basename(image_path)}")
    
    text_lines = ocr_processor.extract_text(image_path)
    logger.info(f"The text identified is: {text_lines}")

    extracted_data = extractor.extract_fields(text_lines)

    category = classifier.classify(text_lines)

    final_data = {
        "image_name": os.path.basename(image_path),
        "shop_name": extracted_data["shop_name"],
        "phone_number": extracted_data["phone_number"],
        "email": extracted_data["email"],
        "address": extracted_data["address"],
        "category": category,
        "gst_number": extracted_data["gst_number"],
        "website": extracted_data["website"],
        "opening_time": extracted_data["opening_time"],
        "closing_time": extracted_data["closing_time"]
    }

    return final_data
    