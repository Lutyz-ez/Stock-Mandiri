from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd
import io
import uuid
import asyncio

ROOT = Path(__file__).parent
BOOK = ROOT / "inventory.xlsx"
LOCK = asyncio.Lock()
PRODUCT_COLS = ["id", "sku", "barcode", "name", "short_name", "category", "brand", "model", "unit", "cost_price", "sell_price", "stock", "min_stock", "location", "supplier", "active", "created_at", "updated_at"]
MOVEMENT_COLS = ["id", "transaction_no", "sku", "product", "type", "qty_in", "qty_out", "before", "after", "price", "note", "user", "created_at"]
SALE_COLS = ["id", "invoice", "date", "customer", "sku", "product", "qty", "sell_price", "discount", "total", "cost_total", "status", "payment_method", "sales", "note"]

def now_iso(): return datetime.now(timezone.utc).isoformat()

def seed_book():
    if BOOK.exists(): return
    products = [
        [str(uuid.uuid4()), "MTC-300", "899100300001", "Tire Charger", "Tire Charger", "Automotive Equipment", "MTC", "300", "unit", 5000000, 6500000, 10, 3, "Rak A-01", "PT Sumber Teknik", True, now_iso(), now_iso()],
        [str(uuid.uuid4()), "KTN-87A05", "899100300002", "Tool Box Set KING TONY 85PCS", "Tool Box Set", "Hand Tools", "KING TONY", "87A05", "set", 2500000, 3200000, 15, 5, "Rak B-02", "KING TONY Indonesia", True, now_iso(), now_iso()],
        [str(uuid.uuid4()), "INS-2301-10", "899100300003", "Dial Indicator INSIZE 2301-10", "Dial Indicator", "Measuring Tools", "INSIZE", "2301-10", "unit", 750000, 1100000, 20, 5, "Rak C-01", "INSIZE Official", True, now_iso(), now_iso()],
    ]
    movements = [[str(uuid.uuid4()), "OPENING", p[1], p[3], "Stok Awal", p[11], 0, 0, p[11], p[10], "Stok awal sistem", "Admin", now_iso()] for p in products]
    sales = [[str(uuid.uuid4()), "INV-001", (datetime.now(timezone.utc)-timedelta(days=1)).date().isoformat(), "CV Makmur Jaya", "KTN-87A05", products[1][3], 2, products[1][10], 0, products[1][10]*2, products[1][9]*2, "Selesai", "Transfer", "Admin", ""]]
    # Opening demo sale is intentionally reflected in the workbook stock.
    products[1][11] -= 2; movements.append([str(uuid.uuid4()), "INV-001", products[1][1], products[1][3], "Penjualan", 0, 2, 15, 13, products[1][10], "Demo transaksi", "Admin", sales[0][2]])
    with pd.ExcelWriter(BOOK, engine="openpyxl") as writer:
        pd.DataFrame(products, columns=PRODUCT_COLS).to_excel(writer, sheet_name="products", index=False)
        pd.DataFrame(movements, columns=MOVEMENT_COLS).to_excel(writer, sheet_name="movements", index=False)
        pd.DataFrame(sales, columns=SALE_COLS).to_excel(writer, sheet_name="sales", index=False)

def read_sheet(name, cols):
    seed_book()
    try: df = pd.read_excel(BOOK, sheet_name=name)
    except ValueError: return pd.DataFrame(columns=cols)
    return df.reindex(columns=cols).fillna("")

def write_book(products, movements, sales):
    with pd.ExcelWriter(BOOK, engine="openpyxl") as writer:
        products.to_excel(writer, sheet_name="products", index=False)
        movements.to_excel(writer, sheet_name="movements", index=False)
        sales.to_excel(writer, sheet_name="sales", index=False)

class ProductIn(BaseModel):
    sku: str; barcode: str = ""; name: str; short_name: str = ""; category: str = ""; brand: str = ""; model: str = ""; unit: str = "unit"; cost_price: float = 0; sell_price: float = 0; stock: int = 0; min_stock: int = 0; location: str = ""; supplier: str = ""
class ReceiptIn(BaseModel):
    transaction_no: str; sku: str; qty: int = Field(gt=0); cost_price: float = 0; supplier: str = ""; location: str = ""; note: str = ""
class SaleIn(BaseModel):
    invoice: str; sku: str; qty: int = Field(gt=0); customer: str = ""; discount: float = 0; payment_method: str = "Transfer"; note: str = ""

app = FastAPI(title="Mandiri Sejahtera Inventory")
api = APIRouter(prefix="/api")

@api.get("/")
async def root(): return {"message": "Mandiri Sejahtera Inventory API", "storage": "Excel"}

@api.get("/products")
async def products(search: str = ""):
    df = read_sheet("products", PRODUCT_COLS)
    if search: df = df[df.apply(lambda r: search.lower() in " ".join(map(str, r.tolist())).lower(), axis=1)]
    return df.to_dict("records")

@api.post("/products")
async def create_product(item: ProductIn):
    async with LOCK:
        df = read_sheet("products", PRODUCT_COLS)
        if item.sku.upper() in set(df.sku.astype(str).str.upper()): raise HTTPException(409, "SKU sudah digunakan")
        stamp = now_iso(); row = {**item.model_dump(), "id": str(uuid.uuid4()), "sku": item.sku.upper(), "active": True, "created_at": stamp, "updated_at": stamp}
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True); write_book(df, read_sheet("movements", MOVEMENT_COLS), read_sheet("sales", SALE_COLS))
        return row

