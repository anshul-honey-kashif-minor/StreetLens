from utils import logger
import os
import re

try:
    import google.genai as genai
except ImportError:
    genai = None

from dotenv import load_dotenv
load_dotenv()

class ShopClassifier:
    def __init__(self):
        logger.info("Initializing Shop Classifier...")
        
        # Enhanced category keywords - more specific
        self.category_map = {
            "electrical": [
                "electric", "electrical", "electric works", "electrical works",
                "electricals", "electrician", "wiring", "wire", "cable",
                "switch", "switchgear", "lighting", "led", "fan", "motor winding",
                "inverter", "battery", "mcb", "distribution board"
            ],
            "real_estate": [
                "real estate", "sale", "purchase", "renting", "rental",
                "residential", "commercial", "industrial", "group housing",
                "property", "land", "plot", "apartment", "flat", "house",
                "builder", "developer", "estate", "realty", "broker",
                "housing", "construction", "project", "societies"
            ],
            "medical": [
                "medical", "pharmacy", "clinic", "chemist", "drugs", "hospital",
                "doctor", "health", "medicine", "diagnostic", "lab", "ayurveda",
                "homeopathy", "physiotherapy", "dental", "optician", "nursing",
                "nursing home", "healthcare", "pathology", "x-ray", "scan"
            ],
            "restaurant": [
                "restaurant", "hotel", "cafe", "bhojanalaya", "dhaba", "food",
                "kitchen", "bar", "pub", "diner", "eatery", "pizzeria",
                "fast food", "chinese", "indian", "continental", "snacks", "juice",
                "bakery cafe", "coffee shop", "tea stall", "canteen"
            ],
            "electronics": [
                "electronics", "mobile", "computer", "gadgets", "appliances",
                "phone", "laptop", "tablet", "camera", "tv", "refrigerator",
                "washing machine", "microwave", "console", "gaming", "store",
                "repair", "service center", "showroom"
            ],
            "bakery": [
                "bakery", "cake", "sweets", "confectionery", "bread", "pastry",
                "donut", "cookie", "biscuit", "dessert", "ice cream", "sweet",
                "bakehouse", "sweet shop", "panjabi", "mithai"
            ],
            "salon": [
                "salon", "beauty", "parlour", "hair", "spa", "unisex", "barber",
                "haircut", "massage", "cosmetics", "makeup", "threading", "waxing",
                "beauty parlor", "hair salon", "wellness"
            ],
            "clothing": [
                "clothing", "apparel", "garments", "dress", "boutique",
                "mens wear", "womens wear", "kids wear", "fashion", "footwear",
                "saree", "suit", "shirt", "fabric", "tailor", "store"
            ],
            "grocery": [
                "grocery", "supermarket", "mart", "store", "provision",
                "fruits", "vegetables", "dairy", "general store", "shop",
                "kirana", "bazaar", "market"
            ],
            "auto_parts": [
                "auto parts", "motor starter", "starter", "panel board",
                "auto start", "control panel", "capacitor", "mex", "mieco",
                "bentex", "keltron", "sunny", "jayki", "neuton", "supplier",
                "dealer", "distributor", "spares", "ignition"
                 ],
            "jewelry": [
                "jewelry", "jewellery", "jeweler", "goldsmith", "ornament",
                "diamond", "gold", "silver", "precious", "store", "shop",
                "sona", "sonaar"
            ],
            "hardware": [
                "hardware", "tools", "equipment", "plumbing", "electrical",
                "paint", "cement", "steel", "iron", "bolt", "nut",
                "construction materials", "supplies"
            ],
            "automotive": [
                "automotive", "car", "bike", "motorcycle", "vehicle", "garage","service", "repair", "showroom", "dealer", "mechanic"
            ],
            "education": [
                "school", "college", "university", "coaching", "classes",
                "academy", "institute", "center", "tutorial", "education",
                "training", "course"
            ],
            "banking": [
                "bank", "banking", "atm", "branch", "finance", "loan",
                "credit", "deposit", "insurance", "financial", "services"
            ],
            "entertainment": [
                "cinema", "theatre", "theater", "movie", "films", "multiplex",
                "gaming", "arcade", "games", "club", "nightclub", "lounge"
            ],
            "fitness": [
                "gym", "fitness", "yoga", "wellness", "sports", "workout",
                "trainer", "aerobics", "zumba", "dance", "health club"
            ],
            "beauty_products": [
                "cosmetics", "skincare", "makeup", "beauty products", "perfume",
                "fragrance", "shampoo", "soap", "cream", "lotion"
            ],
            "stationery": [
                "stationery", "books", "paper", "pen", "notebook", "office",
                "supplies", "printing", "photocopy", "xerox"
            ],
            "furniture": [
                "furniture", "sofa", "bed", "chair", "table", "wardrobe",
                "wooden", "interior", "decor", "home furnish"
            ],
            "toys": [
                "toys", "toy store", "games", "hobby", "collectibles",
                "dolls", "action figures"
            ],
            "travel": [
                "travel", "agency", "tour", "tourism", "airline", "ticket",
                "booking", "vacation", "holiday"
            ],
            "tuition": [
                "tuition", "coaching", "classes", "education", "academy",
                "center", "institute", "training"
            ],
            "restaurant_fast_food": [
                "fast food", "burger", "pizza", "kfc", "dominos", "mcdonalds",
                "quick service", "takeaway", "delivery"
            ],
            "restaurant_chinese": [
                "chinese", "noodles", "chow mein", "momos", "dumpling"
            ],
            "restaurant_north_indian": [
                "north indian", "tandoori", "curry", "paratha", "tandoor",
                "biryani", "kebab"
            ],
            "restaurant_south_indian": [
                "south indian", "dosa", "idli", "sambar", "filter coffee",
                "uttapam"
            ],
            "restaurant_pizza": [
                "pizza", "pizzeria", "italian", "pasta", "cheese"
            ],
            "cafe": [
                "cafe", "coffee", "cafe", "tea", "espresso", "latte",
                "cappuccino", "beverage"
            ],
            "laundry": [
                "laundry", "dry clean", "drycleaning", "wash", "ironing",
                "pressing"
            ],
            "photography": [
                "photography", "studio", "photographer", "photo", "portrait",
                "wedding"
            ],
            "printing": [
                "printing", "print", "press", "newspaper", "magazine",
                "publishing", "photostat", "photocopy", "copier", "copy center",
                "print out", "color print", "colour print", "b/w print", "binding",
                "plotting", "xerox"
            ],
            "internet_cafe": [
                "internet cafe", "cyber cafe", "computer center", "broadband",
                "wi-fi"
            ]
        }
        self.generic_keywords = {
            "sale", "purchase", "store", "shop", "market", "dealer", "supplier",
            "service", "services", "repair", "center", "centre", "showroom",
            "works", "agency", "office"
        }

    def classify(self, text_lines):
        """Classify shop category using Gemini first, keyword matching as fallback"""
        try:
            full_text = self._normalize_text(" ".join(text_lines))
            
            logger.info(f"Classifying with text: {full_text[:100]}...")
            
            # Try Gemini-based classification first (more accurate)
            gemini_result = self._gemini_classify(text_lines)
            if gemini_result and gemini_result != "General Store":
                logger.info(f"Gemini classified as: {gemini_result}")
                return gemini_result
            
            # Fallback to keyword scoring
            category_scores = {}
            
            for category, keywords in self.category_map.items():
                matches = 0
                specific_matches = 0
                score = 0
                matched_keywords = []
                
                for keyword in keywords:
                    if self._keyword_matches(full_text, keyword):
                        matches += 1
                        keyword_score = self._keyword_score(keyword)
                        score += keyword_score
                        if keyword.lower() not in self.generic_keywords:
                            specific_matches += 1
                        matched_keywords.append(keyword)
                
                if specific_matches > 0:
                    category_scores[category] = {
                        'score': score,
                        'specific_matches': specific_matches,
                        'matches': matches,
                        'keywords': matched_keywords
                    }
            
            if category_scores:
                best_category = max(
                    category_scores,
                    key=lambda x: (
                        category_scores[x]['score'],
                        category_scores[x]['specific_matches'],
                        category_scores[x]['matches']
                    )
                )
                
                logger.info(f"Category scores: {category_scores}")
                logger.info(f"Best category: {best_category} with score {category_scores[best_category]['score']}")
                
                category_names = {
                    "electrical": "Electrical Store",
                    "real_estate": "Real Estate",
                    "medical": "Medical Store",
                    "restaurant": "Restaurant",
                    "electronics": "Electronics Store",
                    "bakery": "Bakery",
                    "salon": "Salon",
                    "auto_parts": "Auto Parts Dealer",
                    "clothing": "Clothing Store",
                    "grocery": "Grocery Store",
                    "jewelry": "Jewelry Store",
                    "hardware": "Hardware Store",
                    "automotive": "Automotive",
                    "education": "Education",
                    "banking": "Banking",
                    "entertainment": "Entertainment",
                    "fitness": "Fitness Center",
                    "beauty_products": "Beauty Products",
                    "stationery": "Stationery Store",
                    "furniture": "Furniture Store",
                    "toys": "Toys Store",
                    "travel": "Travel Agency",
                    "tuition": "Tuition Center",
                    "restaurant_fast_food": "Fast Food",
                    "restaurant_chinese": "Chinese Restaurant",
                    "restaurant_north_indian": "North Indian Restaurant",
                    "restaurant_south_indian": "South Indian Restaurant",
                    "restaurant_pizza": "Pizza Restaurant",
                    "cafe": "Cafe",
                    "laundry": "Laundry",
                    "photography": "Photography Studio",
                    "printing": "Printing Press",
                    "internet_cafe": "Internet Cafe"
                }
                
                return category_names.get(best_category, "General Store")
            
            # If Gemini returned General Store and keywords found nothing, use Gemini result
            if gemini_result:
                return gemini_result
            
            logger.warning("No category matched, returning General Store")
            return "General Store"

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return "General Store"

    def _gemini_classify(self, text_lines):
        """Use Gemini to classify shop category from text"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not genai or not api_key:
            return None
        
        try:
            client = genai.Client(api_key=api_key)
            text = "\n".join(text_lines)
            prompt = f"""Classify this shop/business into ONE category from this list:
