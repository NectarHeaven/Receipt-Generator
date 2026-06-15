import streamlit as st
import pandas as pd
import json
from datetime import datetime
import streamlit.components.v1 as components

# --- PAGE CONFIG ---
st.set_page_config(page_title="Garage Invoice System", layout="wide")

# --- SIMULATED DATABASE / GOOGLE SHEET FUNCTIONALITY ---
# Replace this dictionary initialization with your actual gspread/Google Sheet connection logic
if 'invoice_db' not in st.session_state:
    st.session_state.invoice_db = pd.DataFrame(columns=[
        "Invoice_No", "Invoice_Date", "Customer_Name", "Contact_No", "Vehicle_No", 
        "Vehicle_Name", "Total_KMs", "Mechanic_Names", "Items_JSON", 
        "Total_Items_Count", "GR_Total", "Labour_Charges", "Discount", "Net_Total"
    ])

if 'current_items' not in st.session_state:
    st.session_state.current_items = []

# Mock master parts list for the autocomplete dropdown
MASTER_PARTS = ["", "SERVICE OF VEHICLE WITH WASHING", "ENGINE OIL", "GEAR OIL", "SHOCAB BUSH", "RR BR SHOES", "YOLK PATTI"]

# --- HELPER FUNCTIONS ---
def add_item_to_list(desc, qty, mrp, disc_percent):
    # Calculate row total based on MRP and individual item discount
    raw_amount = qty * mrp
    discount_amount = raw_amount * (disc_percent / 100.0)
    final_amount = raw_amount - discount_amount
    
    item = {
        "Description": desc.upper().strip(),
        "Qty": int(qty),
        "MRP": float(mrp),
        "Discount_Percent": float(disc_percent),
        "Amount": float(final_amount)
    }
    st.session_state.current_items.append(item)

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Main Dashboard", "➕ Create Invoice", "🔍 Search Invoices"])

