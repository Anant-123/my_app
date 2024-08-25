import streamlit as st
import pandas as pd
import re
from datetime import datetime
import matplotlib.pyplot as plt
import plotly.express as px

# Set page config to use wide layout
st.set_page_config(layout="wide")

# Sample user database
USER_DB = {
    "user1": "password1",
    "swapan.g": "password",
    "mahesh.m": "password",
    "anant.m": "123",
    "harendra.s": "password"
}

# Function to verify username and password
def authenticate(username, password):
    return USER_DB.get(username) == password

# Function to handle login
def login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if authenticate(username, password):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
        else:
            st.sidebar.error("Invalid username or password")

# Function to handle logout
def logout():
    st.session_state['logged_in'] = False
    st.session_state['username'] = None

# Check if user is logged in
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None

if not st.session_state['logged_in']:
    login()
else:
    # Sidebar for navigation
    st.sidebar.image('logo.jfif', width=50)
    st.sidebar.title("FRP Planning")
    st.sidebar.write(f"Welcome, {st.session_state['username']}!")
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Page 1: WIP Daily Trend", "Page 2: Circle Daily Status"])
    if st.sidebar.button("Logout"):
        logout()
        st.experimental_rerun()

    # Page 1: WIP Data Processor
    if page == "Page 1: WIP Daily Trend":

        st.image('logo.jfif', width=100)
        st.title('WIP Day-wise Trend')
    
        # File uploader to upload multiple files
        uploaded_files = st.file_uploader("Choose WIP Excel files", accept_multiple_files=True, type="xlsx")
    
        @st.cache_data
        def process_files(uploaded_files):
            files_with_dates = []
    
            for uploaded_file in uploaded_files:
                file_name = uploaded_file.name
                match = re.search(r'Alloy_Product_Wise_Summery__RK_(\d{2})(\d{2})(\d{2})', file_name)
                if match:
                    day, month, year = match.groups()
                    file_date = datetime.strptime(f'{day}{month}{year}', '%d%m%y')
                    files_with_dates.append((uploaded_file, file_date))
                else:
                    st.error(f"Filename does not match the expected pattern: {file_name}")
    
            if not files_with_dates:
                st.error("No valid files were uploaded.")
                return None
    
            files_with_dates.sort(key=lambda x: x[1])
            df_list = []
    
            for uploaded_file, file_date in files_with_dates:
                try:
                    df = pd.read_excel(uploaded_file, sheet_name='FNDWRR')
                    df['Date'] = file_date.strftime('%Y-%m-%d')
                    df_list.append(df)
                except Exception as e:
                    st.error(f"Error reading {uploaded_file.name}: {e}")
    
            all_data = pd.concat(df_list, ignore_index=True)
            all_data['Resources'] = all_data['Resources'].ffill()
            all_data['Qty'] = pd.to_numeric(all_data['Qty'], errors='coerce')
            all_data = all_data.dropna(subset=['Qty']).reset_index(drop=True)

            # Divide Qty by 1000
            all_data['Qty'] = all_data['Qty'] / 1000
    
            pivot_df = pd.pivot_table(
                all_data,
                values='Qty',
                index=['Resources', 'Inv'],
                columns='Date',
                aggfunc='sum',
                fill_value=0
            )
    
            all_dates = pd.date_range(start=min(files_with_dates, key=lambda x: x[1])[1], 
                                      end=max(files_with_dates, key=lambda x: x[1])[1])
            all_dates_str = [d.strftime('%Y-%m-%d') for d in all_dates]
            pivot_df = pivot_df.reindex(columns=all_dates_str, fill_value=0).reset_index()
    
            return pivot_df
    
        if uploaded_files:
            pivot_df = process_files(uploaded_files)
    
            if pivot_df is not None:
                st.dataframe(pivot_df)
    
                # Dropdowns to select the resource and inventory to plot
                resource_to_plot = st.selectbox('Select a Machine center to plot', options=pivot_df['Resources'].unique())
                inv_to_plot = st.selectbox('Select an inventory to plot', options=pivot_df['Inv'].unique())
    
                @st.cache_data
                def get_plot_data(pivot_df, resource_name, inv_name):
                    filtered_data = pivot_df[(pivot_df['Resources'] == resource_name) & (pivot_df['Inv'] == inv_name)]
                    return filtered_data
    
                filtered_data = get_plot_data(pivot_df, resource_to_plot, inv_to_plot)
    
                if filtered_data.empty:
                    st.error(f"No data found for Resource '{resource_to_plot}' and Inventory '{inv_to_plot}'.")
                else:
                    dates = pivot_df.columns[2:]  # Skip 'Resources' and 'Inv' columns
                    values = filtered_data.iloc[0, 2:].values  # Get the values for the selected resource and inventory
    
                    # Use Plotly to create a colorful plot
                    fig = px.line(
                        x=dates,
                        y=values,
                        labels={'x': 'Date', 'y': 'WIP in MT'},
                        title=f'WIP trend of {inv_to_plot} at  {resource_to_plot}',
                        markers=True
                    )
    
                    # Customize the appearance
                    fig.update_traces(line=dict(color='royalblue', width=4))
                    fig.update_layout(
                        xaxis_title='Date',
                        yaxis_title='WIP in MT',
                        title_font_size=24,
                        title_x=0.5,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=True, gridcolor='LightPink'),
                        yaxis=dict(showgrid=True, gridcolor='LightPink'),
                    )
    
                    st.plotly_chart(fig)
            # New plot: Sum of Qty for all Inventories in the selected Resource
            st.subheader(f'Total WIP at {resource_to_plot} Across All Inventories')

            @st.cache_data
            def get_total_qty_data(pivot_df, resource_name):
                filtered_data = pivot_df[pivot_df['Resources'] == resource_name]
                total_qty = filtered_data.iloc[:, 2:].sum()  # Sum across all inventories
                return total_qty

            total_qty_data = get_total_qty_data(pivot_df, resource_to_plot)

            fig2 = px.line(
                x=total_qty_data.index,
                y=total_qty_data.values,
                labels={'x': 'Date', 'y': 'Total WIP (in MT)'},
                title=f'Total WIP for {resource_to_plot}',
                markers=True
            )

            fig2.update_traces(line=dict(color='orange', width=4))
            fig2.update_layout(
                xaxis_title='Date',
                yaxis_title='Total WIP (in MT)',
                title_font_size=24,
                title_x=0.5,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='LightPink'),
                yaxis=dict(showgrid=True, gridcolor='LightPink'),
            )

            st.plotly_chart(fig2)

    

    # Page 2: Upload and Merge DataFrames
    if page == "Page 2: Circle Daily Status":
        st.image('logo.jfif', width=100)
        st.title("Circle Status today")

        # File uploader for production and item description files
        uploaded_files = st.file_uploader("Choose Excel files", accept_multiple_files=True, type="xlsx")

        if uploaded_files:
            df_prod = None
            df_item = None

            for uploaded_file in uploaded_files:
                file_name = uploaded_file.name
                match_prod = re.search(r'Hindalco_Daily_Production_Stat_(\d{6})', file_name)
                match_item = re.search(r'Item_desc', file_name, re.IGNORECASE)
                
                if match_prod:
                    report_date = match_prod.group(1)
                    try:
                        temp_df_prod = pd.read_excel(uploaded_file)
                        temp_df_prod['Report Date'] = datetime.strptime(report_date, '%d%m%y')
                        if df_prod is None:
                            df_prod = temp_df_prod
                        else:
                            df_prod = pd.concat([df_prod, temp_df_prod])
                    except Exception as e:
                        st.error(f"Error reading production file {file_name}: {e}")

                elif match_item:
                    try:
                        df_item = pd.read_excel(uploaded_file)
                    except Exception as e:
                        st.error(f"Error reading item description file {file_name}: {e}")

                else:
                    st.error(f"Filename does not match the expected pattern: {file_name}")

            # Display the dataframes if they exist
            if df_prod is not None:
                st.write("Production Data:")
                st.dataframe(df_prod.head())
            
            if df_item is not None:
                st.write("Item Description Data:")
                st.dataframe(df_item.head())

            # Perform the merge if both dataframes are available
            if df_prod is not None and df_item is not None:
                try:
                    df_merged_prod = df_prod.merge(df_item, how='left', left_on='Item_Code', right_on='FG Item_11')
                    st.write("Merged Data:")
                    st.dataframe(df_merged_prod.head(10))
                    
                    # Group by 'Unit' and calculate sum of 'Prod_Qty(Kg)' divided by 1000
                    df_grouped = df_merged_prod.groupby('Unit')['Prod_Qty(Kg)'].sum().reset_index()
                    df_grouped['Prod_Qty_MT'] = df_grouped['Prod_Qty(Kg)'] / 1000

                    st.write("Grouped Data with Production Quantity in MT:")
                    st.dataframe(df_grouped[['Unit', 'Prod_Qty_MT']])
                except Exception as e:
                    st.error(f"Error merging dataframes: {e}")
