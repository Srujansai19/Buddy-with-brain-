import streamlit as st
import pandas as pd
import pdfplumber
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import datetime
import plotly.express as px
import nltk
from pathlib import Path
import json 
import glob 
from prophet import Prophet 
from prophet.plot import plot_plotly 
from categorynltk import categorize_expense, ALL_CATEGORIES

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


# --- 1. SET UP PAGE ---
st.set_page_config(page_title="Buddy With Brain", page_icon="🧠", layout="wide")

DATA_DIR = Path("user_data")
DATA_DIR.mkdir(exist_ok=True)

def get_user_data_file(username):
    return DATA_DIR / f"data_{username}.parquet"

def load_data(username):
    data_file = get_user_data_file(username)
    if data_file.exists():
        try:
            df = pd.read_parquet(data_file)
        except Exception as e:
            st.error(f"Error loading data: {e}. Creating new empty dataframe.")
            df = pd.DataFrame(columns=['date', 'description', 'amount', 'Income/Expense', 'category'])
    else:
        df = pd.DataFrame(columns=['date', 'description', 'amount', 'Income/Expense', 'category'])
    
    df['date'] = pd.to_datetime(df['date'])
    return df

def save_data(username, df):
    data_file = get_user_data_file(username)
    try:
        df.to_parquet(data_file, index=False)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def get_user_goals_file(username):
    """Returns the Path object for a user's JSON goals file."""
    return DATA_DIR / f"goals_{username}.json"

