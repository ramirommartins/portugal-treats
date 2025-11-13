import requests
import json

# Test data
data = {
    "treat_items": [
        {
            "Treat Name": "Pão de sementes",
            "Category": "Bread",
            "Description": "Medalhas de ouro, sabor inovador e qualidade premiada.",
            "Price Range": "4,95 €",
            "Purchase URL": "https://padariadias.pt",
            "Where to Buy": "Padaria Dias (Covilhã), Padaria Portuguesa (Lisboa)"
        }
    ]
}

# Test local endpoint
try:
    response = requests.post(
        'http://localhost:5000/update-treat',
        json=data,
        headers={'Content-Type': 'application/json'}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
