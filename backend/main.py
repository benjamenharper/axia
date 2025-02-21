from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import requests
import json
import logging
import re
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import hashlib
from datetime import datetime
import jinja2
from jinja2 import Environment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Zillow API configuration
ZILLOW_API_KEY = os.getenv("ZILLOW_API_KEY")
ZILLOW_API_HOST = os.getenv("ZILLOW_API_HOST")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not ZILLOW_API_KEY or not ZILLOW_API_HOST:
    raise ValueError("Missing Zillow API credentials")

if not GROQ_API_KEY:
    raise ValueError("Missing Groq API credentials")

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://axia.vercel.app",  # Production frontend
        "https://axia-git-main-benjamenharper.vercel.app",  # Preview deployments
        "*"  # Allow all origins temporarily for debugging
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Configure static files
app.mount("/static", StaticFiles(directory="static_pages"), name="static")

class SearchRequest(BaseModel):
    query: str

class Property(BaseModel):
    id: str
    title: str
    price: int
    location: str
    summary: str
    image_url: str
    features: List[str]

def extract_location(query: str) -> str:
    """Extract location from the query"""
    logger.info(f"Extracting location from query: {query}")
    
    # Common location patterns
    location_patterns = [
        r'in ([A-Za-z\s,]+)',  # matches "in Boston" or "in New York"
        r'at ([A-Za-z\s,]+)',  # matches "at Miami Beach"
        r'near ([A-Za-z\s,]+)',  # matches "near Chicago"
    ]
    
    # First try to find location using patterns
    for pattern in location_patterns:
        match = re.search(pattern, query, re.IGNORECASE)  # Make pattern matching case-insensitive
        if match:
            location = match.group(1).strip()
            logger.info(f"Found location using pattern '{pattern}': {location}")
            
            # Add state if not present for common cities
            if "," not in location:
                location_lower = location.lower()
                if location_lower == "boston":
                    location += ", MA"
                elif location_lower in ["new york", "nyc"]:
                    location += ", NY"
                elif location_lower == "miami":
                    location += ", FL"
                elif location_lower == "chicago":
                    location += ", IL"
                elif location_lower == "los angeles":
                    location += ", CA"
                elif location_lower in ["princeville", "kapaa", "poipu", "kauai"]:
                    location += ", HI"
            logger.info(f"Final location after state addition: {location}")
            return location
    
    # If no location found in patterns, check if query starts with a location
    words = query.split()
    if words and words[0][0].isupper():  # If first word is capitalized
        location = words[0]
        logger.info(f"Using first capitalized word as location: {location}")
        return location
    
    # No location found, do not default to Kauai
    logger.info("No location found in query")
    raise HTTPException(status_code=400, detail="Please specify a location in your search query (e.g., 'in Boston' or 'near Chicago')")

def extract_search_params(query: str) -> dict:
    """Extract search criteria from the query"""
    # Default criteria
    criteria = {
        "location": None,
        "min_price": None,
        "max_price": None,
        "property_type": "SINGLE_FAMILY"
    }
    
    # Convert query to lowercase for easier matching
    query_lower = query.lower()
    
    # Extract location (case-sensitive)
    criteria["location"] = extract_location(query)
    logger.info(f"Extracted location: {criteria['location']}")
    
    # Extract property type
    if "land" in query_lower or "lot" in query_lower:
        criteria["property_type"] = "LAND"
    elif "condo" in query_lower:
        criteria["property_type"] = "CONDO"
    elif "townhouse" in query_lower or "town house" in query_lower:
        criteria["property_type"] = "TOWNHOUSE"
    elif "multi" in query_lower or "multi-family" in query_lower:
        criteria["property_type"] = "MULTI_FAMILY"
    
    # Extract price range
    price_patterns = [
        (r'under ?\$?(\d+\.?\d*)\s*million', lambda x: float(x) * 1000000),  # "under 2 million" or "under $2 million"
        (r'under ?\$?(\d+,?\d*)', lambda x: float(x.replace(',', ''))),  # "under $500,000" or "under 500000"
        (r'less than ?\$?(\d+\.?\d*)\s*million', lambda x: float(x) * 1000000),  # "less than 2 million"
        (r'less than ?\$?(\d+,?\d*)', lambda x: float(x.replace(',', ''))),  # "less than $500,000"
        (r'\$?(\d+\.?\d*)\s*million', lambda x: float(x) * 1000000),  # "$2 million" or "2 million"
        (r'\$?(\d+,?\d*)', lambda x: float(x.replace(',', ''))),  # "$500,000" or "500000"
    ]
    
    for pattern, converter in price_patterns:
        match = re.search(pattern, query_lower)
        if match:
            try:
                price = converter(match.group(1))
                criteria["max_price"] = str(int(price))
                logger.info(f"Extracted max price: {criteria['max_price']}")
                break
            except:
                continue
    
    logger.info(f"Final search criteria: {criteria}")
    return criteria

