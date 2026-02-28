"""Export Document Generator — Streamlit App
Converted from ExportDocGen.html
"""

import streamlit as st
import pandas as pd
from datetime import date
import io

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Export Document Generator",
    page_icon="📤",
    layout="wide",
)

# ── CSS for generated document previews ──────────────────────────────────────
DOC_CSS = """
<style>
  body { font-family:'Courier New',monospace; background:#f0f0f0; padding:10px; }
  .document-preview {
    background:white; color:black; padding:40px; border-radius:4px;
    box-shadow:0 2px 8px rgba(0,0,0,.15); max-width:800px; margin:20px auto;
    font-family:'Courier New',monospace; font-size:13px; line-height:1.5;
  }
  .doc-title {
    font-size:22px; font-weight:bold; text-align:center; margin-bottom:20px;
    text-transform:uppercase; border-bottom:2px solid #000; padding-bottom:10px;
  }
  .doc-subtitle { text-align:center; font-style:italic; margin-bottom:16px; color:#555; }
  .doc-row { display:flex; justify-content:space-between; margin-bottom:8px;
             flex-wrap:wrap; gap:8px; }
  .doc-label { font-weight:bold; min-width:160px; display:inline-block; }
  .doc-section { margin:15px 0; padding:12px 15px; background:#f8f8f8;
                 border-left:3px solid #aaa; }
  .doc-section-title { font-weight:bold; font-size:13px; margin-bottom:8px;
                       text-decoration:underline; }
  table { width:100%; border-collapse:collapse; margin:15px 0; }
  th,td { border:1px solid #444; padding:6px 9px; text-align:left; font-size:12px; }
  th { background:#e0e0e0; font-weight:bold; }
  tfoot th { background:#f0f0f0; }
  .doc-footer { margin-top:25px; border-top:2px solid #333; padding-top:15px; }
  .signature-line {
    display:inline-block; margin-top:40px; border-top:1px solid #333;
    width:200px; text-align:center; padding-top:6px; font-size:11px;
  }
  .sigs { display:flex; justify-content:space-between; margin-top:30px; }
  .page-divider { border:none; border-top:4px dashed #ccc; margin:30px 0; }
  @media print {
    body { background:white; padding:0; }
    .document-preview { box-shadow:none; margin:0; padding:20px; }
    .page-divider { page-break-after:always; border:none; }
  }
</style>
"""