@api.post("/receipts")
async def receive_stock(item: ReceiptIn):
    async with LOCK:
        p = read_sheet("products", PRODUCT_COLS); idx = p.index[p.sku.astype(str).str.upper() == item.sku.upper()].tolist()
        if not idx: raise HTTPException(404, "SKU tidak ditemukan")
        i = idx[0]; before = int(p.at[i, "stock"]); after = before + item.qty; p.at[i, "stock"] = after; p.at[i, "updated_at"] = now_iso()
        m = read_sheet("movements", MOVEMENT_COLS); row = {"id": str(uuid.uuid4()), "transaction_no": item.transaction_no, "sku": p.at[i,"sku"], "product": p.at[i,"name"], "type": "Barang Masuk", "qty_in": item.qty, "qty_out": 0, "before": before, "after": after, "price": item.cost_price, "note": item.note, "user": "Operator", "created_at": now_iso()}
        m = pd.concat([m, pd.DataFrame([row])], ignore_index=True); write_book(p, m, read_sheet("sales", SALE_COLS)); return row

@api.post("/sales")
async def create_sale(item: SaleIn):
    async with LOCK:
        p = read_sheet("products", PRODUCT_COLS); idx = p.index[p.sku.astype(str).str.upper() == item.sku.upper()].tolist()
        if not idx: raise HTTPException(404, "SKU tidak ditemukan")
        i = idx[0]; before = int(p.at[i,"stock"])
        if item.qty > before: raise HTTPException(400, f"Stok tidak cukup. Tersedia {before} unit")
        price, cost = float(p.at[i,"sell_price"]), float(p.at[i,"cost_price"]); total = item.qty * price - item.discount; stamp = now_iso(); p.at[i,"stock"] = before-item.qty; p.at[i,"updated_at"] = stamp
        s = read_sheet("sales", SALE_COLS); sale = {"id": str(uuid.uuid4()), "invoice": item.invoice, "date": stamp[:10], "customer": item.customer, "sku": p.at[i,"sku"], "product": p.at[i,"name"], "qty": item.qty, "sell_price": price, "discount": item.discount, "total": total, "cost_total": item.qty*cost, "status": "Selesai", "payment_method": item.payment_method, "sales": "Operator", "note": item.note}
        m = read_sheet("movements", MOVEMENT_COLS); movement = {"id": str(uuid.uuid4()), "transaction_no": item.invoice, "sku": p.at[i,"sku"], "product": p.at[i,"name"], "type": "Penjualan", "qty_in": 0, "qty_out": item.qty, "before": before, "after": before-item.qty, "price": price, "note": item.note, "user": "Operator", "created_at": stamp}
        s = pd.concat([s, pd.DataFrame([sale])], ignore_index=True); m = pd.concat([m, pd.DataFrame([movement])], ignore_index=True); write_book(p,m,s); return sale

@api.get("/movements")
async def movements(sku: str = ""):
    df = read_sheet("movements", MOVEMENT_COLS)
    if sku: df = df[df.sku.astype(str).str.upper() == sku.upper()]
    return df.iloc[::-1].to_dict("records")

@api.get("/sales")
async def sales(): return read_sheet("sales", SALE_COLS).iloc[::-1].to_dict("records")

@api.get("/dashboard")
async def dashboard():
    p, m, s = read_sheet("products", PRODUCT_COLS), read_sheet("movements", MOVEMENT_COLS), read_sheet("sales", SALE_COLS)
    today = datetime.now(timezone.utc).date().isoformat(); month = today[:7]; valid = s[s.status == "Selesai"]
    today_sales = valid[valid.date.astype(str) == today]; month_sales = valid[valid.date.astype(str).str.startswith(month)]
    top = valid.groupby("product", as_index=False).agg(qty=("qty","sum"), omzet=("total","sum")).sort_values("qty", ascending=False).head(5).to_dict("records") if len(valid) else []
    return {"total_products": len(p), "total_stock": int(pd.to_numeric(p.stock, errors="coerce").sum()), "inventory_value": float((pd.to_numeric(p.stock, errors="coerce")*pd.to_numeric(p.cost_price, errors="coerce")).sum()), "today_revenue": float(pd.to_numeric(today_sales.total, errors="coerce").sum()), "month_revenue": float(pd.to_numeric(month_sales.total, errors="coerce").sum()), "today_units": int(pd.to_numeric(today_sales.qty, errors="coerce").sum()), "low_stock": p[p.stock.astype(float) <= p.min_stock.astype(float)].to_dict("records"), "recent_movements": m.iloc[::-1].head(6).to_dict("records"), "top_products": top}

@api.get("/export/{sheet}")
async def export_sheet(sheet: str):
    names = {"products": PRODUCT_COLS, "movements": MOVEMENT_COLS, "sales": SALE_COLS}
    if sheet not in names: raise HTTPException(404, "Laporan tidak ditemukan")
    data = read_sheet(sheet, names[sheet]).to_csv(index=False).encode(); return StreamingResponse(io.BytesIO(data), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={sheet}.csv"})

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])