import streamlit as st
import pandas as pd
import re
from datetime import datetime
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np

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
    page = st.sidebar.selectbox("Choose a page", ["Page 1: WIP Daily Trend", "Page 2: Circle Best recovery figure"])
    if st.sidebar.button("Logout"):
        logout()
        st.experimental_rerun()

    # Page 1: WIP Data Processor
    if page == "Page 1: WIP Daily Trend":

        st.image('logo.jfif', width=100)
        st.title('WIP Day-wise Trend')
    
        # File uploader to upload multiple files
        uploaded_files = st.file_uploader("📂Choose WIP Excel files", accept_multiple_files=True, type="xlsx")
    
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
    
                # Multiselect to select the resources and inventories to plot
                resources_to_plot = st.multiselect('Select Machine centers to plot', options=pivot_df['Resources'].unique())
                invs_to_plot = st.multiselect('Select inventories to plot', options=pivot_df['Inv'].unique())
    
                @st.cache_data
                def get_plot_data(pivot_df, resource_names, inv_names):
                    filtered_data = pivot_df[
                        (pivot_df['Resources'].isin(resource_names)) & (pivot_df['Inv'].isin(inv_names))
                    ]
                    summed_data = filtered_data.iloc[:, 2:].sum()  # Sum across selected resources and inventories
                    return summed_data
    
                if resources_to_plot and invs_to_plot:
                    plot_data = get_plot_data(pivot_df, resources_to_plot, invs_to_plot)
    
                    if plot_data.empty:
                        st.error(f"No data found for selected Machine centers and Inventories.")
                    else:
                        dates = plot_data.index
                        values = plot_data.values
    
                        # Use Plotly to create a colorful plot
                        fig = px.line(
                            x=dates,
                            y=values,
                            labels={'x': 'Date', 'y': 'WIP in MT'},
                            title=f'WIP trend for selected inventories at {", ".join(resources_to_plot)}',
                            markers=True
                        )
    
                        # Customize the appearance
                        fig.update_traces(line=dict(color='royalblue', width=4))
                        fig.update_layout(
                            xaxis_title='Date',
                            yaxis_title='WIP in MT',
                            title_font_size=24,
                            title_x=0.3,  # Center title
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(showgrid=True, gridcolor='LightPink'),
                            yaxis=dict(showgrid=True, gridcolor='LightPink'),
                        )
    
                        st.plotly_chart(fig)
                
                # New plot: Sum of Qty for all Inventories in the selected Resource
                st.subheader(f'Total WIP Across Selected Machine centers and Inventories')
    
                @st.cache_data
                def get_total_qty_data(pivot_df, resource_names):
                    filtered_data = pivot_df[pivot_df['Resources'].isin(resource_names)]
                    total_qty = filtered_data.iloc[:, 2:].sum()  # Sum across all inventories
                    return total_qty
    
                total_qty_data = get_total_qty_data(pivot_df, resources_to_plot)
    
                # Adding the selected machine centers to the title
                selected_resources_str = ", ".join(resources_to_plot)
                fig2 = px.line(
                    x=total_qty_data.index,
                    y=total_qty_data.values,
                    labels={'x': 'Date', 'y': 'Total WIP (in MT)'},
                    title=f'Total WIP for {selected_resources_str}',
                    markers=True
                )
    
                fig2.update_traces(line=dict(color='orange', width=4))
                fig2.update_layout(
                    xaxis_title='Date',
                    yaxis_title='Total WIP (in MT)',
                    title_font_size=24,
                    title_x=0.3,  # Center title
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=True, gridcolor='LightPink'),
                    yaxis=dict(showgrid=True, gridcolor='LightPink'),
                )
    
                st.plotly_chart(fig2)

    

    # Page 2: Upload and Merge DataFrames
    if page == "Page 2: Circle Best recovery figure":
        st.image('logo.jfif', width=100)
        st.title("Circle Best recovery figure")
        # Define the recovery calculation function
        def recovery(w, b, t, angle_deg):
            # Convert angle from degrees to radians
            angle_rad = np.pi * angle_deg / 180
            
            blank_center = b + 5
            tool_pitch = blank_center * np.sin(angle_rad)
            coil_pitch = blank_center * np.cos(angle_rad)
            
            # Constants
            disc_to_border = 30  # Fixed value
            
            # Usable width
            usable_width = w - 2 * disc_to_border
            
            # Ensure that the usable width is positive
            if usable_width <= b:
                return -np.inf  # Infeasible solution
            
            # Number of blanks
            no_of_blanks = np.floor((usable_width - b) / tool_pitch) + 1
            
            # Material used
            material_used = 2 * coil_pitch * w * t / 1000  # in cubic meters
            
            # Blank volume
            blank_vol = (no_of_blanks * np.pi * b**2 * t) / 4000  # in cubic meters
            
            # Percentage loss
            percent_loss = (material_used - blank_vol) / material_used * 100
            
            # Percentage recovery
            percent_recovery = 100 - percent_loss
            
            return percent_recovery

            # Inputs for b and t from user
        b = st.number_input("Enter the disc diameter (b) in mm:", min_value=100, max_value=1000, value=500, step=10)
        t = st.number_input("Enter the thickness (t) in mm:", min_value=1, max_value=100, value=10, step=1)

        # Possible discrete values for coil width w
        w_values = [914, 965, 1016, 1067, 1118, 1270, 1320]

        # Generate angle values from 30 to 60 in steps of 1.5 degrees
        angle_values = np.arange(30, 60.1, 1.5)

        # Initialize variables to track the optimal values
        best_w = None
        best_angle = None
        max_recovery = -np.inf

        # Initialize a list to store detailed recovery results
        recovery_data = []
        # Evaluate recovery for each value of w and angle
        for w in w_values:
            for angle in angle_values:
                rec = recovery(w, b, t, angle)
                recovery_data.append([w, angle, rec])
                
                # Update optimal recovery if a better value is found
                if rec > max_recovery:
                    max_recovery = rec
                    best_w = w
                    best_angle = angle

        # # Display the optimal coil width, angle, and maximum recovery
        # st.subheader("Optimal Recovery Results")
        # st.write(f"**Optimal coil width:** {best_w} mm")
        # st.write(f"**Optimal angle:** {best_angle:.2f}°")
        # st.write(f"**Maximum recovery percentage:** {max_recovery:.2f}%")

        # Custom HTML for a light pink rounded box
        box_style = """
            <div style="
                background-color: #FFCCCB; 
                border-radius: 10px; 
                padding: 20px; 
                margin: 10px 0px;
                box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.1);
            ">
            <h3 style="color: #333333;">Optimal Recovery Results 🔍</h3>
            <p><b>Optimal coil width:</b> {best_w} mm</p>
            <p><b>Optimal angle:</b> {best_angle:.2f}°</p>
            <p><b>Maximum recovery percentage:</b> {max_recovery:.2f}%</p>
            </div>
        """.format(best_w=best_w, best_angle=best_angle, max_recovery=max_recovery)

        # Display the custom box using st.markdown
        st.markdown(box_style, unsafe_allow_html=True)

        # Create a DataFrame for detailed recovery results
        df_recovery = pd.DataFrame(recovery_data, columns=["Width (mm)", "Angle (°)", "% Recovery"])

        #st.dataframe(df_recovery)

        # Filter the DataFrame to show only the maximum recovery row for each width
        df_best_recovery = df_recovery.groupby("Width (mm)", as_index=False).apply(lambda x: x.loc[x["% Recovery"].idxmax()])

        # Round the recovery percentage and angle to 2 decimal places
        df_best_recovery["% Recovery"] = df_best_recovery["% Recovery"].round(2)
        df_best_recovery["Angle (°)"] = df_best_recovery["Angle (°)"].round(2)

        # Display the optimal coil width, angle, and maximum recovery with rounded values
        st.subheader("Recovery % for Each Width")
        st.dataframe(df_best_recovery)

        # Create two columns
        #col1, col2 = st.columns(2)

        # # Display df_recovery in the first column
        # with col1:
        #     st.subheader("All possible combinations of width and angles")
        #     st.dataframe(df_recovery)

        # # Display df_best_recovery in the second column
        # with col2:
        #     st.subheader("Best possible Recovery for Each Width")
        #     st.dataframe(df_best_recovery)

        
        # Assuming df_best_recovery is already defined and has columns "Width (mm)" and "% Recovery"
        w_values = df_best_recovery["Width (mm)"].unique()  # Get unique coil widths

        # Create a bar graph with Plotly
        fig = px.bar(df_best_recovery, 
                    x="Width (mm)", 
                    y="% Recovery", 
                    text="% Recovery",  # Add data labels on top of bars
                    title=" Recovery for Each Width📈",
                    labels={"% Recovery": "Recovery (%)", "Width (mm)": "Coil Width (mm)"},
                    height=500)

        # Customize the appearance of the bar graph
        fig.update_traces(
            texttemplate='%{text:.2f}',  # Format data labels to 2 decimal places
            textposition='outside',
            textfont=dict(size=14, color='black', family='Arial', weight="bold")  # Increase size and make text bold
        )

        fig.update_layout(
            yaxis_title="Recovery (%)", 
            xaxis_title="Coil Width (mm)", 
            xaxis=dict(
                tickvals=w_values  # Set x-axis tick values to the unique coil widths
            ),
            uniformtext_minsize=8, 
            uniformtext_mode='hide',
            bargap=0.1  # Adjust space between bars if needed
        )

        # Display the bar chart in Streamlit
        st.plotly_chart(fig, use_container_width=True)  # Enable dynamic width        
