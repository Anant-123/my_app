import streamlit as st
import pandas as pd
import re
from datetime import datetime
import matplotlib.pyplot as plt

# Sidebar for navigation
st.sidebar.image('logo.jfif', width=50)
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["Page 1: WIP Data Processor", "Page 2: Placeholder"])

# Page 1: WIP Data Processor
if page == "Page 1: WIP Data Processor":
    
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

                plt.figure(figsize=(16, 10))  # Increased plot size
                plt.plot(dates, values, label=f'{resource_to_plot} - {inv_to_plot}', marker='o')
                plt.xlabel('Date')
                plt.ylabel('Quantity')
                plt.title(f'Variation of {resource_to_plot} - {inv_to_plot} with Date')
                plt.legend(title='Resources - Inventory')
                plt.xticks(rotation=45)
                plt.grid(True)  # Add grid lines for better readability
                plt.tight_layout()
                st.pyplot(plt)

# Page 2: Placeholder for new functionality
elif page == "Page 2: Placeholder":
    st.image('logo.jfif', width=100)
    st.title("Page 2: Placeholder")
    st.write("This is a placeholder for your new functionality.")
    # Add your new page content here
