import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { BarChart3, Boxes, CalendarRange, ClipboardList, Download, LayoutDashboard, Menu, PackagePlus, Plus, Search, ShoppingCart, Trash2, Upload, X } from "lucide-react";
import "./App.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const rupiah = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(n || 0));
const NAV = [["Dashboard", LayoutDashboard], ["Produk", Boxes], ["Barang Masuk", PackagePlus], ["Penjualan", ShoppingCart], ["Stock Movement", ClipboardList], ["Laporan", BarChart3]];

const iso = (d) => d.toISOString().slice(0, 10);
function presetRange(key) {
  const t = new Date(); t.setHours(0, 0, 0, 0);
  if (key === "today") return { start: iso(t), end: iso(t) };
  if (key === "week") { const d = new Date(t); d.setDate(t.getDate() - t.getDay() + (t.getDay() === 0 ? -6 : 1)); return { start: iso(d), end: iso(t) }; }
  if (key === "month") return { start: iso(new Date(t.getFullYear(), t.getMonth(), 1)), end: iso(t) };
  if (key === "year") return { start: iso(new Date(t.getFullYear(), 0, 1)), end: iso(t) };
  const d = new Date(t); d.setDate(t.getDate() - 6); return { start: iso(d), end: iso(t) };
}

function DateFilter({ range, setRange, preset, setPreset }) {
  const options = [["today", "Hari ini"], ["week", "Minggu ini"], ["month", "Bulan ini"], ["year", "Tahun ini"], ["custom", "Kustom"]];
  const pick = (k) => { setPreset(k); if (k !== "custom") setRange(presetRange(k)); };
  return (
    <div className="date-filter" data-testid="date-filter">
      <CalendarRange size={16} />
      <div className="preset-group">
        {options.map(([k, l]) => (
          <button key={k} type="button" className={preset === k ? "active" : ""} onClick={() => pick(k)} data-testid={`date-preset-${k}`}>{l}</button>
        ))}
      </div>
      {preset === "custom" && (
        <div className="custom-range">
          <input type="date" value={range.start} onChange={e => setRange({ ...range, start: e.target.value })} data-testid="date-custom-start" />
          <span>—</span>
          <input type="date" value={range.end} onChange={e => setRange({ ...range, end: e.target.value })} data-testid="date-custom-end" />
        </div>
      )}
    </div>
  );
}

function Sidebar({ page, setPage, open, close, productsCount }) {
  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <div className="brand">
        <span className="brand-mark">MS</span>
        <div><b>Mandiri Sejahtera</b><small>INVENTORY SYSTEM</small></div>
        <button className="mobile-close" onClick={close} data-testid="sidebar-close-button"><X size={18} /></button>
      </div>
      <div className="side-label">OPERASIONAL</div>
      <nav>
        {NAV.map(([name, Icon]) => (
          <button key={name} className={page === name ? "active" : ""} onClick={() => { setPage(name); close(); }} data-testid={`sidebar-${name.toLowerCase().replaceAll(" ", "-")}-link`}>
            <Icon size={18} /><span>{name}</span>
            {name === "Produk" && <em>{productsCount}</em>}
          </button>
        ))}
      </nav>
      <div className="side-foot">
        <div className="excel-status"><span className="status-dot" /><div><b>Excel aktif</b><small>Penyimpanan utama</small></div></div>
        <small>Sinkronisasi lokal · sekarang</small>
      </div>
    </aside>
  );
}

function Header({ setOpen, query, setQuery, setPage }) {
  return (
    <header className="topbar">
      <button className="menu-button" onClick={() => setOpen(true)} data-testid="sidebar-open-button"><Menu size={20} /></button>
      <div className="crumb">Mandiri Sejahtera <span>/</span> <b>Operasional</b></div>
      <div className="global-search">
        <Search size={17} />
        <input data-testid="global-sku-search-input" placeholder="Cari SKU, barcode, produk, brand..." value={query} onChange={e => { setQuery(e.target.value); setPage("Produk"); }} />
        <kbd>⌘ K</kbd>
      </div>
      <div className="user-chip"><span>OP</span><div><b>Operator</b><small>Administrator</small></div></div>
    </header>
  );
}

