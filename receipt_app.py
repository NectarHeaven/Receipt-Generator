import streamlit as st
import pandas as pd
import json
import re
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

st.set_page_config(page_title="Shree Gurudev Auto", layout="wide")

# ==========================================
# 0. HELPERS
# ==========================================
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

# Columns that must always be stored as plain strings in the sheet.
# This prevents pandas/gsheets from casting phone numbers to float64.
STR_COLS = ['Customer_Name', 'Contact_No', 'Vehicle_No', 'Total_KMs',
            'Mechanic_Names', 'Invoice_Date', 'Items_JSON']

def sanitise_df(df: pd.DataFrame) -> pd.DataFrame:
    """Force text columns to str and strip trailing '.0' from phone numbers."""
    for col in STR_COLS:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna('')
                .astype(str)
                .str.replace(r'\.0$', '', regex=True)   # "9876543210.0" → "9876543210"
                .str.strip()
            )
    return df

# ==========================================
# 1. PDF GENERATOR  (Received_Amt removed)
# ==========================================
class ReceiptPDF(FPDF):
    def header(self):
        self.rect(10, 10, 190, 254)
        self.set_xy(10, 12)
        self.set_font("helvetica", "B", 18)
        self.cell(110, 8, "SHREE GURUDEV AUTOMOBILES", border=0, ln=1, align="L")
        self.set_xy(10, 20)
        self.set_font("helvetica", "B", 8)
        self.cell(110, 4, "MULTI BRAND AUTHORISED WORKSHOP FOR TWO WHEELERS", border=0, ln=1, align="L")
        self.set_xy(110, 12)
        self.set_font("helvetica", "", 8)
        address = (
            "GROUND FLR, SHOP NO. 08 & 09, DEEPLAXMI BLDG.,\n"
            "MOHINDER SINGH, KABUL SINGH ROAD,\n"
            "KALYAN-421301.\n"
            "TEL.No. :Nitin Zope 9323962011, 8369846161"
        )
        self.multi_cell(90, 4, address, border=0, align="R")

    def footer(self):
        self.set_xy(10, 266)
        self.set_font("helvetica", "", 9)
        self.cell(0, 5, f"PAGE NO. : {self.page_no()}", align="L")

    def add_customer_details(self, data):
        self.line(10, 32, 200, 32)
        self.set_font("helvetica", "B", 9)
        self.set_xy(10, 34)
        self.cell(25, 5, "NAME");         self.set_font("helvetica", "", 9)
        self.cell(80, 5, str(data.get('Customer_Name', '')))
        self.set_font("helvetica", "B", 9)
        self.cell(30, 5, "BILL NO.");     self.set_font("helvetica", "", 9)
        self.cell(45, 5, str(data.get('Invoice_No', '')), align="R")
        self.ln(5)
        self.set_x(10)
        self.set_font("helvetica", "B", 9)
        self.cell(25, 5, "CONTACT NO."); self.set_font("helvetica", "", 9)
        contact = re.sub(r'\.0$', '', str(data.get('Contact_No', '')))
        self.cell(80, 5, contact)
        self.set_font("helvetica", "B", 9)
        self.cell(30, 5, "DATE");         self.set_font("helvetica", "", 9)
        
        # Display clean date string in PDF
        date_val = data.get('Invoice_Date', '')
        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime("%Y-%m-%d")
        else:
            date_str = str(date_val)[:10]
        self.cell(45, 5, date_str, align="R")
        
        self.ln(5)
        self.set_x(10)
        self.set_font("helvetica", "B", 9)
        self.cell(25, 5, "VEHICLE NO."); self.set_font("helvetica", "", 9)
        self.cell(80, 5, str(data.get('Vehicle_No', '')))
        self.ln(5)
        self.set_x(10)
        self.set_font("helvetica", "B", 9)
        self.cell(25, 5, "TOTAL KMS");   self.set_font("helvetica", "", 9)
        self.cell(80, 5, str(data.get('Total_KMs', '')))
        self.ln(6)
        self.line(10, 54, 200, 54)

    def add_table_headers(self):
        self.set_xy(10, 54)
        self.set_font("helvetica", "B", 9)
        self.cell(10,  8, "SNo.",                    align="C")
        self.cell(100, 8, "PRODUCT / SERVICE NAME", align="L")
        self.cell(20,  8, "QTY",                     align="C")
        self.cell(25,  8, "RATE",                    align="C")
        self.cell(35,  8, "AMOUNT",                  align="R")
        self.ln(8)
        self.line(10, 62, 200, 62)

    def draw_grid_lines(self, is_last_page=True):
        col1_3_y = 240 if is_last_page else 264
        self.line(20,  54, 20,  col1_3_y)
        self.line(120, 54, 120, 264)
        self.line(140, 54, 140, col1_3_y)
        self.line(165, 54, 165, 264)

    def add_footer_totals(self, totals_dict):
        self.line(10, 240, 200, 240)
        self.set_xy(10, 240)
        self.set_font("helvetica", "B", 9)
        self.cell(110, 6, f"TOTAL ITEMS {totals_dict.get('Total_Items_Count', '')}", align="L")
        self.line(10, 246, 120, 246)
        self.set_xy(10, 247)
        self.cell(110, 6, f"MECHANIC : {totals_dict.get('Mechanic_Names', '')}", align="L")
        self.set_xy(10, 255)
        self.set_font("helvetica", "I", 12)
        self.cell(110, 6, "*** THANK YOU ***", align="C")

        self.set_font("helvetica", "", 9)
        self.set_xy(120, 240)
        self.cell(45, 6, "GR. TOTAL",    align="R")
        self.cell(35, 6, f"{float(totals_dict.get('GR_Total', 0)):.2f}", align="R")
        self.line(120, 246, 200, 246)

        self.set_xy(120, 246)
        self.cell(45, 6, "LABOUR CHRGS", align="R")
        self.cell(35, 6, f"{float(totals_dict.get('Labour_Charges', 0)):.2f}", align="R")
        self.line(120, 252, 200, 252)

        self.set_xy(120, 252)
        self.set_font("helvetica", "B", 9)
        self.cell(45, 6, "NET TOTAL",    align="R")
        self.cell(35, 6, f"{float(totals_dict.get('Net_Total', 0)):.2f}", align="R")
        self.line(120, 258, 200, 258)

