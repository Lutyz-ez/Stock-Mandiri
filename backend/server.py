from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List
import pandas as pd
import io
import uuid
import asyncio
import os

ROOT = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
BOOK = DATA_DIR / "inventory.xlsx"
LOCK = asyncio.Lock()
PRODUCT_COLS = ["id", "sku", "barcode", "name", "short_name", "category", "brand", "model", "unit",
                "cost_price", "sell_price", "online_price", "stock", "min_stock", "location", "supplier",
                "active", "created_at", "updated_at"]
MOVEMENT_COLS = ["id", "transaction_no", "sku", "product", "type", "qty_in", "qty_out", "before", "after",
                 "price", "note", "user", "created_at"]
SALE_COLS = ["id", "invoice", "date", "customer", "sku", "product", "qty", "sell_price", "discount",
             "total", "cost_total", "status", "payment_status", "payment_method", "sales", "note", "due_date"]


def now_iso(): return datetime.now(timezone.utc).isoformat()


def seed_book():
    if BOOK.exists(): return
    products = [
        [str(uuid.uuid4()), "MTC-300", "899100300001", "Tire Charger", "Tire Charger", "Automotive Equipment", "MTC", "300", "unit", 5000000, 6500000, 6800000, 10, 3, "Rak A-01", "PT Sumber Teknik", True, now_iso(), now_iso()],
        [str(uuid.uuid4()), "KTN-87A05", "899100300002", "Tool Box Set KING TONY 85PCS", "Tool Box Set", "Hand Tools", "KING TONY", "87A05", "set", 2500000, 3200000, 3350000, 15, 5, "Rak B-02", "KING TONY Indonesia", True, now_iso(), now_iso()],
        [str(uuid.uuid4()), "INS-2301-10", "899100300003", "Dial Indicator INSIZE 2301-10", "Dial Indicator", "Measuring Tools", "INSIZE", "2301-10", "unit", 750000, 1100000, 1150000, 20, 5, "Rak C-01", "INSIZE Official", True, now_iso(), now_iso()],
    ]
    movements = [[str(uuid.uuid4()), "OPENING", p[1], p[3], "Stok Awal", p[12], 0, 0, p[12], p[10], "Stok awal sistem", "Admin", now_iso()] for p in products]
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    sale_row = [str(uuid.uuid4()), "INV-001", yesterday, "CV Makmur Jaya", "KTN-87A05", products[1][3], 2, products[1][10], 0, products[1][10]*2, products[1][9]*2, "Selesai", "Lunas", "Transfer", "Admin", ""]
    sales = [sale_row]
    products[1][12] -= 2
    movements.append([str(uuid.uuid4()), "INV-001", products[1][1], products[1][3], "Penjualan", 0, 2, 15, 13, products[1][10], "Demo transaksi", "Admin", yesterday])
    with pd.ExcelWriter(BOOK, engine="openpyxl") as writer:
        pd.DataFrame(products, columns=PRODUCT_COLS).to_excel(writer, sheet_name="products", index=False)
        pd.DataFrame(movements, columns=MOVEMENT_COLS).to_excel(writer, sheet_name="movements", index=False)
        pd.DataFrame(sales, columns=SALE_COLS).to_excel(writer, sheet_name="sales", index=False)


def read_sheet(name, cols):
    seed_book()
    try:
        df = pd.read_excel(BOOK, sheet_name=name)
    except ValueError:
        return pd.DataFrame(columns=cols)
    return df.reindex(columns=cols).fillna("")


def write_book(products, movements, sales):
    with pd.ExcelWriter(BOOK, engine="openpyxl") as writer:
        products.to_excel(writer, sheet_name="products", index=False)
        movements.to_excel(writer, sheet_name="movements", index=False)
        sales.to_excel(writer, sheet_name="sales", index=False)


def next_invoice(sales_df):
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"INV-{today}-"
    existing = [str(x) for x in sales_df.invoice.tolist() if str(x).startswith(prefix)]
    n = 1
    while f"{prefix}{n:03d}" in existing: n += 1
    return f"{prefix}{n:03d}"


class ProductIn(BaseModel):
    sku: str
    barcode: str = ""
    name: str
    short_name: str = ""
    category: str = ""
    brand: str = ""
    model: str = ""
    unit: str = "unit"
    cost_price: float = 0
    sell_price: float = 0
    online_price: float = 0
    stock: int = 0
    min_stock: int = 0
    location: str = ""
    supplier: str = ""


