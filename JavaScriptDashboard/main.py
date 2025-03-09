

# Manual alerts
# Get theme from here: https://www.wrmd.org/features



from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import json
import requests
from datetime import datetime
from collections import defaultdict
from typing import Dict
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv('API_KEY')
BASE = os.getenv('BASE')
PRODUCTS = os.getenv('PRODUCTS')
CATEGORIES = os.getenv('CATEGORIES')
ORDERS = os.getenv('ORDERS')
USAGES = os.getenv('USAGES')

CRITICAL_DAYS = int(os.getenv('CRITICAL_DAYS'))
WARNING_DAYS = int(os.getenv('WARNING_DAYS'))

HEADERS ={ 
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def airtable_read(table: str):
    url = f'https://api.airtable.com/v0/{BASE}/{table}'
    response = requests.get(url, headers=HEADERS)
    return response.json()

def airtable_write(table: str, data: dict):
    url = f'https://api.airtable.com/v0/{BASE}/{table}'
    response = requests.post(url, headers=HEADERS, data=json.dumps(data))
    
    # Return both status code and the actual response content (JSON)
    return response.status_code, response.json()  # Return both the status code and the parsed response body


# JSON to be passed to the front end:
# {
#   "charts": [
#     {
#       "category": "category-1",
#       "data": [
#         {"month": "2025-02", "orders": 5, "usages": 4},
#         {"month": "2025-03", "orders": 3, "usages": 2}
#       ]
#     },
#     {
#       "category": "category-2",
#       "data": [
#         {"month": "2025-02", "orders": 4, "usages": 3},
#         {"month": "2025-03", "orders": 2, "usages": 1}
#       ]
#     }
#   ]
# }
def parse_chart_json(categories_data, orders_data, usages_data):
    # Map product IDs to categories
    category_map = {}
    category_names = {}
    
    for category in categories_data['records']:
        category_id = category['fields']['id']
        category_name = category['fields']['name']
        category_names[category_id] = category_name
        for product in category['fields'].get('products', []):
            category_map[product] = category_id

    # Helper function to extract year-month from a date
    def extract_month(date_str):
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m")

    # Count orders per category per month
    category_orders = defaultdict(lambda: defaultdict(int))
    
    for order in orders_data['records']:
        product_ids = order['fields'].get('product', [])
        order_month = extract_month(order['fields']['order-date'])
        for product_id in product_ids:
            category_id = category_map.get(product_id)
            if category_id:
                category_orders[category_id][order_month] += 1

    # Count usages per category per month
    category_usages = defaultdict(lambda: defaultdict(int))
    
    for usage in usages_data['records']:
        product_ids = usage['fields'].get('product', [])
        usage_month = extract_month(usage['fields']['usage-date'])
        for product_id in product_ids:
            category_id = category_map.get(product_id)
            if category_id:
                category_usages[category_id][usage_month] += 1

    # Construct the final JSON
    charts = []
    for category_id, category_name in category_names.items():
        months = set(category_orders[category_id].keys()) | set(category_usages[category_id].keys())
        data = [
            {
                "month": month,
                "orders": category_orders[category_id].get(month, 0),
                "usages": category_usages[category_id].get(month, 0)
            }
            for month in sorted(months)
        ]
        charts.append({"category": category_name, "data": data})

    return {"charts": charts}



# JSON to be passed to the front end:
# {
#   "alerts": [
#     {
#       "urgency": "Critical",
#       "type": "Low Inventory",
#       "category": "category-3",
#       "product": "Product A",
#       "effective-date": "2025-04-01"
#     },
#     {
#       "urgency": "Warning",
#       "type": "Projected Run Out",
#       "category": "category-2",
#       "product": "Product B",
#       "effective-date": "2025-04-03"
#     }
#   ]
# }
def parse_table_json(categories_data, products_data, orders_data, usages_data):
    # Initialize an empty list to hold the alerts
    alerts = []

    # Define thresholds for critical and warning urgency based on effective date
    
    # Step 1: Map products to categories
    product_to_category = {}
    for category in categories_data['records']:
        category_name = category['fields']['name']
        category_products = category['fields'].get('products', [])
        for product_id in category_products:
            product_to_category[product_id] = category_name

    # Step 2: Process orders and build a map of product expiration dates
    product_expiration_dates = {}
    for order in orders_data['records']:
        for product_id in order['fields']['product']:
            try:
                expiration_date = order['fields']['expiration-date']
            except:
                expiration_date = None
            # Store the latest expiration date for each product
            if product_id not in product_expiration_dates:
                product_expiration_dates[product_id] = expiration_date
            else:
                # If multiple orders exist, keep the earliest expiration date
                if expiration_date:
                    if expiration_date < product_expiration_dates[product_id]:
                        product_expiration_dates[product_id] = expiration_date

    # Step 3: Track product usage dates (just in case you need to track usage trends in the future)
    product_usage_dates = {}
    for usage in usages_data['records']:
        for product_id in usage['fields']['product']:
            usage_date = usage['fields']['usage-date']
            if product_id not in product_usage_dates:
                product_usage_dates[product_id] = []
            product_usage_dates[product_id].append(usage_date)

    # Step 4: Generate alerts based on proximity of the effective date (expiration)
    current_date = datetime.now()

    for product_id, category_name in product_to_category.items():
        # Get the expiration date for the product
        expiration_date_str = product_expiration_dates.get(product_id)
        if not expiration_date_str:
            continue  # Skip if there's no expiration date
        
        expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d")

        # Calculate how many days to expiration
        days_to_expire = (expiration_date - current_date).days

        # Determine urgency based on how close the expiration date is
        if days_to_expire <= CRITICAL_DAYS:
            urgency = "Critical"
        elif days_to_expire <= WARNING_DAYS:
            urgency = "Warning"
        else:
            continue  # Skip if it's not within the critical or warning window
        
        # Get the product name from the products data
        product_name = None
        for product in products_data['records']:
            if product['id'] == product_id:
                product_name = product['fields']['name']
                break
        
        if not product_name:
            continue  # Skip if product name is not found
        
        # Add the alert to the list
        alert = {
            "urgency": urgency,
            "type": "Expiration",  # Since it's based on expiration dates, it's a projected run out
            "category": category_name,
            "product": product_name,
            "effective-date": expiration_date_str
        }
        alerts.append(alert)

    # Return the generated alerts as a JSON-like dictionary
    return {"alerts": alerts}


app = FastAPI()

@app.get("/favicon.ico")
async def favicon():
    return FileResponse('frontend/images/favicon.ico')

@app.get("/")
async def redirect_to_dashboard():
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard")
async def get_dashboard():
    return FileResponse('frontend/dashboard.html')

@app.get("/api/dashboard-chart-data")
async def dashboard_chart_data():
    categories_data = airtable_read(CATEGORIES)
    orders_data = airtable_read(ORDERS)
    usages_data = airtable_read(USAGES)

    chart_json = parse_chart_json(categories_data, orders_data, usages_data)
    return JSONResponse(content=chart_json)

@app.get("/api/dashboard-table-data")
async def dashboard_table_data():
    categories_data = airtable_read(CATEGORIES)
    products_data = airtable_read(PRODUCTS)
    orders_data = airtable_read(ORDERS)
    usages_data = airtable_read(USAGES)

    table_json = parse_table_json(categories_data, products_data, orders_data, usages_data)
    return JSONResponse(content=table_json)

@app.get("/api/form-product-data")
async def dashboard_table_data():
    products_data = airtable_read(PRODUCTS)
    # Extract both 'id' and 'name' for each product
    products_json = {
        "products": [
            {"id": product['id'], "name": product['fields']['name']} 
            for product in products_data['records']
        ]
    }
    return JSONResponse(content=products_json)

def get_product_record_id(product_name):
    """Retrieve the record ID for the product from the 'Products' table based on the product name."""
    url = f'https://api.airtable.com/v0/{BASE}/{PRODUCTS}?filterByFormula={{Name}}="{product_name}"'
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        records = data.get("records", [])
        
        if len(records) > 0:
            return records[0]["id"]  # Return the record ID of the first match
        else:
            raise HTTPException(status_code=400, detail=f"Product '{product_name}' not found in Airtable.")
    else:
        raise HTTPException(status_code=500, detail="Error retrieving product data from Airtable.")

def format_date_to_airtable(date_string: str) -> str:
    try:
        # Convert the date string to a datetime object
        date_obj = datetime.strptime(date_string, "%Y-%m-%d")
        # Format it to MM/DD/YYYY
        return date_obj.strftime("%m/%d/%Y")
    except ValueError:
        # If there's an issue with the date format, log it or raise an exception
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date_string}")

