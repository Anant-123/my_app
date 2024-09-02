import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# Set page configuration
st.set_page_config(page_title="Extrusion Renukoot NRT & Delay Analysis", layout="wide")

st.title(" Extrusion Renukoot NRT & Delay Analysis 🔍")

# Initialize session state for data and graphs
if 'data' not in st.session_state:
    st.session_state.data = None
if 'fig1' not in st.session_state:
    st.session_state.fig1 = None
if 'todate_nrt' not in st.session_state:
    st.session_state.todate_nrt = None
if 'avg_nrt' not in st.session_state:
    st.session_state.avg_nrt = None
if 'todate_delay' not in st.session_state:
    st.session_state.todate_delay = None

# Function to process uploaded Excel file
def process_excel(uploaded_file):
    try:
        # Load the Excel file
        excel_data = pd.ExcelFile(uploaded_file)

        # Initialize an empty list to store the data
        all_data = []

        # Define the mapping for presses and their corresponding rows
        presses = {
            1: (2, 4, 23),  # Press 1: E3 to V3
            2: (4, 4, 23),  # Press 2: E5 to V5
            3: (6, 4, 23),  # Press 3: E7 to V7
            5: (8, 4, 23),  # Press 5: E9 to V9
            6: (10, 4, 23), # Press 6: E11 to V11
            7: (12, 4, 23), # Press 7: E13 to V13
            8: (14, 4, 23), # Press 8: E15 to V15
            9: (16, 4, 23)  # Press 9: E17 to V17
        }

        # Loop through each sheet name
        for sheet_name in excel_data.sheet_names:
            # Load the sheet into a DataFrame
            sheet_df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)

            # Loop through each press and extract the corresponding data
            for press_num, (row, col_start, col_end) in presses.items():
                # Check if the necessary rows and columns exist
                if sheet_df.shape[0] > row and sheet_df.shape[1] >= col_end:
                    headers = sheet_df.iloc[0, col_start:col_end].fillna(f"Col_{col_start}").values
                    values = sheet_df.iloc[row, col_start:col_end].values

                    # Create a dictionary for the current press data
                    press_data = {'Date': sheet_name, 'Press': press_num}
                    press_data.update(dict(zip(headers, values)))

                    # Append to the list
                    all_data.append(press_data)
                else:
                    st.warning(f"Sheet '{sheet_name}' does not have the expected format for Press {press_num}.")

        if all_data:
            # Convert the list of dictionaries into a DataFrame
            df = pd.DataFrame(all_data)

            # Convert the 'Date' column to datetime
            df['Date'] = pd.to_datetime(df['Date'], format="%d.%m.%y", errors='coerce')

            # **Sort the DataFrame by Date**
            df = df.sort_values(by='Date')

            # Drop rows with invalid dates
            df = df.dropna(subset=['Date'])

            # Calculate the 'Total delay' as the sum of all delay columns
            delay_columns = df.columns.drop(['Date', 'Press','Major Delay'])  # Exclude non-delay columns
            df['Total delay'] = df[delay_columns].sum(axis=1)

            # Calculate the 'Total NRT' as 24 minus 'Total delay'
            df['Total NRT'] = 24 - df['Total delay']

            # **Calculate the Todate NRT and Todate Delay after sorting**
            df['Todate NRT'] = df.groupby('Press')['Total NRT'].cumsum()
            df['Todate delay'] = df.groupby('Press')['Total delay'].cumsum()

            # Reorder the columns
            remaining_columns = [col for col in df.columns if col not in ['Date', 'Press', 'Total delay', 'Total NRT', 'Todate NRT', 'Todate delay']]
            df = df[['Date', 'Press', 'Total delay', 'Total NRT', 'Todate NRT', 'Todate delay'] + remaining_columns]

            # Save the data in session state
            st.session_state.data = df

            return df
        else:
            st.error("No valid data extracted from the sheets.")
            return None

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        return None

