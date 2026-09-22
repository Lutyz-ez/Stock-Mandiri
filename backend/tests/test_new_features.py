"""Regression tests for new features: hard-delete products, payment due_date, reminders."""
import os
import time
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback: read frontend/.env
    envp = "/app/frontend/.env"
    if os.path.exists(envp):
        for line in open(envp):
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Product hard delete ----------
class TestProductHardDelete:
    def test_hard_delete_product(self, api):
        sku = "TEST-DEL-" + str(int(time.time()))
        # Create
        r = api.post(f"{BASE_URL}/api/products", json={
            "sku": sku, "name": "TEST Delete Me", "sell_price": 1000, "stock": 1
        })
        assert r.status_code == 200, r.text
        # Confirm present
        lst = api.get(f"{BASE_URL}/api/products").json()
        assert any(p["sku"] == sku.upper() for p in lst)
        # Delete
        r = api.delete(f"{BASE_URL}/api/products/{sku}")
        assert r.status_code == 200
        # Confirm absent (hard delete)
        lst = api.get(f"{BASE_URL}/api/products").json()
        assert not any(p["sku"] == sku.upper() for p in lst), "Product should be hard-deleted"

    def test_delete_unknown_sku_404(self, api):
        r = api.delete(f"{BASE_URL}/api/products/NOPE-XYZ-999")
        assert r.status_code == 404


# ---------- Sales with due_date ----------
def _first_available_sku(api):
    items = api.get(f"{BASE_URL}/api/products").json()
    for p in items:
        if int(p.get("stock", 0) or 0) > 0:
            return p["sku"]
    return None


class TestSalesDueDate:
    def test_tempo_without_due_date_400(self, api):
        sku = _first_available_sku(api)
        assert sku
        r = api.post(f"{BASE_URL}/api/sales", json={
            "customer": "TEST_Tempo NoDate", "payment_status": "Tempo",
            "items": [{"sku": sku, "qty": 1}]
        })
        assert r.status_code == 400
        assert "Tanggal pembayaran wajib" in r.json().get("detail", "")

    def test_cicilan_without_due_date_400(self, api):
        sku = _first_available_sku(api)
        r = api.post(f"{BASE_URL}/api/sales", json={
            "customer": "TEST_Cicilan NoDate", "payment_status": "Cicilan",
            "items": [{"sku": sku, "qty": 1}]
        })
        assert r.status_code == 400

    def test_tempo_with_due_date_ok(self, api):
        sku = _first_available_sku(api)
        due = (date.today() + timedelta(days=10)).isoformat()
        r = api.post(f"{BASE_URL}/api/sales", json={
            "customer": "TEST_TempoOK", "payment_status": "Tempo",
            "due_date": due, "items": [{"sku": sku, "qty": 1}]
        })
        assert r.status_code == 200, r.text
        data = r.json()
        for it in data["items"]:
            assert it["due_date"] == due
        # store for later
        pytest.tempo_invoice = data["invoice"]
        pytest.tempo_due = due

    def test_lunas_ignores_due_date(self, api):
        sku = _first_available_sku(api)
        due = (date.today() + timedelta(days=5)).isoformat()
        r = api.post(f"{BASE_URL}/api/sales", json={
            "customer": "TEST_Lunas", "payment_status": "Lunas",
            "due_date": due, "items": [{"sku": sku, "qty": 1}]
        })
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["due_date"] in ("", None)


# ---------- Reminders ----------
class TestReminders:
    def test_reminders_shape_and_sort(self, api):
        r = api.get(f"{BASE_URL}/api/sales/reminders")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        prev = None
        for row in data:
            for k in ["invoice", "customer", "payment_status", "due_date",
                      "days_left", "overdue", "due_today", "total", "items"]:
                assert k in row, f"missing {k}"
            assert row["payment_status"] in ("Tempo", "Cicilan")
            if prev is not None:
                assert row["days_left"] >= prev
            prev = row["days_left"]

    def test_reminders_overdue_flag(self, api):
        data = api.get(f"{BASE_URL}/api/sales/reminders").json()
        today = date.today()
        for row in data:
            due = date.fromisoformat(row["due_date"])
            assert row["overdue"] == (due < today)

    def test_dashboard_includes_reminders(self, api):
        r = api.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert "payment_reminders" in d
        rem = api.get(f"{BASE_URL}/api/sales/reminders").json()
        assert len(d["payment_reminders"]) == len(rem)

    def test_mark_paid(self, api):
        # create a fresh tempo invoice
        sku = _first_available_sku(api)
        due = (date.today() + timedelta(days=3)).isoformat()
        r = api.post(f"{BASE_URL}/api/sales", json={
            "customer": "TEST_MarkPaid", "payment_status": "Tempo",
            "due_date": due, "items": [{"sku": sku, "qty": 1}]
        })
        invoice = r.json()["invoice"]
        # should appear in reminders
        rem = api.get(f"{BASE_URL}/api/sales/reminders").json()
        assert any(x["invoice"] == invoice for x in rem)
        # pay it
        r2 = api.put(f"{BASE_URL}/api/sales/{invoice}/pay")
        assert r2.status_code == 200
        # gone from reminders
        rem2 = api.get(f"{BASE_URL}/api/sales/reminders").json()
        assert not any(x["invoice"] == invoice for x in rem2)

    def test_mark_paid_unknown_404(self, api):
        r = api.put(f"{BASE_URL}/api/sales/INV-DOES-NOT-EXIST/pay")
        assert r.status_code == 404