@app.post("/api/purchase-report")
async def purchase_report(data: Dict):
    # Check if the data contains the items key and that it is a non-empty list
    if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:

        # Iterate over each item in the 'items' list
        for item in data["items"]:
            product_id = item.get("product")  # This is the product record ID
            order_date = item.get("orderDate")
            expiration_date = item.get("expirationDate")

            # Validate the data
            if not product_id or not order_date:
                raise HTTPException(status_code=400, detail="Missing product or order date")

            # Format the dates to the required MM/DD/YYYY format for Airtable
            formatted_order_date = format_date_to_airtable(order_date)
            formatted_expiration_date = format_date_to_airtable(expiration_date) if expiration_date else None

            # Check if expiration date is valid
            if expiration_date and expiration_date < order_date:
                raise HTTPException(status_code=400, detail="Expiration date cannot be earlier than order date")

            # Format the data to send to Airtable
            airtable_data = {
                "fields": {
                    "product": [product_id],  # This is an array of record IDs
                    "order-date": formatted_order_date,
                    "expiration-date": formatted_expiration_date if formatted_expiration_date else None
                }
            }

            # Write to Airtable Orders table
            status_code, response_data = airtable_write(ORDERS, airtable_data)

            # Handle any errors from Airtable
            if status_code != 200:
                raise HTTPException(status_code=500, detail=f"Error writing to Airtable: {response_data.get('message')}")

        # If data is valid, return a success response
        return JSONResponse(content={
            "status": 200,  # Success status code
            "message": "Report submitted successfully"  # Success message
        })
    
    else:
        # If data validation fails (missing 'items' or 'items' is not a list), return a failure response
        raise HTTPException(status_code=400, detail="Invalid data or missing items")