def generate_pdf(data):
    pdf = ReceiptPDF(orientation="P", unit="mm", format="A4")

    def create_new_page():
        pdf.add_page()
        pdf.add_customer_details(data)
        pdf.add_table_headers()
        return 64

    create_new_page()
    pdf.set_font("helvetica", "", 9)
    items_list = parse_items_json(data.get('Items_JSON', '[]'))

    for index, item in enumerate(items_list):
        if not isinstance(item, dict):
            continue
        desc   = str(item.get('Description', item.get('DESCRIPTION', '')))
        qty    = str(item.get('Qty',    item.get('QTY',    '')))
        rate   = float(item.get('Rate',   item.get('RATE',   0)))
        amount = float(item.get('Amount', item.get('AMOUNT', 0)))

        start_y = pdf.get_y()
        if start_y > 230:
            pdf.draw_grid_lines(is_last_page=False)
            create_new_page()
            pdf.set_font("helvetica", "", 9)
            start_y = pdf.get_y()

        pdf.set_xy(10, start_y)
        pdf.cell(10, 6, str(index + 1), border=0, align="C")
        pdf.set_xy(20, start_y)
        pdf.multi_cell(100, 6, desc, border=0, align="L")
        end_y = pdf.get_y()
        h = end_y - start_y

        pdf.set_xy(120, start_y); pdf.cell(20, h, qty,             border=0, align="C")
        pdf.set_xy(140, start_y); pdf.cell(25, h, f"{rate:.2f}",   border=0, align="C")
        pdf.set_xy(165, start_y); pdf.cell(35, h, f"{amount:.2f}", border=0, align="R")
        pdf.set_y(end_y)

    pdf.draw_grid_lines(is_last_page=True)
    pdf.add_footer_totals(data)
    return bytes(pdf.output())

