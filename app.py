import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File
from service.save_image import saveImageTemp, deleteTemp
from service.ocr_service import process_image

app = FastAPI()

@app.get("/health-check")
def health():
    return {"message": "API Working"}

@app.post("/image-analyzer")
def image_analyzer(file: UploadFile = File(...)):
    filename = saveImageTemp(file)
    result = process_image(filename)
    deleteTemp(filename)
    return result

import math
from typing import Optional
from fastapi import HTTPException, Query
from database.db import SessionLocal
from database.models import Shop
from sqlalchemy import select

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@app.get("/nearby")
def get_nearby(
    lat: float = Query(..., description="User's latitude"),
    lon: float = Query(..., description="User's longitude"),
    category: Optional[str] = Query(None, description="Shop category"),
    limit: int = Query(5, ge=1, le=50),
    offset: int = Query(0, ge=0),
    max_distance: Optional[float] = Query(None, description="Max distance in km"),
    search: Optional[str] = Query(None, description="Fuzzy search term for shop name"),
):
    try:
        with SessionLocal() as session:
            stmt = select(Shop).where(Shop.latitude.is_not(None), Shop.longitude.is_not(None))
            if category and category != "All":
                stmt = stmt.where(Shop.category == category)
            
            shops = session.scalars(stmt).all()
            
            results = []
            search_lower = search.lower().strip() if search else None
            for shop in shops:
                dist = haversine(lat, lon, shop.latitude, shop.longitude)
                if max_distance is not None and dist > max_distance:
                    continue
                if search_lower:
                    name = (shop.shop_name or "").lower()
                    addr = (shop.address or "").lower()
                    if search_lower not in name and search_lower not in addr:
                        continue
                results.append({
                    "id": shop.id,
                    "shop_name": shop.shop_name,
                    "category": shop.category,
                    "phone_number": shop.phone_number,
                    "address": shop.address,
                    "latitude": shop.latitude,
                    "longitude": shop.longitude,
                    "distance_km": round(dist, 2)
                })
            
            results.sort(key=lambda x: x["distance_km"])
            paginated = results[offset:offset+limit]
            
            return {
                "total": len(results),
                "offset": offset,
                "limit": limit,
                "results": paginated
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nearby/categories")
def get_nearby_categories():
    try:
        with SessionLocal() as session:
            rows = session.execute(
                select(Shop.category)
                .where(Shop.category.is_not(None), Shop.category != "")
                .distinct()
                .order_by(Shop.category)
            ).all()
            return {"categories": [r[0] for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))