@app.post("/api/usage-report")
async def usage_report(data: Dict):
    # Check if the data contains the items key and that it is a non-empty list
    if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:

        # Iterate over each item in the 'items' list
        for item in data["items"]:
            product_id = item.get("product")  # This is the product record ID
            usage_date = item.get("usageDate")

            # Validate the data
            if not product_id or not usage_date:
                raise HTTPException(status_code=400, detail="Missing product or usage date")

            # Format the usage date to the required MM/DD/YYYY format for Airtable
            formatted_usage_date = format_date_to_airtable(usage_date)

            # Format the data to send to Airtable
            airtable_data = {
                "fields": {
                    "product": [product_id],  # This is an array of record IDs
                    "usage-date": formatted_usage_date,
                }
            }

            # Write to Airtable USAGES table
            status_code, response_data = airtable_write(USAGES, airtable_data)

            # Handle any errors from Airtable
            if status_code != 200:
                raise HTTPException(status_code=500, detail=f"Error writing to Airtable: {response_data.get('message')}")

        # If data is valid, return a success response
        return JSONResponse(content={
            "status": 200,  # Success status code
            "message": "Usage report submitted successfully"  # Success message
        })
    
    else:
        # If data validation fails (missing 'items' or 'items' is not a list), return a failure response
        raise HTTPException(status_code=400, detail="Invalid data or missing items")

@app.get("/purchase-report")
async def get_purchase_report():
    return FileResponse('frontend/purchase-report.html')

@app.get("/usage-report")
async def get_usage_report():
    return FileResponse('frontend/usage-report.html')

@app.get("/server-settings")
async def get_server_settings():
    return FileResponse('frontend/server-settings.html')

app.mount("/styles", StaticFiles(directory="frontend/styles"), name="styles")
app.mount("/scripts", StaticFiles(directory="frontend/scripts"), name="scripts")
app.mount("/images", StaticFiles(directory="frontend/images"), name="images")
