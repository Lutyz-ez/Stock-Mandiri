import os
import uuid
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://mandiri-sales.preview.emergentagent.com").rstrip("/")


def test_dashboard_products_and_search():
    dashboard = requests.get(f"{BASE_URL}/api/dashboard", timeout=20)
    assert dashboard.status_code == 200
    assert {"total_products", "month_revenue", "low_stock", "recent_movements", "top_products"} <= dashboard.json().keys()
    products = requests.get(f"{BASE_URL}/api/products", timeout=20)
    assert products.status_code == 200 and isinstance(products.json(), list)
    search = requests.get(f"{BASE_URL}/api/products", params={"search": "MTC-300"}, timeout=20)
    assert search.status_code == 200 and any(p["sku"] == "MTC-300" for p in search.json())


def test_duplicate_sku_rejected():
    response = requests.post(f"{BASE_URL}/api/products", json={"sku": "MTC-300", "name": "Duplicate", "sell_price": 1}, timeout=20)
    assert response.status_code == 409
    assert "SKU" in response.text


def test_receipt_movement_and_sale_stock_validation():
    sku = "MTC-300"
    before = next(p for p in requests.get(f"{BASE_URL}/api/products", timeout=20).json() if p["sku"] == sku)["stock"]
    receipt = requests.post(f"{BASE_URL}/api/receipts", json={"transaction_no": f"TEST-{uuid.uuid4().hex[:8]}", "sku": sku, "qty": 1, "cost_price": 1}, timeout=20)
    assert receipt.status_code == 200 and receipt.json()["after"] == before + 1
    sale = requests.post(f"{BASE_URL}/api/sales", json={"invoice": f"TEST-{uuid.uuid4().hex[:8]}", "sku": sku, "qty": 1}, timeout=20)
    assert sale.status_code == 200 and sale.json()["qty"] == 1
    blocked = requests.post(f"{BASE_URL}/api/sales", json={"invoice": f"TEST-{uuid.uuid4().hex[:8]}", "sku": sku, "qty": 999999}, timeout=20)
    assert blocked.status_code == 400 and "Stok tidak cukup" in blocked.text


def test_movements_sales_and_exports():
    movements = requests.get(f"{BASE_URL}/api/movements", timeout=20)
    sales = requests.get(f"{BASE_URL}/api/sales", timeout=20)
    assert movements.status_code == 200 and isinstance(movements.json(), list)
    assert sales.status_code == 200 and isinstance(sales.json(), list)
    export = requests.get(f"{BASE_URL}/api/export/sales", timeout=20)
    assert export.status_code == 200 and "invoice" in export.text.splitlines()[0]