def generate_search_summary(search_criteria: dict) -> str:
    """Generate a natural language summary of the search criteria"""
    summary_parts = []
    
    # Add location
    if search_criteria["location"]:
        summary_parts.append(f"Looking for properties in {search_criteria['location']}")
    
    # Add property type
    property_type_display = {
        "SINGLE_FAMILY": "single-family homes",
        "CONDO": "condominiums",
        "TOWNHOUSE": "townhouses",
        "MULTI_FAMILY": "multi-family homes",
        "LAND": "land"
    }
    if search_criteria["property_type"]:
        prop_type = property_type_display.get(search_criteria["property_type"], "properties")
        summary_parts[0] = f"Looking for {prop_type} in {search_criteria['location']}"
    
    # Add price range
    if search_criteria["min_price"] and search_criteria["max_price"]:
        min_price = int(float(search_criteria["min_price"].replace("$", "").replace(",", "")))
        max_price = int(float(search_criteria["max_price"].replace("$", "").replace(",", "")))
        summary_parts.append(f"priced between ${min_price:,} and ${max_price:,}")
    elif search_criteria["min_price"]:
        min_price = int(float(search_criteria["min_price"].replace("$", "").replace(",", "")))
        summary_parts.append(f"priced above ${min_price:,}")
    elif search_criteria["max_price"]:
        max_price = int(float(search_criteria["max_price"].replace("$", "").replace(",", "")))
        summary_parts.append(f"priced under ${max_price:,}")
    
    # Combine all parts
    summary = " ".join(summary_parts)
    
    logger.info(f"Generated search summary: {summary}")
    return summary