# Function to calculate lowest and highest Todate delay
def calculate_delay_extremes(df):
    todate_delay_summary = df.groupby('Press')['Todate delay'].max()
    lowest_todate_delay_press = todate_delay_summary.idxmin()
    highest_todate_delay_press = todate_delay_summary.idxmax()
    lowest_delay_value = todate_delay_summary.min()
    highest_delay_value = todate_delay_summary.max()
    return lowest_todate_delay_press, lowest_delay_value, highest_todate_delay_press, highest_delay_value

# Function to create Plotly figure
def create_nrt_plot(press_data, avg_nrt, press_num):
    fig = px.bar(
        press_data, 
        x='Date', 
        y='Total NRT', 
        title=f'Total NRT - Press {press_num}',
        labels={'Total NRT': 'Total NRT (hrs)', 'Date': 'Date'},
        text_auto='.2f'  # Display labels with 2 decimal places
    )
    fig.add_hline(
        y=avg_nrt, 
        line_dash="dash", 
        annotation_text=f"Avg NRT: {avg_nrt:.2f} hrs", 
        annotation_position="bottom right",
        line_color="red"
    )
    fig.update_layout(hovermode="x unified")
    return fig

def create_mech_ei_plot(press_data, press_num):
    # Calculate the sum of Mechanical and E&I columns
    press_data['Mech_EI_Sum'] = press_data['Mechanical'] + press_data['E&I']

    # Create the bar chart
    fig = px.bar(
        press_data, 
        x='Date', 
        y='Mech_EI_Sum', 
        title=f'Engineering downtime - Press {press_num}',
        labels={'Mech_EI_Sum': 'Mechanical + E&I (hrs)', 'Date': 'Date'},
        text_auto='.2f'  # Display labels with 2 decimal places
    )
    
    # Optional: If you want to add an average line for the sum
    avg_mech_ei = press_data['Mech_EI_Sum'].mean()
    fig.add_hline(
        y=avg_mech_ei, 
        line_dash="dash", 
        annotation_text=f"Avg Mech + E&I: {avg_mech_ei:.2f} hrs", 
        annotation_position="bottom right",
        line_color="blue"
    )


    # Update layout with unified hovermode for better interaction
    fig.update_layout(hovermode="x unified")
    
    return fig

# Function to create a pie chart
def create_pie_chart(data, press_num):
    # Sum all the relevant columns
    pie_data = data[['Mechanical', 'E&I', 'Operation', 'Die Shop']].sum()

    # Convert to a DataFrame
    pie_df = pd.DataFrame({'Category': pie_data.index, 'Total Hours': pie_data.values})

    # Calculate percentage
    pie_df['Percentage'] = (pie_df['Total Hours'] / pie_df['Total Hours'].sum()) * 100

    # Create the pie chart
    fig = px.pie(
        pie_df, 
        values='Total Hours', 
        names='Category', 
        title=f'Pie Chart Downtime Categories - Press {press_num}',
        labels={'Total Hours': 'Total Hours (hrs)', 'Category': 'Category'},
        hover_data=['Percentage'],
        hole=.3  # To create a donut chart effect (optional)
    )

    return fig

# Function to calculate and display the scorecard
def display_mech_ei_scorecard(press_data):
    total_mech_ei = press_data['Mech_EI_Sum'].sum()

# File uploader
uploaded_file = st.file_uploader("📂 Choose an Excel file", type="xlsx")

