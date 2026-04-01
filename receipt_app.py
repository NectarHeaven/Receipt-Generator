import streamlit as st
import pandas as pd
import json
import re
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
from datetime import date

st.set_page_config(page_title="Shree Gurudev Auto", layout="wide")

# ==========================================
# 1. PDF GENERATOR CLASS WITH PAGINATION
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

    def add_customer_details(self, data):
        self.line(10, 32, 200, 32) 
        self.set_font("helvetica", "B", 9)
        self.set_xy(10, 34)
        self.cell(25, 5, "NAME")
        self.set_font("helvetica", "", 9)
        self.cell(80, 5, str(data.get('Customer_Name', '')))
        
        self.set_font("helvetica", "B", 9)
        self.cell(30, 5, "BILL NO.")
        self.set_font("helvetica", "", 9)
        self.cell(45, 5, str(data.get('Invoice_No', '')), align="R")
        self.ln(5)

        self.set_x(10)
        self.set_font("helvetica", "B", 9)
        self.cell(25, 5, "CONTACT NO.")
        self.set_font("helvetica", "", 9)
        self.cell(80, 5, str(data.get('Contact_No', '')))
        
        self.set_font("helvetica", "B", 9)
        self.cell(30, 5, "DATE")
        self.set_font("helvetica", "", 9)
        self.cell(45, 5, str(data.get('Invoice_Date', '')), align="R")
        self.ln(5)

        self.set_x(10)
        self.set_font("helvetica", "B", 9)
        self.cell(25, 5, "VEHICLE NO.")
        self.set_font("helvetica", "", 9)
        self.cell(80, 5, str(data.get('Vehicle_No', '')))
        self.ln(5)

        self.set_x(10)
        self.set_font("helvetica", "B", 9)
        self.cell(25, 5, "TOTAL KMS")
        self.set_font("helvetica", "", 9)
        self.cell(80, 5, str(data.get('Total_KMs', '')))
        self.ln(6)
        self.line(10, 54, 200, 54) 

    def add_table_headers(self):
        self.set_xy(10, 54)
        self.set_font("helvetica", "B", 9)
        self.cell(10, 8, "SNo.", align="C")
        self.cell(100, 8, "PRODUCT / SERVICE NAME", align="L")
        self.cell(20, 8, "QTY", align="C")
        self.cell(25, 8, "RATE", align="C")
        self.cell(35, 8, "AMOUNT", align="R")
        self.ln(8)
        self.line(10, 62, 200, 62)

    def draw_grid_lines(self):
        self.line(20, 54, 20, 240)   
        self.line(120, 54, 120, 264) 
        self.line(140, 54, 140, 240) 
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
        self.cell(45, 6, "GR. TOTAL", align="R")
        self.cell(35, 6, f"{float(totals_dict.get('GR_Total', 0)):.2f}", align="R")
        self.line(120, 246, 200, 246)

        self.set_xy(120, 246)
        self.cell(45, 6, "LABOUR CHRGS", align="R")
        self.cell(35, 6, f"{float(totals_dict.get('Labour_Charges', 0)):.2f}", align="R")
        self.line(120, 252, 200, 252)

        self.set_xy(120, 252)
        self.set_font("helvetica", "B", 9)
        self.cell(45, 6, "NET TOTAL", align="R")
        self.cell(35, 6, f"{float(totals_dict.get('Net_Total', 0)):.2f}", align="R")
        self.line(120, 258, 200, 258)

        self.set_xy(120, 258)
        self.set_font("helvetica", "", 9)
        self.cell(45, 6, "Received Amt", align="R")
        self.cell(35, 6, f"{float(totals_dict.get('Received_Amt', 0)):.2f}", align="R")
        
        self.set_xy(10, 266)
        self.cell(0, 5, f"PAGE NO. : {self.page_no()}", align="L")