def generate_location_overview(location: str) -> str:
    """Generate an AI overview of the location using Groq API"""
    try:
        logger.info(f"Generating location overview for: {location}")
        
        # Extract city and state
        parts = location.split(",")
        city = parts[0].strip()
        state = parts[1].strip() if len(parts) > 1 else ""
        
        # Create prompt for location overview
        prompt = f"""Generate a concise overview of {city}{', ' + state if state else ''} covering:
1. Brief history
2. Population and demographics
3. Education (schools and universities)
4. Economy and job market
5. Quality of life (climate, culture, amenities)

Format as markdown with sections. Keep it factual and concise."""

        # Call Groq API
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "https://api.groq.com/v1/completions",
            headers=headers,
            json={
                "model": "mixtral-8x7b-32768",
                "messages": [
                    {"role": "system", "content": "You are a knowledgeable assistant that provides accurate, concise information about locations."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
        )
        
        if response.status_code == 200:
            overview = response.json()["choices"][0]["message"]["content"]
            logger.info(f"Successfully generated overview for {location}")
            return overview
        else:
            logger.error(f"Error from Groq API: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating location overview: {str(e)}")
        return None

def search_zillow(location: str, min_price: Optional[str] = None, max_price: Optional[str] = None, property_type: str = "SINGLE_FAMILY"):
    """Search Zillow API with error handling and logging"""
    try:
        logger.info(f"Searching Zillow for properties in {location}")
        logger.info(f"Price range: {min_price} - {max_price}")
        logger.info(f"Property type: {property_type}")

        # Map our property types to Zillow's property types
        property_type_map = {
            "SINGLE_FAMILY": "Houses",
            "CONDO": "Condos",
            "TOWNHOUSE": "Townhomes",
            "MULTI_FAMILY": "Multi-family",
            "LAND": "Lots_Land"  # Updated to correct Zillow property type
        }

        zillow_property_type = property_type_map.get(property_type)
        logger.info(f"Mapped property type to Zillow type: {zillow_property_type}")
        
        # Prepare search parameters
        params = {
            "location": location,
            "status_type": "ForSale",
            "sort": "Price_High_Low"
        }

        # Only add home_type if we have a valid mapping
        if zillow_property_type:
            params["home_type"] = zillow_property_type
            logger.info(f"Added home_type filter: {zillow_property_type}")
        
        # Add price filters if specified
        if min_price:
            params["price_min"] = min_price
        if max_price:
            params["price_max"] = max_price

        headers = {
            "X-RapidAPI-Key": ZILLOW_API_KEY,
            "X-RapidAPI-Host": ZILLOW_API_HOST
        }

        logger.info(f"Zillow API Key: {ZILLOW_API_KEY[:10]}...")
        logger.info(f"Zillow API Host: {ZILLOW_API_HOST}")
        logger.info(f"Searching Zillow with URL: https://zillow-com1.p.rapidapi.com/propertyExtendedSearch")
        logger.info(f"Query parameters: {params}")
        logger.info(f"Headers (partial): {{'X-RapidAPI-Host': {headers['X-RapidAPI-Host']}}}")

        response = requests.get("https://zillow-com1.p.rapidapi.com/propertyExtendedSearch", headers=headers, params=params, timeout=30)
        
        # Log the response details
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {str(e)}")
            logger.error(f"Response text: {response.text}")
            if response.status_code == 401:
                raise HTTPException(status_code=500, detail="Invalid Zillow API credentials")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Too many requests to Zillow API")
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Zillow API error: {response.text}")
        
        try:
            results = response.json()
            logger.info(f"Zillow API raw response: {results}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.error(f"Raw response text: {response.text}")
            raise HTTPException(status_code=500, detail="Invalid response format from Zillow API")
        
        if not isinstance(results, dict):
            logger.error(f"Unexpected response type from Zillow API: {type(results)}")
            raise HTTPException(status_code=500, detail=f"Invalid response type from Zillow API: {type(results)}")
        
        # Check for API-level errors
        if "error" in results:
            error_msg = results.get("error", {}).get("message", "Unknown API error")
            logger.error(f"Zillow API returned error: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Zillow API error: {error_msg}")
        
        # Get properties from the correct response field
        properties_data = results.get("props", results.get("results", []))
        if not properties_data:
            logger.warning(f"No properties found for location: {location}")
            logger.warning(f"Full response: {results}")
            raise HTTPException(status_code=404, detail=f"No properties found in {location}")
        
        properties = []
        for prop in properties_data:
            try:
                # Extract price
                price_str = prop.get("price", "0")
                if isinstance(price_str, str):
                    price_str = price_str.replace("$", "").replace(",", "")
                price = int(float(price_str))
                
                # Build features list
                features = []
                if prop.get("bedrooms"):
                    features.append(f"{prop['bedrooms']} bedrooms")
                if prop.get("bathrooms"):
                    features.append(f"{prop['bathrooms']} bathrooms")
                if prop.get("livingArea"):
                    features.append(f"{prop['livingArea']} sqft")
                
                # Get property type
                prop_type = prop.get("propertyType", prop.get("homeType", "Property"))
                
                # Build location string
                location_parts = [
                    prop.get("streetAddress", "").strip(),
                    prop.get("city", "").strip(),
                    prop.get("state", "").strip()
                ]
                location_str = ", ".join(filter(None, location_parts))
                
                property_data = Property(
                    id=str(prop.get("zpid", prop.get("id", ""))),
                    title=f"{prop_type} in {prop.get('city', location)}",
                    price=price,
                    location=location_str,
                    summary=f"{prop_type} with {prop.get('bedrooms', 'N/A')} beds, {prop.get('bathrooms', 'N/A')} baths",
                    image_url=prop.get("imgSrc", prop.get("imageUrl", "")),
                    features=features
                )
                properties.append(property_data)
                logger.info(f"Successfully processed property: {property_data.id}")
            except Exception as e:
                logger.error(f"Error processing property: {str(e)}")
                logger.error(f"Property data: {prop}")
                continue
        
        logger.info(f"Successfully processed {len(properties)} properties")
        return properties
    
    except requests.exceptions.Timeout:
        logger.error("Zillow API request timed out")
        raise HTTPException(status_code=504, detail="Zillow API request timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"Zillow API request error: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.error(f"Response text: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Error fetching properties: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in search_zillow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/api/search")
async def search_properties(request: SearchRequest):
    """Search for properties using natural language query"""
    try:
        logger.info(f"Received search query: {request.query}")
        
        # Extract search parameters
        search_criteria = extract_search_params(request.query)
        logger.info(f"Extracted search criteria: {search_criteria}")
        
        if not search_criteria["location"]:
            logger.error("No location found in query")
            raise HTTPException(status_code=400, detail="Please specify a location in your search query")
        
        # Generate search summary
        search_summary = generate_search_summary(search_criteria)
        logger.info(f"Generated search summary: {search_summary}")
        
        # Generate location overview
        location_overview = generate_location_overview(search_criteria["location"])
        logger.info(f"Generated location overview: {location_overview}")
        
        # Search Zillow
        try:
            properties = search_zillow(
                location=search_criteria["location"],
                min_price=search_criteria["min_price"],
                max_price=search_criteria["max_price"],
                property_type=search_criteria["property_type"]
            )
            logger.info(f"Found {len(properties)} properties")
            
            if not properties:
                logger.warning("No properties found")
                return {
                    "results": [],
                    "static_page_url": None,
                    "search_summary": search_summary,
                    "location_overview": location_overview
                }
            
            # Generate static page
            try:
                static_page_url = generate_static_page(properties, request.query, search_summary)
                logger.info(f"Generated static page: {static_page_url}")
            except Exception as e:
                logger.error(f"Error generating static page: {str(e)}")
                static_page_url = None
            
            return {
                "results": properties,
                "static_page_url": static_page_url,
                "search_summary": search_summary,
                "location_overview": location_overview
            }
            
        except HTTPException as e:
            logger.error(f"HTTP error during Zillow search: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Error during Zillow search: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error searching properties: {str(e)}")
            
    except HTTPException as e:
        logger.error(f"HTTP error in search_properties: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in search_properties: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

def generate_static_page(properties: List[Property], search_query: str, search_summary: str) -> Optional[str]:
    """Generate a static HTML page for the search results"""
    try:
        # Create static_pages directory if it doesn't exist
        os.makedirs("static_pages", exist_ok=True)
        
        # Clean and format the search query for the URL
        url_query = search_query.lower()
        url_query = re.sub(r'[^a-z0-9]+', '-', url_query)
        url_query = re.sub(r'-+', '-', url_query)
        url_query = url_query.strip('-')
        
        # Generate a unique filename using timestamp and search query
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}-{url_query}.html"
        
        template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Real Estate Search: {{ search_query }}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                .property-card {
                    height: 100%;
                    transition: transform 0.2s;
                }
                .property-card:hover {
                    transform: translateY(-5px);
                }
                .property-image {
                    height: 200px;
                    object-fit: cover;
                }
                .timestamp {
                    font-size: 0.8rem;
                    color: #666;
                }
                .search-summary {
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 1rem;
                    margin-bottom: 1.5rem;
                    border-left: 4px solid #0d6efd;
                }
            </style>
        </head>
        <body>
            <div class="container py-4">
                <div class="row mb-4">
                    <div class="col">
                        <h1 class="mb-3">Real Estate Search Results</h1>
                        <div class="search-summary">
                            <p class="lead mb-0">{{ search_summary }}</p>
                        </div>
                        <p class="timestamp">Generated on: {{ timestamp }}</p>
                    </div>
                </div>
                
                <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
                    {% for property in properties %}
                    <div class="col">
                        <div class="card property-card h-100 shadow-sm">
                            {% if property.image_url %}
                            <img src="{{ property.image_url }}" class="card-img-top property-image" alt="{{ property.title }}">
                            {% else %}
                            <div class="card-img-top property-image bg-light d-flex align-items-center justify-content-center">
                                <span class="text-muted">No image available</span>
                            </div>
                            {% endif %}
                            <div class="card-body">
                                <h5 class="card-title">{{ property.title }}</h5>
                                <h6 class="card-subtitle mb-2 text-primary">${{ '{:,}'.format(property.price) }}</h6>
                                <p class="card-text text-muted">{{ property.location }}</p>
                                <p class="card-text">{{ property.summary }}</p>
                                {% if property.features %}
                                <div class="mt-2">
                                    {% for feature in property.features %}
                                    <span class="badge bg-primary me-1">{{ feature }}</span>
                                    {% endfor %}
                                </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
        
        # Format the current timestamp for display
        display_timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        # Create the Jinja2 environment and template
        env = Environment(autoescape=True)
        template = env.from_string(template)
        
        # Render the template
        html_content = template.render(
            properties=properties,
            search_query=search_query,
            search_summary=search_summary,
            timestamp=display_timestamp
        )
        
        # Write the file
        with open(os.path.join("static_pages", filename), "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"Generated static page: {filename}")
        return f"/static/{filename}"
        
    except Exception as e:
        logger.error(f"Error generating static page: {str(e)}")
        return None

@app.get("/static/{filename}")
async def get_static_page(filename: str):
    return FileResponse(f"static_pages/{filename}")

@app.get("/")
async def read_root():
    return {"status": "ok", "message": "Real Estate AI Search API"}
