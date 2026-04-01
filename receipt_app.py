import streamlit as st
import pandas as pd
import json
import base64
import re
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
from datetime import date

st.set_page_config(page_title="Shree Gurudev Auto", layout="wide")

# ==========================================
# 1. PDF GENERATOR CLASS (Unchanged & Cleaned)
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
        self.cell(0, 5, f"PAGE NO. : {self.page_no()} (1)", align="L")

def generate_pdf(data):
    pdf = ReceiptPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.add_customer_details(data)
    pdf.add_table_headers()
    
    pdf.set_font("helvetica", "", 9)
    y_pos = 64
    items_list = json.loads(data['Items_JSON'])
    for index, item in enumerate(items_list):
        pdf.set_xy(10, y_pos)
        pdf.cell(10, 5, str(index + 1), align="C") 
        pdf.cell(100, 5, str(item['Description']), align="L")
        pdf.cell(20, 5, str(item['Qty']), align="C")
        pdf.cell(25, 5, f"{float(item['Rate']):.2f}", align="C")
        pdf.cell(35, 5, f"{float(item['Amount']):.2f}", align="R")
        y_pos += 6
        
    pdf.draw_grid_lines()
    pdf.add_footer_totals(data)
    return bytes(pdf.output())

def show_pdf_preview(pdf_bytes):
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


# ==========================================
# 2. APP STATE & GOOGLE SHEETS DB
# ==========================================
# Initialize Session State
if 'pending_items' not in st.session_state: st.session_state.pending_items = []
if 'preview_pdf' not in st.session_state: st.session_state.preview_pdf = None
if 'next_invoice_no' not in st.session_state: st.session_state.next_invoice_no = 1

# Database Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        # ttl=0 forces it to fetch live data so increments work
        df = conn.read(ttl=0)
        return df
    except Exception:
        return pd.DataFrame()

df_db = load_db()

# Calculate auto-incremental invoice number safely
if not df_db.empty and 'Invoice_No' in df_db.columns:
    last_invoice = pd.to_numeric(df_db['Invoice_No'], errors='coerce').max()
    st.session_state.next_invoice_no = int(last_invoice) + 1 if pd.notna(last_invoice) else 1

# Callbacks to clear forms automatically
def add_part_callback():
    desc = st.session_state.part_desc.upper() # UPPERCASE FORCE
    qty = st.session_state.part_qty
    rate = st.session_state.part_rate
    if desc:
        st.session_state.pending_items.append({
            "Description": desc, "Qty": qty, "Rate": rate, "Amount": qty * rate
        })
        # Reset the input fields automatically
        st.session_state.part_desc = ""
        st.session_state.part_qty = 1
        st.session_state.part_rate = 0.0

# ==========================================
# 3. TABS UI LAYOUT
# ==========================================
tab_dash, tab_create, tab_search = st.tabs(["📊 Main Dashboard", "➕ Create Invoice", "🔍 Search & Update"])