function Kpi({ label, value, note, tone = "" }) {
  return (
    <div className={`kpi ${tone}`} data-testid={`${label.toLowerCase().replaceAll(" ", "-")}-kpi`}>
      <small>{label}</small><strong>{value}</strong><span>{note}</span>
    </div>
  );
}

function Dashboard({ data, setPage, range, setRange, preset, setPreset }) {
  const maxBar = Math.max(1, ...(data.chart || []).map(b => b.value));
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <p className="eyebrow">RINGKASAN PERIODE</p>
          <h1>Selamat datang kembali, Operator.</h1>
          <p className="sub">Pantau arus stok dan penjualan dari satu tempat.</p>
        </div>
        <button className="primary" onClick={() => setPage("Penjualan")} data-testid="dashboard-new-sale-button"><Plus size={17} /> Transaksi penjualan</button>
      </div>
      <DateFilter range={range} setRange={setRange} preset={preset} setPreset={setPreset} />
      <div className="kpi-grid">
        <Kpi label="Omzet Periode" value={rupiah(data.period_revenue)} note={`${data.period_units} unit · ${data.period_transactions} invoice`} tone="accent" />
        <Kpi label="Laba Kotor" value={rupiah((data.period_revenue || 0) - (data.period_cost || 0))} note={`${data.period_revenue ? Math.round(((data.period_revenue - data.period_cost) / data.period_revenue) * 100) : 0}% margin`} />
        <Kpi label="Omzet Hari Ini" value={rupiah(data.today_revenue)} note={`${data.today_units} unit terjual`} />
        <Kpi label="Total Stok" value={`${data.total_stock} unit`} note={`Nilai ${rupiah(data.inventory_value)}`} />
      </div>
      <div className="dashboard-grid">
        <section className="panel revenue-panel">
          <div className="panel-head"><div><p className="eyebrow">PERFORMA PENJUALAN</p><h2>Omzet {data.period_start} → {data.period_end}</h2></div><span className="legend"><i /> Omzet</span></div>
          <div className="bars">{(data.chart || []).map((b, i) => (
            <div className="bar-col" key={i}><div className="bar" style={{ height: `${Math.max(6, (b.value / maxBar) * 100)}%` }} title={rupiah(b.value)} /><small>{b.label}</small></div>
          ))}</div>
          <div className="chart-total"><b>{rupiah(data.period_revenue)}</b><span>total periode</span></div>
        </section>
        <section className="panel alert-panel">
          <div className="panel-head"><div><p className="eyebrow">PERLU PERHATIAN</p><h2>Stok menipis</h2></div><button className="text-button" onClick={() => setPage("Produk")} data-testid="dashboard-low-stock-link">Lihat semua</button></div>
          {data.low_stock.length ? data.low_stock.map(p => (
            <div className="alert-row" key={p.sku} data-testid="stock-alert-row">
              <span className="warning-icon">!</span>
              <div><b>{p.name}</b><small className="mono">{p.sku} · {p.location || "Belum ada lokasi"}</small></div>
              <strong>{p.stock} <small>/ min {p.min_stock}</small></strong>
            </div>
          )) : <div className="empty">Semua stok dalam kondisi aman.</div>}
        </section>
        <section className="panel movement-panel">
          <div className="panel-head"><div><p className="eyebrow">AKTIVITAS TERBARU</p><h2>Pergerakan stok</h2></div><button className="text-button" onClick={() => setPage("Stock Movement")} data-testid="dashboard-movements-link">Buka kartu stok</button></div>
          <div className="table-wrap"><table><thead><tr><th>WAKTU</th><th>TRANSAKSI</th><th>PRODUK</th><th>JENIS</th><th>QTY</th></tr></thead>
            <tbody>{data.recent_movements.map(m => (
              <tr key={m.id}>
                <td className="muted">{String(m.created_at).slice(11, 16)}</td>
                <td className="mono">{m.transaction_no}</td>
                <td><b>{m.product}</b><small className="mono">{m.sku}</small></td>
                <td><span className={`badge ${m.qty_in > 0 ? "green" : "orange"}`}>{m.type}</span></td>
                <td className="qty">{m.qty_in > 0 ? "+" : "-"}{m.qty_in || m.qty_out}</td>
              </tr>
            ))}</tbody></table></div>
        </section>
        <section className="panel top-panel">
          <div className="panel-head"><div><p className="eyebrow">TERLARIS PADA PERIODE</p><h2>Top penjualan</h2></div><span className="period">{data.period_start} → {data.period_end}</span></div>
          {data.top_products.length ? data.top_products.map((p, i) => (
            <div className="top-row" key={p.product}>
              <span className="rank">0{i + 1}</span>
              <div><b>{p.product}</b><small>{p.qty} unit terjual</small></div>
              <strong>{rupiah(p.omzet)}</strong>
            </div>
          )) : <div className="empty">Belum ada transaksi pada periode ini.</div>}
        </section>
      </div>
    </div>
  );
}

