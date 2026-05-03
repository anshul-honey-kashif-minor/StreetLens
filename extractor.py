import google.genai as genai
from utils import logger
import os
from dotenv import load_dotenv
import re

load_dotenv()

class InformationExtractor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-2.5-flash-lite'
        
        self.email_pattern = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
        self.phone_pattern = re.compile(r'\b[6-9]\d{9}\b')
        self.gst_pattern = re.compile(r'\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b')
        self.website_pattern = re.compile(r'\b(?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')
        
        self.address_keywords = [
            'road','street','sector','scheme','nagar','colony','marg','near','opp',
            'market','complex','building','lane','block','chowk','plot','house','no',
            'apt','apartment','floor','area','complex','city','town','village','district','state','pincode','pin code','market','bazaar','square','junction','crossing','circle','park','garden',
        ]
        self.non_address_keywords = [
            'gst', 'gstin', 'gst no', 'gst number', 'phone', 'mobile', 'email',
            'website', 'www.', 'http'
        ]
        self.address_keywords = [kw for kw in self.address_keywords if kw != 'no']

    def extract_fields(self, text_lines):
        clean_lines = []
        for line in text_lines:
            line = line.replace(")", "").replace("_", "").strip()
            if line and len(line) > 1:
                clean_lines.append(line)

        data = {
            "shop_name": "NA",
            "phone_number": [],
            "email": "NA",
            "address": "NA",
            "gst_number": "NA",
            "website": "NA"
        }

        full_text = " ".join(clean_lines)
        upper_text = full_text.upper()

        # -------- PHONE EXTRACTION --------
        phones = set()
        pattern1 = re.findall(r'\b[6-9]\d{9}\b', full_text)
        pattern2 = re.findall(r'\b[6-9]\d{3,4}[\-\s]\d{5,6}\b', full_text)
        pattern3 = re.findall(r'\b0\d{2,3}[\-\s]?\d{6,8}\b', full_text)
        
        all_matches = pattern1 + pattern2 + pattern3
        for num in all_matches:
            digits = re.sub(r'\D', '', num)
            if len(digits) == 10:
                phones.add(digits)
            elif len(digits) > 10:
                phones.add(digits[-10:])
        
        data["phone_number"] = sorted(list(phones))

        # -------- EMAIL --------
        match = self.email_pattern.search(full_text)
        if match:
            data["email"] = match.group()

        # -------- GST --------
        data["gst_number"] = self._extract_gst_number(clean_lines, upper_text)

        # -------- WEBSITE --------
        match = self.website_pattern.search(full_text)
        if match:
            data["website"] = match.group()

        # -------- SHOP NAME: Use Gemini --------
        data["shop_name"] = self._extract_shop_name_with_gemini(text_lines)

        # -------- ADDRESS --------
        for line in clean_lines:
            line_lower = line.lower()
            if self._is_non_address_line(line):
                continue
            if any(re.search(rf'\b{re.escape(kw)}\b', line_lower) for kw in self.address_keywords):
                data["address"] = line
                break

        return data

    def _extract_gst_number(self, clean_lines, upper_text):
        """Extract GSTIN even when OCR inserts spaces, hyphens, or labels."""
        for line in clean_lines:
            line_upper = line.upper()
            match = self.gst_pattern.search(line_upper)
            if match:
                return match.group()

            if 'GST' in line_upper:
                compact_line = re.sub(r'[^A-Z0-9]', '', line_upper)
                match = self.gst_pattern.search(compact_line)
                if match:
                    return match.group()

        compact_text = re.sub(r'[^A-Z0-9]', '', upper_text)
        match = self.gst_pattern.search(compact_text)
        if match:
            return match.group()

        return "NA"

    def _is_non_address_line(self, line):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in self.non_address_keywords):
            return True

        if self.gst_pattern.search(line.upper()):
            return True

        if self.email_pattern.search(line) or self.website_pattern.search(line):
            return True

        digits = re.sub(r'\D', '', line)
        return len(digits) >= 10 and bool(self.phone_pattern.search(digits[-10:]))

    def _extract_shop_name_with_gemini(self, text_lines):
        """Use Gemini to identify the actual shop/business name"""
        try:
            full_text = "\n".join(text_lines)
            
            prompt = f"""From this shop banner text, identify and return ONLY the main business/shop name.
The shop name is the primary business identifier (company name), NOT brands, products, or services listed.

For example:
- If text says "ABC Auto Parts - Distributor of BENTEX, MIECO, etc." → Answer: "ABC Auto Parts"
- If text says "LAKSHMI SALES CORPORATION" → Answer: "LAKSHMI SALES CORPORATION"  
- If text says "XYZ ENTERPRISES - Dealers in motors, starters, etc." → Answer: "XYZ ENTERPRISES"

Banner text:
{full_text}

Return ONLY the shop name, nothing else. If unclear, return the most prominent line."""

            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ]
            )

            if response and response.text:
                shop_name = response.text.strip()
                logger.info(f"Gemini extracted shop name: {shop_name}")
                return shop_name
            
            logger.warning("Gemini shop name extraction failed")
            return "NA"

        except Exception as e:
            logger.error(f"Gemini shop name extraction error: {e}")
            return "NA"