# ==========================================
# 2. SESSION STATE
# ==========================================
defaults = {
    'pending_items':      [],
    'next_invoice_no':    1,
    'view_invoice':       None,
    'part_qty':           None,
    'part_rate':          None,
    'part_select':        "--- TYPE NEW PART ---",
    'edit_preview_items': None,
    'edit_preview_meta':  None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# 3. DB CONNECTION
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        df = conn.read(ttl=0)
        if df.empty:
            return df
        df = sanitise_df(df)
        if 'Invoice_No' in df.columns:
            df['Invoice_No'] = pd.to_numeric(df['Invoice_No'], errors='coerce').fillna(0).astype(int)
        
        if 'Invoice_Date' in df.columns:
            # Coerce unparseable values to NaT, then map completely to pure datetime.date objects safely
            parsed_dates = pd.to_datetime(df['Invoice_Date'], errors='coerce')
            default_date = date.today()
            
            # Extract only the date part; if NaT, swap with default native python date object immediately
            df['Invoice_Date'] = [p.date() if pd.notna(p) else default_date for p in parsed_dates]
            
        for num_col in ['GR_Total', 'Labour_Charges', 'Net_Total', 'Total_Items_Count']:
            if num_col in df.columns:
                df[num_col] = pd.to_numeric(df[num_col], errors='coerce').fillna(0)
        return df
    except Exception:
        return pd.DataFrame()

df_db = load_db()

if not df_db.empty and 'Invoice_No' in df_db.columns:
    last = df_db['Invoice_No'].max()
    st.session_state.next_invoice_no = int(last) + 1 if pd.notna(last) else 1

# ==========================================
# 4. DYNAMIC PARTS LIST
# ==========================================
def get_dynamic_parts_list(df_invoices):
    parts_set = set()
    if not df_invoices.empty and 'Master_Parts' in df_invoices.columns:
        for p in df_invoices['Master_Parts'].dropna():
            if str(p).strip():
                parts_set.add(str(p).strip().upper())
    if not df_invoices.empty and 'Items_JSON' in df_invoices.columns:
        for raw_val in df_invoices['Items_JSON'].dropna():
            for item in parse_items_json(raw_val):
                if isinstance(item, dict):
                    desc = item.get('Description', item.get('DESCRIPTION', ''))
                    if desc:
                        parts_set.add(str(desc).strip().upper())
    return ["--- TYPE NEW PART ---"] + sorted(parts_set)

AVAILABLE_PARTS = get_dynamic_parts_list(df_db)

# ==========================================
# 5. CRUD HELPERS
# ==========================================
def delete_invoice(inv_no):
    try:
        df = conn.read(ttl=0)
        df = sanitise_df(df)
        df['Invoice_No'] = pd.to_numeric(df['Invoice_No'], errors='coerce').fillna(0).astype(int)
        updated = df[df['Invoice_No'] != inv_no]
        conn.update(worksheet="Sheet1", data=updated)
        st.session_state.view_invoice = None
        st.success(f"Invoice #{inv_no} deleted.")
        st.rerun()
    except Exception as e:
        st.error(f"Error deleting: {e}")

def build_row_dict(inv_no, inv_date, cust, contact, veh, kms, mech,
                    items, gr_total, labour, net_total):
    """Single place to build a row — explicitly stores dates as text YYYY-MM-DD format."""
    if hasattr(inv_date, 'strftime'):
        date_str = inv_date.strftime("%Y-%m-%d")
    else:
        date_str = str(inv_date)[:10]

    return {
        "Invoice_No":        int(inv_no),
        "Invoice_Date":      date_str,
        "Customer_Name":     str(cust),
        "Contact_No":        str(contact),
        "Vehicle_No":        str(veh),
        "Total_KMs":         str(kms),
        "Mechanic_Names":    str(mech),
        "Items_JSON":        json.dumps(items),
        "Total_Items_Count": int(len(items)),
        "GR_Total":          round(float(gr_total),  2),
        "Labour_Charges":    round(float(labour),    2),
        "Net_Total":         round(float(net_total), 2),
    }

def save_updated_invoice(original_inv_no, updated_row: dict):
    try:
        df = conn.read(ttl=0)
        df = sanitise_df(df)
        df['Invoice_No'] = pd.to_numeric(df['Invoice_No'], errors='coerce').fillna(0).astype(int)

        idx_list = df.index[df['Invoice_No'] == original_inv_no].tolist()
        if not idx_list:
            st.error("Could not find invoice to update.")
            return

        for col, val in updated_row.items():
            if col not in df.columns:
                df[col] = None
            df.at[idx_list[0], col] = val

        df = sanitise_df(df)
        conn.update(worksheet="Sheet1", data=df)
        st.success(f"Invoice #{original_inv_no} updated!")
        
        # Resolve state safely by turning string back to native Python date object
        resolved_row = updated_row.copy()
        resolved_row['Invoice_Date'] = datetime.strptime(updated_row['Invoice_Date'], "%Y-%m-%d").date()
        
        st.session_state.view_invoice      = resolved_row
        st.session_state.edit_preview_items = None
        st.session_state.edit_preview_meta  = None
        st.rerun()
    except Exception as e:
        st.error(f"Error saving: {e}")

def add_part_callback():
    if st.session_state.part_select == "--- TYPE NEW PART ---":
        desc = st.session_state.get("part_desc_custom", "").upper()
    else:
        desc = st.session_state.part_select.upper()
    qty  = st.session_state.part_qty  if st.session_state.part_qty  is not None else 1
    rate = st.session_state.part_rate if st.session_state.part_rate is not None else 0.0
    if desc:
        st.session_state.pending_items.append({
            "Description": desc, "Qty": qty, "Rate": rate, "Amount": qty * rate
        })
        st.session_state.part_select = "--- TYPE NEW PART ---"
        if "part_desc_custom" in st.session_state:
            st.session_state.part_desc_custom = ""
        st.session_state.part_qty  = None
        st.session_state.part_rate = None

# ==========================================
# 6. DASHBOARD TABLE
# ==========================================
def display_interactive_rows(df, prefix=""):
    h1, h2, h3, h4, h5 = st.columns([1, 1.5, 3, 1.5, 3.5])
    for lbl, col in zip(["**Inv No**","**Date**","**Customer**","**Net Total**","**Actions**"],
                        [h1, h2, h3, h4, h5]):
        col.markdown(lbl)
    st.divider()

    for idx, row in df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([1, 1.5, 3, 1.5, 3.5])
        c1.write(str(row['Invoice_No']))
        
        date_val = row['Invoice_Date']
        c2.write(str(date_val.date()) if hasattr(date_val, 'date') else str(date_val))
        
        c3.write(str(row['Customer_Name']))
        c4.write(f"₹{float(row['Net_Total']):.2f}")

        with c5:
            b1, b2, b3 = st.columns([4, 4, 2])
            if b1.button("👁️ View / Edit", key=f"v_{prefix}_{idx}_{row['Invoice_No']}"):
                st.session_state.view_invoice      = row.to_dict()
                st.session_state.edit_preview_items = None
                st.session_state.edit_preview_meta  = None
                st.rerun()
            pdf_bytes = generate_pdf(row.to_dict())
            b2.download_button("📥 PDF", data=pdf_bytes,
                file_name=f"Invoice_{row['Invoice_No']}.pdf",
                mime="application/pdf",
                key=f"d_{prefix}_{idx}_{row['Invoice_No']}")
            if b3.button("🗑️", key=f"del_{prefix}_{idx}_{row['Invoice_No']}"):
                delete_invoice(row['Invoice_No'])

# ==========================================
# 7. EDITABLE PREVIEW / EDIT PANEL
# ==========================================
def show_edit_preview():
    data = st.session_state.view_invoice

    # ── initialise edit buffers on first open ──
    if st.session_state.edit_preview_meta is None:
        date_raw = data.get('Invoice_Date', '')
        safe_date = date.today()  # absolute fallback
        
        if pd.isna(date_raw) or not date_raw:
            safe_date = date.today()
        elif hasattr(date_raw, 'date'):
            safe_date = date_raw.date()
        elif isinstance(date_raw, date):
            safe_date = date_raw
        elif isinstance(date_raw, str):
            try:
                safe_date = datetime.strptime(date_raw.strip()[:10], "%Y-%m-%d").date()
            except Exception:
                safe_date = date.today()

        st.session_state.edit_preview_meta = {
            'Customer_Name':  str(data.get('Customer_Name', '')),
            'Contact_No':     re.sub(r'\.0$', '', str(data.get('Contact_No', ''))),
            'Vehicle_No':     str(data.get('Vehicle_No', '')),
            'Total_KMs':      str(data.get('Total_KMs', '')),
            'Invoice_Date':   safe_date,
            'Mechanic_Names': str(data.get('Mechanic_Names', '')),
        }

    if st.session_state.edit_preview_items is None:
        st.session_state.edit_preview_items = [
            dict(item) for item in parse_items_json(data.get('Items_JSON', '[]'))
        ]

    meta  = st.session_state.edit_preview_meta
    items = st.session_state.edit_preview_items

    st.markdown(
        f"## 📋 Invoice #{data.get('Invoice_No')} "
        f"<span style='font-size:14px;color:#FF6B2B;'>— all fields editable</span>",
        unsafe_allow_html=True
    )
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        meta['Customer_Name'] = st.text_input("Customer Name", value=meta['Customer_Name'], key="ep_cust").upper()
        meta['Contact_No']    = st.text_input("Contact No",    value=meta['Contact_No'],    key="ep_contact")
    with col2:
        meta['Vehicle_No']    = st.text_input("Vehicle No",    value=meta['Vehicle_No'],    key="ep_veh").upper()
        meta['Total_KMs']     = st.text_input("Total KMs",     value=meta['Total_KMs'],     key="ep_kms")
    with col3:
        meta['Invoice_Date']  = st.date_input("Date",          value=meta['Invoice_Date'],  key="ep_date")
        meta['Mechanic_Names']= st.text_input("Mechanic(s)",   value=meta['Mechanic_Names'],key="ep_mech").upper()

    st.divider()
    st.markdown("#### 🔧 Parts / Services")

    to_delete = None
    hc = st.columns([3, 1, 1, 1, 0.5])
    for lbl, col in zip(["**Description**","**Qty**","**Rate (₹)**","**Amount (₹)**","**Del**"], hc):
        col.markdown(lbl)

    for i, item in enumerate(items):
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 0.5])
        new_desc = c1.text_input("", value=str(item.get('Description', '')),
                                  key=f"ep_desc_{i}", label_visibility="collapsed").upper()
        new_qty  = c2.number_input("", value=int(item.get('Qty', 1)),    min_value=1,
                                   key=f"ep_qty_{i}",  label_visibility="collapsed")
        new_rate = c3.number_input("", value=float(item.get('Rate', 0)), min_value=0.0, step=1.0,
                                   key=f"ep_rate_{i}", label_visibility="collapsed")
        new_amt  = new_qty * new_rate
        c4.markdown(f"<div style='padding-top:32px;font-family:monospace;'>₹{new_amt:.2f}</div>",
                    unsafe_allow_html=True)
        if c5.button("🗑", key=f"ep_del_{i}"):
            to_delete = i
        items[i] = {'Description': new_desc, 'Qty': new_qty, 'Rate': new_rate, 'Amount': new_amt}

    if to_delete is not None:
        items.pop(to_delete)
        st.rerun()

    st.markdown("**➕ Add a part to this invoice**")
    na1, na2, na3, na4 = st.columns([3, 1, 1, 1])
    new_row_desc = na1.text_input("New description", key="ep_new_desc",
                                   placeholder="Part / service name").upper()
    new_row_qty  = na2.number_input("Qty",  min_value=1, value=1,   key="ep_new_qty",
                                    label_visibility="collapsed")
    new_row_rate = na3.number_input("Rate", min_value=0.0, value=0.0, step=1.0,
                                    key="ep_new_rate", label_visibility="collapsed")
    if na4.button("Add Row", key="ep_add_row"):
        if new_row_desc:
            items.append({'Description': new_row_desc, 'Qty': new_row_qty,
                          'Rate': new_row_rate, 'Amount': new_row_qty * new_row_rate})
            st.rerun()
        else:
            st.warning("Enter a description first.")

    st.divider()

    gr_total = sum(float(it.get('Amount', 0)) for it in items)
    labour   = st.number_input("Labour Charges (₹)", min_value=0.0, step=10.0,
                                value=float(data.get('Labour_Charges', 0)), key="ep_labour")
    net_total = gr_total + labour
    st.info(f"**GR Total:** ₹{gr_total:.2f}   |   **Labour:** ₹{labour:.2f}   |   **Net Total:** ₹{net_total:.2f}")

    act1, act2, act3 = st.columns([2, 2, 2])

    if act1.button("💾 Save All Changes", type="primary", use_container_width=True):
        row = build_row_dict(
            data.get('Invoice_No'), meta['Invoice_Date'],
            meta['Customer_Name'], meta['Contact_No'],
            meta['Vehicle_No'],    meta['Total_KMs'],
            meta['Mechanic_Names'], items, gr_total, labour, net_total
        )
        save_updated_invoice(int(data.get('Invoice_No')), row)

    pdf_data = {
        'Invoice_No':        data.get('Invoice_No'),
        'Invoice_Date':      meta['Invoice_Date'],
        'Customer_Name':     meta['Customer_Name'],
        'Contact_No':        meta['Contact_No'],
        'Vehicle_No':        meta['Vehicle_No'],
        'Total_KMs':         meta['Total_KMs'],
        'Mechanic_Names':    meta['Mechanic_Names'],
        'Items_JSON':        json.dumps(items),
        'Total_Items_Count': len(items),
        'GR_Total':          gr_total,
        'Labour_Charges':    labour,
        'Net_Total':         net_total,
    }
    pdf_bytes = generate_pdf(pdf_data)
    act2.download_button("📥 Download PDF", data=pdf_bytes,
        file_name=f"Invoice_{data.get('Invoice_No')}.pdf",
        mime="application/pdf", use_container_width=True)

    if act3.button("❌ Close", use_container_width=True):
        st.session_state.view_invoice       = None
        st.session_state.edit_preview_items = None
        st.session_state.edit_preview_meta  = None
        st.rerun()

