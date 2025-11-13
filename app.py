import os
from flask import Flask, request, jsonify
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# NOTION DB & SECRET - Loaded from environment variables
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
DATABASE_ID = os.environ.get('DATABASE_ID')

if not NOTION_TOKEN or not DATABASE_ID:
    raise ValueError("NOTION_TOKEN and DATABASE_ID environment variables must be set")

notion = Client(auth=NOTION_TOKEN)

# Helper: Find a page by Treat Name (unique identifier)
def find_page_by_name(name):
    query = notion.databases.query(
        database_id=DATABASE_ID,
        filter={
            "property": "Treat Name",
            "title": {"equals": name}
        }
    )
    results = query.get('results', [])
    return results[0] if results else None

# Helper: Map price to price range category
def map_price_to_range(price_input):
    """
    Convert price input to one of the predefined Price Range values.
    Accepts:
    - Already valid categories: "€ (Budget)", "€€ (Moderate)", "€€€ (Premium)"
    - Numeric values or strings containing numbers (e.g., "4,95 €", "15", 25.50)

    Returns one of: "€ (Budget)", "€€ (Moderate)", "€€€ (Premium)", or None
    """
    if not price_input:
        return None

    price_str = str(price_input).strip()

    # If already a valid category, return it
    valid_categories = ["€ (Budget)", "€€ (Moderate)", "€€€ (Premium)"]
    if price_str in valid_categories:
        return price_str

    # Try to extract numeric value
    import re
    # Remove currency symbols and extract number
    # Handles formats like "4,95 €", "15.50", "20€", etc.
    number_match = re.search(r'(\d+[,.]?\d*)', price_str)
    if number_match:
        # Replace comma with dot for float conversion
        number_str = number_match.group(1).replace(',', '.')
        try:
            price_value = float(number_str)

            # Map to category based on ranges
            if 1 <= price_value <= 5:
                return "€ (Budget)"
            elif 6 <= price_value <= 20:
                return "€€ (Moderate)"
            elif price_value >= 21:
                return "€€€ (Premium)"
        except ValueError:
            pass

    return None

# Helper: Format one item to match Notion property types
def format_properties(item):
    return {
        "Treat Name": {
            "title": [{"text": {"content": item.get("Treat Name", "")}}]
        },
        "Category": {
            "select": {"name": item.get("Category", "")} if item.get("Category") else None
        },
        "Description": {
            "rich_text": [{"text": {"content": item.get("Description", "")}}]
        },
        "Export Potential": {
            "select": {"name": item.get("Export Potential", "")} if item.get("Export Potential") else None
        },
        "Photo": {
            "url": item.get("Photo") or None
        },
        "Price Range": {
            "select": {"name": map_price_to_range(item.get("Price Range"))} if map_price_to_range(item.get("Price Range")) else None
        },
        "Product Type": {
            "select": {"name": item.get("Product Type", "")} if item.get("Product Type") else None
        },
        "Purchase URL": {
            "url": item.get("Purchase URL") or None
        },
        "Rating": {
            "number": float(item.get("Rating", 0) or 0)
        },
        "Region": {
            "select": {"name": item.get("Region", "")} if item.get("Region") else None
        },
        "Shelf Life": {
            "select": {"name": item.get("Shelf Life", "")} if item.get("Shelf Life") else None
        },
        "Tried": {
            "checkbox": str(item.get("Tried", "")).strip().lower() in ["yes", "true", "1"]
        },
        "Where to Buy": {
            "rich_text": [{"text": {"content": item.get("Where to Buy", "")}}]
        }
    }

@app.route('/update-treat', methods=['POST'])
def update_treat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload received"}), 400

    treat_items = data.get('treat_items', [])
    if not isinstance(treat_items, list):
        return jsonify({"error": "'treat_items' must be a list"}), 400

    created = 0
    updated = 0

    for item in treat_items:
        page = find_page_by_name(item.get("Treat Name", ""))
        props = format_properties(item)

        if page:
            notion.pages.update(page_id=page['id'], properties=props)
            updated += 1
        else:
            notion.pages.create(parent={"database_id": DATABASE_ID}, properties=props)
            created += 1

    return jsonify({
        "status": "success",
        "created": created,
        "updated": updated,
        "total": len(treat_items)
    })

@app.route('/read-treats', methods=['GET'])
def read_treats():
    all_items = []
    cursor = None
    while True:
        response = notion.databases.query(
            database_id=DATABASE_ID,
            start_cursor=cursor,
            page_size=100
        )
        for page in response.get('results', []):
            props = page['properties']
            item = {}

            # Helper function to safely extract property values
            def get_prop(prop_name, prop_type, default=""):
                try:
                    if prop_name not in props:
                        return default
                    prop = props[prop_name]
                    if prop_type == 'title':
                        return prop['title'][0]['text']['content'] if prop.get('title') else default
                    elif prop_type == 'rich_text':
                        return prop['rich_text'][0]['text']['content'] if prop.get('rich_text') else default
                    elif prop_type == 'url':
                        return prop['url'] if prop.get('url') else default
                    elif prop_type == 'number':
                        return prop['number'] if prop.get('number') is not None else default
                    elif prop_type == 'checkbox':
                        return prop.get('checkbox', False)
                    elif prop_type == 'select':
                        return prop['select']['name'] if prop.get('select') else default
                except (KeyError, IndexError, TypeError):
                    return default
                return default

            item = {
                "Treat Name": get_prop('Treat Name', 'title'),
                "Category": get_prop('Category', 'select'),
                "Description": get_prop('Description', 'rich_text'),
                "Export Potential": get_prop('Export Potential', 'rich_text'),
                "Photo": get_prop('Photo', 'url'),
                "Price Range": get_prop('Price Range', 'select'),
                "Product Type": get_prop('Product Type', 'rich_text'),
                "Purchase URL": get_prop('Purchase URL', 'url'),
                "Rating": get_prop('Rating', 'number'),
                "Region": get_prop('Region', 'rich_text'),
                "Shelf Life": get_prop('Shelf Life', 'rich_text'),
                "Tried": get_prop('Tried', 'checkbox', False),
                "Where to Buy": get_prop('Where to Buy', 'rich_text')
            }
            all_items.append(item)
        if response.get('has_more', False):
            cursor = response.get('next_cursor')
        else:
            break
    return jsonify({"treat_items": all_items})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
