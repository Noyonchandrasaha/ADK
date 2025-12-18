import httpx
from typing import Optional, List
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

# Consolidated Agent-Friendly Search Tool
def discover_products(
    product_id: Optional[str] = None,
    name: Optional[str] = None,
    query: Optional[str] = None,
    category: Optional[str] = None,
    sub_category: Optional[str] = None,
    brand: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    sort_by: str = "item_name",
    order: str = "asc",
    page: int = 1,
    limit: int = 5
) -> dict:
    """
    Search and discover products in our catalog using various filters.
    Use this tool for all product-related questions, including finding items by ID, name, brand, or price.
    
    Args:
        product_id: Exact ID to fetch one specific item.
        name: Filter by product name.
        query: Full-text search (keywords, tags).
        category: Filter by main category (e.g., 'electronics').
        sub_category: Filter by sub-category.
        brand: Filter by brand name.
        price_min: Minimum price filter.
        price_max: Maximum price filter.
        sort_by: Field to sort by ('price' or 'item_name').
        order: Sort order ('asc' or 'desc').
        page: Page number for browsing.
        limit: Number of items per page (default is 5 for agent readability).
    """
    url = "http://localhost:8050/api/products/search"
    params = {
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "limit": limit
    }
    
    # Map arguments to API parameters
    if product_id: params["product_id"] = product_id
    if name: params["name"] = name
    if query: params["q"] = query
    if category: params["category"] = category
    # sub_category mapping if supported by API logic (currently API handles main category)
    if brand: params["brand"] = brand
    if price_min is not None: params["price_min"] = price_min
    if price_max is not None: params["price_max"] = price_max

    try:
        with httpx.Client() as client:
            response = client.get(url, params=params, timeout=15.0)
            
            # Handle error response format defined in guidelines
            if response.status_code != 200:
                return response.json() # Returns {"error": {"code": "...", "message": "..."}}
            
            return response.json() # Returns {"meta": {...}, "data": [...]}
    except Exception as e:
        return {
            "error": {
                "code": "CONNECTION_ERROR",
                "message": f"Failed to reach the search API: {str(e)}"
            }
        }

root_agent = Agent(
    model=LiteLlm(model='openai/gpt-3.5-turbo'),
    name='product_recommender_agent',
    description="A professional product discovery and recommendation assistant.",
    instruction="""You are an expert Shopping Assistant. Your goal is to help users find products from our catalog.
    
    BEST PRACTICES FOR YOUR FLOW:
    1. EXPLICIT LOOKUP: If a user mentions a product name or ID, use the 'name' or 'product_id' parameter specifically.
    2. KEYWORD SEARCH: For general requests like "show me some bags", use the 'query' parameter.
    3. FILTERING: Always apply 'brand', 'category', or price filters (price_min/max) if the user mentions them.
    4. SORTING: For "cheapest" or "best price", use sort_by='price' and order='asc'. For "premium" or "most expensive", use order='desc'.
    5. DATA INTERPRETATION:
       - The tool returns a 'meta' block with total_count and facets (brands, etc.). Use this to tell the user how many items match.
       - The results are in the 'data' block.
    6. ERROR HANDLING: If the tool returns an 'error' block, explain the issue to the user using the provided message.
    """,
    tools=[discover_products],
)