import streamlit as st
import pandas as pd
import pdfplumber
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import datetime
import plotly.express as px
import nltk  # <-- IMPORT NLTK
from categorizer import categorize_expense  # <-- IMPORT NEW FILE

# --- NLTK Data Downloads ---
# This checks if the data is present and downloads it if not.
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    st.info("Downloading NLTK data (punkt)...")
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    st.info("Downloading NLTK data (stopwords)...")
    nltk.download('stopwords')
# --- End NLTK Downloads ---


# --- 1. SET UP PAGE ---
st.set_page_config(page_title="Buddy With Brain", page_icon="🧠", layout="wide")

# --- 2. LOAD AUTHENTICATION CONFIG ---
try:
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
except FileNotFoundError:
    st.error("Error: 'config.yaml' file not found. Please make sure it's in the same directory.")
    st.stop()
except Exception as e:
    st.error(f"Error loading config.yaml: {e}")
    st.stop()

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- 3. CHECK LOGIN STATUS ---
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None

# --- 4. SHOW THE MAIN APP (IF LOGGED IN) ---
if st.session_state["authentication_status"]:
    # --- This is the "Logged In" view ---
    st.sidebar.write(f'Welcome *{st.session_state["name"]}*')
    authenticator.logout('Logout', 'sidebar')

    # --- NEW: Helper function for currency formatting ---
    def format_indian_currency(amount):
        """Formats a number into Indian Lakhs/Crores style."""
        if not isinstance(amount, (int, float)):
            return "₹0.00"

        val_str = ""
        if amount < 0:
            val_str = "-"
            amount = abs(amount)

        if amount >= 1_00_00_000:
            val_str += f"₹{amount / 1_00_00_000:.2f} Cr"
        elif amount >= 1_00_000:
            val_str += f"₹{amount / 1_00_000:.2f} L"
        else:
             # Standard formatting for under 1 Lakh
             val_str += f"₹{amount:,.2f}"
        
        return val_str
    # --- End of helper function ---

    # --- Initialize session state for our data (ADDED 'category') ---
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame(columns=['date', 'description', 'amount', 'Income/Expense', 'category'])

    st.title("Buddy With Brain 🧠")
    st.header("My Personal Expense Analyzer")

    # --- Create two columns for input ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Upload a File")
        uploaded_file = st.file_uploader("Upload (CSV, Excel, PDF)", type=["csv", "xlsx", "pdf"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            try:
                df = None
                # --- Handle Excel and CSV ---
                if uploaded_file.name.endswith('xlsx'):
                    df = pd.read_excel(uploaded_file)
                elif uploaded_file.name.endswith('csv'):
                    df = pd.read_csv(uploaded_file)

                # --- If file was CSV or Excel, load it into session state ---
                if df is not None:
                    # --- CRITICAL DATA PREP ---
                    # Standardize the date column (convert to datetime)
                    # errors='coerce' will turn bad dates into 'NaT' (Not a Time)
                    # format='%d-%m-%Y %H:%M' is specific to your dataset.csv
                    df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y %H:%M', errors='coerce')
                    # Standardize amount column (convert to numeric)
                    df['amount'] = pd.to_numeric(df['amount'])
                    
                    # --- APPLY CATEGORIZATION ON UPLOAD ---
                    df['category'] = df.apply(lambda row: categorize_expense(row['description'], row['Income/Expense']), axis=1)
                    
                    st.session_state.df = df # Overwrite session df
                    st.success(f"File '{uploaded_file.name}' loaded successfully.")

                # --- Handle PDF ---
                elif uploaded_file.name.endswith('pdf'):
                    st.header("Extracted Text from PDF")
                    text = ""
                    with pdfplumber.open(uploaded_file) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                    st.text_area("PDF Content", text, height=300)
                    st.info("PDF text extracted. Analysis is only for CSV/Excel data.")
            
            except Exception as e:
                st.error(f"Error: Could not read the file. Details: {e}")

    with col2:
        st.subheader("Add a New Transaction")
        # Create a form for manual entry
        with st.form("manual_entry_form", clear_on_submit=True):
            entry_date = st.date_input("Date", datetime.date.today())
            entry_desc = st.text_input("Description")
            entry_type = st.selectbox("Type", ["Expense", "Income"])
            entry_amount = st.number_input("Amount (₹)", min_value=0.01, format="%.2f")
            
            submitted = st.form_submit_button("Add Transaction")

        if submitted:
            if not entry_desc:
                st.warning("Please enter a description.")
            else:
                # --- APPLY CATEGORIZATION ON MANUAL ENTRY ---
                entry_category = categorize_expense(entry_desc, entry_type)
                
                # Create a new DataFrame for the single entry
                new_entry = pd.DataFrame([{
                    "date": pd.to_datetime(entry_date), # Convert to datetime
                    "description": entry_desc,
                    "amount": entry_amount,
                    "Income/Expense": entry_type,
                    "category": entry_category # <-- ADDED CATEGORY
                }])
                
                # Add the new entry to our session state DataFrame
                st.session_state.df = pd.concat([st.session_state.df, new_entry], ignore_index=True)
                st.success("Transaction added!")

    # --- 5. NEW: ANALYSIS DASHBOARD ---
    
    # Run this part only if the session DataFrame is not empty
    if not st.session_state.df.empty:
        st.divider() # Add a visual separator
        st.header("Analysis Dashboard")

        # --- Data Prep for Dashboard ---
        # Make a copy to avoid changing the original data
        df_analysis = st.session_state.df.copy()

        df_analysis['date'] = pd.to_datetime(df_analysis['date'])
        df_analysis['amount'] = pd.to_numeric(df_analysis['amount'])
        
        # Create helper columns for filtering
        df_analysis['year'] = df_analysis['date'].dt.year
        df_analysis['month_year'] = df_analysis['date'].dt.strftime('%B %Y')
        
        # --- Filter Widgets ---
        st.subheader("Filter Your Data")
        filter_type = st.selectbox("Select Filter Type", ["Overall", "Yearly", "Monthly", "Date Range"])
        
        # Create columns for filters
        fcol1, fcol2 = st.columns(2)
        
        df_filtered = df_analysis.copy()
        
        if filter_type == "Yearly":
            years = sorted(df_analysis['year'].unique(), reverse=True)
            selected_year = fcol1.selectbox("Select Year", years)
            df_filtered = df_analysis[df_analysis['year'] == selected_year]
        
        elif filter_type == "Monthly":
            months = sorted(df_analysis['month_year'].unique(), reverse=True)
            selected_month = fcol1.selectbox("Select Month", months)
            df_filtered = df_analysis[df_analysis['month_year'] == selected_month]
        
        elif filter_type == "Date Range":
            start_date = fcol1.date_input("Start Date", df_analysis['date'].min())
            end_date = fcol2.date_input("End Date", df_analysis['date'].max())
            
            if start_date > end_date:
                st.error("Error: Start date must be before end date.")
            else:
                df_filtered = df_analysis[
                    (df_analysis['date'].dt.date >= start_date) & 
                    (df_analysis['date'].dt.date <= end_date)
                ]

        # --- Check if filtered data exists ---
        if df_filtered.empty:
            st.warning("No data found for the selected filter.")
        else:
            # --- KPI Metrics ---
            st.subheader("Dashboard Overview")
            total_income = df_filtered[df_filtered['Income/Expense'] == 'Income']['amount'].sum()
            total_expenses = df_filtered[df_filtered['Income/Expense'] == 'Expense']['amount'].sum()
            net_balance = total_income - total_expenses
            
            # --- UPDATED: Format values using the new function ---
            formatted_income = format_indian_currency(total_income)
            formatted_expenses = format_indian_currency(total_expenses)
            formatted_balance = format_indian_currency(net_balance)

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Total Income", formatted_income)
            kpi2.metric("Total Expenses", formatted_expenses)
            kpi3.metric("Net Balance", formatted_balance, 
                        delta=formatted_balance, # Use the formatted string for the delta
                        delta_color="normal" if net_balance >= 0 else "inverse")

            # --- Charts ---
            st.subheader("Visualizations")
            chart1, chart2 = st.columns(2)

            with chart1:
                # Pie chart for Income vs Expense
                pie_data = df_filtered.groupby('Income/Expense')['amount'].sum().reset_index()
                fig_pie = px.pie(pie_data, 
                                 names='Income/Expense', 
                                 values='amount', 
                                 title='Income vs. Expense', 
                                 hole=0.3,
                                 color_discrete_map={'Income':'green', 'Expense':'red'})
                # --- NEW: Update hover text to show Rupees ---
                fig_pie.update_traces(hovertemplate='<b>%{label}</b><br>Amount: ₹%{value:,.2f}<br>Percentage: %{percent:.1%}')
                st.plotly_chart(fig_pie, use_container_width=True)

            # --- ADDED CATEGORY CHART ---
            with chart2:
                # Bar chart for Spending by Category
                expense_data = df_filtered[df_filtered['Income/Expense'] == 'Expense']
                # Group by the new 'category' column
                category_spending = expense_data.groupby('category')['amount'].sum().sort_values(ascending=False).reset_index()
                
                fig_bar = px.bar(category_spending, 
                                 x='category', 
                                 y='amount', 
                                 title='Spending by Category',
                                 labels={'category': 'Category', 'amount': 'Amount (₹)'})
                # --- NEW: Update hover text to show Rupees ---
                fig_bar.update_traces(hovertemplate='<b>Category:</b> %{x}<br><b>Amount:</b> ₹%{y:,.2f}')
                st.plotly_chart(fig_bar, use_container_width=True)


            # --- Filtered Data Table (ADDED 'category') ---
            st.subheader("Filtered Transaction Data")
            
            # Format date for display (remove helper columns)
            df_display = df_filtered.drop(columns=['year', 'month_year']).copy()
            df_display['date'] = df_display['date'].dt.strftime('%Y-%m-%d')
            
            # Reorder columns to show category first
            cols_to_show = ['category', 'date', 'description', 'amount', 'Income/Expense']
            cols_to_show = [col for col in cols_to_show if col in df_display.columns]
            
            st.dataframe(df_display[cols_to_show], use_container_width=True)

# --- 6. SHOW LOGIN/REGISTER (IF NOT LOGGED IN) ---
else:
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        authenticator.login()

    with register_tab:
        try:
            if authenticator.register_user():
                st.success('User registered successfully! Please go to the Login tab.')
                with open('config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)
        except Exception as e:
            st.error(e)

    if st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please login or register.')