class ReceiptItem(BaseModel):
    sku: str
    qty: int = Field(gt=0)
    cost_price: float = 0


class ReceiptIn(BaseModel):
    transaction_no: str
    supplier: str = ""
    location: str = ""
    note: str = ""
    items: List[ReceiptItem]


class SaleItem(BaseModel):
    sku: str
    qty: int = Field(gt=0)
    sell_price: Optional[float] = None


class SaleIn(BaseModel):
    invoice: Optional[str] = ""
    customer: str = ""
    payment_method: str = "Transfer"
    payment_status: str = "Lunas"  # Lunas / Tempo / Cicilan
    due_date: Optional[str] = ""
    note: str = ""
    items: List[SaleItem]


class BulkProductsIn(BaseModel):
    products: List[ProductIn]


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    barcode: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
    online_price: Optional[float] = None
    stock: Optional[int] = None
    min_stock: Optional[int] = None
    location: Optional[str] = None
    supplier: Optional[str] = None
    active: Optional[bool] = None


app = FastAPI(title="Mandiri Sejahtera Inventory")
api = APIRouter(prefix="/api")


@api.get("/")
async def root(): return {"message": "Mandiri Sejahtera Inventory API", "storage": "Excel"}


@api.get("/products")
async def products(search: str = ""):
    df = read_sheet("products", PRODUCT_COLS)
    if search:
        df = df[df.apply(lambda r: search.lower() in " ".join(map(str, r.tolist())).lower(), axis=1)]
    return df.to_dict("records")


@api.post("/products")
async def create_product(item: ProductIn):
    async with LOCK:
        df = read_sheet("products", PRODUCT_COLS)
        if item.sku.upper() in set(df.sku.astype(str).str.upper()):
            raise HTTPException(409, "SKU sudah digunakan")
        stamp = now_iso()
        row = {**item.model_dump(), "id": str(uuid.uuid4()), "sku": item.sku.upper(),
               "active": True, "created_at": stamp, "updated_at": stamp}
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        write_book(df, read_sheet("movements", MOVEMENT_COLS), read_sheet("sales", SALE_COLS))
        return row


@api.put("/products/{sku}")
async def update_product(sku: str, patch: ProductUpdate):
    async with LOCK:
        df = read_sheet("products", PRODUCT_COLS)
        idx = df.index[df.sku.astype(str).str.upper() == sku.upper()].tolist()
        if not idx:
            raise HTTPException(404, "Produk tidak ditemukan")
        i = idx[0]
        for k, v in patch.model_dump(exclude_unset=True).items():
            if v is not None:
                df.at[i, k] = v
        df.at[i, "updated_at"] = now_iso()
        write_book(df, read_sheet("movements", MOVEMENT_COLS), read_sheet("sales", SALE_COLS))
        return df.iloc[i].to_dict()


@api.delete("/products/{sku}")
async def delete_product(sku: str):
    async with LOCK:
        df = read_sheet("products", PRODUCT_COLS)
        idx = df.index[df.sku.astype(str).str.upper() == sku.upper()].tolist()
        if not idx:
            raise HTTPException(404, "Produk tidak ditemukan")
        df = df.drop(idx[0]).reset_index(drop=True)
        write_book(df, read_sheet("movements", MOVEMENT_COLS), read_sheet("sales", SALE_COLS))
        return {"deleted": sku.upper()}


@api.post("/receipts")
async def receive_stock(data: ReceiptIn):
    async with LOCK:
        p = read_sheet("products", PRODUCT_COLS)
        m = read_sheet("movements", MOVEMENT_COLS)
        stamp = now_iso()
        created = []
        for it in data.items:
            idx = p.index[p.sku.astype(str).str.upper() == it.sku.upper()].tolist()
            if not idx:
                raise HTTPException(404, f"SKU tidak ditemukan: {it.sku}")
            i = idx[0]
            before = int(p.at[i, "stock"])
            after = before + it.qty
            p.at[i, "stock"] = after
            p.at[i, "updated_at"] = stamp
            if it.cost_price and float(it.cost_price) > 0:
                p.at[i, "cost_price"] = it.cost_price
            row = {"id": str(uuid.uuid4()), "transaction_no": data.transaction_no, "sku": p.at[i, "sku"],
                   "product": p.at[i, "name"], "type": "Barang Masuk", "qty_in": it.qty, "qty_out": 0,
                   "before": before, "after": after, "price": it.cost_price, "note": data.note,
                   "user": "Operator", "created_at": stamp}
            m = pd.concat([m, pd.DataFrame([row])], ignore_index=True)
            created.append(row)
        write_book(p, m, read_sheet("sales", SALE_COLS))
        return {"transaction_no": data.transaction_no, "items": created}


