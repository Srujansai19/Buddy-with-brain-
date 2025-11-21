import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Expense Visualizer",
    page_icon="📊",
    layout="wide"
)

#Title of the App
st.title("📊 My Personal Expense Visualizer")
st.write("This dashboard shows your historical spending from the dataset.")

#Load the Processed Data 
try:
    data = pd.read_csv('processed_dataset.csv')
    data['Date'] = pd.to_datetime(data['Date'])
    data.set_index('Date', inplace=True)
except FileNotFoundError:
    st.error("Error: 'processed_dataset.csv' not found.")
    st.info("Please make sure the processed data file is in the same folder as this app.py file.")
    st.stop() 

#Sidebar for Filtering
st.sidebar.header("Filter by Date")
# .date() converts the full timestamp to just a date object for the slider
min_date = data.index.min().date()
max_date = data.index.max().date()

# Date slider widgets
start_date = st.sidebar.slider(
    "Start Date",
    min_value=min_date,
    max_value=max_date,
    value=min_date
)

end_date = st.sidebar.slider(
    "End Date",
    min_value=min_date,
    max_value=max_date,
    value=max_date
)


# Use .loc for robust date range slicing. This correctly handles
# cases where the start or end dates are not in the index.
filtered_data = data.loc[start_date:end_date]


# Main Page Display
st.subheader(f"Displaying data from {start_date} to {end_date}")

#Summary Metrics
total_spent = filtered_data['Amount'].sum()
avg_daily_spent = filtered_data['Amount'].mean()

col1, col2 = st.columns(2)
col1.metric("Total Spent in Period", f"{total_spent:,.2f}")
col2.metric("Average Daily Spend", f"{avg_daily_spent:,.2f}")

#Chart
st.subheader("Daily Expenses Chart")
st.line_chart(filtered_data['Amount'])

#  Data Table 
if st.checkbox("Show Data Table for Selected Period"):
    st.dataframe(filtered_data)
