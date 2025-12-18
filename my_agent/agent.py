import httpx
import litellm
from typing import Optional
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

# Tool to fetch a single product by its ID
def get_product_details(product_id: str) -> dict:
    """
    Fetches full details for a specific product using its unique ID.
    Use this when you have a product ID and need to know everything about that specific item.
    """
    try:
        with httpx.Client() as client:
            response = client.get(
                f"http://localhost:8050/products/{product_id}",
                timeout=10.0
            )
            if response.status_code == 404:
                return {"error": f"Product with ID {product_id} not found."}
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch product details: {str(e)}"}

# Advanced tool to fetch multiple products with filtering and sorting
def search_products(
    query: Optional[str] = None, 
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = "item_name",
    sort_order: int = 1,
    page: int = 1, 
    limit: int = 10
) -> dict:
    """
    Searches for products in the database with advanced filters.
    Returns a list of products.
    """
    try:
        params = {
            "page": page, 
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        if query: params["q"] = query
        if category: params["category"] = category
        if brand: params["brand"] = brand
        if min_price is not None: params["min_price"] = min_price
        if max_price is not None: params["max_price"] = max_price
            
        with httpx.Client() as client:
            response = client.get(
                "http://localhost:8050/products",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch products: {str(e)}"}

root_agent = Agent(
    model=LiteLlm(model='openai/gpt-3.5-turbo'),
    name='product_recommender_agent',
    description="A powerful product search and recommendation agent.",
    instruction="""You are an expert Shopping Assistant. 
    
    TOOLS AT YOUR DISPOSAL:
    1. 'search_products': Use this to browse inventory, search by name, filter by brand/price, or sort items.
    2. 'get_product_details': Use this ONLY when you have a specific Product ID and need more information about that single item.
    
    GUIDELINES:
    - If a user asks for a specific product ID (e.g., "tell me about 693a6897..."), use 'get_product_details'.
    - If a user asks for a type of product or a brand, use 'search_products'.
    - Always present the information in a professional and helpful manner.
    """,
    tools=[search_products, get_product_details],
)