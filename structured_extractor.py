import os
import re
from dotenv import load_dotenv
from utils import logger

try:
    import google.genai as genai
except ImportError:
    genai = None

load_dotenv()


class InformationExtractor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if genai and api_key else None
        self.model = "gemini-2.5-flash-lite"

        # patterns
        self.phone_pattern = re.compile(r"\b[6-9]\d{9}\b")
        self.landline_pattern = re.compile(r"\b0\d{2,4}[-\s]?\d{5,8}\b")
        self.gst_pattern = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b")
        self.email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        self.website_pattern = re.compile(r"(?:https?://|www\.)\S+")

        # Coordinate patterns for geotagged text overlays
        # Matches: "28.6139° N" or "77.2090° E" or "28.6139°N"
        self.coord_degree_pattern = re.compile(
            r"(-?\d{1,3}\.\d{2,8})\s*°?\s*([NSEW])", re.IGNORECASE
        )
        # Matches: "Lat: 28.6139" or "Latitude: 28.6139" or "lat 28.6139"
        self.lat_label_pattern = re.compile(
            r"(?:lat(?:itude)?)[:\s]+(-?\d{1,3}\.\d{2,8})", re.IGNORECASE
        )
        # Matches: "Lon: 77.2090" or "Long: 77.2090" or "Longitude: 77.2090"
        self.lng_label_pattern = re.compile(
            r"(?:lon(?:g(?:itude)?)?)[:\s]+(-?\d{1,3}\.\d{2,8})", re.IGNORECASE
        )

        # scoring hints
        self.business_keywords = [
            "system", "systems", "enterprise", "enterprises", "traders",
            "copier", "digital", "graphics", "solutions", "center", "centre"
        ]

        self.service_keywords = [
            "photostat", "print", "printing", "binding", "lamination",
            "xerox", "b/w", "color", "colour", "service"
        ]

        self.address_keywords = [
            "road", "street", "sector", "nagar", "colony", "market",
            "complex", "near", "opp", "noida", "delhi", "shop"
        ]

    # ================= MAIN =================
    def extract_fields(self, text_lines, line_metadata=None, engine="easyocr"):
        clean_lines = self._clean_lines(text_lines)
        full_text = " ".join(clean_lines)

        lat, lng = self._extract_coordinates(full_text)

        return {
            "shop_name": self._extract_shop_name(clean_lines, line_metadata, engine),
            "phone_number": self._extract_phones(full_text),
            "email": self._extract_email(full_text),
            "address": self._extract_address(clean_lines),
            "gst_number": self._extract_gst(full_text),
            "website": self._extract_website(full_text),
            "latitude": lat,
            "longitude": lng,
        }

    # ================= CLEAN =================
    def _clean_lines(self, lines):
        out = []
        for l in lines:
            l = re.sub(r"\s+", " ", str(l)).strip(" |,;")
            if len(l) > 1:
                out.append(l)
        return out

    # ================= SHOP NAME =================
    def _extract_shop_name(self, lines, metadata, engine):
        # try Gemini if available
        if engine == "gemini" and self.client:
            name = self._gemini_shop_name(lines)
            if name != "NA":
                return name

        return self._local_shop_name(lines, metadata)

    def _local_shop_name(self, lines, metadata):
        if not lines:
            return "NA"

        meta_map = {
            self._norm(m.get("text", "")): m for m in (metadata or [])
        }

        candidates = []

        for i, line in enumerate(lines[:8]):
            norm = self._norm(line)
            meta = meta_map.get(norm, {})

            prominence = meta.get("prominence", 0)
            confidence = meta.get("confidence", 0.6)
            top_ratio = meta.get("top_ratio", 0.5)

            alpha = sum(c.isalpha() for c in line)
            upper = sum(c.isupper() for c in line if c.isalpha())
            upper_ratio = upper / max(alpha, 1)

            score = 0
            score += confidence * 20
            score += min(prominence / 8000, 15)
            score += (1 - top_ratio) * 12
            score += upper_ratio * 10
            score += max(0, 5 - i)  # top bias
            score += min(len(line), 30) / 5

            lowered = line.lower()

            if any(k in lowered for k in self.business_keywords):
                score += 6

            if any(k in lowered for k in self.service_keywords):
                score -= 8

            if any(k in lowered for k in self.address_keywords):
                score -= 6

            candidates.append((score, line))

        best = max(candidates, key=lambda x: x[0])[1]

        # final cleanup
        best = re.sub(r"[^A-Za-z0-9\s&]", "", best)
        return best.strip()

    # ================= PHONES =================
    def _extract_phones(self, text):
        phones = set()

        for match in self.phone_pattern.findall(text):
            phones.add(match)

        for match in self.landline_pattern.findall(text):
            digits = re.sub(r"\D", "", match)
            if len(digits) >= 10:
                phones.add(digits[-10:])

        return list(phones)

    # ================= EMAIL =================
    def _extract_email(self, text):
        m = self.email_pattern.search(text)
        return m.group() if m else "NA"

    # ================= WEBSITE =================
    def _extract_website(self, text):
        m = self.website_pattern.search(text)
        return m.group() if m else "NA"

    # ================= GST =================
    def _extract_gst(self, text):
        m = self.gst_pattern.search(text.upper())
        return m.group() if m else "NA"

    # ================= ADDRESS =================
    def _extract_address(self, lines):
        for i, line in enumerate(lines):
            low = line.lower()

            if any(k in low for k in self.address_keywords):
                address = [line]

                # extend next lines
                for nxt in lines[i + 1:i + 3]:
                    if any(k in nxt.lower() for k in self.address_keywords):
                        address.append(nxt)
                    else:
                        break

                return ", ".join(address)

        return "NA"

    # ================= GEMINI =================
    def _gemini_shop_name(self, lines):
        try:
            text = "\n".join(lines)
            prompt = f"""
Extract ONLY the main business/shop name from this text.
Ignore services, phone numbers, GST, address.

{text}
"""
            response = self.client.models.generate_content(
                model=self.model,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )

            return response.text.strip() if response and response.text else "NA"

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "NA"

    # ================= COORDINATES =================
    def _extract_coordinates(self, text):
        """Extract latitude and longitude from geotagged text on the image."""
        lat, lng = None, None

        # Method 1: Labeled patterns — "Lat: 28.6139" / "Long: 77.2090"
        lat_match = self.lat_label_pattern.search(text)
        lng_match = self.lng_label_pattern.search(text)
        if lat_match:
            lat = float(lat_match.group(1))
        if lng_match:
            lng = float(lng_match.group(1))
        if lat is not None and lng is not None:
            return round(lat, 6), round(lng, 6)

        # Method 2: Degree+direction patterns — "28.6139° N, 77.2090° E"
        coord_matches = self.coord_degree_pattern.findall(text)
        if len(coord_matches) >= 2:
            for value_str, direction in coord_matches:
                value = float(value_str)
                d = direction.upper()
                if d in ("N", "S"):
                    lat = value if d == "N" else -value
                elif d in ("E", "W"):
                    lng = value if d == "E" else -value
            if lat is not None and lng is not None:
                return round(lat, 6), round(lng, 6)

        # Method 3: Plain decimal pair — two numbers that look like coordinates
        # e.g. "28.613900, 77.209000" or "28.613900 77.209000"
        pair_pattern = re.compile(
            r"(-?\d{1,3}\.\d{4,8})\s*[,\s]+\s*(-?\d{1,3}\.\d{4,8})"
        )
        pair_match = pair_pattern.search(text)
        if pair_match:
            val1 = float(pair_match.group(1))
            val2 = float(pair_match.group(2))
            # Heuristic: latitude is typically smaller than longitude for most regions
            if -90 <= val1 <= 90 and -180 <= val2 <= 180:
                return round(val1, 6), round(val2, 6)

        return None, None

    # ================= UTILS =================
    def _norm(self, text):
        return "".join(c.lower() for c in text if c.isalnum())