def generate_pdf(data):
    pdf = ReceiptPDF(orientation="P", unit="mm", format="A4")
    
    # Helper function to trigger a clean new page
    def create_new_page():
        pdf.add_page()
        pdf.add_customer_details(data)
        pdf.add_table_headers()
        return 64 # Reset y_pos to just below the header

    y_pos = create_new_page()
    pdf.set_font("helvetica", "", 9)
    items_list = json.loads(data.get('Items_JSON', '[]'))
    
    for index, item in enumerate(items_list):
        # 🚨 PAGINATION LOGIC: If we hit 230mm down the page, flip to next page
        if y_pos > 230:
            pdf.draw_grid_lines()
            y_pos = create_new_page()
            pdf.set_font("helvetica", "", 9)

        desc = item.get('Description', item.get('DESCRIPTION', ''))
        qty = item.get('Qty', item.get('QTY', 0))
        rate = item.get('Rate', item.get('RATE', 0.0))
        amount = item.get('Amount', item.get('AMOUNT', 0.0))
        
        pdf.set_xy(10, y_pos)
        pdf.cell(10, 5, str(index + 1), align="C") 
        pdf.cell(100, 5, str(desc), align="L")
        pdf.cell(20, 5, str(qty), align="C")
        pdf.cell(25, 5, f"{float(rate):.2f}", align="C")
        pdf.cell(35, 5, f"{float(amount):.2f}", align="R")
        y_pos += 6
        
    pdf.draw_grid_lines()
    pdf.add_footer_totals(data)
    return bytes(pdf.output())


# ==========================================
# 2. APP STATE & DB CONNECTION
# ==========================================
if 'pending_items' not in st.session_state: st.session_state.pending_items = []
if 'next_invoice_no' not in st.session_state: st.session_state.next_invoice_no = 1
if 'view_invoice' not in st.session_state: st.session_state.view_invoice = None

# Explicitly initialize these so the input boxes are truly empty and ready
if 'part_qty' not in st.session_state: st.session_state.part_qty = None
if 'part_rate' not in st.session_state: st.session_state.part_rate = None

conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        df = conn.read(ttl=0)
        if 'Invoice_No' in df.columns:
            df['Invoice_No'] = pd.to_numeric(df['Invoice_No'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame()

df_db = load_db()

if not df_db.empty and 'Invoice_No' in df_db.columns:
    last_invoice = df_db['Invoice_No'].max()
    st.session_state.next_invoice_no = int(last_invoice) + 1 if pd.notna(last_invoice) else 1

def add_part_callback():
    desc = st.session_state.part_desc.upper() if st.session_state.part_desc else ""
    qty = st.session_state.part_qty if st.session_state.part_qty is not None else 1
    rate = st.session_state.part_rate if st.session_state.part_rate is not None else 0.0
    
    if desc:
        st.session_state.pending_items.append({
            "Description": desc, "Qty": qty, "Rate": rate, "Amount": qty * rate
        })
        st.session_state.part_desc = ""
        st.session_state.part_qty = None
        st.session_state.part_rate = None

# ==========================================
# 3. HELPER FUNCTIONS FOR UI
# ==========================================
def display_interactive_rows(df, prefix=""):
    h1, h2, h3, h4, h5 = st.columns([1, 2, 3, 2, 3])
    h1.markdown("**Inv No**")
    h2.markdown("**Date**")
    h3.markdown("**Customer**")
    h4.markdown("**Net Total**")
    h5.markdown("**Actions**")
    st.divider()

    for idx, row in df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([1, 2, 3, 2, 3])
        c1.write(str(row['Invoice_No']))
        c2.write(str(row['Invoice_Date']))
        c3.write(str(row['Customer_Name']))
        c4.write(f"₹{float(row['Net_Total']):.2f}")
        
        with c5:
            b_col1, b_col2 = st.columns(2)
            # FIX: Added 'idx' to the key to prevent Duplicate ID errors
            if b_col1.button("👁️ Preview", key=f"p_{prefix}_{idx}_{row['Invoice_No']}"):
                st.session_state.view_invoice = row.to_dict()
                st.rerun() # Force rerun immediately to trigger full-screen preview
                
            pdf_bytes = generate_pdf(row.to_dict())
            b_col2.download_button("📥 PDF", data=pdf_bytes, file_name=f"Invoice_{row['Invoice_No']}.pdf", mime="application/pdf", key=f"d_{prefix}_{idx}_{row['Invoice_No']}")

# ==========================================
# 4. MAIN UI ROUTING
# ==========================================

# If an invoice is selected for preview, take over the screen completely
if st.session_state.view_invoice:
    data = st.session_state.view_invoice
    
    st.markdown(f"## 📋 Preview: Invoice #{data.get('Invoice_No')}")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**Customer:** {data.get('Customer_Name')}<br>**Contact:** {data.get('Contact_No')}", unsafe_allow_html=True)
    col2.markdown(f"**Vehicle No:** {data.get('Vehicle_No')}<br>**Total KMs:** {data.get('Total_KMs')}", unsafe_allow_html=True)
    col3.markdown(f"**Date:** {data.get('Invoice_Date')}<br>**Mechanic:** {data.get('Mechanic_Names')}", unsafe_allow_html=True)
    
    st.write("")
    items = json.loads(data.get('Items_JSON', '[]'))
    if items:
        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
        
    st.info(f"**GR Total:** ₹{float(data.get('GR_Total', 0)):.2f} &nbsp;&nbsp;|&nbsp;&nbsp; **Labour Charges:** ₹{float(data.get('Labour_Charges', 0)):.2f} &nbsp;&nbsp;|&nbsp;&nbsp; **Net Total:** ₹{float(data.get('Net_Total', 0)):.2f} &nbsp;&nbsp;|&nbsp;&nbsp; **Received:** ₹{float(data.get('Received_Amt', 0)):.2f}")
    
    st.write("")
    action_col1, action_col2, action_col3 = st.columns([1,1,2])
    
    if action_col1.button("❌ Close Preview", use_container_width=True):
        st.session_state.view_invoice = None
        st.rerun()
        
    pdf_bytes = generate_pdf(data)
    action_col2.download_button("📥 Download Receipt (PDF)", data=pdf_bytes, file_name=f"Invoice_{data['Invoice_No']}.pdf", mime="application/pdf", type="primary", use_container_width=True)

# Otherwise, show the normal Tabbed Interface
else:
    tab_dash, tab_create, tab_search = st.tabs(["📊 Main Dashboard", "➕ Create Invoice", "🔍 Search Invoices"])

    # ------------------------------------------
    # TAB 1: MAIN DASHBOARD
    # ------------------------------------------
    with tab_dash:
        st.subheader("Last 10 Invoices Generated")
        if not df_db.empty:
            recent_df = df_db.sort_values(by="Invoice_No", ascending=False).head(10)
            display_interactive_rows(recent_df, prefix="dash")
        else:
            st.info("No invoices found in database.")

    # ------------------------------------------
    # TAB 2: CREATE NEW INVOICE
    # ------------------------------------------
    with tab_create:
        st.subheader("1. Invoice Details")
        col1, col2, col3 = st.columns([1, 1, 2])
        inv_date = col1.date_input("Date", date.today(), key="c_date")
        st.markdown(f"**Invoice No:** {st.session_state.next_invoice_no}")
        
        col4, col5, col6, col7 = st.columns(4)
        raw_cust = col4.text_input("Customer Name", placeholder="Enter Name")
        cust_name = raw_cust.upper()
        
        raw_contact = col5.text_input("Contact No", placeholder="e.g. 9876543210", max_chars=10)
        cust_contact = re.sub(r'\D', '', raw_contact) 
        
        if raw_contact and raw_contact != cust_contact:
            st.warning("Numbers only! Letters have been removed.")
        elif cust_contact and len(cust_contact) < 10:
            st.warning("⚠️ Contact number must be exactly 10 digits.")

        veh_no = col6.text_input("Vehicle No", placeholder="e.g. MH05CR8172").upper()
        tot_kms = col7.text_input("Total KMs", placeholder="e.g. 8500").upper()
        mechanic_names = st.text_input("Mechanic Name(s)", placeholder="Enter mechanics").upper()

        st.divider()

        # --- ADD PARTS ---
        st.subheader("2. Add Parts")
        p_col1, p_col2, p_col3, p_col4 = st.columns([3, 1, 1, 1])
        p_col1.text_input("Description", key="part_desc", placeholder="Enter Part Name")
        
        p_col2.number_input("Qty", min_value=1, step=1, key="part_qty", placeholder="1")
        p_col3.number_input("Rate (₹)", min_value=0.0, step=1.0, key="part_rate", placeholder="0.0")
        
        p_col4.write("")
        p_col4.button("➕ Add Part", on_click=add_part_callback, use_container_width=True)

        # --- PENDING LIST & TOTALS ---
        if len(st.session_state.pending_items) > 0:
            st.dataframe(pd.DataFrame(st.session_state.pending_items), use_container_width=True, hide_index=True)
            
            fin_col1, fin_col2 = st.columns(2)
            labour_chrgs = fin_col1.number_input("Labour Charges (₹)", min_value=0.0, step=10.0, value=None, placeholder="0.0")
            
            gr_total = sum(item['Amount'] for item in st.session_state.pending_items)
            safe_labour = labour_chrgs if labour_chrgs is not None else 0.0
            net_total = gr_total + safe_labour
            
            received_amt = fin_col2.number_input("Received Amount (₹)", step=10.0, value=float(net_total))
            st.write(f"**GR Total:** ₹{gr_total:.2f} | **Net Total:** ₹{net_total:.2f}")

            # --- SAVE ACTION ---
            if st.button("💾 Save & Generate Invoice", type="primary", use_container_width=True):
                if not cust_name:
                    st.error("Customer Name is required.")
                elif cust_contact and len(cust_contact) < 10:
                    st.error("Please enter a valid 10-digit contact number before saving.")
                else:
                    new_row = {
                        "Invoice_No": st.session_state.next_invoice_no,
                        "Invoice_Date": str(inv_date),
                        "Customer_Name": cust_name,
                        "Contact_No": cust_contact,
                        "Vehicle_No": veh_no,
                        "Total_KMs": tot_kms,
                        "Mechanic_Names": mechanic_names,
                        "Items_JSON": json.dumps(st.session_state.pending_items),
                        "Total_Items_Count": len(st.session_state.pending_items),
                        "GR_Total": gr_total,
                        "Labour_Charges": safe_labour,
                        "Net_Total": net_total,
                        "Received_Amt": received_amt if received_amt is not None else net_total
                    }
                    
                    new_df = pd.DataFrame([new_row])
                    updated_df = pd.concat([df_db, new_df], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_df)
                    
                    st.session_state.view_invoice = new_row
                    st.success(f"Invoice {st.session_state.next_invoice_no} Saved successfully!")
                    
                    st.session_state.next_invoice_no += 1
                    st.session_state.pending_items = []
                    st.rerun()

    # ------------------------------------------
    # TAB 3: SEARCH INVOICES
    # ------------------------------------------
    with tab_search:
        st.subheader("🔍 Search Database")
        search_query = st.text_input("Search by Invoice No, Vehicle No, Name, or Contact").upper()
        
        if search_query and not df_db.empty:
            mask = (
                df_db['Invoice_No'].astype(str).str.contains(search_query) |
                df_db['Customer_Name'].astype(str).str.contains(search_query) |
                df_db['Vehicle_No'].astype(str).str.contains(search_query) |
                df_db['Contact_No'].astype(str).str.contains(search_query)
            )
            results = df_db[mask]
            
            if not results.empty:
                display_interactive_rows(results, prefix="search")
            else:
                st.warning("No records found matching your search.")