function ProductForm({ onClose, onSaved }) {
  const [form, setForm] = useState({ sku: "", name: "", category: "", brand: "", cost_price: "", sell_price: "", online_price: "", stock: "", min_stock: "", location: "", supplier: "" });
  const save = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/products`, {
        ...form,
        cost_price: +form.cost_price || 0,
        sell_price: +form.sell_price || 0,
        online_price: +form.online_price || 0,
        stock: +form.stock || 0,
        min_stock: +form.min_stock || 0,
      });
      onSaved();
    } catch (err) { alert(err.response?.data?.detail || "Gagal menyimpan produk"); }
  };
  const fields = [
    ["sku", "SKU *"], ["name", "Nama produk *"], ["brand", "Brand"], ["category", "Kategori"],
    ["cost_price", "Harga modal"], ["sell_price", "Harga jual *"], ["online_price", "Harga jual online"],
    ["stock", "Stok awal"], ["min_stock", "Minimum stok"], ["location", "Lokasi / rak"], ["supplier", "Supplier"],
  ];
  return (
    <div className="modal-backdrop">
      <form className="modal" onSubmit={save}>
        <div className="modal-head">
          <div><p className="eyebrow">MASTER PRODUK</p><h2>Tambah produk</h2></div>
          <button type="button" onClick={onClose} data-testid="product-form-close-button"><X size={18} /></button>
        </div>
        <div className="form-grid">
          {fields.map(([k, l]) => (
            <label key={k}>{l}
              <input required={k === "sku" || k === "name" || k === "sell_price"}
                type={k.includes("price") || ["stock", "min_stock"].includes(k) ? "number" : "text"}
                value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}
                data-testid={`product-form-${k}-input`} />
            </label>
          ))}
        </div>
        <button className="primary full" data-testid="product-form-submit-button"><Plus size={17} /> Simpan produk</button>
      </form>
    </div>
  );
}

function ImportModal({ onClose, onDone }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const upload = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await axios.post(`${API}/import/products/preview`, fd);
      setPreview(data);
    } catch (err) { alert(err.response?.data?.detail || "Gagal membaca file"); }
    setLoading(false);
  };
  const commit = async () => {
    const valid = preview.rows.filter(r => r.valid).map(r => ({
      sku: r.sku, name: r.name, brand: r.brand, category: r.category,
      sell_price: r.sell_price, online_price: r.online_price,
      stock: r.stock, min_stock: r.min_stock, location: r.location, supplier: r.supplier,
    }));
    try {
      const { data } = await axios.post(`${API}/import/products/commit`, { products: valid });
      alert(`Berhasil impor ${data.added} produk. Dilewati: ${data.skipped.length}`);
      onDone();
    } catch (err) { alert(err.response?.data?.detail || "Gagal impor"); }
  };
  return (
    <div className="modal-backdrop">
      <div className="modal modal-wide">
        <div className="modal-head">
          <div><p className="eyebrow">IMPORT DATA</p><h2>Impor produk dari Excel</h2></div>
          <button type="button" onClick={onClose} data-testid="import-close-button"><X size={18} /></button>
        </div>
        {!preview ? (
          <div>
            <p className="sub" style={{ marginTop: 0 }}>Format kolom yang didukung: <b>SKU, Nama Produk, Brand, Kategori, Harga Jual, Harga Jual Online, Stok, Min Stok, Lokasi, Supplier</b>. Kolom wajib: SKU, Nama Produk, Harga Jual.</p>
            <label style={{ display: "block", margin: "20px 0" }}>
              <input type="file" accept=".xlsx,.xls,.csv" onChange={e => setFile(e.target.files[0])} data-testid="import-file-input" />
            </label>
            <button className="primary full" disabled={!file || loading} onClick={upload} data-testid="import-preview-button">
              <Upload size={17} /> {loading ? "Memproses..." : "Baca & preview"}
            </button>
          </div>
        ) : (
          <div>
            <div className="report-strip" style={{ gridTemplateColumns: "repeat(3,1fr)" }}>
              <Kpi label="Total baris" value={preview.total} note="Dari file" />
              <Kpi label="Valid" value={preview.valid} note="Siap impor" tone="accent" />
              <Kpi label="Bermasalah" value={preview.invalid} note="Akan dilewati" />
            </div>
            <div className="table-wrap" style={{ maxHeight: 320, overflow: "auto", border: "1px solid var(--line)" }}>
              <table>
                <thead><tr><th>#</th><th>SKU</th><th>NAMA</th><th>HARGA JUAL</th><th>STOK</th><th>STATUS</th></tr></thead>
                <tbody>{preview.rows.map(r => (
                  <tr key={r.row} data-testid="import-preview-row">
                    <td className="muted">{r.row}</td>
                    <td className="mono">{r.sku || "—"}</td>
                    <td><b>{r.name || "—"}</b>{r.errors.length > 0 && <small className="red-text">{r.errors.join(", ")}</small>}</td>
                    <td className="money">{rupiah(r.sell_price)}</td>
                    <td className="qty">{r.stock}</td>
                    <td><span className={`badge ${r.valid ? "green" : "red"}`}>{r.valid ? "VALID" : "SKIP"}</span></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
              <button className="secondary" onClick={() => setPreview(null)} data-testid="import-back-button">Ganti file</button>
              <button className="primary" style={{ flex: 1, justifyContent: "center" }} disabled={preview.valid === 0} onClick={commit} data-testid="import-commit-button">
                <Upload size={17} /> Impor {preview.valid} produk valid
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Products({ products, query, setQuery, reload, setSelected }) {
  const [show, setShow] = useState(false);
  const [showImport, setShowImport] = useState(false);
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <p className="eyebrow">KATALOG & MASTER DATA</p>
          <h1>Produk</h1>
          <p className="sub">Kelola SKU, harga, lokasi, dan ambang stok.</p>
        </div>
        <div className="head-actions">
          <button className="secondary" onClick={() => setShowImport(true)} data-testid="products-import-button"><Upload size={16} /> Import Excel</button>
          <a className="secondary" href={`${API}/export/products`} data-testid="products-export-button"><Download size={16} /> Export CSV</a>
          <button className="primary" onClick={() => setShow(true)} data-testid="product-create-button"><Plus size={17} /> Produk baru</button>
        </div>
      </div>
      <div className="toolbar">
        <div className="inline-search"><Search size={16} /><input data-testid="products-search-input" placeholder="Filter produk..." value={query} onChange={e => setQuery(e.target.value)} /></div>
        <span className="result-count">{products.length} produk ditemukan</span>
      </div>
      <section className="panel table-panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>PRODUK / SKU</th><th>KATEGORI</th><th>HARGA JUAL</th><th>HARGA ONLINE</th><th>STOK</th><th>LOKASI</th><th>STATUS</th></tr></thead>
            <tbody>{products.map(p => (
              <tr key={p.id} onClick={() => setSelected(p)} className="clickable" data-testid="product-table-row">
                <td><b>{p.name}</b><small className="mono">{p.sku} · {p.brand || "Tanpa brand"}</small></td>
                <td>{p.category || "—"}</td>
                <td className="money">{rupiah(p.sell_price)}</td>
                <td className="money">{Number(p.online_price) > 0 ? rupiah(p.online_price) : "—"}</td>
                <td><span className={`stock-number ${Number(p.stock) <= Number(p.min_stock) ? "low" : ""}`}>{p.stock} <small>{p.unit}</small></span></td>
                <td className="mono">{p.location || "—"}</td>
                <td><span className={`badge ${Number(p.stock) === 0 ? "red" : Number(p.stock) <= Number(p.min_stock) ? "amber" : "green"}`}>{Number(p.stock) === 0 ? "STOK HABIS" : Number(p.stock) <= Number(p.min_stock) ? "MENIPIS" : "AMAN"}</span></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>
      {show && <ProductForm onClose={() => setShow(false)} onSaved={() => { setShow(false); reload(); }} />}
      {showImport && <ImportModal onClose={() => setShowImport(false)} onDone={() => { setShowImport(false); reload(); }} />}
    </div>
  );
}

function ReceiptPage({ products, reload }) {
  const [header, setHeader] = useState({ transaction_no: "GR-" + Date.now().toString().slice(-6), supplier: "", note: "" });
  const [items, setItems] = useState([{ sku: "", qty: 1, cost_price: "" }]);
  const setItem = (idx, patch) => setItems(items.map((it, i) => i === idx ? { ...it, ...patch } : it));
  const addRow = () => setItems([...items, { sku: "", qty: 1, cost_price: "" }]);
  const removeRow = (idx) => setItems(items.length > 1 ? items.filter((_, i) => i !== idx) : items);
  const submit = async (e) => {
    e.preventDefault();
    const payload = {
      transaction_no: header.transaction_no,
      supplier: header.supplier,
      note: header.note,
      items: items.filter(it => it.sku).map(it => ({ sku: it.sku, qty: +it.qty || 0, cost_price: +it.cost_price || 0 })),
    };
    if (!payload.items.length) { alert("Tambahkan minimal satu produk"); return; }
    try {
      await axios.post(`${API}/receipts`, payload);
      alert(`Barang masuk tersimpan (${payload.items.length} item). Stok telah diperbarui.`);
      setItems([{ sku: "", qty: 1, cost_price: "" }]);
      setHeader({ ...header, transaction_no: "GR-" + Date.now().toString().slice(-6), note: "" });
      reload();
    } catch (err) { alert(err.response?.data?.detail || "Transaksi gagal"); }
  };
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <p className="eyebrow">RECEIVING / INBOUND</p>
          <h1>Barang masuk</h1>
          <p className="sub">Catat penerimaan multi-SKU dari supplier dan tambah saldo stok.</p>
        </div>
      </div>
      <form className="panel form-panel" onSubmit={submit}>
        <div className="panel-head"><h2>Detail penerimaan</h2><span className="badge blue">Excel aktif</span></div>
        <div className="form-grid">
          <label>Nomor penerimaan
            <input required value={header.transaction_no} onChange={e => setHeader({ ...header, transaction_no: e.target.value })} data-testid="receipt-form-transaction_no-input" />
          </label>
          <label>Supplier
            <input value={header.supplier} onChange={e => setHeader({ ...header, supplier: e.target.value })} data-testid="receipt-form-supplier-input" />
          </label>
        </div>
        <div className="line-header"><span>PRODUK</span><span>QTY</span><span>HARGA MODAL</span><span /></div>
        {items.map((it, idx) => {
          const sel = products.find(p => p.sku === it.sku);
          return (
            <div className="line-row" key={idx} data-testid="receipt-line-row">
              <select value={it.sku} onChange={e => setItem(idx, { sku: e.target.value, cost_price: products.find(p => p.sku === e.target.value)?.cost_price || "" })} data-testid={`receipt-line-${idx}-sku-input`}>
                <option value="">Pilih SKU / produk...</option>
                {products.map(p => <option key={p.sku} value={p.sku}>{p.sku} — {p.name} (stok {p.stock})</option>)}
              </select>
              <input type="number" min="1" value={it.qty} onChange={e => setItem(idx, { qty: e.target.value })} data-testid={`receipt-line-${idx}-qty-input`} />
              <input type="number" placeholder={sel ? `default ${sel.cost_price}` : "harga modal"} value={it.cost_price} onChange={e => setItem(idx, { cost_price: e.target.value })} data-testid={`receipt-line-${idx}-cost-input`} />
              <button type="button" className="icon-btn" onClick={() => removeRow(idx)} data-testid={`receipt-line-${idx}-remove-button`}><Trash2 size={16} /></button>
            </div>
          );
        })}
        <button type="button" className="secondary" onClick={addRow} data-testid="receipt-add-row-button" style={{ marginTop: 10 }}><Plus size={15} /> Tambah baris</button>
        <label style={{ marginTop: 18 }}>Catatan
          <textarea value={header.note} onChange={e => setHeader({ ...header, note: e.target.value })} data-testid="receipt-form-note-input" />
        </label>
        <button className="primary full" data-testid="receipt-form-submit-button"><PackagePlus size={17} /> Konfirmasi barang masuk</button>
      </form>
    </div>
  );
}

function SalesPage({ products, reload }) {
  const [header, setHeader] = useState({ invoice: "", customer: "", payment_method: "Transfer", payment_status: "Lunas", note: "" });
  const [items, setItems] = useState([{ sku: "", name: "", qty: 1, sell_price: "" }]);
  const setItem = (idx, patch) => setItems(items.map((it, i) => i === idx ? { ...it, ...patch } : it));
  const addRow = () => setItems([...items, { sku: "", name: "", qty: 1, sell_price: "" }]);
  const removeRow = (idx) => setItems(items.length > 1 ? items.filter((_, i) => i !== idx) : items);
  const onSelectSku = (idx, sku) => {
    const p = products.find(x => x.sku === sku);
    setItem(idx, { sku, name: p?.name || "", sell_price: p?.sell_price || "" });
  };
  const total = items.reduce((a, it) => a + (Number(it.qty || 0) * Number(it.sell_price || 0)), 0);
  const stockError = items.find(it => {
    const p = products.find(x => x.sku === it.sku);
    return it.sku && p && Number(it.qty) > Number(p.stock);
  });
  const submit = async (e) => {
    e.preventDefault();
    const payload = {
      invoice: header.invoice || "",
      customer: header.customer,
      payment_method: header.payment_method,
      payment_status: header.payment_status,
      note: header.note,
      items: items.filter(it => it.sku).map(it => ({ sku: it.sku, qty: +it.qty || 0, sell_price: +it.sell_price || 0 })),
    };
    if (!payload.items.length) { alert("Tambahkan minimal satu produk"); return; }
    try {
      const { data } = await axios.post(`${API}/sales`, payload);
      alert(`Penjualan berhasil disimpan · Invoice ${data.invoice}. Stok telah dikurangi.`);
      setItems([{ sku: "", name: "", qty: 1, sell_price: "" }]);
      setHeader({ invoice: "", customer: "", payment_method: "Transfer", payment_status: "Lunas", note: "" });
      reload();
    } catch (err) { alert(err.response?.data?.detail || "Transaksi gagal"); }
  };
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <p className="eyebrow">SALES / OUTBOUND</p>
          <h1>Penjualan</h1>
          <p className="sub">Buat transaksi multi-SKU, validasi stok, dan atur status pembayaran.</p>
        </div>
      </div>
      <form className="transaction-layout" onSubmit={submit}>
        <section className="panel form-panel">
          <div className="panel-head"><h2>Detail transaksi</h2><span className="badge blue">Excel aktif</span></div>
          <div className="form-grid">
            <label>Nomor invoice (opsional)
              <input placeholder="Otomatis jika kosong" value={header.invoice} onChange={e => setHeader({ ...header, invoice: e.target.value })} data-testid="sale-form-invoice-input" />
            </label>
            <label>Customer
              <input value={header.customer} onChange={e => setHeader({ ...header, customer: e.target.value })} data-testid="sale-form-customer-input" />
            </label>
            <label>Metode pembayaran
              <select value={header.payment_method} onChange={e => setHeader({ ...header, payment_method: e.target.value })} data-testid="sale-form-payment-method-input">
                <option>Transfer</option><option>Tunai</option><option>QRIS</option><option>Kartu Kredit</option>
              </select>
            </label>
            <label>Status pembayaran
              <select value={header.payment_status} onChange={e => setHeader({ ...header, payment_status: e.target.value })} data-testid="sale-form-payment-status-input">
                <option>Lunas</option><option>Tempo</option><option>Cicilan</option>
              </select>
            </label>
          </div>
          <div className="line-header"><span>PRODUK</span><span>QTY</span><span>HARGA JUAL</span><span /></div>
          {items.map((it, idx) => {
            const sel = products.find(p => p.sku === it.sku);
            return (
              <div className="line-row" key={idx} data-testid="sale-line-row">
                <select value={it.sku} onChange={e => onSelectSku(idx, e.target.value)} data-testid={`sale-line-${idx}-sku-input`}>
                  <option value="">Pilih SKU / produk...</option>
                  {products.map(p => <option key={p.sku} value={p.sku}>{p.sku} — {p.name} (stok {p.stock})</option>)}
                </select>
                <input type="number" min="1" value={it.qty} onChange={e => setItem(idx, { qty: e.target.value })} data-testid={`sale-line-${idx}-qty-input`} />
                <input type="number" placeholder={sel ? `default ${sel.sell_price}` : "harga jual"} value={it.sell_price} onChange={e => setItem(idx, { sell_price: e.target.value })} data-testid={`sale-line-${idx}-price-input`} />
                <button type="button" className="icon-btn" onClick={() => removeRow(idx)} data-testid={`sale-line-${idx}-remove-button`}><Trash2 size={16} /></button>
              </div>
            );
          })}
          <button type="button" className="secondary" onClick={addRow} data-testid="sale-add-row-button" style={{ marginTop: 10 }}><Plus size={15} /> Tambah baris</button>
          <label style={{ marginTop: 18 }}>Catatan
            <textarea value={header.note} onChange={e => setHeader({ ...header, note: e.target.value })} data-testid="sale-form-note-input" />
          </label>
        </section>
        <aside className="panel summary-panel">
          <p className="eyebrow">RINGKASAN</p>
          <h2>{items.filter(i => i.sku).length} item</h2>
          <p className="mono">{header.payment_status} · {header.payment_method}</p>
          <div className="summary-line"><span>Total transaksi</span><b>{rupiah(total)}</b></div>
          {stockError && <div className="form-error" data-testid="sale-stock-error">Stok tidak cukup untuk {stockError.sku}</div>}
          <button className="primary full" disabled={!items.some(i => i.sku) || stockError} data-testid="sale-form-submit-button">
            <ShoppingCart size={17} /> Konfirmasi penjualan
          </button>
        </aside>
      </form>
    </div>
  );
}

function Movements({ movements }) {
  return (
    <div className="page">
      <div className="page-head"><div><p className="eyebrow">LEDGER STOK</p><h1>Stock Movement</h1><p className="sub">Jejak lengkap setiap perubahan saldo inventory.</p></div></div>
      <section className="panel table-panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>TANGGAL</th><th>TRANSAKSI</th><th>SKU / PRODUK</th><th>JENIS</th><th>MASUK</th><th>KELUAR</th><th>SALDO</th></tr></thead>
            <tbody>{movements.map(m => (
              <tr key={m.id}>
                <td className="muted">{String(m.created_at).slice(0, 10)}</td>
                <td className="mono">{m.transaction_no}</td>
                <td><b>{m.product}</b><small className="mono">{m.sku}</small></td>
                <td><span className={`badge ${m.qty_in > 0 ? "green" : "orange"}`}>{m.type}</span></td>
                <td className="qty green-text">{m.qty_in || "—"}</td>
                <td className="qty red-text">{m.qty_out || "—"}</td>
                <td className="qty">{m.after}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Reports({ sales, range, setRange, preset, setPreset }) {
  const total = sales.reduce((a, s) => a + Number(s.total || 0), 0);
  const qty = sales.reduce((a, s) => a + Number(s.qty || 0), 0);
  const cost = sales.reduce((a, s) => a + Number(s.cost_total || 0), 0);
  return (
    <div className="page">
      <div className="page-head">
        <div><p className="eyebrow">ANALISIS & EXPORT</p><h1>Laporan penjualan</h1><p className="sub">Ringkasan transaksi yang sudah selesai dan tervalidasi.</p></div>
        <a className="secondary" href={`${API}/export/sales`} data-testid="report-export-button"><Download size={16} /> Export CSV</a>
      </div>
      <DateFilter range={range} setRange={setRange} preset={preset} setPreset={setPreset} />
      <div className="report-strip">
        <Kpi label="Total transaksi" value={sales.length} note="Baris terjual" />
        <Kpi label="Produk terjual" value={`${qty} unit`} note="Jumlah unit" />
        <Kpi label="Omzet" value={rupiah(total)} note={`${range.start} → ${range.end}`} />
        <Kpi label="Laba kotor" value={rupiah(total - cost)} note={`${total ? Math.round((total - cost) / total * 100) : 0}% margin`} />
      </div>
      <section className="panel table-panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>TANGGAL</th><th>INVOICE</th><th>PRODUK</th><th>QTY</th><th>HARGA JUAL</th><th>TOTAL</th><th>BAYAR</th><th>STATUS</th></tr></thead>
            <tbody>{sales.length ? sales.map(s => (
              <tr key={s.id}>
                <td>{s.date}</td>
                <td className="mono">{s.invoice}</td>
                <td><b>{s.product}</b><small className="mono">{s.sku}</small></td>
                <td>{s.qty}</td>
                <td>{rupiah(s.sell_price)}</td>
                <td className="money">{rupiah(s.total)}</td>
                <td><span className={`badge ${s.payment_status === "Lunas" ? "green" : s.payment_status === "Tempo" ? "amber" : "blue"}`}>{s.payment_status || "Lunas"}</span></td>
                <td><span className="badge green">{s.status}</span></td>
              </tr>
            )) : <tr><td colSpan={8}><div className="empty">Tidak ada transaksi pada periode ini.</div></td></tr>}</tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function App() {
  const [page, setPage] = useState("Dashboard");
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [data, setData] = useState({ low_stock: [], recent_movements: [], top_products: [] });
  const [products, setProducts] = useState([]);
  const [allProducts, setAllProducts] = useState([]);
  const [movements, setMovements] = useState([]);
  const [sales, setSales] = useState([]);
  const [selected, setSelected] = useState(null);
  const [dashRange, setDashRange] = useState(() => presetRange("week"));
  const [dashPreset, setDashPreset] = useState("week");
  const [reportRange, setReportRange] = useState(() => presetRange("month"));
  const [reportPreset, setReportPreset] = useState("month");

  const reload = useCallback(async () => {
    const dq = `?start=${dashRange.start}&end=${dashRange.end}`;
    const sq = `?start=${reportRange.start}&end=${reportRange.end}`;
    const [d, p, all, m, s] = await Promise.all([
      axios.get(`${API}/dashboard${dq}`),
      axios.get(`${API}/products?search=${encodeURIComponent(query)}`),
      axios.get(`${API}/products`),
      axios.get(`${API}/movements`),
      axios.get(`${API}/sales${sq}`),
    ]);
    setData(d.data); setProducts(p.data); setAllProducts(all.data);
    setMovements(m.data); setSales(s.data);
  }, [query, dashRange.start, dashRange.end, reportRange.start, reportRange.end]);

  useEffect(() => { reload().catch(console.error); }, [reload]);

  const content =
    page === "Dashboard" ? <Dashboard data={data} setPage={setPage} range={dashRange} setRange={setDashRange} preset={dashPreset} setPreset={setDashPreset} /> :
    page === "Produk" ? <Products products={products} query={query} setQuery={setQuery} reload={reload} setSelected={setSelected} /> :
    page === "Barang Masuk" ? <ReceiptPage products={allProducts} reload={reload} /> :
    page === "Penjualan" ? <SalesPage products={allProducts} reload={reload} /> :
    page === "Stock Movement" ? <Movements movements={movements} /> :
    <Reports sales={sales} range={reportRange} setRange={setReportRange} preset={reportPreset} setPreset={setReportPreset} />;

  return (
    <div className="app-shell">
      <Sidebar page={page} setPage={setPage} open={open} close={() => setOpen(false)} productsCount={allProducts.length} />
      <main>
        <Header setOpen={setOpen} query={query} setQuery={setQuery} setPage={setPage} />
        {content}
      </main>
      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div className="modal detail" onClick={e => e.stopPropagation()}>
            <div className="modal-head">
              <div><p className="eyebrow">DETAIL PRODUK</p><h2>{selected.name}</h2></div>
              <button onClick={() => setSelected(null)} data-testid="product-detail-close-button"><X size={18} /></button>
            </div>
            <div className="detail-grid">
              <div><small>SKU</small><b className="mono">{selected.sku}</b></div>
              <div><small>STOK SAAT INI</small><b>{selected.stock} {selected.unit}</b></div>
              <div><small>HARGA JUAL</small><b>{rupiah(selected.sell_price)}</b></div>
              <div><small>HARGA ONLINE</small><b>{Number(selected.online_price) > 0 ? rupiah(selected.online_price) : "—"}</b></div>
              <div><small>HARGA MODAL</small><b>{rupiah(selected.cost_price)}</b></div>
              <div><small>LOKASI</small><b>{selected.location || "—"}</b></div>
            </div>
            <button className="secondary full" onClick={() => { setQuery(selected.sku); setPage("Stock Movement"); setSelected(null); }} data-testid="product-detail-stock-card-button"><ClipboardList size={16} /> Lihat kartu stok</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
