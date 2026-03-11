import argparse
from pathlib import Path
from utils import logger, save_outputs
from ocr_module import OCRProcessor
from extractor import InformationExtractor
from classifier import ShopClassifier

def main():
    parser = argparse.ArgumentParser(description="Automated Shop Signboard Information Extraction System")
    parser.add_argument("--input_folder", type=str, required=True, help="Path to the folder containing shop images.")
    parser.add_argument("--output_folder", type=str, default="outputs", help="Folder to save JSON and CSV outputs.")
    args = parser.parse_args()

    input_dir = Path(args.input_folder)
    
    if not input_dir.exists() or not input_dir.is_dir():
        logger.error(f"Input directory does not exist: {input_dir}")
        return

    # Initialize modules
    ocr_processor = OCRProcessor()
    extractor = InformationExtractor()
    classifier = ShopClassifier()

    results = []
    valid_extensions = {'.jpg', '.jpeg', '.png'}

    # Process images loop
    for img_path in input_dir.iterdir():
        if img_path.suffix.lower() not in valid_extensions:
            continue

        logger.info(f"Processing: {img_path.name}")
        
        try:
            # 1. OCR Extraction
            text_lines = ocr_processor.extract_text(img_path)
            
            if not text_lines:
                logger.warning(f"No text found or OCR failed for {img_path.name}")
                continue
                
            # 2. Field Extraction
            extracted_data = extractor.extract_fields(text_lines)
            
            # 3. Classification
            category = classifier.classify(text_lines)
            
            # 4. Assemble final dictionary
            final_data = {
                "image_name": img_path.name,
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
            
            results.append(final_data)
            
        except Exception as e:
            logger.error(f"Error processing {img_path.name}: {e}")

    # Save Results
    save_outputs(results, args.output_folder)
    logger.info("Processing complete.")

if __name__ == "__main__":
    main()