def load_goals(username):
    """Loads a user's goals from a JSON file."""
    goals_file = get_user_goals_file(username)
    if goals_file.exists():
        try:
            with open(goals_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading goals: {e}. Returning empty list.")
            return []
    return []

def save_goals(username, goals):
    """Saves a user's goals to a JSON file."""
    goals_file = get_user_goals_file(username)
    try:
        with open(goals_file, 'w') as f:
            json.dump(goals, f, indent=4)
    except Exception as e:
        st.error(f"Error saving goals: {e}")


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
    st.sidebar.write(f'Welcome *{st.session_state["name"]}*')
    authenticator.logout('Logout', 'sidebar')

    username = st.session_state["username"]
    # --- ADDON: Get User Roles ---
    user_roles = st.session_state.get("roles", []) 
    # -----------------------------

    def format_indian_currency(amount):
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
            val_str += f"₹{amount:,.2f}"
        return val_str

    if "df" not in st.session_state:
        st.session_state.df = load_data(username)
    
    if "goals" not in st.session_state:
        st.session_state.goals = load_goals(username)
    # ---

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
                if uploaded_file.name.endswith('xlsx'):
                    df = pd.read_excel(uploaded_file)
                elif uploaded_file.name.endswith('csv'):
                    df = pd.read_csv(uploaded_file)

                if df is not None:
                    df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y %H:%M', errors='coerce')
                    df['amount'] = pd.to_numeric(df['amount'])
                    df['category'] = df.apply(lambda row: categorize_expense(row['description'], row['Income/Expense']), axis=1)
                    st.session_state.df = pd.concat([st.session_state.df, df], ignore_index=True)
                    save_data(username, st.session_state.df)
                    st.success(f"File '{uploaded_file.name}' loaded and saved.")
                    st.rerun()

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
                entry_category = categorize_expense(entry_desc, entry_type)
                new_entry = pd.DataFrame([{
                    "date": pd.to_datetime(entry_date),
                    "description": entry_desc,
                    "amount": entry_amount,
                    "Income/Expense": entry_type,
                    "category": entry_category
                }])
                st.session_state.df = pd.concat([st.session_state.df, new_entry], ignore_index=True)
                save_data(username, st.session_state.df)
                st.success("Transaction added and saved!")

    # --- 5. TABS FOR DASHBOARD AND FORECASTING ---
    
    #  Dynamic Tab Logic 
    tabs_list = ["📊 Analysis Dashboard", "📈 Forecasting & Goals"]
    if user_roles and 'admin' in user_roles:
        tabs_list.append("🔒 Admin Dashboard")
    
    # Create tabs (unpack only what we need)
    tabs = st.tabs(tabs_list)
    # ---------------------------------------------

    # --- ANALYSIS DASHBOARD ---
    with tabs[0]:
        if not st.session_state.df.empty:
            df_analysis = st.session_state.df.copy()

            df_analysis['date'] = pd.to_datetime(df_analysis['date'])
            df_analysis['amount'] = pd.to_numeric(df_analysis['amount'])
            
            df_analysis['year'] = df_analysis['date'].dt.year
            df_analysis['month_year'] = df_analysis['date'].dt.strftime('%B %Y')
            
            st.header("Filter Your Data")
            filter_type = st.selectbox("Select Filter Type", ["Overall", "Yearly", "Monthly", "Date Range"])
            
            fcol1, fcol2 = st.columns(2)
            
            df_filtered = df_analysis.copy()
            
            if filter_type == "Yearly":
                years = sorted(df_analysis['year'].unique(), reverse=True)
                selected_year = fcol1.selectbox("Select Year", years)
                df_filtered = df_analysis[df_analysis['year'] == selected_year]
            
            elif filter_type == "Monthly":
                month_options = df_analysis[['year', 'date']].copy()
                month_options['month_num'] = month_options['date'].dt.month
                month_options['month_year'] = month_options['date'].dt.strftime('%B %Y')
                months_sorted = month_options.sort_values(by=['year', 'month_num'], ascending=[False, False])
                months = months_sorted['month_year'].unique()
                
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

            if df_filtered.empty:
                st.warning("No data found for the selected filter.")
            else:
                st.header("Dashboard Overview")
                total_income = df_filtered[df_filtered['Income/Expense'] == 'Income']['amount'].sum()
                total_expenses = df_filtered[df_filtered['Income/Expense'] == 'Expense']['amount'].sum()
                net_balance = total_income - total_expenses
                
                # --- DASHBOARD KPIs ---
                savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
                # -----------------------------------------------

                formatted_income = format_indian_currency(total_income)
                formatted_expenses = format_indian_currency(total_expenses)
                formatted_balance = format_indian_currency(net_balance)

                # --- DASHBOARD KPIs ---
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                kpi1.metric("Total Income", formatted_income)
                kpi2.metric("Total Expenses", formatted_expenses)
                kpi3.metric("Net Balance", formatted_balance, 
                            delta=formatted_balance, 
                            delta_color="normal" if net_balance >= 0 else "inverse")
                kpi4.metric("Savings Rate", f"{savings_rate:.1f}%", help="% of Income Saved")
                # --------------------------------------------------------

                st.header("Visualizations")

                st.subheader("📈 Income vs. Expense Trends")
                trend_df = df_filtered.copy()
                # Group by Date and Type
                trend_grouped = trend_df.groupby([trend_df['date'].dt.date, 'Income/Expense'])['amount'].sum().reset_index()
                trend_grouped.columns = ['date', 'Income/Expense', 'amount']
                
                fig_trend = px.line(trend_grouped, x='date', y='amount', color='Income/Expense',
                                    title="Daily Cash Flow Trend", markers=True,
                                    color_discrete_map={'Income':'green', 'Expense':'red'})
                st.plotly_chart(fig_trend, use_container_width=True)
                # -----------------------------------------------------

                chart1, chart2 = st.columns(2)

                with chart1:
                    pie_data = df_filtered.groupby('Income/Expense')['amount'].sum().reset_index()
                    fig_pie = px.pie(pie_data, names='Income/Expense', values='amount', 
                                     title='Income vs. Expense',
                                     color_discrete_map={'Income':'green', 'Expense':'red'})
                    fig_pie.update_traces(hovertemplate='<b>%{label}</b><br>Amount: ₹%{value:,.2f}<br>Percentage: %{percent:.1%}')
                    st.plotly_chart(fig_pie, use_container_width=True)

                with chart2:
                    expense_data = df_filtered[df_filtered['Income/Expense'] == 'Expense']
                    category_spending = expense_data.groupby('category')['amount'].sum().sort_values(ascending=False).reset_index()
                    
                    fig_bar = px.bar(category_spending, x='category', y='amount', 
                                     title='Spending by Category',
                                     labels={'category': 'Category', 'amount': 'Amount (₹)'})
                    fig_bar.update_traces(hovertemplate='<b>Category:</b> %{x}<br><b>Amount:</b> ₹%{y:,.2f}')
                    st.plotly_chart(fig_bar, use_container_width=True)

                st.header("Filtered Transaction Data")
                df_display = df_filtered.drop(columns=['year', 'month_year']).copy()
                df_display['date'] = df_display['date'].dt.strftime('%Y-%m-%d')
                
                cols_to_show = ['category', 'date', 'description', 'amount', 'Income/Expense']
                df_display = df_display[cols_to_show]

                column_config = {
                    "category": st.column_config.SelectboxColumn(
                        "Category", help="Double-click to edit the transaction category",
                        options=ALL_CATEGORIES, required=True
                    ),
                    "date": st.column_config.TextColumn("Date", disabled=True),
                    "description": st.column_config.TextColumn("Description", disabled=True),
                    "amount": st.column_config.NumberColumn("Amount (₹)", disabled=True),
                    "Income/Expense": st.column_config.TextColumn("Type", disabled=True),
                }

                edited_df = st.data_editor(
                    df_display, column_config=column_config,
                    use_container_width=True, hide_index=True, num_rows="dynamic"
                )

                if not edited_df.equals(df_display):
                    st.session_state.df.update(edited_df)
                    save_data(username, st.session_state.df)
                    st.success("Changes saved!")
                    st.rerun()
        else:
            st.info("Upload a file or add a transaction to get started.")


    # FORECASTING & GOALS 
    with tabs[1]:
        if not st.session_state.df.empty:
            st.header("Financial Goal Setting")
            
            expense_categories = [cat for cat in ALL_CATEGORIES if cat != 'Income']
            with st.form("goal_form", clear_on_submit=True):
                st.write("Set a new monthly spending goal:")
                goal_cat = st.selectbox("Category", options=expense_categories)
                goal_amount = st.number_input("Target Monthly Amount (₹)", min_value=1.0)
                goal_submitted = st.form_submit_button("Set Goal")

                if goal_submitted:
                    # Remove old goal for the same category if it exists
                    st.session_state.goals = [g for g in st.session_state.goals if g['category'] != goal_cat]
                    # Add new goal
                    st.session_state.goals.append({"category": goal_cat, "amount": goal_amount})
                    save_goals(username, st.session_state.goals)
                    st.success(f"Goal set for {goal_cat}: {format_indian_currency(goal_amount)} per month.")

            #  Display Current Goals 
            if st.session_state.goals:
                st.subheader("Your Current Goals")
                goal_cols = st.columns(len(st.session_state.goals))
                for i, goal in enumerate(st.session_state.goals):
                    with goal_cols[i]:
                        st.metric(
                            label=f"Goal: {goal['category']}",
                            value=format_indian_currency(goal['amount'])
                        )

            st.divider()

            #  Forecasting Section
            st.header("Expense Forecasting")
            
            # Prepare data for forecasting
            df_expense = st.session_state.df[st.session_state.df['Income/Expense'] == 'Expense'].copy()
            
            if df_expense.empty:
                st.warning("You have no expense data to forecast.")
            else:
                forecast_cat_options = ['All Expenses'] + sorted(df_expense['category'].unique())
                forecast_cat = st.selectbox("Select category to forecast", options=forecast_cat_options)
                forecast_days = st.slider("Select forecast period (days)", 30, 365, 90)

                if st.button("Generate Forecast"):
                    
                    # 1. Historical Data Preparation
                    if forecast_cat == 'All Expenses':
                        df_to_forecast = df_expense
                    else:
                        df_to_forecast = df_expense[df_expense['category'] == forecast_cat]

                    # Aggregate by day
                    df_prophet = df_to_forecast.set_index('date').resample('D')['amount'].sum().reset_index()
                    df_prophet.columns = ['ds', 'y'] 

                    if len(df_prophet) < 7:
                        st.error("Not enough data to create a forecast. Please add more transactions.")
                    else:
                        with st.spinner("Training model and generating forecast..."):
                            # 2. Prophet Integration
                            m = Prophet()
                            m.fit(df_prophet)
                            future = m.make_future_dataframe(periods=forecast_days)
                            forecast = m.predict(future)

                            # 3. Forecast Visualization
                            st.subheader(f"Forecast for {forecast_cat}")
                            fig = plot_plotly(m, forecast)
                            fig.update_layout(
                                title=f"{forecast_cat} Spending Forecast",
                                xaxis_title="Date",
                                yaxis_title="Amount (₹)"
                            )
                            st.plotly_chart(fig, use_container_width=True)

                            # 4. Show projected spending vs. goals
                            # Get the average monthly spend from the forecast
                            forecast_period_df = forecast.set_index('ds').tail(forecast_days)
                            avg_daily_spend = forecast_period_df['yhat'].mean()
                            projected_monthly_spend = avg_daily_spend * 30.44 

                            st.subheader("Forecast vs. Goal")
                            
                            # Find the goal for this category
                            current_goal = None
                            if forecast_cat != 'All Expenses':
                                for g in st.session_state.goals:
                                    if g['category'] == forecast_cat:
                                        current_goal = g
                                        break
                            
                            if current_goal:
                                goal_amount = current_goal['amount']
                                diff = projected_monthly_spend - goal_amount
                                
                                kpi_col1, kpi_col2 = st.columns(2)
                                kpi_col1.metric(
                                    label=f"Projected Monthly Spend ({forecast_cat})",
                                    value=format_indian_currency(projected_monthly_spend)
                                )
                                kpi_col2.metric(
                                    label=f"Your Goal ({forecast_cat})",
                                    value=format_indian_currency(goal_amount),
                                    delta=format_indian_currency(diff),
                                    delta_color="inverse" if diff <= 0 else "normal"
                                )
                                if diff <= 0:
                                    st.success("🎉 You are on track to meet your goal!")
                                else:
                                    st.warning("You are currently projected to spend *more* than your goal.")
                            else:
                                st.metric(
                                    label=f"Projected Monthly Spend ({forecast_cat})",
                                    value=format_indian_currency(projected_monthly_spend)
                                )
                                if forecast_cat != 'All Expenses':
                                    st.info(f"You have no goal set for {forecast_cat}. You can set one above.")
        else:
             st.info("Upload a file or add a transaction to get started.")

    # Admin Dashboard (Only visible to Admin) 
    if user_roles and 'admin' in user_roles:
        with tabs[2]:
            st.header("🔒 Administrator Dashboard")
            st.markdown("---")
            
            # 1. System Stats Logic
            total_users = len(config['credentials']['usernames'])
            
            # Scan all parquet files in user_data folder
            all_files = glob.glob(str(DATA_DIR / "data_*.parquet"))
            total_transactions = 0
            total_volume = 0
            
            for f in all_files:
                try:
                    temp_df = pd.read_parquet(f)
                    total_transactions += len(temp_df)
                    total_volume += temp_df['amount'].sum()
                except:
                    pass

            a1, a2, a3 = st.columns(3)
            a1.metric("Total Users Registered", total_users)
            a2.metric("Total System Transactions", total_transactions)
            a3.metric("Total Transaction Volume", format_indian_currency(total_volume))
            
            st.markdown("---")
            
            # 2. User Management View
            st.subheader("User Directory")
            user_data = []
            for u, details in config['credentials']['usernames'].items():
                user_data.append({
                    "Username": u,
                    "Name": f"{details['first_name']} {details['last_name']}",
                    "Email": details['email'],
                    "Role": details['roles'][0] if details['roles'] else 'user',
                    "Status": "Logged In" if details.get('logged_in') else "Offline"
                })
            st.dataframe(pd.DataFrame(user_data), use_container_width=True)

            st.markdown("---")
            st.success("System Operational - Parquet Database Active")
    # ----------------------------------------------------------------


# SHOW LOGIN/REGISTER (IF NOT LOGGED IN) 
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