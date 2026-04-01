import streamlit as st
import pandas as pd
import json
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
from datetime import date

# ==========================================
# 1. PDF GENERATOR CLASS
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
        self.cell(35, 6, f"{totals_dict.get('GR_Total', 0):.2f}", align="R")
        self.line(120, 246, 200, 246)

        self.set_xy(120, 246)
        self.cell(45, 6, "LABOUR CHRGS", align="R")
        self.cell(35, 6, f"{totals_dict.get('Labour_Charges', 0):.2f}", align="R")
        self.line(120, 252, 200, 252)

        self.set_xy(120, 252)
        self.set_font("helvetica", "B", 9)
        self.cell(45, 6, "NET TOTAL", align="R")
        self.cell(35, 6, f"{totals_dict.get('Net_Total', 0):.2f}", align="R")
        self.line(120, 258, 200, 258)

        self.set_xy(120, 258)
        self.set_font("helvetica", "", 9)
        self.cell(45, 6, "Received Amt", align="R")
        self.cell(35, 6, f"{totals_dict.get('Received_Amt', 0):.2f}", align="R")
        
        self.set_xy(10, 266)
        self.cell(0, 5, f"PAGE NO. : {self.page_no()} (1)", align="L")

def generate_pdf(customer_info, items_list, totals_info):
    pdf = ReceiptPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.add_customer_details(customer_info)
    pdf.add_table_headers()
    
    pdf.set_font("helvetica", "", 9)
    y_pos = 64
    for index, item in enumerate(items_list):
        pdf.set_xy(10, y_pos)
        pdf.cell(10, 5, str(index + 1), align="C") 
        pdf.cell(100, 5, str(item['Description']), align="L")
        pdf.cell(20, 5, str(item['Qty']), align="C")
        pdf.cell(25, 5, f"{item['MRP']:.2f}", align="C")
        pdf.cell(35, 5, f"{item['Amount']:.2f}", align="R")
        y_pos += 6
        
    pdf.draw_grid_lines()
    pdf.add_footer_totals(totals_info)
    return bytes(pdf.output())


# ==========================================
# 2. STREAMLIT APP & GOOGLE SHEETS LOGIC
# ==========================================
st.set_page_config(page_title="Receipt Generator", layout="wide")

# Initialize Session State for Pending Items
if 'pending_items' not in st.session_state:
    st.session_state.pending_items = []

# Connect to Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_db = conn.read()
    
    # Auto-Incremental Invoice Logic
    if not df_db.empty and 'Invoice_No' in df_db.columns:
        last_invoice = pd.to_numeric(df_db['Invoice_No'], errors='coerce').max()
        next_invoice_no = int(last_invoice) + 1 if pd.notna(last_invoice) else 1
    else:
        next_invoice_no = 1
except Exception as e:
    st.warning("Google Sheets not connected. Run locally for now.")
    next_invoice_no = 1
    df_db = pd.DataFrame()

st.title("➕ Enter New Invoice")

# --- UI SECTION 1: INVOICE DETAILS ---
st.subheader("1. Invoice Details")
col1, col2, col3, col4 = st.columns(4)
inv_date = col1.date_input("Date", date.today())
# Auto-generated and disabled to prevent manual errors
inv_no = col2.text_input("Invoice No (Auto-Generated)", value=str(next_invoice_no), disabled=True)
cgst = col3.number_input("CGST (%)", value=9.0, step=1.0)
sgst = col4.number_input("SGST (%)", value=9.0, step=1.0)

col5, col6, col7, col8 = st.columns(4)
cust_name = col5.text_input("Customer Name")
cust_contact = col6.text_input("Contact No")
veh_no = col7.text_input("Vehicle No")
tot_kms = col8.text_input("Total KMs")

mechanic_names = st.text_input("Mechanic Name(s) (Comma separated if multiple)")

st.divider()

# --- UI SECTION 2: ADD PARTS ---
st.subheader("2. Add Parts")
p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns([1, 2, 1, 1, 1])
part_no = p_col1.text_input("Part No (Optional)")
desc = p_col2.text_input("Description")
qty = p_col3.number_input("Qty", min_value=1, step=1)
mrp = p_col4.number_input("MRP (₹)", min_value=0.0, step=1.0)
discount = p_col5.number_input("Discount (%)", min_value=0.0, step=1.0)

if st.button("Add Part to List"):
    if desc.strip() == "":
        st.error("Description cannot be empty!")
    else:
        # Calculate Item Total
        discount_amt = mrp * (discount / 100)
        rate_after_discount = mrp - discount_amt
        amount = qty * rate_after_discount
        
        st.session_state.pending_items.append({
            "Part_No": part_no,
            "Description": desc,
            "Qty": qty,
            "MRP": mrp,
            "Discount": discount,
            "CGST": cgst,
            "SGST": sgst,
            "Amount": amount
        })
        st.success(f"Added {desc} to list.")
        st.rerun()

st.divider()

# --- UI SECTION 3: PENDING BILL ITEMS ---
st.subheader("3. Pending Bill Items")

if len(st.session_state.pending_items) > 0:
    df_pending = pd.DataFrame(st.session_state.pending_items)
    st.dataframe(df_pending, use_container_width=True)
    
    # Financial Inputs
    fin_col1, fin_col2 = st.columns(2)
    labour_chrgs = fin_col1.number_input("Labour Charges (₹)", min_value=0.0, step=10.0)
    
    # Calculations
    gr_total = df_pending['Amount'].sum()
    net_total = gr_total + labour_chrgs
    
    received_amt = fin_col2.number_input("Received Amount (₹)", value=float(net_total), step=10.0)
    
    st.write(f"**GR Total:** ₹{gr_total:.2f} | **Net Total:** ₹{net_total:.2f}")

    # --- UI SECTION 4: SAVE TO DATABASE & PDF ---
    col_save, col_clear, col_pdf = st.columns([2, 2, 4])
    
    if col_save.button("💾 Save Invoice to Database"):
        if not cust_name:
            st.error("Customer Name is required.")
        else:
            # Prepare data dictionary for the row
            new_row = {
                "Invoice_No": int(inv_no),
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
            
            # Append and Save to Google Sheets
            try:
                new_df = pd.DataFrame([new_row])
                updated_df = pd.concat([df_db, new_df], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.success(f"Invoice {inv_no} saved successfully!")
                
                # Flag to show PDF button
                st.session_state['saved_invoice_data'] = new_row
            except Exception as e:
                st.error(f"Failed to save to database. Error: {e}")

    if col_clear.button("❌ Clear Pending List"):
        st.session_state.pending_items = []
        if 'saved_invoice_data' in st.session_state:
            del st.session_state['saved_invoice_data']
        st.rerun()

    # If successfully saved, show the download button
    if 'saved_invoice_data' in st.session_state:
        data = st.session_state['saved_invoice_data']
        pdf_bytes = generate_pdf(
            customer_info=data, 
            items_list=json.loads(data['Items_JSON']), 
            totals_info=data
        )
        
        col_pdf.download_button(
            label="📥 Download A4 Receipt",
            data=pdf_bytes,
            file_name=f"receipt_{data['Invoice_No']}.pdf",
            mime="application/pdf",
            type="primary"
        )
else:
    st.info("No items added yet. Add parts above.")