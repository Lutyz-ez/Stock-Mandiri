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
- Filter tanggal (Hari ini/Minggu/Bulan/Tahun/Kustom) di Dashboard & Laporan
- Produk: Edit & Hapus (HARD DELETE, permintaan user); form tanpa Harga Modal & Min Stok; supplier/lokasi opsional

## Implemented (2026-06, sesi ini) — Jatuh tempo pembayaran
- Sheet `sales` kolom baru `due_date`. POST /api/sales wajib `due_date` jika status Tempo/Cicilan (400 jika kosong), dikosongkan jika Lunas.
- GET /api/sales/reminders → invoice Tempo/Cicilan belum lunas (group per invoice, days_left, overdue, due_today, total). Juga dikirim di GET /api/dashboard sebagai `payment_reminders`.
- PUT /api/sales/{invoice}/pay → tandai invoice Lunas.
- UI: form Penjualan menampilkan input tanggal saat Tempo/Cicilan; Dashboard panel "Pengingat Pembayaran" + banner merah bila jatuh tempo + tombol "Lunas"; Laporan kolom JATUH TEMPO.
- Tested: testing_agent iteration_2 — semua lolos.

## Backlog (P1/P2)
- Halaman detail produk penuh + grafik penjualan produk
- Customer & Supplier master
- Retur penjualan / pembelian
- Multi gudang (kolom `warehouse` di stock)
- Audit log & user role login
- Barcode scan (input + generator)
- Halaman daftar piutang (semua tempo/cicilan + histori pembayaran cicilan parsial)
