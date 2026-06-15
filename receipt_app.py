import streamlit as st
import pandas as pd
import json
import re
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

st.set_page_config(page_title="Shree Gurudev Auto", layout="wide")

# ─────────────────────────────────────────────
# 0. HELPERS
# ─────────────────────────────────────────────
def parse_items_json(raw_data):
    if isinstance(raw_data, str):
        try:
            parsed = json.loads(raw_data)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    elif isinstance(raw_data, list):
        return raw_data
    return []

STR_COLS = [
    'Customer_Name', 'Contact_No', 'Vehicle_No', 'Vehicle_Name',
    'Total_KMs', 'Mechanic_Names', 'Mechanic_Name', 'Invoice_Date', 'Items_JSON',
]

def sanitise_df(df: pd.DataFrame) -> pd.DataFrame:
    for col in STR_COLS:
        if col in df.columns:
            df[col] = (
                df[col].fillna('').astype(str)
                .str.replace(r'\.0$', '', regex=True).str.strip()
            )
    return df

def safe_date(val):
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return date.today()
        if isinstance(val, date) and not isinstance(val, datetime):
            return val
        if isinstance(val, datetime):
            return val.date()
        if hasattr(val, 'date'):
            d = val.date()
            return d if str(d) != 'NaT' else date.today()
        if isinstance(val, str) and val.strip():
            return datetime.strptime(val.strip()[:10], "%Y-%m-%d").date()
    except Exception:
        pass
    return date.today()

