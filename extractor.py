import re
from utils import logger

class InformationExtractor:
    def __init__(self):
        # Compiled regex patterns
        self.email_pattern = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
        self.gst_pattern = re.compile(r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b')
        self.website_pattern = re.compile(r'\b(?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')
        self.time_pattern = re.compile(r'\b(?:1[0-2]|0?[1-9])(?::[0-5][0-9])?\s?(?:AM|PM|am|pm)\b')
        
        self.shop_keywords = ['store', 'traders', 'medical', 'electronics', 'mart', 'bakery', 'salon', 'enterprises', 'bhojnalay',]
        self.address_keywords = [
            'road','street','sector','nagar','colony','marg',
            'near','opp','market','complex','building','lane',
            'block','chowk','shop','no'
        ]
    def extract_fields(self, text_lines):

        clean_lines = []
        for line in text_lines:
            line = line.replace(")", "")
            line = line.replace("_", "")
            line = line.strip()
            clean_lines.append(line)

        data = {
            "shop_name": "NA",
            "phone_number": "NA",
            "email": "NA",
            "address": "NA",
            "gst_number": "NA",
            "website": "NA",
            "opening_time": "NA",
            "closing_time": "NA"
        }

        full_text = " ".join(clean_lines)
        times_found = []

        numbers = re.findall(r'\+?\d[\d\s\-]{8,14}\d', full_text)

        phones = []

        for num in numbers:
            logger.info(f"numbers identified : {num}")
            digits = re.sub(r'\D', '', num)

            if len(digits) > 8 & len(digits) < 12:
                phones.append(digits)

        data["phone_number"] = phones if phones else "NA"
            
        if match := self.email_pattern.search(full_text):
            data["email"] = match.group()
            
        if match := self.gst_pattern.search(full_text):
            data["gst_number"] = match.group()
            
        if match := self.website_pattern.search(full_text):
            data["website"] = match.group()
            
        times_found = self.time_pattern.findall(full_text)
        if len(times_found) >= 1:
            data["opening_time"] = times_found[0].upper()
        if len(times_found) >= 2:
            data["closing_time"] = times_found[1].upper()


        for line in clean_lines :
            line_lower = line.lower()
            
            if data["address"] == "NA" and any(kw in line_lower for kw in self.address_keywords):
                data["address"] = line
                
            if data["shop_name"] == "NA" and any(kw in line_lower for kw in self.shop_keywords):
                data["shop_name"] = line
        

        # Fallback for Shop Name: If no keyword matched, assume the first line is the shop name
        if data["shop_name"] == "NA" and clean_lines:
            data["shop_name"] = clean_lines[0]

        return data