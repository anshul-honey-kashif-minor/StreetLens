import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

from classifier import ShopClassifier
from easyocr_module import EasyOCRProcessor
from ocr_module import OCRProcessor
from structured_extractor import InformationExtractor
from utils import logger

load_dotenv()

gemini_ocr_processor = OCRProcessor()
easyocr_processor = EasyOCRProcessor()
extractor = InformationExtractor()
classifier = ShopClassifier()

ENGINE_LABELS = {
    "gemini": "Gemini Vision",
    "easyocr": "EasyOCR",
}


def _build_miscellaneous(extracted_data):
    miscellaneous = {}
    if extracted_data["email"] != "NA":
        miscellaneous["email"] = extracted_data["email"]
    if extracted_data["website"] != "NA":
        miscellaneous["website"] = extracted_data["website"]
    return miscellaneous


# ✅ FIXED SCORING (shop-name aware)
def _score_engine_result(result):
    if result["status"] != "success":
        return -1

    primary_fields = [
        result.get("shop_name"),
        result.get("address"),
        result.get("gst_number"),
    ]

    populated_field_score = sum(
        1 for value in primary_fields if value and value != ""
    ) * 10

    phone_score = len(result.get("phone_number", [])) * 4
    text_score = min(len(result.get("extracted_text", "")), 200) / 20
    quality_score = float(result.get("quality_score", 0.0)) / 25

    # 🔥 NEW: reward good shop name
    shop_name_bonus = 0
    if result.get("shop_name"):
        shop_name_bonus = min(len(result["shop_name"]), 30) / 3

    return populated_field_score + phone_score + text_score + quality_score + shop_name_bonus


def _process_with_engine(engine_key, processor, image_path):
    started_at = time.perf_counter()
    ocr_payload = processor.extract_text(image_path)
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)

    text_lines = ocr_payload.get("text_lines", [])
    line_metadata = ocr_payload.get("line_metadata", [])
    error = ocr_payload.get("error")

    if not text_lines:
        return {
            "engine_key": engine_key,
            "display_name": ENGINE_LABELS[engine_key],
            "status": "error",
            "error": error or f"{ENGINE_LABELS[engine_key]} returned no readable text.",
            "shop_name": "",
            "phone_number": [],
            "category": "",
            "address": "",
            "gst_number": "",
            "miscellaneous_data": {},
            "extracted_text": "",
            "text_lines": [],
            "line_count": 0,
            "quality_score": float(ocr_payload.get("quality_score", 0.0)),
            "timing_ms": elapsed_ms,
        }

    # ✅ Extraction (WITH metadata)
    extracted_data = extractor.extract_fields(
        text_lines,
        line_metadata=line_metadata,
        engine=engine_key,
    )

    # ✅ FIXED classification (use clean structured input)
    classification_input = [
    extracted_data.get("shop_name", ""),
    " ".join(text_lines[:5])  # only top lines (actual banner content)
]
    category = classifier.classify(classification_input)

    miscellaneous = _build_miscellaneous(extracted_data)

    return {
        "engine_key": engine_key,
        "display_name": ENGINE_LABELS[engine_key],
        "status": "success",
        "error": "",
        "shop_name": extracted_data["shop_name"] if extracted_data["shop_name"] != "NA" else "",
        "phone_number": extracted_data["phone_number"],
        "category": category if category != "General Store" else "",  # ✅ FIXED
        "address": extracted_data["address"] if extracted_data["address"] != "NA" else "",
        "gst_number": extracted_data["gst_number"] if extracted_data["gst_number"] != "NA" else "",
        "miscellaneous_data": miscellaneous,
        "extracted_text": "\n".join(text_lines),
        "text_lines": text_lines,
        "line_count": len(text_lines),
        "quality_score": float(ocr_payload.get("quality_score", 0.0)),
        "timing_ms": elapsed_ms,
    }


def process_image(image_path):
    logger.info(f"Processing: {os.path.basename(image_path)}")

    processors = {
        "gemini": gemini_ocr_processor,
        "easyocr": easyocr_processor,
    }

    comparison = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_map = {
            executor.submit(_process_with_engine, engine_key, processor, image_path): engine_key
            for engine_key, processor in processors.items()
        }

        for future in as_completed(future_map):
            engine_key = future_map[future]
            try:
                comparison[engine_key] = future.result()
            except Exception as exc:
                logger.error(f"{ENGINE_LABELS[engine_key]} crashed: {exc}")
                comparison[engine_key] = {
                    "engine_key": engine_key,
                    "display_name": ENGINE_LABELS[engine_key],
                    "status": "error",
                    "error": str(exc),
                    "shop_name": "",
                    "phone_number": [],
                    "category": "",
                    "address": "",
                    "gst_number": "",
                    "miscellaneous_data": {},
                    "extracted_text": "",
                    "text_lines": [],
                    "line_count": 0,
                    "quality_score": 0.0,
                    "timing_ms": 0.0,
                }

    # keep order consistent
    comparison = {k: comparison[k] for k in processors}

    successful = [k for k, v in comparison.items() if v["status"] == "success"]

    if not successful:
        return {
            "image_name": os.path.basename(image_path),
            "error": "Both OCR engines failed.",
            "selected_engine": "",
            "comparison": comparison,
            "shop_name": "",
            "phone_number": [],
            "category": "",
            "address": "",
            "gst_number": "",
            "miscellaneous_data": {},
            "extracted_text": "",
        }

    # ✅ best engine selection (fixed scoring)
    selected_engine = max(successful, key=lambda k: _score_engine_result(comparison[k]))
    selected = comparison[selected_engine]

    return {
        "image_name": os.path.basename(image_path),
        "selected_engine": selected_engine,
        "comparison": comparison,
        "shop_name": selected["shop_name"],
        "phone_number": selected["phone_number"],
        "category": selected["category"],
        "address": selected["address"],
        "gst_number": selected["gst_number"],
        "miscellaneous_data": selected["miscellaneous_data"],
        "miscellaneous": selected["miscellaneous_data"],
        "extracted_text": selected["extracted_text"],
    }