@api.post("/sales")
async def create_sale(data: SaleIn):
    async with LOCK:
        p = read_sheet("products", PRODUCT_COLS)
        s = read_sheet("sales", SALE_COLS)
        m = read_sheet("movements", MOVEMENT_COLS)
        stamp = now_iso()
        invoice = (data.invoice or "").strip() or next_invoice(s)
        due_date = (data.due_date or "").strip()
        if data.payment_status in ("Tempo", "Cicilan"):
            if not due_date:
                raise HTTPException(400, "Tanggal pembayaran wajib diisi untuk status Tempo/Cicilan")
            try:
                datetime.fromisoformat(due_date)
            except ValueError:
                raise HTTPException(400, "Format tanggal pembayaran tidak valid (YYYY-MM-DD)")
        else:
            due_date = ""
        # Prevalidate every line before committing anything
        line_products = []
        for it in data.items:
            idx = p.index[p.sku.astype(str).str.upper() == it.sku.upper()].tolist()
            if not idx:
                raise HTTPException(404, f"SKU tidak ditemukan: {it.sku}")
            i = idx[0]
            before = int(p.at[i, "stock"])
            if it.qty > before:
                raise HTTPException(400, f"Stok {p.at[i,'sku']} tidak cukup. Tersedia {before} unit")
            line_products.append((i, before, it))
        created = []
        for i, before, it in line_products:
            price = float(it.sell_price) if it.sell_price not in (None, "", 0) else float(p.at[i, "sell_price"])
            cost = float(p.at[i, "cost_price"])
            total = it.qty * price
            after = before - it.qty
            p.at[i, "stock"] = after
            p.at[i, "updated_at"] = stamp
            sale = {"id": str(uuid.uuid4()), "invoice": invoice, "date": stamp[:10], "customer": data.customer,
                    "sku": p.at[i, "sku"], "product": p.at[i, "name"], "qty": it.qty, "sell_price": price,
                    "discount": 0, "total": total, "cost_total": it.qty * cost, "status": "Selesai",
                    "payment_status": data.payment_status, "payment_method": data.payment_method,
                    "sales": "Operator", "note": data.note, "due_date": due_date}
            movement = {"id": str(uuid.uuid4()), "transaction_no": invoice, "sku": p.at[i, "sku"],
                        "product": p.at[i, "name"], "type": "Penjualan", "qty_in": 0, "qty_out": it.qty,
                        "before": before, "after": after, "price": price, "note": data.note,
                        "user": "Operator", "created_at": stamp}
            s = pd.concat([s, pd.DataFrame([sale])], ignore_index=True)
            m = pd.concat([m, pd.DataFrame([movement])], ignore_index=True)
            created.append(sale)
        write_book(p, m, s)
        return {"invoice": invoice, "items": created}


@api.get("/movements")
async def movements(sku: str = ""):
    df = read_sheet("movements", MOVEMENT_COLS)
    if sku:
        df = df[df.sku.astype(str).str.upper() == sku.upper()]
    return df.iloc[::-1].to_dict("records")


@api.get("/sales")
async def sales(start: str = "", end: str = ""):
    df = read_sheet("sales", SALE_COLS)
    if len(df) and start:
        df = df[df.date.astype(str) >= start]
    if len(df) and end:
        df = df[df.date.astype(str) <= end]
    return df.iloc[::-1].to_dict("records")


def payment_reminders(s):
    today = datetime.now(timezone.utc).date()
    if not len(s):
        return []
    pending = s[(s.payment_status.astype(str).isin(["Tempo", "Cicilan"])) & (s.due_date.astype(str).str.strip() != "")]
    if not len(pending):
        return []
    out = []
    for inv, g in pending.groupby("invoice", sort=False):
        due_raw = str(g.due_date.iloc[0])[:10]
        try:
            due = datetime.fromisoformat(due_raw).date()
        except ValueError:
            continue
        days_left = (due - today).days
        out.append({
            "invoice": str(inv),
            "customer": str(g.customer.iloc[0]),
            "payment_status": str(g.payment_status.iloc[0]),
            "due_date": due.isoformat(),
            "days_left": days_left,
            "overdue": days_left < 0,
            "due_today": days_left == 0,
            "total": float(pd.to_numeric(g.total, errors="coerce").sum()),
            "items": int(len(g)),
        })
    out.sort(key=lambda r: r["days_left"])
    return out


