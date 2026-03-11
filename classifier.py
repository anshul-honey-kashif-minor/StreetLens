class ShopClassifier:
    def __init__(self):
        # Keyword mapping for categories
        self.category_map = {
            "medical": ["medical", "pharmacy", "clinic", "chemist", "drugs"],
            "restaurant": ["restaurant", "hotel", "cafe", "bhojanalaya", "dhaba", "food"],
            "electronics": ["electronics", "mobile", "computer", "gadgets", "appliances"],
            "bakery": ["bakery", "cake", "sweets", "confectionery"],
            "salon": ["salon", "beauty", "parlour", "hair", "spa"]
        }

    def classify(self, text_lines):
        """Classifies the shop category based on text content."""
        full_text = " ".join(text_lines).lower()

        for category, keywords in self.category_map.items():
            if any(kw in full_text for kw in keywords):
                # Return Title Case (e.g., "Medical Store")
                if category == "medical": return "Medical Store"
                if category == "restaurant": return "Restaurant"
                if category == "electronics": return "Electronics"
                if category == "bakery": return "Bakery"
                if category == "salon": return "Salon"

        return "General Store"