import os
import math
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ADK Agent-Friendly Product API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
MONGO_DETAILS = os.getenv("MONGO_DETAILS")
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.get_database("product_recommender")
product_collection = database.get_collection("products")

# --- Models ---

class Category(BaseModel):
    main_category: str
    sub_categories: List[str]

class ProductResponseModel(BaseModel):
    """Refined product model for agent consumption with explicit naming"""
    product_id: str
    slug: str
    item_name: str
    price: float
    brand: str
    availability: str
    category: Category
    description: str
    attributes: Dict[str, Any]
    tags: List[str]
    features: List[str]

    model_config = ConfigDict(populate_by_name=True)

class Meta(BaseModel):
    page: int
    limit: int
    total_count: int
    total_pages: int
    facets: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    meta: Meta
    data: List[ProductResponseModel]

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

# --- Helper Functions ---

def map_mongo_to_product(doc: dict) -> ProductResponseModel:
    """Explicitly map MongoDB document structure to the agent-friendly model"""
    return ProductResponseModel(
        product_id=str(doc.get("_id")),
        slug=doc.get("slug", ""),
        item_name=doc.get("item_name", ""),
        price=doc.get("basic_metadata", {}).get("price", 0.0),
        brand=doc.get("basic_metadata", {}).get("brand", "Unknown"),
        availability=doc.get("basic_metadata", {}).get("availability_status", "N/A"),
        category=Category(
            main_category=doc.get("basic_metadata", {}).get("category", {}).get("main_category", "Uncategorized"),
            sub_categories=doc.get("basic_metadata", {}).get("category", {}).get("sub_categories", [])
        ),
        description=doc.get("descriptive_metadata", {}).get("description", ""),
        attributes=doc.get("descriptive_metadata", {}).get("attributes", {}),
        tags=doc.get("descriptive_metadata", {}).get("tags", []),
        features=doc.get("descriptive_metadata", {}).get("features", [])
    )

# --- Endpoints ---

@app.get("/")
async def root():
    return {"message": "Welcome to the ADK Agent-Friendly API", "docs": "/docs"}

@app.get("/api/products/search", response_model=SearchResponse)
async def search_products(
    product_id: Optional[str] = Query(None, description="Exact ID lookup"),
    name: Optional[str] = Query(None, description="Exact or partial product name"),
    q: Optional[str] = Query(None, description="Full-text search in name and tags"),
    category: Optional[str] = Query(None, description="Filter by main category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    price_min: Optional[float] = Query(None, description="Minimum price range"),
    price_max: Optional[float] = Query(None, description="Maximum price range"),
    sort_by: str = Query("item_name", regex="^(item_name|price)$"),
    order: str = Query("asc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    filter_query = {}

    # Exact ID Lookup
    if product_id:
        if not ObjectId.is_valid(product_id):
            raise HTTPException(
                status_code=400, 
                detail={"error": {"code": "INVALID_PARAMETER", "message": "Invalid product_id format"}}
            )
        filter_query["_id"] = ObjectId(product_id)

    # Name Search
    if name:
        filter_query["item_name"] = {"$regex": name, "$options": "i"}

    # Full-text Search (q)
    if q:
        filter_query["$or"] = [
            {"item_name": {"$regex": q, "$options": "i"}},
            {"descriptive_metadata.tags": {"$regex": q, "$options": "i"}}
        ]

    # Category Filter
    if category:
        filter_query["basic_metadata.category.main_category"] = category

    # Brand Filter
    if brand:
        filter_query["basic_metadata.brand"] = brand

    # Price Range Filter
    if price_min is not None or price_max is not None:
        price_filter = {}
        if price_min is not None: price_filter["$gte"] = price_min
        if price_max is not None: price_filter["$lte"] = price_max
        filter_query["basic_metadata.price"] = price_filter

    # Sorting
    sort_field = "item_name" if sort_by == "item_name" else "basic_metadata.price"
    sort_order = 1 if order == "asc" else -1

    # Execute Query
    total_count = await product_collection.count_documents(filter_query)
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 0
    
    skip = (page - 1) * limit
    cursor = product_collection.find(filter_query).sort(sort_field, sort_order).skip(skip).limit(limit)
    
    products = []
    async for doc in cursor:
        products.append(map_mongo_to_product(doc))

    # Facets (Aggregation for brands and categories)
    # Note: For production, you might want to cache or optimize this
    facets = {}
    if total_count > 0 and not product_id:
        # Simplified facets for demo
        brands_pipeline = [
            {"$match": filter_query},
            {"$group": {"_id": "$basic_metadata.brand", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        brands_agg = await product_collection.aggregate(brands_pipeline).to_list(length=5)
        facets["brands"] = {b["_id"]: b["count"] for b in brands_agg}

    return {
        "meta": {
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": total_pages,
            "facets": facets
        },
        "data": products
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8050, reload=True)
