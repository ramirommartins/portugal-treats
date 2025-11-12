import os
from flask import Flask, request, jsonify
from notion_client import Client

app = Flask(__name__)
# just for the sake of committing. 22

# NOTION DB & SECRET - TBR by variables or config file in production
NOTION_TOKEN = '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'
DATABASE_ID = '2a5bed35c6cb80a9937bf8abcde98bd1'

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

# Helper: Format one item to match Notion property types
def format_properties(item):
    return {
        "Treat Name": {
            "title": [{"text": {"content": item.get("Treat Name", "")}}]
        },
        "Category": {
            "rich_text": [{"text": {"content": item.get("Category", "")}}]
        },
        "Description": {
            "rich_text": [{"text": {"content": item.get("Description", "")}}]
        },
        "Export Potential": {
            "rich_text": [{"text": {"content": item.get("Export Potential", "")}}]
        },
        "Photo": {
            "url": item.get("Photo", "")
        },
        "Price Range": {
            "rich_text": [{"text": {"content": item.get("Price Range", "")}}]
        },
        "Product Type": {
            "rich_text": [{"text": {"content": item.get("Product Type", "")}}]
        },
        "Purchase URL": {
            "url": item.get("Purchase URL", "")
        },
        "Rating": {
            "number": float(item.get("Rating", 0) or 0)
        },
        "Region": {
            "rich_text": [{"text": {"content": item.get("Region", "")}}]
        },
        "Shelf Life": {
            "rich_text": [{"text": {"content": item.get("Shelf Life", "")}}]
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
        response = notion.databases.query(database_id=DATABASE_ID, start_cursor=cursor, page_size=100)
        for page in response.get('results', []):
            props = page['properties']
            item = {
                "Treat Name": props['Treat Name']['title'][0]['text']['content'] if props['Treat Name']['title'] else "",
                "Category": props['Category']['rich_text'][0]['text']['content'] if props['Category']['rich_text'] else "",
                "Description": props['Description']['rich_text'][0]['text']['content'] if props['Description']['rich_text'] else "",
                "Export Potential": props['Export Potential']['rich_text'][0]['text']['content'] if props['Export Potential']['rich_text'] else "",
                "Photo": props['Photo']['url'] if props['Photo']['url'] else "",
                "Price Range": props['Price Range']['rich_text'][0]['text']['content'] if props['Price Range']['rich_text'] else "",
                "Product Type": props['Product Type']['rich_text'][0]['text']['content'] if props['Product Type']['rich_text'] else "",
                "Purchase URL": props['Purchase URL']['url'] if props['Purchase URL']['url'] else "",
                "Rating": props['Rating']['number'] if props['Rating']['number'] is not None else "",
                "Region": props['Region']['rich_text'][0]['text']['content'] if props['Region']['rich_text'] else "",
                "Shelf Life": props['Shelf Life']['rich_text'][0]['text']['content'] if props['Shelf Life']['rich_text'] else "",
                "Tried": props['Tried']['checkbox'],
                "Where to Buy": props['Where to Buy']['rich_text'][0]['text']['content'] if props['Where to Buy']['rich_text'] else ""
            }
            all_items.append(item)
        if response.get('has_more', False):
            cursor = response.get('next_cursor')
        else:
            break
    return jsonify({"treat_items": all_items})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