# Process the uploaded file
if uploaded_file is not None:
    with st.spinner('🔄 Processing the uploaded file...'):
        df = process_excel(uploaded_file)
    
    if df is not None:
        # Save the data in session state
        st.session_state.data = df

        # Calculate delay extremes
        lowest_press, lowest_delay, highest_press, highest_delay = calculate_delay_extremes(df)

        # Display running text
        st.markdown(
            f"""
            <div style='background-color:#f0f8ff; padding:10px; border-radius:5px;'>
                <p style='font-size:16px;'><b>📉 Lowest Todate Delay:</b> Press <b>{lowest_press}</b> with a value of <b>{lowest_delay:.2f} hrs</b></p>
                <p style='font-size:16px;'><b>📈 Highest Todate Delay:</b> Press <b>{highest_press}</b> with a value of <b>{highest_delay:.2f} hrs</b></p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Sidebar for filters
        st.sidebar.header("🔧 Filters")

        # Select multiple presses (initially blank)
        presses = sorted(df['Press'].unique())
        selected_presses = st.sidebar.multiselect("Select Press(es)", options=presses)

        # Select date range
        min_date = df['Date'].min()
        max_date = df['Date'].max()
        selected_dates = st.sidebar.date_input("Select Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

        if len(selected_dates) != 2:
            st.sidebar.error("Please select a start and end date.")
            filtered_df = df[df['Press'].isin(selected_presses)]
        else:
            start_date, end_date = selected_dates
            filtered_df = df[
                (df['Press'].isin(selected_presses)) & 
                (df['Date'] >= pd.to_datetime(start_date)) & 
                (df['Date'] <= pd.to_datetime(end_date))
            ]

        if filtered_df.empty:
            st.warning("No data available for the selected filters.")
        else:
            for press_num in selected_presses:
                press_data = filtered_df[filtered_df['Press'] == press_num]

                # Calculate metrics for the current press
                avg_nrt = press_data['Total NRT'].mean()
                press_data['Mech_EI_Sum'] = press_data['Mechanical'] + press_data['E&I']
                todate_nrt = press_data['Todate NRT'].iloc[-1]
                todate_delay = press_data['Todate delay'].iloc[-1]
                total_mech_ei = press_data['Mech_EI_Sum'].sum()

                 # Calculate Total hours (24 hours * number of days in the selected range)
                total_days = (press_data['Date'].max() - press_data['Date'].min()).days + 1
                total_hours = 24 * total_days

                # Calculate percentage of Total Engineering downtime
                mech_ei_percentage = (total_mech_ei * 100) / total_hours

                # Display metrics for the current press
                # Display metrics for the current press in a single horizontal line
                st.subheader(f"Press {press_num} Metrics")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(label="📊 Todate NRT (hrs)", value=f"{todate_nrt:.2f}")
                with col2:
                    st.metric(label="📊 Todate Delay (hrs)", value=f"{todate_delay:.2f}")
                with col3:
                    st.metric(label="📊 Total Engineering downtime (hrs)", 
                    value=f"{total_mech_ei:.2f} ({mech_ei_percentage:.2f}%)")
                with col4:
                    st.metric(label="📊 Average NRT (hrs)", value=f"{avg_nrt:.2f}")

                # Generate and display the plots for the current press
                fig = create_nrt_plot(press_data, avg_nrt, press_num)
                st.plotly_chart(fig, use_container_width=True)
                
                fig2 = create_mech_ei_plot(press_data, press_num)
                st.plotly_chart(fig2, use_container_width=True)
                
                # Define the columns that represent different types of delays
                delay_columns = [
                    "Mechanical", "E&I", "Operation", "Die Shop", "Misc", "P.M.",
                    "SD / BD", "No Order", "No Billet", "Center Crack", "Planning",
                    "Die Failure", "Die Management", "Die Development", "Die change Time",
                    "System", "Power", "Die Withdrawal"
                ]

                # Calculate the sum for each delay type
                delay_sums = press_data[delay_columns].sum()

                # Calculate the percentage for each delay type
                delay_percentages = delay_sums / delay_sums.sum() * 100

                # Prepare data for pie chart
                pie_data = pd.DataFrame({
                    'Delay Type': delay_sums.index,
                    'Sum': delay_sums.values,
                    'Percentage': delay_percentages.values
                })



                # Filter to include only those delay types where percentage is greater than 5%
                filtered_pie_data = pie_data[pie_data['Percentage'] > 5]

                # Create the pie chart
                fig = px.pie(filtered_pie_data, values='Sum', names='Delay Type', 
                            title='Delay Distribution (Only >5%)',
                            hover_data=['Percentage'], 
                            labels={'Percentage':'% of Total'})

                # Show the chart in Streamlit
                st.plotly_chart(fig)


        # Display DataFrame preview
        st.write("### Data Preview")
        st.dataframe(filtered_df.style.format(precision=2))

else:
    st.info("Upload an Excel file to get started.")