# ==============================================================================
# TAB 2: CREATE INVOICE (With Fixed Layout and Polished PDF/HTML Template)
# ==============================================================================
with tab2:
    st.markdown("## 📄 Create New Invoice")
    
    # 1. Customer & Vehicle Details Grid
    with st.expander("1. Customer & Vehicle Information", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            inv_no = st.text_input("Invoice No", value="103")
            cust_name = st.text_input("Customer Name", value="MR. NITIN K")
        with c2:
            inv_date = st.date_input("Invoice Date", value=datetime.today())
            contact_no = st.text_input("Contact No", value="9730813966")
        with c3:
            veh_no = st.text_input("Vehicle No", value="MH05FF4768")
            veh_name = st.text_input("Vehicle Name", value="ACTIVA")
            
        c4, c5 = st.columns(2)
        with c4:
            total_kms = st.number_input("Total KMs", min_value=0, value=66664, step=1)
        with c5:
            mechanic_name = st.text_input("Mechanic Name", value="ASDFASDFAS")

    st.markdown("---")

    # 2. Add Parts Form (FIXED: Clean, Horizontal Single-Line Row Grid Layout)
    st.markdown("### 2. Add Parts")
    
    col1, col2, col3, col4, col5 = st.columns([4, 3, 1, 2, 2])
    
    with col1:
        selected_part = st.selectbox(
            "Select Existing Part", 
            options=MASTER_PARTS,
            key="part_select"
        )
    with col2:
        custom_part = st.text_input(
            "Or Type New Part Name", 
            placeholder="Type manually if not in list...",
            key="part_custom"
        )
    with col3:
        qty = st.number_input("Qty", min_value=1, value=1, step=1, key="part_qty")
    with col4:
        mrp = st.number_input("MRP / Rate (₹)", min_value=0.0, value=0.0, step=10.0, key="part_mrp")
    with col5:
        disc_per = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="part_disc")
        
    # Single Wide button row right underneath the inputs for clear submission
    if st.button("➕ Add Item to Invoice", use_container_width=True):
        final_description = custom_part if custom_part.strip() != "" else selected_part
        if final_description.strip() == "":
            st.error("Please select or enter a valid item description.")
        elif mrp <= 0:
            st.error("Please enter a valid rate/MRP greater than 0.")
        else:
            add_item_to_list(final_description, qty, mrp, disc_per)
            st.toast(f"Added {final_description} successfully!")
            st.rerun()

    # Table displaying items currently added to the invoice basket
    if st.session_state.current_items:
        st.markdown("#### Current Invoice Items")
        df_items = pd.DataFrame(st.session_state.current_items)
        st.dataframe(df_items, use_container_width=True)
        if st.button("🗑️ Clear All Items"):
            st.session_state.current_items = []
            st.rerun()

    st.markdown("---")

    # 3. Totals & Calculations
    st.markdown("### 3. Final Settlement")
    
    # Calculate parts subtotal dynamically
    gr_total = sum(item["Amount"] for item in st.session_state.current_items)
    
    cx, cy = st.columns(2)
    with cx:
        labour_charges = st.number_input("Labour Charges (₹)", min_value=0.0, value=0.0, step=10.0)
    with cy:
        # Legacy bottom global discount is locked to 0 since item-wise discount is calculated inside items row amounts
        st.text_input("Global Bottom Discount (₹)", value="0.00 (Disabled - Item-wise active)", disabled=True)
        
    net_total = gr_total + labour_charges
    
    st.metric(label="Final Net Total Payable", value=f"₹ {net_total:,.2f}")

    # ==============================================================================
    # PRINTABLE INVOICE TEMPLATE GENERATION (FIXED: Clean Borders, Compact Totals)
    # ==============================================================================
    if st.session_state.current_items:
        # Generate dynamic clean HTML table records rows
        table_rows_html = ""
        for idx, item in enumerate(st.session_state.current_items, start=1):
            table_rows_html += f"""
            <tr>
                <td style='text-align: center;'>{idx}</td>
                <td>{item['Description']}</td>
                <td style='text-align: center;'>{item['Qty']}</td>
                <td style='text-align: right;'>{item['MRP']:.2f}</td>
                <td style='text-align: center;'>{item['Discount_Percent']}%</td>
                <td style='text-align: right;'>{item['Amount']:.2f}</td>
            </tr>
            """

        # Beautiful Print Invoice Component Structure
        invoice_template_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            .invoice-box {{
                max-width: 850px;
                margin: auto;
                padding: 25px;
                border: 1px solid #dee2e6;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.05);
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #333;
                background: #fff;
            }}
            .header-table {{
                width: 100%;
                margin-bottom: 20px;
                border-bottom: 2px solid #333;
                padding-bottom: 10px;
            }}
            .title-header {{
                font-size: 26px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            .meta-table {{
                width: 100%;
                font-size: 13px;
                margin-bottom: 20px;
            }}
            .meta-table td {{
                padding: 4px 0;
            }}
            .items-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
                margin-top: 10px;
            }}
            .items-table th {{
                background-color: #f8f9fa;
                color: #495057;
                font-weight: 600;
                padding: 10px;
                border-top: 1px solid #dee2e6;
                border-bottom: 2px solid #dee2e6;
            }}
            .items-table td {{
                padding: 10px;
                border-bottom: 1px solid #efefef;
            }}
            .summary-container {{
                width: 100%;
                margin-top: 20px;
                display: inline-block;
            }}
            .thanks-box {{
                float: left;
                width: 55%;
                margin-top: 15px;
            }}
            .mechanic-text {{
                font-size: 13px;
                font-weight: bold;
                color: #495057;
                text-transform: uppercase;
            }}
            .thanks-text {{
                margin-top: 15px;
                font-style: italic;
                color: #6c757d;
                font-size: 14px;
                letter-spacing: 1px;
            }}
            .totals-table {{
                float: right;
                width: 40%;
                border-top: 2px solid #333;
                font-size: 14px;
            }}
            .totals-table td {{
                padding: 7px 8px;
                border: none !important;
            }}
            .text-right {{
                text-align: right;
            }}
            .net-total-row {{
                font-size: 16px;
                font-weight: bold;
                border-top: 1px solid #333 !important;
                border-bottom: 2px double #333 !important;
                background-color: #f8f9fa;
            }}
            @media print {{
                .invoice-box {{ border: none; box-shadow: none; padding: 0; }}
                body {{ background: #fff; }}
            }}
        </style>
        </head>
        <body>
        <div class="invoice-box">
            <table class="header-table">
                <tr>
                    <td class="title-header">INVOICE / BILL</td>
                    <td style="text-align: right; font-size: 14px; color:#6c757d;">Original Copy</td>
                </tr>
            </table>

            <table class="meta-table">
                <tr>
                    <td style="width:15%;"><strong>Invoice No:</strong></td>
                    <td style="width:35%;">{inv_no}</td>
                    <td style="width:18%;"><strong>Vehicle No:</strong></td>
                    <td style="width:32%;">{veh_no.upper()}</td>
                </tr>
                <tr>
                    <td><strong>Date:</strong></td>
                    <td>{inv_date.strftime('%d/%m/%Y')}</td>
                    <td><strong>Vehicle Model:</strong></td>
                    <td>{veh_name.upper()}</td>
                </tr>
                <tr>
                    <td><strong>Customer:</strong></td>
                    <td>{cust_name.upper()}</td>
                    <td><strong>Total KMs:</strong></td>
                    <td>{total_kms:,} kms</td>
                </tr>
                <tr>
                    <td><strong>Contact:</strong></td>
                    <td>{contact_no}</td>
                    <td></td>
                    <td></td>
                </tr>
            </table>

            <table class="items-table">
                <thead>
                    <tr>
                        <th style="width: 8%; text-align: center;">SR.</th>
                        <th style="text-align: left;">DESCRIPTION</th>
                        <th style="width: 10%; text-align: center;">QTY</th>
                        <th style="width: 15%; text-align: right;">RATE (₹)</th>
                        <th style="width: 12%; text-align: center;">DISC</th>
                        <th style="width: 18%; text-align: right;">AMOUNT (₹)</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>

            <div class="summary-container">
                <div class="thanks-box">
                    <div class="mechanic-text">MECHANIC: {mechanic_name.upper()}</div>
                    <div class="thanks-text">*** THANK YOU ***</div>
                    <div style="margin-top: 25px; font-size: 11px; color: #aaa;">Page 1 of 1</div>
                </div>
                
                <table class="totals-table">
                    <tr>
                        <td>TOTAL ITEMS: {len(st.session_state.current_items)}</td>
                        <td class="text-right">SUBTOTAL</td>
                        <td class="text-right">{gr_total:,.2f}</td>
                    </tr>
                    <tr>
                        <td></td>
                        <td class="text-right">LABOUR CHRGS</td>
                        <td class="text-right">{labour_charges:,.2f}</td>
                    </tr>
                    <tr class="net-total-row">
                        <td></td>
                        <td class="text-right">NET TOTAL</td>
                        <td class="text-right">₹ {net_total:,.2f}</td>
                    </tr>
                </table>
            </div>
        </div>
        </body>
        </html>
        """
        
        st.markdown("### 🖨️ Live Print Preview")
        # Renders the exact print layout dynamically safely inside the web browser dashboard
        components.html(invoice_template_html, height=520, scrolling=True)
        
        if st.button("🚀 Save Invoice Data to Database & Print"):
            # Construct the exact data dictionary row format matching your Google Sheet
            new_row = {
                "Invoice_No": inv_no,
                "Invoice_Date": inv_date.strftime('%Y-%m-%d'),
                "Customer_Name": cust_name.upper(),
                "Contact_No": contact_no,
                "Vehicle_No": veh_no.upper(),
                "Vehicle_Name": veh_name.upper(),
                "Total_KMs": total_kms,
                "Mechanic_Names": mechanic_name.upper(),
                "Items_JSON": json.dumps(st.session_state.current_items), # Packed inside Items_JSON column
                "Total_Items_Count": len(st.session_state.current_items),
                "GR_Total": gr_total,
                "Labour_Charges": labour_charges,
                "Discount": 0.0, # Kept safe for backward data consistency
                "Net_Total": net_total
            }
            
            # Save data to session state dataframe simulation
            st.session_state.invoice_db = pd.concat([st.session_state.invoice_db, pd.DataFrame([new_row])], ignore_index=True)
            st.success("Invoice successfully written to Database / Google Sheet storage row structure!")
            st.session_state.current_items = [] # Reset basket buffer

# --- TAB 1 & 3 PLACEHOLDERS FOR RUNNING COMPLETENESS ---
with tab1:
    st.markdown("## 📊 Workshop Metrics Overview")
    st.dataframe(st.session_state.invoice_db, use_container_width=True)

with tab3:
    st.markdown("## 🔍 Quick Search Engine")
    st.text_input("Search Vehicle Number Plate", value="MH05")