# ------------------------------------------
# TAB 1: MAIN DASHBOARD
# ------------------------------------------
with tab_dash:
    st.subheader("Last 10 Invoices Generated")
    if not df_db.empty:
        # Sort descending and take top 10
        recent_df = df_db.sort_values(by="Invoice_No", ascending=False).head(10)
        # Display clean columns
        display_df = recent_df[['Invoice_No', 'Invoice_Date', 'Customer_Name', 'Vehicle_No', 'Net_Total', 'Received_Amt']]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
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
    # Using placeholders so text clears when clicked. Forcing uppercase on output.
    raw_cust = col4.text_input("Customer Name", placeholder="Enter Name")
    cust_name = raw_cust.upper()
    
    raw_contact = col5.text_input("Contact No", placeholder="e.g. 9876543210")
    # ENFORCE NUMBERS ONLY using regex
    cust_contact = re.sub(r'\D', '', raw_contact) 
    if raw_contact != cust_contact:
        st.warning("Numbers only! Letters have been removed.")

    veh_no = col6.text_input("Vehicle No", placeholder="e.g. MH05CR8172").upper()
    tot_kms = col7.text_input("Total KMs", placeholder="e.g. 8500").upper()
    
    mechanic_names = st.text_input("Mechanic Name(s)", placeholder="Enter mechanics").upper()

    st.divider()

    # --- ADD PARTS ---
    st.subheader("2. Add Parts (Auto-Resets)")
    p_col1, p_col2, p_col3, p_col4 = st.columns([3, 1, 1, 1])
    p_col1.text_input("Description", key="part_desc", placeholder="Enter Part Name")
    p_col2.number_input("Qty", min_value=1, step=1, key="part_qty")
    p_col3.number_input("Rate (₹)", min_value=0.0, step=1.0, key="part_rate")
    p_col4.button("➕ Add Part", on_click=add_part_callback, use_container_width=True)

    # --- PENDING LIST & TOTALS ---
    if len(st.session_state.pending_items) > 0:
        st.dataframe(pd.DataFrame(st.session_state.pending_items), use_container_width=True)
        
        fin_col1, fin_col2 = st.columns(2)
        labour_chrgs = fin_col1.number_input("Labour Charges (₹)", min_value=0.0, step=10.0)
        
        gr_total = sum(item['Amount'] for item in st.session_state.pending_items)
        net_total = gr_total + labour_chrgs
        received_amt = fin_col2.number_input("Received Amount (₹)", value=float(net_total), step=10.0)
        
        st.write(f"**GR Total:** ₹{gr_total:.2f} | **Net Total:** ₹{net_total:.2f}")

        # --- SAVE ACTION ---
        if st.button("💾 Save & Generate Invoice", type="primary", use_container_width=True):
            if not cust_name:
                st.error("Customer Name is required.")
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
                    "Labour_Charges": labour_chrgs,
                    "Net_Total": net_total,
                    "Received_Amt": received_amt
                }
                
                # Update Database
                new_df = pd.DataFrame([new_row])
                updated_df = pd.concat([df_db, new_df], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.success(f"Invoice {st.session_state.next_invoice_no} Saved! DB Incremented.")
                
                # Generate PDF for Preview
                pdf_bytes = generate_pdf(new_row)
                st.session_state.preview_pdf = pdf_bytes
                
                # Reset Form for Next Invoice safely
                st.session_state.next_invoice_no += 1
                st.session_state.pending_items = []
                st.rerun()

    # --- PDF PREVIEW ---
    if st.session_state.preview_pdf:
        st.divider()
        st.subheader("Invoice Preview")
        show_pdf_preview(st.session_state.preview_pdf)
        st.download_button(
            label="📥 Download This Receipt",
            data=st.session_state.preview_pdf,
            file_name="receipt_latest.pdf",
            mime="application/pdf"
        )


# ------------------------------------------
# TAB 3: SEARCH & UPDATE
# ------------------------------------------
with tab_search:
    st.subheader("Search Database")
    search_query = st.text_input("Search by Invoice No, Vehicle No, Name, or Contact").upper()
    
    if search_query and not df_db.empty:
        # Filter the dataframe across multiple columns using String matching
        mask = (
            df_db['Invoice_No'].astype(str).str.contains(search_query) |
            df_db['Customer_Name'].astype(str).str.contains(search_query) |
            df_db['Vehicle_No'].astype(str).str.contains(search_query) |
            df_db['Contact_No'].astype(str).str.contains(search_query)
        )
        results = df_db[mask]
        
        if not results.empty:
            st.dataframe(results[['Invoice_No', 'Invoice_Date', 'Customer_Name', 'Vehicle_No', 'Net_Total']], hide_index=True)
            
            # Select an invoice to update
            selected_inv = st.selectbox("Select Invoice to Update/Print:", results['Invoice_No'].tolist())
            
            if selected_inv:
                # Get the specific row data
                row_data = results[results['Invoice_No'] == selected_inv].iloc[0].to_dict()
                
                st.markdown(f"### Editing Invoice: {selected_inv}")
                
                u_col1, u_col2 = st.columns(2)
                # Form pre-filled with existing data
                u_name = u_col1.text_input("Update Name", value=row_data['Customer_Name']).upper()
                u_contact = u_col2.text_input("Update Contact", value=str(row_data['Contact_No']))
                u_contact = re.sub(r'\D', '', u_contact) # Force numbers
                u_veh = u_col1.text_input("Update Vehicle No", value=str(row_data['Vehicle_No'])).upper()
                u_mech = u_col2.text_input("Update Mechanic", value=str(row_data['Mechanic_Names'])).upper()
                
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.button("💾 Update Record & Generate PDF", key="btn_update"):
                    # Update row in dataframe
                    idx = df_db.index[df_db['Invoice_No'] == selected_inv].tolist()[0]
                    df_db.at[idx, 'Customer_Name'] = u_name
                    df_db.at[idx, 'Contact_No'] = u_contact
                    df_db.at[idx, 'Vehicle_No'] = u_veh
                    df_db.at[idx, 'Mechanic_Names'] = u_mech
                    
                    conn.update(worksheet="Sheet1", data=df_db)
                    st.success("Record Updated Successfully!")
                    
                    # Generate fresh PDF with updated data
                    updated_row_data = df_db.iloc[idx].to_dict()
                    up_pdf_bytes = generate_pdf(updated_row_data)
                    
                    st.download_button(
                        label="📥 Download Updated Receipt",
                        data=up_pdf_bytes,
                        file_name=f"receipt_{selected_inv}_updated.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
        else:
            st.warning("No records found matching your search.")