# ── Session-state defaults ────────────────────────────────────────────────────
_DEFAULTS = {
    "exp_name": "", "exp_addr": "", "exp_city": "",
    "exp_contact": "", "exp_email": "", "exp_iec": "", "exp_gst": "",
    "con_name": "", "con_addr": "", "con_city": "",
    "con_contact": "", "con_email": "",
    "inv_number": "", "inv_date": date.today(), "po_number": "",
    "port_loading": "", "port_discharge": "", "country_origin": "",
    "incoterms": "", "payment_terms": "", "vessel": "",
    "pkg_type": "", "num_packages": "", "gross_wt": "", "net_wt": "",
    "currency": "USD",
    "generated_html": "",
    "saved_data": None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

if "items" not in st.session_state:
    st.session_state.items = pd.DataFrame({
        "Description": [""], "HS Code": [""],
        "Quantity": [0.0], "Unit": ["PCS"],
        "Unit Price": [0.0],
    })

# ── Helpers ───────────────────────────────────────────────────────────────────
def na(val):
    return val if val else "N/A"


def number_to_words(num: float) -> str:
    if num == 0:
        return "Zero"
    ones  = ["","One","Two","Three","Four","Five","Six","Seven","Eight","Nine"]
    teens = ["Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen",
             "Sixteen","Seventeen","Eighteen","Nineteen"]
    tens_w = ["","","Twenty","Thirty","Forty","Fifty",
               "Sixty","Seventy","Eighty","Ninety"]
    thousands = ["","Thousand","Million","Billion"]

    def conv_h(n):
        n = int(n)
        if n == 0: return ""
        if n < 10: return ones[n]
        if n < 20: return teens[n - 10]
        if n < 100:
            return tens_w[n // 10] + (" " + ones[n % 10] if ones[n % 10] else "")
        tail = conv_h(n % 100)
        return ones[n // 100] + " Hundred" + (" " + tail if tail else "")

    num, parts, i = int(num), [], 0
    while num > 0:
        if num % 1000:
            chunk = conv_h(num % 1000)
            if thousands[i]:
                chunk += " " + thousands[i]
            parts.insert(0, chunk)
        num //= 1000
        i += 1
    return " ".join(parts).strip()


def exp_block(exp: dict) -> str:
    lines = [f"<div><strong>{exp['name']}</strong></div>"]
    for f, label in [("address",""), ("city",""), ("contact","Tel: "),
                     ("email","Email: "), ("iec","IEC: "), ("gst","GST: ")]:
        if exp.get(f):
            lines.append(f"<div>{label}{exp[f]}</div>")
    return "\n".join(lines)


def con_block(con: dict) -> str:
    lines = [f"<div><strong>{con['name']}</strong></div>"]
    for f, label in [("address",""), ("city",""),
                     ("contact","Tel: "), ("email","Email: ")]:
        if con.get(f):
            lines.append(f"<div>{label}{con[f]}</div>")
    return "\n".join(lines)


def collect_data() -> dict:
    """Gather all widget values into a structured dict."""
    ss = st.session_state
    df: pd.DataFrame = ss.get("items_editor", ss.items).copy()
    df["Total"] = df["Quantity"] * df["Unit Price"]
    items = []
    for _, row in df.iterrows():
        if row["Description"] or row["Quantity"] or row["Unit Price"]:
            items.append({
                "desc":  str(row["Description"]),
                "hs":    str(row["HS Code"]),
                "qty":   row["Quantity"],
                "unit":  str(row["Unit"]),
                "price": round(float(row["Unit Price"]), 2),
                "total": round(float(row["Total"]), 2),
            })
    return {
        "exporter": {
            "name": ss.exp_name, "address": ss.exp_addr, "city": ss.exp_city,
            "contact": ss.exp_contact, "email": ss.exp_email,
            "iec": ss.exp_iec, "gst": ss.exp_gst,
        },
        "consignee": {
            "name": ss.con_name, "address": ss.con_addr, "city": ss.con_city,
            "contact": ss.con_contact, "email": ss.con_email,
        },
        "shipment": {
            "invoiceNumber": ss.inv_number,
            "invoiceDate":   str(ss.inv_date),
            "poNumber":      ss.po_number,
            "portLoading":   ss.port_loading,
            "portDischarge": ss.port_discharge,
            "countryOrigin": ss.country_origin,
            "incoterms":     ss.incoterms,
            "paymentTerms":  ss.payment_terms,
            "vesselName":    ss.vessel,
            "packageType":   ss.pkg_type,
            "numPackages":   ss.num_packages,
            "grossWeight":   ss.gross_wt,
            "netWeight":     ss.net_wt,
            "currency":      ss.currency,
        },
        "items": items,
    }


# ── Document generators ───────────────────────────────────────────────────────

def gen_commercial_invoice(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    total = sum(it["total"] for it in items)
    cur   = ship["currency"]
    rows  = "".join(
        f"<tr><td>{i}</td><td>{it['desc']}</td><td>{it['hs']}</td>"
        f"<td>{it['qty']} {it['unit']}</td><td>{it['price']}</td><td>{it['total']}</td></tr>"
        for i, it in enumerate(items, 1)
    )
    return f"""
<div class="document-preview">
  <div class="doc-title">Commercial Invoice</div>
  <div class="doc-section"><div class="doc-section-title">Exporter / Shipper</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Consignee / Buyer</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Invoice No:</span> {ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">PO / Contract No:</span> {na(ship.get('poNumber'))}</div>
    <div><span class="doc-label">Incoterms:</span> {na(ship.get('incoterms'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Port of Loading:</span> {na(ship.get('portLoading'))}</div>
    <div><span class="doc-label">Port of Discharge:</span> {na(ship.get('portDischarge'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Country of Origin:</span> {na(ship.get('countryOrigin'))}</div>
    <div><span class="doc-label">Payment Terms:</span> {na(ship.get('paymentTerms'))}</div>
  </div>
  <table>
    <thead><tr><th>#</th><th>Description of Goods</th><th>HS Code</th>
      <th>Quantity</th><th>Unit Price</th><th>Amount ({cur})</th></tr></thead>
    <tbody>{rows}</tbody>
    <tfoot><tr><th colspan="5" style="text-align:right">TOTAL:</th>
      <th>{cur} {total:.2f}</th></tr></tfoot>
  </table>
  <div class="doc-footer">
    <div><strong>Total in Words:</strong> {number_to_words(total)} {cur} Only</div>
    <div style="margin-top:15px"><strong>Declaration:</strong> We declare that this invoice
      shows the actual price of the goods described and that all particulars are true and correct.</div>
    <div class="signature-line">Authorized Signature</div>
  </div>
</div>"""


def gen_packing_list(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    rows = "".join(
        f"<tr><td>{i}</td><td>{it['desc']}</td><td>{it['qty']} {it['unit']}</td>"
        f"<td>{na(ship.get('packageType'))}</td><td>{it['hs']}</td></tr>"
        for i, it in enumerate(items, 1)
    )
    return f"""
<div class="document-preview">
  <div class="doc-title">Packing List</div>
  <div class="doc-section"><div class="doc-section-title">Exporter / Shipper</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Consignee</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Invoice No:</span> {ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Vessel / Flight:</span> {na(ship.get('vesselName'))}</div>
    <div><span class="doc-label">No. of Packages:</span> {na(ship.get('numPackages'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Gross Weight:</span> {na(ship.get('grossWeight'))} KG</div>
    <div><span class="doc-label">Net Weight:</span> {na(ship.get('netWeight'))} KG</div>
  </div>
  <table>
    <thead><tr><th>#</th><th>Description</th><th>Quantity</th><th>Packing Type</th><th>HS Code</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="doc-footer">
    <div><strong>Marks &amp; Numbers:</strong> {con['name']} / {na(ship.get('portDischarge'))}</div>
    <div class="signature-line">Authorized Signature</div>
  </div>
</div>"""


def gen_certificate_of_origin(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    rows = "".join(
        f"<tr><td>{i}</td><td>{it['desc']}</td><td>{it['qty']} {it['unit']}</td>"
        f"<td>{na(ship.get('countryOrigin'))}</td></tr>"
        for i, it in enumerate(items, 1)
    )
    return f"""
<div class="document-preview">
  <div class="doc-title">Certificate of Origin</div>
  <div class="doc-row">
    <div><span class="doc-label">Certificate No:</span> COO-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Exporter</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Consignee</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Invoice No:</span> {ship['invoiceNumber']}</div>
    <div><span class="doc-label">Port of Discharge:</span> {na(ship.get('portDischarge'))}</div>
  </div>
  <table>
    <thead><tr><th>#</th><th>Description of Goods</th><th>Quantity</th><th>Country of Origin</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Declaration:</strong> We hereby certify that the goods
      described above originated in {na(ship.get('countryOrigin'))}.</div>
    <div class="sigs">
      <div class="signature-line">Exporter's Signature</div>
      <div class="signature-line">Chamber of Commerce Stamp</div>
    </div>
  </div>
</div>"""


def gen_shipping_bill(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    total = sum(it["total"] for it in items)
    cur   = ship["currency"]
    rows  = "".join(
        f"<tr><td>{i}</td><td>{it['desc']}</td><td>{it['hs']}</td>"
        f"<td>{it['qty']} {it['unit']}</td><td>{it['total']}</td></tr>"
        for i, it in enumerate(items, 1)
    )
    return f"""
<div class="document-preview">
  <div class="doc-title">Shipping Bill</div>
  <div class="doc-row">
    <div><span class="doc-label">Shipping Bill No:</span> SB-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Exporter Details</div>{exp_block(exp)}
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Port of Loading:</span> {na(ship.get('portLoading'))}</div>
    <div><span class="doc-label">Port of Discharge:</span> {na(ship.get('portDischarge'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Country of Destination:</span> {na(con.get('city'))}</div>
    <div><span class="doc-label">Invoice Value:</span> {cur} {total:.2f}</div>
  </div>
  <table>
    <thead><tr><th>#</th><th>Description</th><th>HS Code</th>
      <th>Quantity</th><th>FOB Value ({cur})</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="doc-footer">
    <div><strong>Total FOB Value:</strong> {cur} {total:.2f}</div>
    <div class="signature-line">Customs Authorized Officer</div>
  </div>
</div>"""


def gen_sli(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    goods = "".join(f"<div>• {it['qty']} {it['unit']} of {it['desc']}</div>" for it in items)
    return f"""
<div class="document-preview">
  <div class="doc-title">Shipper's Letter of Instruction (SLI)</div>
  <div class="doc-row">
    <div><span class="doc-label">Reference No:</span> SLI-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">To: Freight Forwarder / Carrier</div>
    <div>Please arrange shipment as per the following instructions:</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Shipper</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Consignee</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Port of Loading:</span> {na(ship.get('portLoading'))}</div>
    <div><span class="doc-label">Port of Discharge:</span> {na(ship.get('portDischarge'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Vessel / Flight:</span> {na(ship.get('vesselName'))}</div>
    <div><span class="doc-label">No. of Packages:</span> {na(ship.get('numPackages'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Gross Weight:</span> {na(ship.get('grossWeight'))} KG</div>
    <div><span class="doc-label">Incoterms:</span> {na(ship.get('incoterms'))}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Description of Goods</div>{goods}</div>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Special Instructions:</strong> Handle with care.
      Notify consignee upon arrival.</div>
    <div class="signature-line">Shipper's Signature</div>
  </div>
</div>"""


def gen_proforma_invoice(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    total = sum(it["total"] for it in items)
    cur   = ship["currency"]
    rows  = "".join(
        f"<tr><td>{i}</td><td>{it['desc']}</td><td>{it['qty']} {it['unit']}</td>"
        f"<td>{it['price']}</td><td>{it['total']}</td></tr>"
        for i, it in enumerate(items, 1)
    )
    return f"""
<div class="document-preview">
  <div class="doc-title">Proforma Invoice</div>
  <div class="doc-subtitle">(For Reference Only — Not a Tax Invoice)</div>
  <div class="doc-section"><div class="doc-section-title">Seller</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Buyer</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Proforma Invoice No:</span> PI-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Incoterms:</span> {na(ship.get('incoterms'))}</div>
    <div><span class="doc-label">Payment Terms:</span> {na(ship.get('paymentTerms'))}</div>
  </div>
  <table>
    <thead><tr><th>#</th><th>Description</th><th>Quantity</th>
      <th>Unit Price ({cur})</th><th>Amount ({cur})</th></tr></thead>
    <tbody>{rows}</tbody>
    <tfoot><tr><th colspan="4" style="text-align:right">TOTAL:</th>
      <th>{cur} {total:.2f}</th></tr></tfoot>
  </table>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Validity:</strong> This proforma invoice is valid
      for 30 days from the date of issue.</div>
    <div style="margin-top:10px"><strong>Note:</strong> This is a preliminary invoice for
      quotation purposes only. Final commercial invoice will be issued upon shipment.</div>
    <div class="signature-line">Authorized Signature</div>
  </div>
</div>"""


def gen_bill_of_lading(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    goods = "".join(f"<div>• {it['qty']} {it['unit']} — {it['desc']}</div>" for it in items)
    return f"""
<div class="document-preview">
  <div class="doc-title">Bill of Lading (B/L)</div>
  <div class="doc-subtitle">Non-Negotiable Copy</div>
  <div class="doc-row">
    <div><span class="doc-label">B/L No:</span> BL-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Shipper</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Consignee</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Vessel:</span> {na(ship.get('vesselName'))}</div>
    <div><span class="doc-label">Port of Loading:</span> {na(ship.get('portLoading'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Port of Discharge:</span> {na(ship.get('portDischarge'))}</div>
    <div><span class="doc-label">No. of Packages:</span> {na(ship.get('numPackages'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Gross Weight:</span> {na(ship.get('grossWeight'))} KG</div>
    <div><span class="doc-label">Net Weight:</span> {na(ship.get('netWeight'))} KG</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Description of Goods</div>{goods}</div>
  <div class="doc-footer">
    <div><strong>Freight Terms:</strong> {na(ship.get('incoterms'))}</div>
    <div><strong>Container Type:</strong> {na(ship.get('packageType'))}</div>
    <div class="signature-line">Carrier's Signature &amp; Stamp</div>
  </div>
</div>"""


def gen_air_waybill(d):
    import random
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    goods = "".join(f"<div>• {it['qty']} {it['unit']} — {it['desc']}</div>" for it in items)
    awb_no = random.randint(10000000, 99999999)
    return f"""
<div class="document-preview">
  <div class="doc-title">Air Waybill (AWB)</div>
  <div class="doc-subtitle">Non-Negotiable</div>
  <div class="doc-row">
    <div><span class="doc-label">AWB No:</span> {awb_no}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Shipper / Consignor</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Consignee</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Airport of Departure:</span> {na(ship.get('portLoading'))}</div>
    <div><span class="doc-label">Airport of Destination:</span> {na(ship.get('portDischarge'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Flight:</span> {na(ship.get('vesselName'))}</div>
    <div><span class="doc-label">No. of Pieces:</span> {na(ship.get('numPackages'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Gross Weight:</span> {na(ship.get('grossWeight'))} KG</div>
    <div><span class="doc-label">Chargeable Weight:</span> {na(ship.get('grossWeight'))} KG</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Nature and Quantity of Goods</div>{goods}
  </div>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Handling Information:</strong> Handle with care.</div>
    <div class="signature-line">Airline Agent Signature</div>
  </div>
</div>"""


def gen_insurance_certificate(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    total = sum(it["total"] for it in items)
    insured = round(total * 1.1, 2)
    cur = ship["currency"]
    goods = "".join(f"<div>• {it['desc']}</div>" for it in items)
    return f"""
<div class="document-preview">
  <div class="doc-title">Certificate of Insurance</div>
  <div class="doc-row">
    <div><span class="doc-label">Certificate No:</span> INS-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Assured / Insured</div>{con_block(con)}
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Invoice No:</span> {ship['invoiceNumber']}</div>
    <div><span class="doc-label">Vessel / Flight:</span> {na(ship.get('vesselName'))}</div>
  </div>
  <div class="doc-row">
    <div><span class="doc-label">From:</span> {na(ship.get('portLoading'))}</div>
    <div><span class="doc-label">To:</span> {na(ship.get('portDischarge'))}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Description of Goods</div>{goods}</div>
  <div class="doc-row">
    <div><span class="doc-label">Sum Insured:</span> {cur} {insured}</div>
    <div><span class="doc-label">Basis:</span> 110% of Invoice Value</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Coverage</div>
    <div>• All risks of physical loss or damage from external causes</div>
    <div>• War, strikes, riots and civil commotion risks</div>
    <div>• Total loss and general average</div>
  </div>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Terms:</strong> Institute Cargo Clauses (A)</div>
    <div class="signature-line">Insurance Co. Authorized Signature</div>
  </div>
</div>"""


def gen_inspection_certificate(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    goods = "".join(f"<div>• {it['qty']} {it['unit']} of {it['desc']}</div>" for it in items)
    return f"""
<div class="document-preview">
  <div class="doc-title">Inspection Certificate</div>
  <div class="doc-row">
    <div><span class="doc-label">Certificate No:</span> IC-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Exporter</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Buyer / Consignee</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Invoice No:</span> {ship['invoiceNumber']}</div>
    <div><span class="doc-label">PO No:</span> {na(ship.get('poNumber'))}</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Description of Goods Inspected</div>{goods}
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Inspection Results</div>
    <div>✓ Quality conforms to purchase order specifications</div>
    <div>✓ Quantity verified and matches shipping documents</div>
    <div>✓ Packaging is suitable for international transport</div>
    <div>✓ Goods are in good condition and fit for shipment</div>
  </div>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Declaration:</strong> We hereby certify that the goods
      have been inspected and found to be in accordance with the specifications.</div>
    <div class="sigs">
      <div class="signature-line">Inspector's Signature</div>
      <div class="signature-line">Company Stamp</div>
    </div>
  </div>
</div>"""


def gen_phytosanitary(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    goods = "".join(f"<div>• {it['qty']} {it['unit']} of {it['desc']}</div>" for it in items)
    return f"""
<div class="document-preview">
  <div class="doc-title">Phytosanitary Certificate</div>
  <div class="doc-subtitle">Plant Protection Organization</div>
  <div class="doc-row">
    <div><span class="doc-label">Certificate No:</span> PC-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Exporter</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Consignee</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Port of Entry:</span> {na(ship.get('portDischarge'))}</div>
    <div><span class="doc-label">Country of Origin:</span> {na(ship.get('countryOrigin'))}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Description of Consignment</div>{goods}</div>
  <div class="doc-section">
    <div class="doc-section-title">Phytosanitary Declaration</div>
    <div>This is to certify that the plants, plant products, or other regulated articles described
      herein have been inspected and/or tested according to appropriate official procedures and are
      considered to be free from quarantine pests and practically free from other injurious pests.</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Treatment</div>
    <div>✓ Inspection conducted on: {ship['invoiceDate']}</div>
    <div>✓ No quarantine pests detected</div>
    <div>✓ Meets phytosanitary import requirements</div>
  </div>
  <div class="doc-footer">
    <div class="sigs">
      <div class="signature-line">Plant Protection Officer</div>
      <div class="signature-line">Official Stamp</div>
    </div>
  </div>
</div>"""


def gen_fumigation(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    goods = "".join(f"<div>• {it['desc']}</div>" for it in items)
    return f"""
<div class="document-preview">
  <div class="doc-title">Fumigation Certificate</div>
  <div class="doc-subtitle">Pest Control Treatment Certificate</div>
  <div class="doc-row">
    <div><span class="doc-label">Certificate No:</span> FC-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Exporter</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Consignee</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Container No:</span> CONT-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">No. of Packages:</span> {na(ship.get('numPackages'))}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Description of Goods</div>{goods}</div>
  <div class="doc-section">
    <div class="doc-section-title">Fumigation Details</div>
    <div><span class="doc-label">Fumigant Used:</span> Methyl Bromide / Aluminum Phosphide</div>
    <div><span class="doc-label">Dosage:</span> As per ISPM 15 standards</div>
    <div><span class="doc-label">Treatment Duration:</span> 24 hours</div>
    <div><span class="doc-label">Temperature:</span> 25°C</div>
    <div><span class="doc-label">Treatment Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Certification:</strong> We hereby certify that the
      above-mentioned consignment and wooden packaging material have been fumigated according to
      ISPM-15 standards and are free from pests.</div>
    <div class="sigs">
      <div class="signature-line">Licensed Fumigation Agency</div>
      <div class="signature-line">License No. &amp; Stamp</div>
    </div>
  </div>
</div>"""


def gen_health_certificate(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    goods = "".join(f"<div>• {it['qty']} {it['unit']} of {it['desc']}</div>" for it in items)
    return f"""
<div class="document-preview">
  <div class="doc-title">Health Certificate</div>
  <div class="doc-subtitle">For Export of Food Products</div>
  <div class="doc-row">
    <div><span class="doc-label">Certificate No:</span> HC-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Exporter / Manufacturer</div>{exp_block(exp)}
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Importer / Consignee</div>{con_block(con)}
  </div>
  <div class="doc-section"><div class="doc-section-title">Description of Products</div>{goods}</div>
  <div class="doc-section">
    <div class="doc-section-title">Health Declaration</div>
    <div>✓ The products have been prepared under hygienic conditions</div>
    <div>✓ Raw materials used are of good quality and fit for human consumption</div>
    <div>✓ Products comply with food safety standards and regulations</div>
    <div>✓ No harmful substances or contaminants detected</div>
    <div>✓ Storage and transportation meet sanitary requirements</div>
  </div>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Validity:</strong> This certificate is valid for
      6 months from date of issue.</div>
    <div class="sigs">
      <div class="signature-line">Health Authority Officer</div>
      <div class="signature-line">Official Seal</div>
    </div>
  </div>
</div>"""


def gen_bill_of_exchange(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    total = sum(it["total"] for it in items)
    cur   = ship["currency"]
    return f"""
<div class="document-preview">
  <div class="doc-title">Bill of Exchange / Draft</div>
  <div class="doc-row">
    <div><span class="doc-label">Draft No:</span> BE-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section" style="padding:20px">
    <div style="font-size:18px;margin-bottom:12px">
      <strong>Amount:</strong> {cur} {total:.2f}</div>
    <div style="font-size:16px">
      <strong>In Words:</strong> {number_to_words(total)} {cur} Only</div>
  </div>
  <div class="doc-section">
    <div>At <strong>{na(ship.get('paymentTerms'))}</strong> of this FIRST Bill of Exchange
      (Second of the same tenor and date being unpaid)</div>
    <div style="margin-top:12px">Pay to the order of <strong>{exp['name']}</strong></div>
    <div style="margin-top:12px">The sum of <strong>{cur} {total:.2f}</strong></div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">To (Drawee)</div>{con_block(con)}
  </div>
  <div class="doc-section">
    <div class="doc-section-title">For</div>
    <div>Value received as per Invoice No. {ship['invoiceNumber']}</div>
    <div>dated {ship['invoiceDate']}</div>
  </div>
  <div class="doc-footer">
    <div style="text-align:right;margin-top:30px">
      <div><strong>{exp['name']}</strong></div>
      <div class="signature-line">Drawer's Signature</div>
    </div>
  </div>
</div>"""


def gen_letter_of_credit(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    total = sum(it["total"] for it in items)
    cur   = ship["currency"]
    goods = "".join(f"<div>• {it['qty']} {it['unit']} of {it['desc']}</div>" for it in items)
    return f"""
<div class="document-preview">
  <div class="doc-title">Letter of Credit (L/C)</div>
  <div class="doc-subtitle">Irrevocable Documentary Credit</div>
  <div class="doc-row">
    <div><span class="doc-label">L/C No:</span> LC-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date of Issue:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Applicant (Buyer)</div>{con_block(con)}
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Beneficiary (Seller)</div>{exp_block(exp)}
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Amount:</span> {cur} {total:.2f}</div>
    <div><span class="doc-label">Expiry Date:</span> 90 days from issue</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Description of Goods</div>{goods}</div>
  <div class="doc-section">
    <div class="doc-section-title">Shipment Details</div>
    <div><span class="doc-label">From:</span> {na(ship.get('portLoading'))}</div>
    <div><span class="doc-label">To:</span> {na(ship.get('portDischarge'))}</div>
    <div><span class="doc-label">Incoterms:</span> {na(ship.get('incoterms'))}</div>
    <div><span class="doc-label">Latest Shipment:</span> 60 days from L/C date</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Documents Required</div>
    <div>• Commercial Invoice (3 originals)</div>
    <div>• Packing List (2 copies)</div>
    <div>• Bill of Lading (full set)</div>
    <div>• Certificate of Origin</div>
    <div>• Insurance Certificate</div>
  </div>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Special Conditions:</strong> This credit is subject to
      Uniform Customs and Practice for Documentary Credits (UCP 600).</div>
    <div class="signature-line">Issuing Bank Authorized Signature</div>
  </div>
</div>"""


def gen_export_license(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    goods = "".join(
        f"<div>• {it['qty']} {it['unit']} of {it['desc']} (HS Code: {it['hs']})</div>"
        for it in items
    )
    return f"""
<div class="document-preview">
  <div class="doc-title">Export License</div>
  <div class="doc-row">
    <div><span class="doc-label">License No:</span> EL-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date of Issue:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Exporter Details</div>{exp_block(exp)}
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Consignee Details</div>{con_block(con)}
  </div>
  <div class="doc-row">
    <div><span class="doc-label">Country of Destination:</span> {na(con.get('city'))}</div>
    <div><span class="doc-label">Port of Export:</span> {na(ship.get('portLoading'))}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Description of Goods</div>{goods}</div>
  <div class="doc-section">
    <div class="doc-section-title">License Conditions</div>
    <div>✓ This license is valid for single shipment only</div>
    <div>✓ Shipment must be completed within 6 months</div>
    <div>✓ Goods must be exported as per approved specifications</div>
    <div>✓ Any amendments require prior approval</div>
  </div>
  <div class="doc-footer">
    <div><strong>Validity:</strong> 6 months from date of issue</div>
    <div style="margin-top:10px"><strong>Note:</strong> This license is issued subject to the
      provisions of the Foreign Trade Policy.</div>
    <div class="signature-line">Licensing Authority Signature &amp; Seal</div>
  </div>
</div>"""


def gen_dangerous_goods(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    rows = "".join(
        f"<tr><td>UN####</td><td>{it['desc']}</td><td>-</td><td>-</td>"
        f"<td>{it['qty']} {it['unit']}</td></tr>"
        for it in items
    )
    return f"""
<div class="document-preview">
  <div class="doc-title">Dangerous Goods Declaration</div>
  <div class="doc-subtitle">IMDG / IATA Dangerous Goods Transport Document</div>
  <div class="doc-row">
    <div><span class="doc-label">DGD No:</span> DGD-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section"><div class="doc-section-title">Shipper</div>{exp_block(exp)}</div>
  <div class="doc-section"><div class="doc-section-title">Consignee</div>{con_block(con)}</div>
  <div class="doc-row">
    <div><span class="doc-label">Vessel / Flight:</span> {na(ship.get('vesselName'))}</div>
    <div><span class="doc-label">Port of Loading:</span> {na(ship.get('portLoading'))}</div>
  </div>
  <table>
    <thead><tr><th>UN No.</th><th>Proper Shipping Name</th><th>Class</th>
      <th>Packing Group</th><th>Quantity</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="doc-section">
    <div class="doc-section-title">Additional Handling Information</div>
    <div>• Package type: {na(ship.get('packageType'))}</div>
    <div>• Emergency response: Contact shipper immediately</div>
    <div>• Special precautions: Handle with care</div>
  </div>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Shipper's Declaration:</strong> I hereby declare that
      the contents of this consignment are fully and accurately described above and are classified,
      packaged, marked and labeled, and are in proper condition for transport according to applicable
      regulations.</div>
    <div class="signature-line">Shipper's Signature &amp; Date</div>
  </div>
</div>"""


def gen_free_sale(d):
    exp, con, ship, items = d["exporter"], d["consignee"], d["shipment"], d["items"]
    goods = "".join(f"<div>• {it['desc']}</div>" for it in items)
    return f"""
<div class="document-preview">
  <div class="doc-title">Certificate of Free Sale</div>
  <div class="doc-row">
    <div><span class="doc-label">Certificate No:</span> CFS-{ship['invoiceNumber']}</div>
    <div><span class="doc-label">Date:</span> {ship['invoiceDate']}</div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Manufacturer / Exporter</div>{exp_block(exp)}
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Importer / Buyer</div>{con_block(con)}
  </div>
  <div class="doc-section"><div class="doc-section-title">Product Details</div>{goods}</div>
  <div class="doc-section">
    <div class="doc-section-title">Certification</div>
    <div style="line-height:1.8">
      This is to certify that the products listed above are manufactured by
      <strong>{exp['name']}</strong> and are freely sold and distributed in
      {na(ship.get('countryOrigin'))} without any restrictions. The products comply with all
      applicable regulations and standards for sale and distribution in the country of manufacture.
    </div>
  </div>
  <div class="doc-section">
    <div class="doc-section-title">Regulatory Compliance</div>
    <div>✓ Products meet national quality standards</div>
    <div>✓ Manufacturing facility is licensed and registered</div>
    <div>✓ Products are in compliance with health and safety regulations</div>
    <div>✓ No restrictions on sale or distribution in country of origin</div>
  </div>
  <div class="doc-footer">
    <div style="margin-top:15px"><strong>Validity:</strong> 12 months from date of issue</div>
    <div class="sigs">
      <div class="signature-line">Regulatory Authority Signature</div>
      <div class="signature-line">Official Seal</div>
    </div>
  </div>
</div>"""


# Map key → (label, generator_fn, default_checked)
DOC_REGISTRY = [
    ("commercial_invoice",      "Commercial Invoice",              gen_commercial_invoice,    True),
    ("packing_list",            "Packing List",                    gen_packing_list,          True),
    ("certificate_origin",      "Certificate of Origin",           gen_certificate_of_origin, False),
    ("shipping_bill",           "Shipping Bill",                   gen_shipping_bill,         False),
    ("sli",                     "Shipper's Letter of Instruction", gen_sli,                   False),
    ("proforma",                "Proforma Invoice",                gen_proforma_invoice,      False),
    ("bill_lading",             "Bill of Lading (B/L)",            gen_bill_of_lading,        False),
    ("air_waybill",             "Air Waybill (AWB)",               gen_air_waybill,           False),
    ("insurance_certificate",   "Insurance Certificate",           gen_insurance_certificate, False),
    ("inspection_certificate",  "Inspection Certificate",          gen_inspection_certificate,False),
    ("phytosanitary",           "Phytosanitary Certificate",       gen_phytosanitary,         False),
    ("fumigation",              "Fumigation Certificate",          gen_fumigation,            False),
    ("health_certificate",      "Health Certificate",              gen_health_certificate,    False),
    ("bill_exchange",           "Bill of Exchange / Draft",        gen_bill_of_exchange,      False),
    ("letter_credit",           "Letter of Credit (L/C)",          gen_letter_of_credit,      False),
    ("export_license",          "Export License",                  gen_export_license,        False),
    ("dangerous_goods",         "Dangerous Goods Declaration",     gen_dangerous_goods,       False),
    ("free_sale",               "Certificate of Free Sale",        gen_free_sale,             False),
]


def build_full_html(docs_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Export Documents</title>{DOC_CSS}</head>
<body>{docs_html}</body></html>"""


def export_csv(d: dict) -> str:
    lines = ["EXPORTER INFORMATION"]
    for k, v in d["exporter"].items():
        lines.append(f"{k},{v}")
    lines += ["", "CONSIGNEE INFORMATION"]
    for k, v in d["consignee"].items():
        lines.append(f"{k},{v}")
    lines += ["", "SHIPMENT DETAILS"]
    for k, v in d["shipment"].items():
        lines.append(f"{k},{v}")
    lines += ["", "ITEMS", "Description,HS Code,Quantity,Unit,Unit Price,Total"]
    for it in d["items"]:
        lines.append(f"{it['desc']},{it['hs']},{it['qty']},{it['unit']},{it['price']},{it['total']}")
    return "\n".join(lines)


# ── UI ────────────────────────────────────────────────────────────────────────
st.title("📤 Export Document Generator")
st.caption("Create professional export documents from a single dataset • Eliminate data re-entry")

tab1, tab2 = st.tabs(["📋 Master Data", "📄 Generate Documents"])

# ════════════════════════════════════════════════════════════
# TAB 1 — MASTER DATA
# ════════════════════════════════════════════════════════════
with tab1:

    # — Exporter ——————————————————————————————————————————————
    st.markdown("### 📤 Exporter / Shipper Information")
    c1, c2, c3 = st.columns(3)
    c1.text_input("Company Name *",         key="exp_name",    placeholder="ABC Export Ltd.")
    c2.text_input("Address *",              key="exp_addr",    placeholder="123 Business Street")
    c3.text_input("City & Country *",       key="exp_city",    placeholder="Mumbai, India")
    c4, c5, c6, c7 = st.columns(4)
    c4.text_input("Contact Number",         key="exp_contact", placeholder="+91 1234567890")
    c5.text_input("Email",                  key="exp_email",   placeholder="export@company.com")
    c6.text_input("IEC Code / License No.", key="exp_iec",     placeholder="1234567890")
    c7.text_input("GST / Tax Registration", key="exp_gst",     placeholder="22AAAAA0000A1Z5")

    st.divider()

    # — Consignee —————————————————————————————————————————————
    st.markdown("### 📥 Consignee / Buyer Information")
    c1, c2, c3 = st.columns(3)
    c1.text_input("Company Name *",   key="con_name",    placeholder="XYZ Imports Inc.")
    c2.text_input("Address *",        key="con_addr",    placeholder="456 Import Avenue")
    c3.text_input("City & Country *", key="con_city",    placeholder="New York, USA")
    c4, c5 = st.columns(2)
    c4.text_input("Contact Number",   key="con_contact", placeholder="+1 234-567-8900")
    c5.text_input("Email",            key="con_email",   placeholder="buyer@imports.com")

    st.divider()

    # — Shipment Details ——————————————————————————————————————
    st.markdown("### 🚢 Shipment Details")
    c1, c2, c3, c4 = st.columns(4)
    c1.text_input("Invoice Number *", key="inv_number", placeholder="INV-2026-001")
    c2.date_input("Invoice Date *",   key="inv_date",   value=date.today())
    c3.text_input("PO / Contract No.", key="po_number", placeholder="PO-12345")
    c4.text_input("Port of Loading",  key="port_loading", placeholder="Mumbai Port")

    c1, c2, c3, c4 = st.columns(4)
    c1.text_input("Port of Discharge",   key="port_discharge",  placeholder="New York Port")
    c2.text_input("Country of Origin",   key="country_origin",  placeholder="India")

    INCOTERMS = {
        "": "Select Incoterm",
        "FOB": "FOB — Free On Board",
        "CIF": "CIF — Cost, Insurance & Freight",
        "CFR": "CFR — Cost and Freight",
        "EXW": "EXW — Ex Works",
        "FCA": "FCA — Free Carrier",
        "DDP": "DDP — Delivered Duty Paid",
        "DAP": "DAP — Delivered At Place",
    }
    c3.selectbox("Incoterms", list(INCOTERMS.keys()),
                 format_func=lambda x: INCOTERMS[x], key="incoterms")

    PAYMENT = {
        "": "Select Payment Terms",
        "L/C": "Letter of Credit (L/C)",
        "T/T": "Telegraphic Transfer (T/T)",
        "D/A": "Documents Against Acceptance",
        "D/P": "Documents Against Payment",
        "Advance": "Advance Payment",
    }
    c4.selectbox("Payment Terms", list(PAYMENT.keys()),
                 format_func=lambda x: PAYMENT[x], key="payment_terms")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.text_input("Vessel / Flight Name", key="vessel", placeholder="MV Cargo Express")

    PKG_TYPES = ["", "20ft Container", "40ft Container",
                 "Pallets", "Cartons", "Wooden Crates", "Drums"]
    c2.selectbox("Package Type", PKG_TYPES, key="pkg_type")
    c3.text_input("No. of Packages", key="num_packages", placeholder="100")
    c4.text_input("Gross Weight (kg)", key="gross_wt",   placeholder="5000.00")
    c5.text_input("Net Weight (kg)",   key="net_wt",     placeholder="4800.00")

    CURRENCIES = {
        "USD": "USD — US Dollar",
        "EUR": "EUR — Euro",
        "GBP": "GBP — British Pound",
        "INR": "INR — Indian Rupee",
        "CNY": "CNY — Chinese Yuan",
    }
    st.selectbox("Currency", list(CURRENCIES.keys()),
                 format_func=lambda x: CURRENCIES[x], key="currency")

    st.divider()

    # — Items Table ———————————————————————————————————————————
    st.markdown("### 📦 Items / Products")
    st.info("💡 Add all items here. Data syncs automatically across all generated documents.")

    edited = st.data_editor(
        st.session_state.items,
        key="items_editor",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Description": st.column_config.TextColumn("Description of Goods", width="large"),
            "HS Code":     st.column_config.TextColumn("HS Code",   width="small"),
            "Quantity":    st.column_config.NumberColumn("Quantity", min_value=0, format="%.2f"),
            "Unit":        st.column_config.SelectboxColumn(
                               "Unit", options=["PCS","KGS","MTR","SET","BOX","ROLL","PAIR"]),
            "Unit Price":  st.column_config.NumberColumn("Unit Price", min_value=0, format="%.4f"),
        },
    )
    # Keep a calculated copy in session_state (used by collect_data)
    if edited is not None:
        calc = edited.copy()
        calc["Total"] = calc["Quantity"] * calc["Unit Price"]
        st.session_state.items = calc
        # Grand total summary
        grand_total = calc["Total"].sum()
        st.metric(f"Grand Total ({st.session_state.currency})", f"{grand_total:,.2f}")

    st.divider()

    # — Save / Load ———————————————————————————————————————————
    b1, b2, _ = st.columns([1, 1, 4])
    if b1.button("💾 Save Form Data"):
        st.session_state.saved_data = {
            k: st.session_state[k]
            for k in _DEFAULTS
            if k not in ("generated_html", "saved_data")
        }
        st.session_state.saved_data["items"] = st.session_state.items.copy()
        st.success("Form data saved! You can load it anytime.")

    if b2.button("📂 Load Saved Data"):
        if st.session_state.saved_data:
            sd = st.session_state.saved_data
            for k in _DEFAULTS:
                if k in sd:
                    st.session_state[k] = sd[k]
            if "items" in sd:
                st.session_state.items = sd["items"]
            st.success("Saved data loaded!")
            st.rerun()
        else:
            st.warning("No saved data found. Please save first.")

    st.info("➡️ Switch to the **Generate Documents** tab when ready.")


# ════════════════════════════════════════════════════════════
# TAB 2 — GENERATE DOCUMENTS
# ════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📄 Select Documents to Generate")
    st.info("✨ All data from Master Data populates automatically — no re-entry needed!")

    # Checkboxes in 3 columns
    cols = st.columns(3)
    selected = {}
    for i, (key, label, _, default) in enumerate(DOC_REGISTRY):
        selected[key] = cols[i % 3].checkbox(label, value=default, key=f"doc_{key}")

    st.divider()

    if st.button("🚀 Generate Selected Documents", type="primary", use_container_width=True):
        data = collect_data()

        # Validation
        if not data["exporter"]["name"] or not data["consignee"]["name"] or not data["shipment"]["invoiceNumber"]:
            st.error("Please fill in required fields: Exporter Name, Consignee Name, and Invoice Number.")
            st.stop()
        if not data["items"]:
            st.error("Please add at least one item in the Master Data tab.")
            st.stop()

        # Build combined HTML
        docs_html = ""
        first = True
        for key, label, gen_fn, _ in DOC_REGISTRY:
            if selected.get(key):
                if not first:
                    docs_html += '<hr class="page-divider">'
                docs_html += gen_fn(data)
                first = False

        if not docs_html:
            st.warning("No documents selected.")
        else:
            st.session_state.generated_html = build_full_html(docs_html)
            st.session_state.generated_data = data
            st.success(f"Generated {sum(selected.values())} document(s) successfully!")

    # ── Preview & export ─────────────────────────────────────
    if st.session_state.generated_html:
        data = st.session_state.get("generated_data", {})

        # Action buttons row
        col_dl1, col_dl2, col_email = st.columns(3)

        col_dl1.download_button(
            "⬇️ Download as HTML",
            data=st.session_state.generated_html,
            file_name="export-documents.html",
            mime="text/html",
            use_container_width=True,
        )

        if data:
            csv_bytes = export_csv(data).encode()
            col_dl2.download_button(
                "📊 Download as CSV",
                data=csv_bytes,
                file_name="export-data.csv",
                mime="text/csv",
                use_container_width=True,
            )

            inv_no = data["shipment"].get("invoiceNumber", "")
            exp_name = data["exporter"].get("name", "")
            con_name = data["consignee"].get("name", "")
            mailto = (
                f"mailto:?subject=Export Documents - Invoice {inv_no}"
                f"&body=Dear Partner,%0D%0A%0D%0APlease find the export documents "
                f"for Invoice {inv_no}.%0D%0A%0D%0AExporter: {exp_name}"
                f"%0D%0AConsignee: {con_name}%0D%0A%0D%0ABest regards"
            )
            col_email.link_button("📧 Email Documents", mailto, use_container_width=True)

        st.caption("💡 To print or save as PDF: download the HTML file and open it in a browser, then use **Ctrl+P → Save as PDF**.")

        st.divider()
        st.markdown("#### Preview")
        st.components.v1.html(st.session_state.generated_html, height=900, scrolling=True)
