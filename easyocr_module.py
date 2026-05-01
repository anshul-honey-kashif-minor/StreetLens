import os
import re
import threading
from typing import Dict, List, Tuple

import cv2
import numpy as np
from dotenv import load_dotenv

from utils import logger

try:
    import easyocr
except ImportError:  # pragma: no cover - optional runtime dependency
    easyocr = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class EasyOCRProcessor:
    def __init__(self):
        self.languages = [
            language.strip()
            for language in os.getenv("EASYOCR_LANGUAGES", "en,hi").split(",")
            if language.strip()
        ]
        self.gpu_enabled = os.getenv("EASYOCR_GPU", "0").strip().lower() in {"1", "true", "yes"}
        self.reader = None
        self._reader_lock = threading.Lock()

    def _get_reader(self):
        if easyocr is None:
            raise RuntimeError(
                "EasyOCR is not installed. Install it in the active Python environment first."
            )

        if self.reader is None:
            with self._reader_lock:
                if self.reader is None:
                    logger.info(
                        "Initializing EasyOCR reader with languages=%s gpu=%s",
                        self.languages,
                        self.gpu_enabled,
                    )
                    self.reader = easyocr.Reader(self.languages, gpu=self.gpu_enabled)
        return self.reader

    def _load_image(self, image_path):
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Could not load image at {image_path}")
        return image

    def _resize_for_ocr(self, image):
        height, width = image.shape[:2]
        longest_side = max(height, width)

        if longest_side < 1200:
            scale = 1600 / float(longest_side)
            return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        if longest_side > 2400:
            scale = 2400 / float(longest_side)
            return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        return image

    def _build_variants(self, image):
        resized = self._resize_for_ocr(image)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        gray_scale = 1.0
        if min(gray.shape[:2]) < 1400:
            gray_scale = 1.5
            gray = cv2.resize(gray, None, fx=gray_scale, fy=gray_scale, interpolation=cv2.INTER_CUBIC)

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
        denoised = cv2.fastNlMeansDenoising(clahe, None, 12, 7, 21)

        sharpened = cv2.addWeighted(
            denoised,
            1.35,
            cv2.GaussianBlur(denoised, (0, 0), 1.0),
            -0.35,
            0,
        )

        return {
            "color": (resized, 1.0, 1.0),
            "gray": (gray, gray_scale, gray_scale),
            "clahe": (clahe, gray_scale, gray_scale),
            "denoised": (denoised, gray_scale, gray_scale),
            "sharpened": (sharpened, gray_scale, gray_scale),
        }

    def _read_variant(self, reader, image_variant):
        return reader.readtext(
            image_variant,
            detail=1,
            paragraph=False,
            decoder="greedy",
            contrast_ths=0.05,
            adjust_contrast=0.7,
            text_threshold=0.45,
            low_text=0.2,
            link_threshold=0.25,
            canvas_size=2048,
            mag_ratio=1.2,
            min_size=10,
            slope_ths=0.2,
            ycenter_ths=0.5,
            height_ths=0.5,
            width_ths=0.5,
            add_margin=0.05,
            batch_size=1,
        )

    def _clean_text(self, text):
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        text = text.strip(".,;:-_•|")
        return text

    def _group_to_lines(self, detections, variant_name, image_height):
        if not detections:
            return []

        detections.sort(key=lambda item: (item["y_center"], item["x_min"]))
        groups = []

        for detection in detections:
            assigned_group = None
            for group in groups:
                tolerance = max(group["avg_height"], detection["height"]) * 0.40
                if abs(detection["y_center"] - group["y_center"]) <= tolerance:
                    assigned_group = group
                    break

            if assigned_group is None:
                assigned_group = {
                    "items": [],
                    "y_center": detection["y_center"],
                    "avg_height": detection["height"],
                }
                groups.append(assigned_group)

            assigned_group["items"].append(detection)
            assigned_group["items"].sort(key=lambda item: item["x_min"])
            assigned_group["y_center"] = sum(item["y_center"] for item in assigned_group["items"]) / len(
                assigned_group["items"]
            )
            assigned_group["avg_height"] = sum(item["height"] for item in assigned_group["items"]) / len(
                assigned_group["items"]
            )

        line_metadata = []
        for group in groups:
            items = group["items"]
            text = self._clean_text(" ".join(item["text"] for item in items))
            if len(text) < 2:
                continue

            confidences = [max(item["confidence"], 0.0) for item in items]
            confidence = sum(confidences) / len(confidences) if confidences else 0.0
            x_min = min(item["x_min"] for item in items)
            y_min = min(item["y_min"] for item in items)
            x_max = max(item["x_max"] for item in items)
            y_max = max(item["y_max"] for item in items)

            line_metadata.append(
                {
                    "text": text,
                    "confidence": round(confidence, 4),
                    "bbox": [int(x_min), int(y_min), int(x_max), int(y_max)],
                    "prominence": int((x_max - x_min) * (y_max - y_min)),
                    "height": int(y_max - y_min),
                    "y_center": float((y_min + y_max) / 2),
                    "x_min": int(x_min),
                    "top_ratio": float((y_min + y_max) / 2 / max(image_height, 1)),
                    "variant": variant_name,
                }
            )

        line_metadata.sort(key=lambda item: (item["y_center"], item["x_min"]))
        return line_metadata

    def _line_quality_score(self, line):
        text = line["text"]
        confidence = max(line.get("confidence", 0.0), 0.0)
        prominence = max(line.get("prominence", 0), 0)
        top_ratio = min(max(line.get("top_ratio", 1.0), 0.0), 1.0)

        alpha_count = sum(char.isalpha() for char in text)
        digit_count = sum(char.isdigit() for char in text)
        upper_alpha_count = sum(char.isupper() for char in text if char.isalpha())
        upper_ratio = upper_alpha_count / max(alpha_count, 1)

        score = 0.0
        score += confidence * 25.0
        score += min(prominence / 10000.0, 10.0)
        score += (1.0 - top_ratio) * 8.0
        score += min(len(text) / 10.0, 4.0)
        score += min(alpha_count * 0.12, 4.0)
        score += min(digit_count * 0.20, 4.0)

        lowered = text.lower()
        if any(
            token in lowered
            for token in (
                "shop",
                "store",
                "market",
                "salon",
                "clinic",
                "consultants",
                "real estate",
                "restaurant",
                "services",
                "service",
                "hotel",
                "pharmacy",
                "tailor",
                "building",
                "builders",
            )
        ):
            score += 3.0

        if re.search(r"\d{6,}", text):
            score += 4.0

        if upper_ratio >= 0.7:
            score += 2.5

        if len(text) <= 2:
            score -= 2.0

        return score

    def _variant_score(self, line_metadata):
        if not line_metadata:
            return 0.0
        ranked = sorted(
            (self._line_quality_score(line) for line in line_metadata),
            reverse=True,
        )
        top = ranked[:6]
        return round(sum(top) + (top[0] * 0.5 if top else 0.0), 4)

    def _iou(self, box_a, box_b):
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)

        union = area_a + area_b - inter_area
        if union <= 0:
            return 0.0
        return inter_area / union

    def _same_region(self, line_a, line_b):
        box_a = line_a["bbox"]
        box_b = line_b["bbox"]

        if self._iou(box_a, box_b) >= 0.30:
            return True

        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        acx = (ax1 + ax2) / 2.0
        acy = (ay1 + ay2) / 2.0
        bcx = (bx1 + bx2) / 2.0
        bcy = (by1 + by2) / 2.0

        aw = max(1.0, ax2 - ax1)
        ah = max(1.0, ay2 - ay1)
        bw = max(1.0, bx2 - bx1)
        bh = max(1.0, by2 - by1)

        x_limit = max(aw, bw) * 0.55
        y_limit = max(ah, bh) * 0.55

        return abs(acx - bcx) <= x_limit and abs(acy - bcy) <= y_limit

    def _combine_variants(self, variant_payloads):
        if not variant_payloads:
            return []

        clusters = []

        for payload in variant_payloads:
            for line in payload["line_metadata"]:
                best_cluster = None
                for cluster in clusters:
                    if self._same_region(cluster["line"], line):
                        best_cluster = cluster
                        break

                line_score = self._line_quality_score(line)
                candidate = dict(line)
                candidate["score"] = line_score

                if best_cluster is None:
                    clusters.append({"line": candidate})
                    continue

                current_score = best_cluster["line"].get("score", self._line_quality_score(best_cluster["line"]))
                current_conf = best_cluster["line"].get("confidence", 0.0)
                new_conf = candidate.get("confidence", 0.0)

                if (line_score > current_score + 0.5) or (new_conf > current_conf + 0.08):
                    best_cluster["line"] = candidate

        merged_lines = [cluster["line"] for cluster in clusters]
        merged_lines.sort(key=lambda item: (item["y_center"], item["x_min"]))
        return merged_lines

    def extract_text(self, image_path):
        try:
            reader = self._get_reader()
            image = self._load_image(image_path)
            variants = self._build_variants(image)

            variant_payloads = []
            for variant_name, (variant_image, scale_x, scale_y) in variants.items():
                raw_results = self._read_variant(reader, variant_image)
                detections = []

                for bbox, text, confidence in raw_results:
                    cleaned_text = self._clean_text(text)
                    if len(cleaned_text) < 2:
                        continue

                    points = np.array(bbox, dtype=np.float32)
                    x_values = points[:, 0] / float(scale_x)
                    y_values = points[:, 1] / float(scale_y)

                    x_min = float(np.min(x_values))
                    x_max = float(np.max(x_values))
                    y_min = float(np.min(y_values))
                    y_max = float(np.max(y_values))

                    detections.append(
                        {
                            "text": cleaned_text,
                            "confidence": float(confidence or 0.0),
                            "x_min": x_min,
                            "x_max": x_max,
                            "y_min": y_min,
                            "y_max": y_max,
                            "y_center": float((y_min + y_max) / 2.0),
                            "height": float(y_max - y_min),
                        }
                    )

                base_height = image.shape[0]
                line_metadata = self._group_to_lines(detections, variant_name, base_height)
                variant_payloads.append(
                    {
                        "variant": variant_name,
                        "line_metadata": line_metadata,
                        "score": self._variant_score(line_metadata),
                    }
                )

            combined_lines = self._combine_variants(variant_payloads)
            text_lines = [line["text"] for line in combined_lines]
            quality_score = self._variant_score(combined_lines)

            if not text_lines:
                return {
                    "text_lines": [],
                    "line_metadata": [],
                    "quality_score": 0.0,
                    "error": "EasyOCR could not detect readable text.",
                }

            return {
                "text_lines": text_lines,
                "line_metadata": combined_lines,
                "quality_score": quality_score,
                "error": None,
            }
        except Exception as exc:  # pragma: no cover - runtime dependent path
            logger.error(f"EasyOCR failed for {image_path}: {exc}")
            return {
                "text_lines": [],
                "line_metadata": [],
                "quality_score": 0.0,
                "error": str(exc),
            }