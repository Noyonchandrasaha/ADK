import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ADK Agent API")

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
database = client.get_database("product_recommender") # Replace with your DB name
product_collection = database.get_collection("products")

class Category(BaseModel):
    main_category: str
    sub_categories: List[str]

class BasicMetadata(BaseModel):
    price: float
    category: Category
    brand: str
    availability_status: str

class DescriptiveMetadata(BaseModel):
    description: str
    attributes: dict
    tags: List[str]
    features: List[str]

class Product(BaseModel):
    id: str = Field(alias="_id")
    slug: str
    item_name: str
    basic_metadata: BasicMetadata
    descriptive_metadata: DescriptiveMetadata

    model_config = ConfigDict(populate_by_name=True)

@app.get("/")
async def root():
    return {"message": "Welcome to the ADK Agent API"}

@app.get("/products/{product_id}", response_model=Product)
async def get_product_by_id(product_id: str):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    product = await product_collection.find_one({"_id": ObjectId(product_id)})
    if product:
        product["_id"] = str(product["_id"])
        return product
    raise HTTPException(status_code=404, detail="Product not found")

@app.get("/products")
async def get_products(
    q: Optional[str] = Query(None, description="Search by item name or tags"),
    category: Optional[str] = Query(None, description="Filter by main category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    sort_by: Optional[str] = Query("item_name", regex="^(item_name|price)$", description="Field to sort by"),
    sort_order: int = Query(1, ge=-1, le=1, description="1 for ascending, -1 for descending"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    skip = (page - 1) * limit
    
    # Build filter query
    filter_query = {}
    
    # Text Search (name or tags)
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
    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        filter_query["basic_metadata.price"] = price_filter

    # Determine sorting field
    actual_sort_field = "item_name" if sort_by == "item_name" else "basic_metadata.price"
    
    total_count = await product_collection.count_documents(filter_query)
    cursor = product_collection.find(filter_query).sort(actual_sort_field, sort_order).skip(skip).limit(limit)
    
    products = []
    async for product in cursor:
        product["_id"] = str(product["_id"])
        products.append(product)
    
    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "products": products
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8050, reload=True)