@api.get("/sales/reminders")
async def sales_reminders():
    return payment_reminders(read_sheet("sales", SALE_COLS))


@api.put("/sales/{invoice}/pay")
async def mark_paid(invoice: str):
    async with LOCK:
        s = read_sheet("sales", SALE_COLS)
        idx = s.index[s.invoice.astype(str) == invoice].tolist()
        if not idx:
            raise HTTPException(404, "Invoice tidak ditemukan")
        s.loc[idx, "payment_status"] = "Lunas"
        write_book(read_sheet("products", PRODUCT_COLS), read_sheet("movements", MOVEMENT_COLS), s)
        return {"invoice": invoice, "payment_status": "Lunas", "rows": len(idx)}


def _period_bounds(start: str, end: str):
    today = datetime.now(timezone.utc).date()
    if not end:
        end = today.isoformat()
    if not start:
        start = (today - timedelta(days=6)).isoformat()
    return start, end


@api.get("/dashboard")
async def dashboard(start: str = "", end: str = ""):
    p, m, s = read_sheet("products", PRODUCT_COLS), read_sheet("movements", MOVEMENT_COLS), read_sheet("sales", SALE_COLS)
    today = datetime.now(timezone.utc).date().isoformat()
    month = today[:7]
    p_start, p_end = _period_bounds(start, end)
    valid = s[s.status == "Selesai"] if len(s) else s
    today_sales = valid[valid.date.astype(str) == today] if len(valid) else valid
    month_sales = valid[valid.date.astype(str).str.startswith(month)] if len(valid) else valid
    period = valid[(valid.date.astype(str) >= p_start) & (valid.date.astype(str) <= p_end)] if len(valid) else valid
    top = period.groupby("product", as_index=False).agg(qty=("qty", "sum"), omzet=("total", "sum")).sort_values("omzet", ascending=False).head(5).to_dict("records") if len(period) else []
    # Chart buckets: daily buckets across the range (max 31)
    from datetime import date as _date
    d0 = _date.fromisoformat(p_start); d1 = _date.fromisoformat(p_end)
    days = (d1 - d0).days
    if days < 0: days = 0
    step = max(1, (days // 30) + 1)
    buckets = []
    cur = d0
    while cur <= d1:
        nxt = cur + timedelta(days=step - 1)
        if nxt > d1: nxt = d1
        chunk = period[(period.date.astype(str) >= cur.isoformat()) & (period.date.astype(str) <= nxt.isoformat())] if len(period) else period
        buckets.append({
            "label": cur.strftime("%d/%m") if step == 1 else f"{cur.strftime('%d/%m')}–{nxt.strftime('%d/%m')}",
            "value": float(pd.to_numeric(chunk.total, errors="coerce").sum()) if len(chunk) else 0.0,
        })
        cur = nxt + timedelta(days=1)
    return {
        "total_products": len(p),
        "total_stock": int(pd.to_numeric(p.stock, errors="coerce").sum()),
        "inventory_value": float((pd.to_numeric(p.stock, errors="coerce") * pd.to_numeric(p.cost_price, errors="coerce")).sum()),
        "today_revenue": float(pd.to_numeric(today_sales.total, errors="coerce").sum()),
        "month_revenue": float(pd.to_numeric(month_sales.total, errors="coerce").sum()),
        "today_units": int(pd.to_numeric(today_sales.qty, errors="coerce").sum()),
        "period_start": p_start,
        "period_end": p_end,
        "period_revenue": float(pd.to_numeric(period.total, errors="coerce").sum()) if len(period) else 0.0,
        "period_units": int(pd.to_numeric(period.qty, errors="coerce").sum()) if len(period) else 0,
        "period_transactions": int(period.invoice.nunique()) if len(period) else 0,
        "period_cost": float(pd.to_numeric(period.cost_total, errors="coerce").sum()) if len(period) else 0.0,
        "chart": buckets,
        "low_stock": p[p.stock.astype(float) <= p.min_stock.astype(float)].to_dict("records"),
        "recent_movements": m.iloc[::-1].head(6).to_dict("records"),
        "top_products": top,
        "payment_reminders": payment_reminders(s),
    }


@api.get("/export/{sheet}")
async def export_sheet(sheet: str):
    names = {"products": PRODUCT_COLS, "movements": MOVEMENT_COLS, "sales": SALE_COLS}
    if sheet not in names:
        raise HTTPException(404, "Laporan tidak ditemukan")
    data = read_sheet(sheet, names[sheet]).to_csv(index=False).encode()
    return StreamingResponse(io.BytesIO(data), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={sheet}.csv"})


# ---------- Excel Import ----------

IMPORT_COLS = {
    "sku": ["sku", "kode"],
    "name": ["nama produk", "nama", "product", "product name"],
    "brand": ["brand", "merek"],
    "category": ["kategori", "category"],
    "sell_price": ["harga jual", "sell price", "price"],
    "online_price": ["harga jual online", "harga online", "online price", "harga ecommerce", "harga e-commerce"],
    "stock": ["stok", "stock", "qty"],
    "min_stock": ["min stok", "minimum stok", "min stock"],
    "location": ["lokasi", "rak", "location"],
    "supplier": ["supplier", "vendor"],
}


def normalize_header(h): return str(h or "").strip().lower()


def map_columns(df):
    lookup = {normalize_header(c): c for c in df.columns}
    mapping = {}
    for key, aliases in IMPORT_COLS.items():
        for a in aliases:
            if a in lookup:
                mapping[key] = lookup[a]
                break
    return mapping


@api.post("/import/products/preview")
async def import_preview(file: UploadFile = File(...)):
    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content)) if file.filename.lower().endswith((".xlsx", ".xls")) else pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"Gagal membaca file: {e}")
    mapping = map_columns(df)
    required = ["sku", "name", "sell_price"]
    missing = [r for r in required if r not in mapping]
    if missing:
        raise HTTPException(400, f"Kolom wajib tidak ditemukan: {', '.join(missing)}. Butuh minimal: SKU, Nama Produk, Harga Jual")
    existing_skus = set(read_sheet("products", PRODUCT_COLS).sku.astype(str).str.upper())
    seen = set()
    rows = []
    def clean(v):
        if v is None: return ""
        s = str(v).strip()
        if s.lower() == "nan": return ""
        return s
    for i, r in df.iterrows():
        item = {k: r[v] if v in df.columns else "" for k, v in mapping.items()}
        errors = []
        sku_raw = clean(item.get("sku", "")).upper()
        if not sku_raw:
            errors.append("SKU kosong")
        elif sku_raw in existing_skus:
            errors.append("SKU sudah ada")
        elif sku_raw in seen:
            errors.append("SKU duplikat di file")
        name_val = clean(item.get("name", ""))
        if not name_val:
            errors.append("Nama produk kosong")
        try:
            sell = float(item.get("sell_price") or 0)
            if sell <= 0: errors.append("Harga jual tidak valid")
        except Exception:
            errors.append("Harga jual tidak valid"); sell = 0
        try:
            online = float(item.get("online_price") or 0)
        except Exception:
            online = 0
        try:
            stock = int(float(item.get("stock") or 0))
        except Exception:
            stock = 0
        try:
            min_stock = int(float(item.get("min_stock") or 0))
        except Exception:
            min_stock = 0
        if sku_raw and not errors:
            seen.add(sku_raw)
        rows.append({
            "row": int(i) + 2,
            "sku": sku_raw,
            "name": name_val,
            "brand": clean(item.get("brand", "")),
            "category": clean(item.get("category", "")),
            "sell_price": sell,
            "online_price": online,
            "stock": stock,
            "min_stock": min_stock,
            "location": clean(item.get("location", "")),
            "supplier": clean(item.get("supplier", "")),
            "errors": errors,
            "valid": len(errors) == 0,
        })
    return {"rows": rows, "total": len(rows), "valid": sum(1 for r in rows if r["valid"]),
            "invalid": sum(1 for r in rows if not r["valid"])}


@api.post("/import/products/commit")
async def import_commit(data: BulkProductsIn):
    async with LOCK:
        df = read_sheet("products", PRODUCT_COLS)
        existing = set(df.sku.astype(str).str.upper())
        stamp = now_iso()
        added = 0
        skipped = []
        new_rows = []
        for item in data.products:
            sku = item.sku.strip().upper()
            if not sku or sku in existing:
                skipped.append(sku); continue
            new_rows.append({**item.model_dump(), "id": str(uuid.uuid4()), "sku": sku,
                             "active": True, "created_at": stamp, "updated_at": stamp})
            existing.add(sku); added += 1
        if new_rows:
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            write_book(df, read_sheet("movements", MOVEMENT_COLS), read_sheet("sales", SALE_COLS))
        return {"added": added, "skipped": skipped}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