# ─────────────────────────────────────────────
# 1. PDF GENERATOR (FIXED POSITION FOOTER SYSTEM)
# ─────────────────────────────────────────────
class ReceiptPDF(FPDF):
    def __init__(self, invoice_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice_data = invoice_data

    def header(self):
        # Header banner
        self.set_xy(10, 12); self.set_font("helvetica", "B", 18)
        self.cell(110, 8, "SHREE GURUDEV AUTOMOBILES", border=0, ln=1, align="L")
        self.set_xy(10, 20); self.set_font("helvetica", "B", 8)
        self.cell(110, 4, "MULTI BRAND AUTHORISED WORKSHOP FOR TWO WHEELERS", border=0, ln=1, align="L")
        self.set_xy(110, 12); self.set_font("helvetica", "", 8)
        self.multi_cell(90, 4,
            "GROUND FLR, SHOP NO. 08 & 09, DEEPLAXMI BLDG.,\n"
            "MOHINDER SINGH, KABUL SINGH ROAD,\n"
            "KALYAN-421301.\n"
            "TEL.No. :Nitin Zope 9323962011, 8369846161",
            border=0, align="R")

    def footer(self):
        # Page number at the very bottom edge
        self.set_xy(10, 285); self.set_font("helvetica", "", 9)
        self.cell(0, 5, f"PAGE NO. : {self.page_no()}", align="L")

    def add_customer_details(self):
        self.line(10, 32, 200, 32)
        def bf(b): self.set_font("helvetica", "B" if b else "", 9)

        self.set_xy(10, 34)
        bf(True);  self.cell(25, 5, "NAME")
        bf(False); self.cell(80, 5, str(self.invoice_data.get('Customer_Name', '')))
        bf(True);  self.cell(30, 5, "BILL NO.")
        bf(False); self.cell(45, 5, str(self.invoice_data.get('Invoice_No', '')), align="R")
        self.ln(5)

        self.set_x(10)
        bf(True);  self.cell(25, 5, "CONTACT NO.")
        bf(False); self.cell(80, 5, re.sub(r'\.0$', '', str(self.invoice_data.get('Contact_No', ''))))
        bf(True);  self.cell(30, 5, "DATE")
        bf(False)
        dv = self.invoice_data.get('Invoice_Date', '')
        ds = dv.strftime("%Y-%m-%d") if hasattr(dv, 'strftime') else str(dv)[:10]
        self.cell(45, 5, ds, align="R")
        self.ln(5)

        self.set_x(10)
        bf(True);  self.cell(25, 5, "VEHICLE NO.")
        bf(False); self.cell(80, 5, str(self.invoice_data.get('Vehicle_No', '')))
        bf(True);  self.cell(30, 5, "VEHICLE NAME")
        bf(False); self.cell(45, 5, str(self.invoice_data.get('Vehicle_Name', '')).upper(), align="R")
        self.ln(5)

        self.set_x(10)
        bf(True);  self.cell(25, 5, "TOTAL KMS")
        bf(False); self.cell(80, 5, str(self.invoice_data.get('Total_KMs', '')))
        self.ln(6)
        self.line(10, 54, 200, 54)

    def add_table_headers(self):
        self.set_xy(10, 54); self.set_font("helvetica", "B", 9)
        self.cell(10, 8, "SNo.", align="C")
        self.cell(90, 8, "PRODUCT / SERVICE NAME", align="L")
        self.cell(15, 8, "QTY",    align="C")
        self.cell(25, 8, "MRP",   align="C")
        self.cell(25, 8, "DISC (%)", align="C")
        self.cell(25, 8, "AMOUNT", align="R")
        self.ln(8); self.line(10, 62, 200, 62)

    def draw_page_borders_and_grids(self, end_y):
        """Draws clean boundaries and vertical separator bars down to the designated line."""
        self.line(10, 10, 10, end_y)   # Left external frame
        self.line(200, 10, 200, end_y) # Right external frame
        self.line(20, 54, 20, end_y)   # SNo divider
        self.line(110, 54, 110, end_y) # Description divider
        self.line(125, 54, 125, end_y) # Qty divider
        self.line(150, 54, 150, end_y) # MRP divider
        self.line(175, 54, 175, end_y) # Discount divider
        self.line(10, end_y, 200, end_y) # Base cut closing line

    def draw_fixed_bottom_totals(self):
        """Locks the total summary box exactly to the bottom of the last page canvas."""
        start_y = 245 # Absolute anchor baseline point above page count
        
        # Outer border window structure for the summary card
        self.line(10, start_y, 10, start_y + 35)
        self.line(200, start_y, 200, start_y + 35)
        self.line(110, start_y, 110, start_y + 35)
        self.line(150, start_y, 150, start_y + 35)
        self.line(10, start_y, 200, start_y)
        self.line(10, start_y + 35, 200, start_y + 35)

        # Left Section (Total Items Count, Mechanics and Greetings)
        self.set_xy(12, start_y + 3); self.set_font("helvetica", "B", 9)
        # Ensure count is formatted clearly as a whole number integer
        item_count = int(float(self.invoice_data.get('Total_Items_Count', 0)))
        self.cell(95, 5, f"TOTAL ITEMS {item_count}", align="L")
        
        self.line(10, start_y + 11, 110, start_y + 11)
        
        self.set_xy(12, start_y + 14)
        mc = self.invoice_data.get('Mechanic_Names', self.invoice_data.get('Mechanic_Name', ''))
        self.cell(95, 5, f"MECHANIC : {mc}", align="L")
        
        # Clean centralized positioning for Thank You notice
        self.set_xy(10, start_y + 25); self.set_font("helvetica", "BI", 11)
        self.cell(100, 6, "*** THANK YOU ***", align="C")

        # Right Section (Subtotal, Labour fees, Net figures balances)
        self.set_font("helvetica", "", 9)
        
        # Row 1: Subtotal
        self.set_xy(110, start_y + 2)
        self.cell(40, 6, "SUBTOTAL", align="R")
        self.cell(50, 6, f"{float(self.invoice_data.get('GR_Total', 0)):.2f}", align="R")
        self.line(110, start_y + 9, 200, start_y + 9)
        
        # Row 2: Labour Charges
        self.set_xy(110, start_y + 11)
        self.cell(40, 6, "LABOUR CHRGS", align="R")
        self.cell(50, 6, f"{float(self.invoice_data.get('Labour_Charges', 0)):.2f}", align="R")
        self.line(110, start_y + 18, 200, start_y + 18)

        # Row 3: Double underlined Net Total signature window
        self.set_xy(110, start_y + 21); self.set_font("helvetica", "B", 10)
        self.cell(40, 10, "NET TOTAL", align="R")
        self.cell(50, 10, f"{float(self.invoice_data.get('Net_Total', 0)):.2f}", align="R")
        
        self.line(110, start_y + 31, 200, start_y + 31)
        self.line(110, start_y + 32.5, 200, start_y + 32.5)


def generate_pdf(data):
    pdf = ReceiptPDF(invoice_data=data, orientation="P", unit="mm", format="A4")
    
    def new_page():
        pdf.add_page()
        pdf.line(10, 10, 200, 10) # Top border line
        pdf.add_customer_details()
        pdf.add_table_headers()
        
    new_page()
    pdf.set_font("helvetica", "", 9)
    
    items = parse_items_json(data.get('Items_JSON', '[]'))
    
    for idx, item in enumerate(items):
        if not isinstance(item, dict): continue
        desc   = str(item.get('Description', item.get('DESCRIPTION', '')))
        qty    = str(item.get('Qty',    item.get('QTY',    '')))
        mrp    = float(item.get('MRP', item.get('mrp', item.get('Rate', item.get('RATE', 0)))))
        disc   = float(item.get('Discount_Percent', item.get('discount_percent', 0)))
        amount = float(item.get('Amount', item.get('AMOUNT', 0)))
        
        sy = pdf.get_y()
        
        # Hard stop limit for layout rows on current page. 
        # If a row passes y=240, it will crash into our fixed bottom totals block, so push it to next page.
        if sy > 240:
            pdf.draw_page_borders_and_grids(end_y=sy)
            new_page()
            pdf.set_font("helvetica", "", 9)
            sy = pdf.get_y()
            
        pdf.set_xy(10, sy); pdf.cell(10, 6, str(idx+1), border=0, align="C")
        pdf.set_xy(20, sy); pdf.multi_cell(90, 6, desc, border=0, align="L")
        ey = pdf.get_y(); h = ey - sy
        pdf.set_xy(110, sy); pdf.cell(15, h, qty,             border=0, align="C")
        pdf.set_xy(125, sy); pdf.cell(25, h, f"{mrp:.2f}",   border=0, align="C")
        pdf.set_xy(150, sy); pdf.cell(25, h, f"{disc:.1f}%",  border=0, align="C")
        pdf.set_xy(175, sy); pdf.cell(25, h, f"{amount:.2f}", border=0, align="R")
        pdf.set_y(ey)
        
    final_table_y = pdf.get_y()
    
    # Close off the item table grids wherever it naturally finished on the final page
    pdf.draw_page_borders_and_grids(end_y=final_table_y)
    
    # Stamp the totals box exactly at y=245 at the bottom of the final page
    pdf.draw_fixed_bottom_totals()
    
    return bytes(pdf.output())

# ─────────────────────────────────────────────
# 2. SESSION STATE
# ─────────────────────────────────────────────
defaults = {
    'pending_items':      [],
    'next_invoice_no':    1,
    'view_invoice':       None,
    'edit_preview_items': None,
    'edit_preview_meta':  None,
    'delete_confirm':     None,
    'part_v':             0,   
    'ep_part_v':          0,   
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# 3. DB CONNECTION
# ─────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        df = conn.read(ttl=0)
        if df.empty: return df
        df = sanitise_df(df)
        if 'Mechanic_Name' in df.columns and 'Mechanic_Names' not in df.columns:
            df['Mechanic_Names'] = df['Mechanic_Name']
        if 'Invoice_No' in df.columns:
            df['Invoice_No'] = pd.to_numeric(df['Invoice_No'], errors='coerce').fillna(0).astype(int)
        if 'Invoice_Date' in df.columns:
            parsed = pd.to_datetime(df['Invoice_Date'], errors='coerce')
            df['Invoice_Date'] = [p.date() if pd.notna(p) else date.today() for p in parsed]
        for nc in ['GR_Total', 'Labour_Charges', 'Net_Total', 'Total_Items_Count', 'Discount']:
            if nc in df.columns:
                df[nc] = pd.to_numeric(df[nc], errors='coerce').fillna(0)
        return df
    except Exception:
        return pd.DataFrame()

df_db = load_db()

if not df_db.empty and 'Invoice_No' in df_db.columns:
    last = df_db['Invoice_No'].max()
    st.session_state.next_invoice_no = int(last) + 1 if pd.notna(last) else 1

# ─────────────────────────────────────────────
# 4. PARTS SUGGESTION LIST
# ─────────────────────────────────────────────
def get_parts_list(df_invoices):
    parts = set()
    if not df_invoices.empty and 'Master_Parts' in df_invoices.columns:
        for p in df_invoices['Master_Parts'].dropna():
            if str(p).strip(): parts.add(str(p).strip().upper())
    if not df_invoices.empty and 'Items_JSON' in df_invoices.columns:
        for raw in df_invoices['Items_JSON'].dropna():
            for item in parse_items_json(raw):
                if isinstance(item, dict):
                    d = item.get('Description', item.get('DESCRIPTION', ''))
                    if d: parts.add(str(d).strip().upper())
    return sorted(parts)

ALL_PARTS = get_parts_list(df_db)

# ─────────────────────────────────────────────
# 5. CRUD HELPERS
# ─────────────────────────────────────────────
def build_row_dict(inv_no, inv_date, cust, contact, veh, veh_name,
                    kms, mech, items, gr_total, labour, discount, net_total):
    ds = inv_date.strftime("%Y-%m-%d") if hasattr(inv_date, 'strftime') else str(inv_date)[:10]
    return {
        "Invoice_No":        int(inv_no),
        "Invoice_Date":      ds,
        "Customer_Name":     str(cust),
        "Contact_No":        str(contact),
        "Vehicle_No":        str(veh),
        "Vehicle_Name":      str(veh_name),
        "Total_KMs":         str(kms),
        "Mechanic_Names":    str(mech),
        "Items_JSON":        json.dumps(items),
        "Total_Items_Count": int(len(items)),
        "GR_Total":          round(float(gr_total),   2),
        "Labour_Charges":    round(float(labour),     2),
        "Discount":          round(float(discount),   2),
        "Net_Total":         round(float(net_total),  2),
    }

def delete_invoice(inv_no):
    try:
        df = conn.read(ttl=0); df = sanitise_df(df)
        df['Invoice_No'] = pd.to_numeric(df['Invoice_No'], errors='coerce').fillna(0).astype(int)
        conn.update(worksheet="Sheet1", data=df[df['Invoice_No'] != inv_no])
        st.session_state.view_invoice   = None
        st.session_state.delete_confirm = None
        st.success(f"Invoice #{inv_no} deleted."); st.rerun()
    except Exception as e:
        st.error(f"Error deleting: {e}")

def save_updated_invoice(original_inv_no, updated_row: dict):
    try:
        df = conn.read(ttl=0); df = sanitise_df(df)
        df['Invoice_No'] = pd.to_numeric(df['Invoice_No'], errors='coerce').fillna(0).astype(int)
        idx_list = df.index[df['Invoice_No'] == original_inv_no].tolist()
        if not idx_list:
            st.error("Could not find invoice to update."); return
        for col, val in updated_row.items():
            if col not in df.columns: df[col] = None
            df.at[idx_list[0], col] = val
        df = sanitise_df(df)
        conn.update(worksheet="Sheet1", data=df)
        resolved = updated_row.copy()
        resolved['Invoice_Date'] = safe_date(updated_row['Invoice_Date'])
        st.session_state.view_invoice       = resolved
        st.session_state.edit_preview_items = None
        st.session_state.edit_preview_meta  = None
        st.success(f"Invoice #{original_inv_no} updated!"); st.rerun()
    except Exception as e:
        st.error(f"Error saving: {e}")

# ─────────────────────────────────────────────
# 6. SHARED TOTALS WIDGET
# ─────────────────────────────────────────────
def totals_widget(gr_total, default_labour=0.0, labour_key="labour"):
    st.markdown("""
    <style>
    .totals-box{background:#1a1a2e;border:1px solid #2e4057;border-radius:8px;
                padding:16px 20px;margin-top:12px;}
    .tot-row{display:flex;justify-content:space-between;align-items:center;
             padding:6px 0;font-size:15px;border-bottom:1px solid #2e4057;}
    .tot-row:last-child{border-bottom:none;}
    .tot-label{color:#b0bec5;}
    .tot-val{font-family:monospace;color:#e8eff5;}
    .tot-net{font-size:18px;font-weight:700;color:#ff6b2b;}
    </style>""", unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        labour = st.number_input("Labour Charges (₹)", min_value=0.0, step=10.0,
                                   value=float(default_labour), key=labour_key)
    with c2:
        net_total = gr_total + labour
        st.markdown(f"""
        <div class="totals-box">
          <div class="tot-row">
            <span class="tot-label">Items Total</span>
            <span class="tot-val">₹{gr_total:,.2f}</span>
          </div>
          <div class="tot-row">
            <span class="tot-label">Labour Charges</span>
            <span class="tot-val">₹{labour:,.2f}</span>
          </div>
          <div class="tot-row">
            <span class="tot-net">Net Total</span>
            <span class="tot-net">₹{net_total:,.2f}</span>
          </div>
        </div>""", unsafe_allow_html=True)
    return labour, 0.0, net_total

# ─────────────────────────────────────────────
# 7. PARTS INPUT WIDGET
# ─────────────────────────────────────────────
def parts_input_widget(prefix="c"):
    v_key = "part_v" if prefix == "c" else "ep_part_v"
    v = st.session_state[v_key]
    OPTIONS = [""] + ALL_PARTS   

    p1, p2, p3, p4, p5 = st.columns([2.5, 0.8, 1.1, 1.1, 1.1])
    with p1:
        st.markdown("**Description**")
        chosen = st.selectbox(
            "desc", options=OPTIONS, index=0, key=f"{prefix}_pick_{v}",
            label_visibility="collapsed", placeholder="ENGINE OIL, SPARK PLUG..."
        )
        if chosen == "":
            desc = st.text_input("New part name", key=f"{prefix}_custom_{v}",
                                 placeholder="Type new part...", label_visibility="collapsed").upper().strip()
        else:
            desc = chosen  
            st.caption(f"Selected: **{desc}**")

    with p2:
        st.markdown("**Qty**")
        qty = st.number_input("qty", min_value=1, step=1, value=1, key=f"{prefix}_qty_{v}", label_visibility="collapsed")
    with p3:
        st.markdown("**MRP (₹)**")
        mrp = st.number_input("mrp", min_value=0.0, step=1.0, value=0.0, key=f"{prefix}_mrp_{v}", label_visibility="collapsed")
    with p4:
        st.markdown("**Discount (%)**")
        disc_p = st.number_input("disc_p", min_value=0.0, max_value=100.0, step=0.5, value=0.0, key=f"{prefix}_disc_{v}", label_visibility="collapsed")
    with p5:
        st.write(""); st.write("")
        add_clicked = st.button("➕ Add Part", key=f"{prefix}_add_{v}", use_container_width=True)

    if add_clicked:
        if not desc:
            st.warning("Enter or select a description first.")
            return False
        
        base_amt = int(qty) * float(mrp)
        final_amt = base_amt * (1.0 - (float(disc_p) / 100.0))
        
        result = {
            "Description": desc, 
            "Qty": int(qty), 
            "MRP": float(mrp), 
            "Discount_Percent": float(disc_p), 
            "Amount": round(final_amt, 2)
        }
        st.session_state[v_key] += 1
        return result
    return False

# ─────────────────────────────────────────────
# 8. EDITABLE INLINE PARTS TABLE
# ─────────────────────────────────────────────
def editable_parts_table(items_list, key_prefix="t", inv_no=""):
    if not items_list:
        st.caption("No parts yet.")
        return items_list, False

    hc = st.columns([2.5, 0.8, 1.2, 1.2, 1.2, 0.5])
    for lbl, col in zip(["**Description**","**Qty**","**MRP (₹)**","**Discount (%)**","**Amt (₹)**",""], hc):
        col.markdown(lbl)

    to_del = None
    updated = []
    for i, item in enumerate(items_list):
        c1, c2, c3, c4, c5, c6 = st.columns([2.5, 0.8, 1.2, 1.2, 1.2, 0.5])
        suffix = f"{inv_no}_{i}" if inv_no else str(i)
        
        nd = c1.text_input("", value=str(item.get('Description','')), key=f"{key_prefix}_desc_{suffix}", label_visibility="collapsed").upper()
        nq = c2.number_input("", value=int(item.get('Qty',1)), min_value=1, key=f"{key_prefix}_qty_{suffix}", label_visibility="collapsed")
        
        current_mrp = float(item.get('MRP', item.get('mrp', item.get('Rate', item.get('RATE', 0)))))
        nm = c3.number_input("", value=current_mrp, min_value=0.0, step=1.0, key=f"{key_prefix}_mrp_{suffix}", label_visibility="collapsed")
        
        current_disc = float(item.get('Discount_Percent', item.get('discount_percent', 0)))
        ndisc = c4.number_input("", value=current_disc, min_value=0.0, max_value=100.0, step=0.5, key=f"{key_prefix}_disc_{suffix}", label_visibility="collapsed")
        
        na = round((nq * nm) * (1.0 - (ndisc / 100.0)), 2)
        
        c5.markdown(f"<div style='padding-top:6px;font-family:monospace;'>₹{na:.2f}</div>", unsafe_allow_html=True)
        if c6.button("🗑", key=f"{key_prefix}_del_{suffix}"):
            to_del = i
        updated.append({'Description': nd, 'Qty': nq, 'MRP': nm, 'Discount_Percent': ndisc, 'Amount': na})

    if to_del is not None:
        updated.pop(to_del)
        return updated, True
    return updated, False

# ─────────────────────────────────────────────
# 9. DASHBOARD ROW TABLE
# ─────────────────────────────────────────────
def display_interactive_rows(df, prefix=""):
    h1, h2, h3, h4, h5 = st.columns([1, 1.5, 3, 1.5, 3.5])
    for lbl, col in zip(["**Inv**","**Date**","**Customer**","**Net Total**","**Actions**"], [h1,h2,h3,h4,h5]):
        col.markdown(lbl)
    st.divider()
    for idx, row in df.iterrows():
        c1,c2,c3,c4,c5 = st.columns([1,1.5,3,1.5,3.5])
        c1.write(str(row['Invoice_No']))
        dv = row['Invoice_Date']
        c2.write(str(dv) if isinstance(dv, date) else str(dv)[:10])
        c3.write(str(row['Customer_Name']))
        c4.write(f"₹{float(row['Net_Total']):.2f}")
        with c5:
            b1,b2,b3 = st.columns([4,4,2])
            if b1.button("👁️ View / Edit", key=f"v_{prefix}_{idx}_{row['Invoice_No']}"):
                st.session_state.view_invoice       = row.to_dict()
                st.session_state.edit_preview_items = None
                st.session_state.edit_preview_meta  = None
                st.rerun()
            b2.download_button("📥 PDF", data=generate_pdf(row.to_dict()),
                file_name=f"Invoice_{row['Invoice_No']}.pdf", mime="application/pdf",
                key=f"d_{prefix}_{idx}_{row['Invoice_No']}")
            if b3.button("🗑️", key=f"del_{prefix}_{idx}_{row['Invoice_No']}"):
                st.session_state.delete_confirm = int(row['Invoice_No'])
                st.rerun()

# ─────────────────────────────────────────────
# 10. EDITABLE PREVIEW PANEL
# ─────────────────────────────────────────────
def show_edit_preview():
    data  = st.session_state.view_invoice

    if st.session_state.edit_preview_meta is None:
        st.session_state.edit_preview_meta = {
            'Customer_Name':  str(data.get('Customer_Name', '')),
            'Contact_No':     re.sub(r'\.0$', '', str(data.get('Contact_No', ''))),
            'Vehicle_No':     str(data.get('Vehicle_No', '')),
            'Vehicle_Name':   str(data.get('Vehicle_Name', '')),
            'Total_KMs':      str(data.get('Total_KMs', '')),
            'Invoice_Date':   safe_date(data.get('Invoice_Date', '')),
            'Mechanic_Names': str(data.get('Mechanic_Names', data.get('Mechanic_Name', ''))),
        }
    if st.session_state.edit_preview_items is None:
        st.session_state.edit_preview_items = [
            dict(i) for i in parse_items_json(data.get('Items_JSON', '[]'))
        ]

    meta  = st.session_state.edit_preview_meta
    items = st.session_state.edit_preview_items

    st.markdown(
        f"## 📋 Invoice #{data.get('Invoice_No')} "
        f"<span style='font-size:14px;color:#FF6B2B;'>— all fields editable</span>",
        unsafe_allow_html=True)
    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        meta['Customer_Name'] = st.text_input("Customer Name", value=meta['Customer_Name'], key="ep_cust").upper()
        meta['Contact_No']    = st.text_input("Contact No",    value=meta['Contact_No'],    key="ep_contact")
    with c2:
        meta['Vehicle_No']   = st.text_input("Vehicle No",   value=meta['Vehicle_No'],   key="ep_veh").upper()
        meta['Vehicle_Name'] = st.text_input("Vehicle Name", value=meta['Vehicle_Name'], key="ep_vname").upper()
    with c3:
        meta['Total_KMs']     = st.text_input("Total KMs",  value=meta['Total_KMs'],     key="ep_kms")
        meta['Invoice_Date']  = st.date_input("Date",       value=meta['Invoice_Date'],  key="ep_date")
    meta['Mechanic_Names'] = st.text_input("Mechanic(s)", value=meta['Mechanic_Names'], key="ep_mech").upper()

    st.divider()
    st.markdown("#### 🔧 Parts / Services")

    items, deleted = editable_parts_table(items, key_prefix="ep", inv_no=str(data.get('Invoice_No')))
    st.session_state.edit_preview_items = items
    if deleted: st.rerun()

    st.markdown("**➕ Add a part to this invoice**")
    result = parts_input_widget(prefix="ep")
    if result:
        items.append(result)
        st.session_state.edit_preview_items = items
        st.rerun()

    st.divider()
    gr_total = sum(float(it.get('Amount', 0)) for it in items)
    labour, _, net_total = totals_widget(
        gr_total,
        default_labour = float(data.get('Labour_Charges', 0)),
        labour_key     = "ep_labour"
    )

    act1, act2, act3 = st.columns(3)
    if act1.button("💾 Save All Changes", type="primary", use_container_width=True):
        row = build_row_dict(
            data.get('Invoice_No'), meta['Invoice_Date'],
            meta['Customer_Name'], meta['Contact_No'],
            meta['Vehicle_No'],    meta['Vehicle_Name'],
            meta['Total_KMs'],     meta['Mechanic_Names'],
            items, gr_total, labour, 0.0, net_total
        )
        save_updated_invoice(int(data.get('Invoice_No')), row)

    pdf_data = {**meta,
        'Invoice_No': data.get('Invoice_No'),
        'Invoice_Date': meta['Invoice_Date'],
        'Items_JSON': json.dumps(items),
        'Total_Items_Count': len(items),
        'GR_Total': gr_total, 'Labour_Charges': labour,
        'Discount': 0.0,  'Net_Total': net_total,
        'Mechanic_Names': meta['Mechanic_Names'],
    }
    act2.download_button("📥 Download PDF", data=generate_pdf(pdf_data),
        file_name=f"Invoice_{data.get('Invoice_No')}.pdf",
        mime="application/pdf", use_container_width=True)

    if act3.button("❌ Close", use_container_width=True):
        st.session_state.view_invoice       = None
        st.session_state.edit_preview_items = None
        st.session_state.edit_preview_meta  = None
        st.rerun()

# ─────────────────────────────────────────────
# 11. MAIN ROUTING
# ─────────────────────────────────────────────
if st.session_state.view_invoice:
    show_edit_preview()

else:
    if st.session_state.delete_confirm is not None:
        inv = st.session_state.delete_confirm
        st.error("### ⚠️ Permanent Deletion Warning")
        st.markdown(f"Delete **Invoice #{inv}**? This cannot be undone.")
        ac1, ac2, _ = st.columns([2, 2, 6])
        if ac1.button("🔥 Yes, delete", type="primary", use_container_width=True):
            delete_invoice(inv)
        if ac2.button("🚫 Cancel", use_container_width=True):
            st.session_state.delete_confirm = None; st.rerun()
        st.divider()

    tab_dash, tab_create, tab_search = st.tabs(
        ["📊 Main Dashboard", "➕ Create Invoice", "🔍 Search Invoices"])

    with tab_dash:
        st.subheader("Last 10 Invoices")
        if not df_db.empty:
            display_interactive_rows(
                df_db.sort_values("Invoice_No", ascending=False).head(10), prefix="dash")
        else:
            st.info("No invoices found.")

    with tab_create:
        st.subheader("1. Invoice Details")
        inv_date = st.date_input("Date", date.today(), key="c_date")
        st.markdown(f"**Invoice No:** `{st.session_state.next_invoice_no}`")

        col1, col2, col3, col4 = st.columns(4)
        raw_cust    = col1.text_input("Customer Name", placeholder="Enter Name")
        cust_name   = raw_cust.upper()
        raw_contact = col2.text_input("Contact No", placeholder="10 digits", max_chars=10)
        cust_contact= re.sub(r'\D', '', raw_contact)
        if raw_contact and raw_contact != cust_contact:
            st.warning("Numbers only — letters removed.")
        elif cust_contact and len(cust_contact) < 10:
            st.warning("⚠️ Must be 10 digits.")
        veh_no   = col3.text_input("Vehicle No",   placeholder="MH05CR8172").upper().strip()
        veh_name = col4.text_input("Vehicle Name", placeholder="ACTIVA 6G").upper().strip()

        ck, cm = st.columns(2)
        tot_kms = ck.text_input("Total KMs", placeholder="8500")
        mechanic= cm.text_input("Mechanic Name(s)", placeholder="Enter mechanics").upper()

        st.divider()
        st.subheader("2. Add Parts")

        result = parts_input_widget(prefix="c")
        if result:
            st.session_state.pending_items.append(result)
            st.rerun()

        if st.session_state.pending_items:
            st.markdown("**Parts Added — edit inline or delete:**")
            st.session_state.pending_items, deleted = editable_parts_table(
                st.session_state.pending_items, key_prefix="pi", inv_no="pending")
            if deleted: st.rerun()

            st.divider()
            gr_total = sum(it['Amount'] for it in st.session_state.pending_items)
            labour, _, net_total = totals_widget(gr_total, labour_key="c_labour")

            if st.button("💾 Save & Generate Invoice", type="primary", use_container_width=True):
                if not cust_name:
                    st.error("Customer Name is required.")
                elif cust_contact and len(cust_contact) < 10:
                    st.error("Valid 10-digit contact number required.")
                else:
                    new_row = build_row_dict(
                        st.session_state.next_invoice_no, inv_date,
                        cust_name, cust_contact, veh_no, veh_name,
                        tot_kms, mechanic,
                        st.session_state.pending_items,
                        gr_total, labour, 0.0, net_total
                    )
                    fresh_df = load_db()
                    ndf = pd.DataFrame([new_row])
                    ndf['Invoice_Date'] = pd.to_datetime(ndf['Invoice_Date']).dt.date
                    updated_df = sanitise_df(pd.concat([fresh_df, ndf], ignore_index=True))
                    conn.update(worksheet="Sheet1", data=updated_df)

                    resolved = new_row.copy(); resolved['Invoice_Date'] = inv_date
                    resolved['Items_JSON'] = st.session_state.pending_items
                    
                    st.session_state.view_invoice       = resolved
                    st.session_state.edit_preview_items = None
                    st.session_state.edit_preview_meta  = None
                    st.success(f"Invoice {st.session_state.next_invoice_no} saved!")
                    st.session_state.next_invoice_no += 1
                    st.session_state.pending_items = []
                    st.rerun()

    with tab_search:
        st.subheader("🔍 Search by Vehicle Number")
        sc1, sc2, sc3 = st.columns([2, 1, 1])
        veh_query = sc1.text_input("Vehicle Number", placeholder="MH05CR8172").upper().strip()

        all_dates  = [d for d in df_db.get('Invoice_Date', pd.Series(dtype=object))
                      if isinstance(d, date)] if not df_db.empty else []
        min_date   = min(all_dates) if all_dates else date(2020,1,1)
        date_from  = sc2.date_input("From Date", value=min_date, key="s_from")
        date_to    = sc3.date_input("To Date",   value=date.today(), key="s_to")

        if veh_query or st.button("Show all in date range"):
            if df_db.empty:
                st.info("No invoices in database.")
            else:
                df_s = df_db.copy()
                if veh_query:
                    df_s = df_s[df_s['Vehicle_No'].astype(str).str.upper().str.contains(veh_query, na=False)]
                if 'Invoice_Date' in df_s.columns:
                    df_s = df_s[df_s['Invoice_Date'].apply(
                        lambda d: date_from <= d <= date_to if isinstance(d, date) else False)]
                
                df_s = df_s.sort_values("Invoice_No", ascending=False)
                if df_s.empty:
                    st.warning("No records found.")
                else:
                    m1,m2,m3 = st.columns(3)
                    m1.metric("Found",         len(df_s))
                    m2.metric("Total Revenue", f"₹{df_s['Net_Total'].astype(float).sum():,.2f}")
                    m3.metric("Date Range",    f"{date_from} → {date_to}")
                    st.divider()
                    display_interactive_rows(df_s, prefix="search")