Electrical Store, Real Estate, Medical Store, Restaurant, Electronics Store, Bakery, Salon, Auto Parts Dealer, Clothing Store, Grocery Store, Jewelry Store, Hardware Store, Automotive, Education, Banking, Entertainment, Fitness Center, Beauty Products, Stationery Store, Furniture Store, Toys Store, Travel Agency, Tuition Center, Fast Food, Chinese Restaurant, North Indian Restaurant, South Indian Restaurant, Pizza Restaurant, Cafe, Laundry, Photography Studio, Printing Press, Internet Cafe, General Store

Respond with ONLY the category name, nothing else.

Shop text:
{text}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )
            if response and response.text:
                result = response.text.strip().strip('"').strip("'")
                logger.info(f"Gemini classification result: {result}")
                return result
        except Exception as e:
            logger.error(f"Gemini classification failed: {e}")
        
        return None


    def _normalize_text(self, text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9&+\-./\s]', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    def _keyword_matches(self, text, keyword):
        keyword = self._normalize_text(keyword)
        if not keyword:
            return False

        pattern = re.escape(keyword)
        pattern = pattern.replace(r'\ ', r'\s+')
        return bool(re.search(rf'(?<![a-z0-9]){pattern}(?![a-z0-9])', text))

    def _keyword_score(self, keyword):
        normalized_keyword = self._normalize_text(keyword)
        if normalized_keyword in self.generic_keywords:
            return 0.25
        if " " in normalized_keyword:
            return 3
        return 1