# ==========================================
# 8. MAIN APP ROUTING
# ==========================================
if st.session_state.view_invoice:
    show_edit_preview()

else:
    tab_dash, tab_create, tab_search = st.tabs(
        ["📊 Main Dashboard", "➕ Create Invoice", "🔍 Search Invoices"]
    )

    # ── TAB 1: DASHBOARD ──
    with tab_dash:
        st.subheader("Last 10 Invoices")
        if not df_db.empty:
            recent_df = df_db.sort_values(by="Invoice_No", ascending=False).head(10)
            display_interactive_rows(recent_df, prefix="dash")
        else:
            st.info("No invoices found.")

    # ── TAB 2: CREATE INVOICE ──
    with tab_create:
        st.subheader("1. Invoice Details")
        inv_date = st.date_input("Date", date.today(), key="c_date")
        st.markdown(f"**Invoice No:** `{st.session_state.next_invoice_no}`")

        col4, col5, col6, col7 = st.columns(4)
        raw_cust     = col4.text_input("Customer Name", placeholder="Enter Name")
        cust_name    = raw_cust.upper()
        raw_contact  = col5.text_input("Contact No", placeholder="10 digits", max_chars=10)
        cust_contact = re.sub(r'\D', '', raw_contact)
        if raw_contact and raw_contact != cust_contact:
            st.warning("Numbers only — letters removed.")
        elif cust_contact and len(cust_contact) < 10:
            st.warning("⚠️ Must be 10 digits.")
        veh_no         = col6.text_input("Vehicle No",     placeholder="MH05CR8172").upper().strip()
        tot_kms        = col7.text_input("Total KMs",       placeholder="8500")
        mechanic_names = st.text_input("Mechanic Name(s)", placeholder="Enter mechanics").upper()

        st.divider()
        st.subheader("2. Add Parts")

        p_col1, p_col2, p_col3, p_col4 = st.columns([3, 1, 1, 1])
        with p_col1:
            st.markdown("**Description**")
            st.selectbox("Select Part", AVAILABLE_PARTS, key="part_select",
                         label_visibility="collapsed")
            if st.session_state.get("part_select") == "--- TYPE NEW PART ---":
                st.text_input("Custom Part", key="part_desc_custom",
                              placeholder="Type new part...", label_visibility="collapsed")
        with p_col2:
            st.markdown("**Qty**")
            st.number_input("Qty", min_value=1, step=1, key="part_qty",
                            placeholder="1", label_visibility="collapsed")
        with p_col3:
            st.markdown("**Rate (₹)**")
            st.number_input("Rate", min_value=0.0, step=1.0, key="part_rate",
                            placeholder="0.0", label_visibility="collapsed")
        with p_col4:
            st.write(""); st.write("")
            st.button("➕ Add Part", on_click=add_part_callback, use_container_width=True)

        if st.session_state.pending_items:
            st.markdown("**Parts Added — edit inline or delete:**")
            to_del = None
            hc1, hc2, hc3, hc4, hc5 = st.columns([4, 1, 1.2, 1.2, 0.6])
            for lbl, col in zip(["**Description**","**Qty**","**Rate (₹)**","**Amount (₹)**","**Del**"],
                                 [hc1,hc2,hc3,hc4,hc5]):
                col.markdown(lbl)

            for i, item in enumerate(st.session_state.pending_items):
                ec1, ec2, ec3, ec4, ec5 = st.columns([4, 1, 1.2, 1.2, 0.6])
                nd = ec1.text_input("", value=str(item['Description']),
                                    key=f"pi_desc_{i}", label_visibility="collapsed").upper()
                nq = ec2.number_input("", value=int(item['Qty']), min_value=1,
                                      key=f"pi_qty_{i}",  label_visibility="collapsed")
                nr = ec3.number_input("", value=float(item['Rate']), min_value=0.0, step=1.0,
                                      key=f"pi_rate_{i}", label_visibility="collapsed")
                na = nq * nr
                ec4.markdown(f"<div style='padding-top:32px;font-family:monospace;'>₹{na:.2f}</div>",
                             unsafe_allow_html=True)
                if ec5.button("🗑", key=f"pi_del_{i}"):
                    to_del = i
                st.session_state.pending_items[i] = {'Description': nd, 'Qty': nq, 'Rate': nr, 'Amount': na}

            if to_del is not None:
                st.session_state.pending_items.pop(to_del)
                st.rerun()

            st.divider()
            labour_chrgs = st.number_input("Labour Charges (₹)", min_value=0.0,
                                            step=10.0, value=None, placeholder="0.0")
            gr_total    = sum(it['Amount'] for it in st.session_state.pending_items)
            safe_labour = labour_chrgs if labour_chrgs is not None else 0.0
            net_total   = gr_total + safe_labour
            st.write(f"**GR Total:** ₹{gr_total:.2f}   |   **Net Total:** ₹{net_total:.2f}")

            if st.button("💾 Save & Generate Invoice", type="primary", use_container_width=True):
                if not cust_name:
                    st.error("Customer Name is required.")
                elif cust_contact and len(cust_contact) < 10:
                    st.error("Valid 10-digit contact number required.")
                else:
                    new_row = build_row_dict(
                        st.session_state.next_invoice_no, inv_date,
                        cust_name, cust_contact, veh_no, tot_kms,
                        mechanic_names, st.session_state.pending_items,
                        gr_total, safe_labour, net_total
                    )
                    fresh_df = load_db()
                    
                    # Wrap dictionary inside a DataFrame and convert date row instantly
                    new_row_df = pd.DataFrame([new_row])
                    if 'Invoice_Date' in new_row_df.columns:
                        new_row_df['Invoice_Date'] = pd.to_datetime(new_row_df['Invoice_Date']).dt.date
                        
                    updated_df = pd.concat([fresh_df, new_row_df], ignore_index=True)
                    updated_df = sanitise_df(updated_df)
                    conn.update(worksheet="Sheet1", data=updated_df)

                    # Hand over clean object instance to avoid viewing crashes
                    resolved_row = new_row.copy()
                    resolved_row['Invoice_Date'] = inv_date

                    st.session_state.view_invoice       = resolved_row
                    st.session_state.edit_preview_items = None
                    st.session_state.edit_preview_meta  = None
                    st.success(f"Invoice {st.session_state.next_invoice_no} saved!")
                    st.session_state.next_invoice_no += 1
                    st.session_state.pending_items = []
                    st.rerun()

    # ── TAB 3: SEARCH ──
    with tab_search:
        st.subheader("🔍 Search by Vehicle Number")
        sc1, sc2, sc3 = st.columns([2, 1, 1])
        veh_query = sc1.text_input("Vehicle Number", placeholder="e.g. MH05CR8172").upper().strip()

        min_date = date(2020, 1, 1)
        max_date = date.today()
        
        if not df_db.empty and 'Invoice_Date' in df_db.columns:
            # Extract valid python dates without risking NaN/NaT runtime conflicts
            valid_dates = [d for d in df_db['Invoice_Date'] if isinstance(d, date) and not pd.isna(d)]
            if valid_dates:
                min_date = min(valid_dates)
                max_date = max(valid_dates)

        date_from = sc2.date_input("From Date", value=min_date, key="s_from")
        date_to   = sc3.date_input("To Date",   value=max_date, key="s_to")

        run_search = veh_query or st.button("Show all in date range")
        if run_search:
            if df_db.empty:
                st.info("No invoices in database.")
            else:
                df_search = df_db.copy()
                if veh_query:
                    df_search = df_search[
                        df_search['Vehicle_No'].astype(str).str.upper().str.contains(veh_query, na=False)
                    ]
                
                # Perform direct, pure-python object comparison across dates 
                if 'Invoice_Date' in df_search.columns:
                    df_search = df_search[
                        df_search['Invoice_Date'].apply(lambda d: date_from <= d <= date_to if isinstance(d, date) else False)
                    ]
                df_search = df_search.sort_values(by="Invoice_No", ascending=False)

                if df_search.empty:
                    st.warning("No records found.")
                else:
                    total_rev = df_search['Net_Total'].astype(float).sum()
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Invoices Found", len(df_search))
                    m2.metric("Total Revenue",  f"₹{total_rev:,.2f}")
                    m3.metric("Date Range",     f"{date_from} → {date_to}")
                    st.divider()
                    display_interactive_rows(df_search, prefix="search")
