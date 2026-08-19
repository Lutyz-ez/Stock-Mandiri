# Mandiri Sejahtera Inventory Management — PRD

## Problem Statement
Membangun aplikasi web profesional berbahasa Indonesia untuk distributor alat teknik, otomotif, industrial tools, dan perlengkapan kerja. Sistem harus membantu operator memahami omzet, stok, nilai inventory, produk laris, serta histori setiap perubahan stok.

## User Personas
- **Operator gudang:** mencatat barang masuk, mencari SKU, dan memeriksa saldo stok.
- **Operator penjualan:** membuat transaksi, memvalidasi stok, dan melihat omzet.
- **Pemilik/manajer:** membaca dashboard, laporan penjualan, HPP, laba kotor, dan margin.

## Core Requirements (Static)
- Dashboard KPI, tren omzet, produk terlaris, stok menipis, dan aktivitas terbaru.
- Produk dengan SKU unik, barcode, harga modal/jual, stok minimum, lokasi, supplier, dan status.
- Barang masuk menambah stok dan membuat stock movement.
- Penjualan mengurangi stok, mencegah stok negatif, menghitung total, omzet, HPP, dan laba kotor.
- Stock movement menyimpan saldo sebelum/sesudah, transaksi, qty masuk/keluar, harga, user, waktu.
- Pencarian SKU/barcode/nama/brand dan detail produk.
- Laporan penjualan dan export CSV.
- Penyimpanan utama versi pertama menggunakan workbook Excel.

## Architecture Decisions
- **Frontend:** React 19 dengan CSS operasional desktop-first, responsive mobile, lucide-react, dan data-testid lengkap.
- **Backend:** FastAPI pada port supervisor 8001 dengan endpoint `/api`.
- **Storage:** `backend/inventory.xlsx` dengan sheet `products`, `movements`, dan `sales`; pandas/openpyxl membaca dan menulis workbook.
- **Consistency:** operasi penerimaan/penjualan memakai asyncio lock dalam proses, memperbarui produk serta histori movement/sale dalam satu penulisan workbook.
- **Login:** ditunda sesuai pilihan pengguna; aplikasi menampilkan Operator tanpa autentikasi.
- **Protected environment:** konfigurasi `.env` tidak diubah.

## What's Been Implemented
### 2026-08-12
- Dashboard operasional dengan KPI omzet hari ini/bulan ini, total produk, total stok, nilai inventory, chart omzet, stok menipis, aktivitas, dan top products.
- Master produk dengan data demo tiga SKU, tambah produk, validasi SKU duplikat, detail produk, pencarian global dan filter katalog.
- Barang masuk dengan validasi SKU dan pencatatan saldo sebelum/sesudah.
- Penjualan dengan perhitungan total, HPP/laba di laporan, blokir qty melebihi stok, pengurangan saldo, dan movement otomatis.
- Stock movement ledger dan laporan penjualan dengan total transaksi/unit/omzet/laba kotor serta export CSV.
- Smoke test dan regression test alur barang masuk → penjualan → histori → omzet berhasil.

## Prioritized Backlog
### P0
- Tambahkan transaksi retur penjualan yang mengoreksi stok dan omzet bersih.
- Tambahkan import Excel dengan preview, validasi kolom, dan laporan error per baris.
- Tambahkan backup/versioning workbook dan proteksi konkurensi lintas proses.

### P1
- Customer dan supplier master data beserta histori pembelian/barang masuk.
- Multi-gudang dan saldo per lokasi.
- Barcode scanner/print barcode, pagination, filter tanggal, dan export Excel/PDF.

### P2
- Login JWT dan role Admin/Manager/Staff.
- Audit log perubahan sebelum/sesudah dan pengaturan sistem.
- Optimasi storage ke relational database saat volume transaksi besar.

## Next Tasks
1. Bangun import Excel dengan preview dan validasi SKU/harga/qty.
2. Tambahkan retur penjualan dan koreksi omzet bersih.
3. Tambahkan modul customer, supplier, serta histori per entitas.