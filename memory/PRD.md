# Mandiri Sejahtera Inventory Management — PRD

## Original brief
Aplikasi web profesional untuk Manajemen Inventory Gudang & Penjualan (distributor alat teknik, otomotif, industrial tools). Storage utama: file Excel (`inventory.xlsx`), tanpa login (permintaan user).

## Architecture
- Backend: FastAPI (`/app/backend/server.py`) baca/tulis `inventory.xlsx` via `openpyxl` + `pandas`. Semua tulis melindungi konsistensi dengan `asyncio.Lock`.
- Frontend: React (`/app/frontend/src/App.js`) + Tailwind/plain CSS (`App.css`). Font: IBM Plex Sans/Mono + Manrope.
- Sheets: `products`, `movements`, `sales`.

## Implemented (2026-02-04, updated)
- Dashboard KPI + panels (omzet hari/bulan, top produk, low stock, aktivitas)
- Produk: CRUD + Import Excel (preview+validasi+commit) + Export CSV + Harga Jual Online
- Barang Masuk multi-SKU (dynamic rows)
- Penjualan multi-SKU, invoice opsional (auto INV-YYYYMMDD-nnn), diskon dihapus, status pembayaran (Lunas/Tempo/Cicilan)
- Stock movement ledger, kartu stok per SKU
- Laporan penjualan + margin/laba kotor
- Validasi: SKU unik, stok tidak boleh negatif, preview import (SKU kosong/duplikat/harga invalid)

## Backlog (P1/P2)
- Halaman detail produk penuh + grafik penjualan produk
- Customer & Supplier master
- Retur penjualan / pembelian
- Multi gudang (kolom `warehouse` di stock)
- Audit log & user role login
- Barcode scan (input + generator)
- Filter tanggal custom di dashboard & laporan
