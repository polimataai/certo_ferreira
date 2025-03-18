import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Basic page configuration
st.set_page_config(
    page_title="Harvesting Media - Data Processor",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def format_name(name):
    """Format name to capitalize only the first letter of each word."""
    if pd.isna(name):
        return name
    # Split the name into words and capitalize only the first letter
    return ' '.join(word.lower().capitalize() for word in str(name).split())

# Password protection
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.title("🌾 Harvesting Media")
        st.subheader("Data Processor")
        
        st.text_input(
            "Please enter the password to access the application",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    
    return st.session_state["password_correct"]

def read_file(file, has_headers):
    """Read file based on its extension."""
    try:
        if file.name.endswith('.csv'):
            return pd.read_csv(file, header=0 if has_headers else None)
        elif file.name.endswith('.xlsx'):
            return pd.read_excel(file, header=0 if has_headers else None)
        elif file.name.endswith('.txt'):
            # First try comma separator
            try:
                df = pd.read_csv(file, sep=',', header=0 if has_headers else None)
                # Check if we got more than one column
                if len(df.columns) > 1:
                    return df
            except:
                pass
            
            # If comma didn't work, try tab separator
            return pd.read_csv(file, sep='\t', header=0 if has_headers else None)
        else:
            raise ValueError("Unsupported file format. Please upload CSV, XLSX, or TXT file.")
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

def save_to_gsheets(df, worksheet):
    """Append dataframe to Google Sheets."""
    try:
        # Get the last row with data
        last_row = len(worksheet.get_all_values())
        
        # Replace NaN values with empty strings
        df_clean = df.fillna('')
        
        # Append new records starting from the next row
        worksheet.append_rows(
            df_clean.values.tolist(),
            value_input_option='RAW',
            insert_data_option='INSERT_ROWS',
            table_range=f'A{last_row + 1}'
        )
        return True
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {str(e)}")
        return False

def clear_session_state():
    """Clear all session state variables except password_correct."""
    for key in list(st.session_state.keys()):
        if key != "password_correct":
            del st.session_state[key]

def on_process_change():
    """Handle process selection change."""
    clear_session_state()

def main():
    if not check_password():
        st.error("⚠️ Password incorrect. Please try again.")
        return

    # Header
    st.title("🌾 Harvesting Media")
    st.subheader("Data Processor")
    
    # Initialize session state for process if not exists
    if 'previous_process' not in st.session_state:
        st.session_state['previous_process'] = None
    
    # Process selection
    process = st.selectbox(
        "Select Process",
        ["Certo Market", "Ferreira", "Certo Market Visits Report"],
        help="Choose which process to run",
        key="process"
    )
    
    # Check if process changed
    if st.session_state['previous_process'] is not None and st.session_state['previous_process'] != process:
        clear_session_state()
        st.session_state['process'] = process
        st.rerun()
    
    # Update previous process
    st.session_state['previous_process'] = process
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a file (CSV, XLSX, or TXT)", type=['csv', 'xlsx', 'txt'])
    
    if uploaded_file is not None:
        try:
            # Ask if file has headers
            has_headers = st.checkbox("File has headers", value=True)
            
            # Read the file
            df = read_file(uploaded_file, has_headers)
            
            # If no headers, generate column names
            if not has_headers:
                df.columns = [f'Column {i+1}' for i in range(len(df.columns))]
            
            # Show the first few rows of the data
            st.markdown("### Preview of Data")
            st.dataframe(df.head())
            
            # Column mapping
            st.markdown("### Map Columns")
            st.markdown("Please select which columns contain the required information:")
            
            if process == "Certo Market Visits Report":
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    name_col = st.selectbox("Name Column", df.columns.tolist())
                    email_col = st.selectbox("Email Column", df.columns.tolist())
                
                with col2:
                    phone_col = st.selectbox("Phone Column", df.columns.tolist())
                    reg_date_col = st.selectbox("Registration Date Column", df.columns.tolist())
                
                with col3:
                    first_order_col = st.selectbox("First Order Date Column", df.columns.tolist())
                    spent_col = st.selectbox("Spent Amount Column", df.columns.tolist())
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    email_col = st.selectbox("Email Column", df.columns.tolist())
                    first_name_col = st.selectbox("First Name Column", df.columns.tolist())
                
                with col2:
                    phone_col = st.selectbox("Phone Column", df.columns.tolist())
                    # Add store number selection for Ferreira
                    if process == "Ferreira":
                        store_col = st.selectbox("Store Number Column", df.columns.tolist())
            
            # Process button
            if st.button("Process Data"):
                with st.spinner("Processing data and updating Google Sheets..."):
                    # Create base dataframe
                    if process == "Certo Market Visits Report":
                        # Convert dates to string format before creating DataFrame
                        processed_df = pd.DataFrame({
                            'Name': df[name_col].apply(format_name),
                            'Email': df[email_col].str.lower(),
                            'Phone': df[phone_col],
                            'Registered Date': pd.to_datetime(df[reg_date_col]).dt.strftime('%Y-%m-%d'),
                            'First Order Date': pd.to_datetime(df[first_order_col]).dt.strftime('%Y-%m-%d'),
                            'Spent $': df[spent_col]
                        })
                    else:
                        processed_df = pd.DataFrame({
                            'Email': df[email_col].str.lower(),
                            'First Name': df[first_name_col].apply(format_name),
                            'Phone': df[phone_col]
                        })
                    
                    # Add store number for Ferreira
                    if process == "Ferreira":
                        processed_df['Store Number'] = df[store_col]
                    
                    # Setup Google Sheets connection
                    scope = ['https://spreadsheets.google.com/feeds',
                            'https://www.googleapis.com/auth/drive']
                    credentials_dict = {
                        "type": "service_account",
                        "project_id": "third-hangout-387516",
                        "private_key_id": st.secrets["private_key_id"],
                        "private_key": st.secrets["google_credentials"],
                        "client_email": "apollo-miner@third-hangout-387516.iam.gserviceaccount.com",
                        "client_id": "114223947184571105588",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/apollo-miner%40third-hangout-387516.iam.gserviceaccount.com",
                        "universe_domain": "googleapis.com"
                    }
                    
                    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
                    gc = gspread.authorize(credentials)
                    
                    # Use the specific spreadsheet key
                    spreadsheet_key = "1qWLg1vQHvJQG2hFHrUpO8y6bC8_xDdkLG2ErY_aGxkw"
                    workbook = gc.open_by_key(spreadsheet_key)
                    
                    # Select worksheet based on process
                    if process == "Certo Market":
                        worksheet_name = "Certo_Market"
                    elif process == "Ferreira":
                        worksheet_name = "Ferreira"
                    else:  # Certo Market Visits Report
                        worksheet_name = "Certo_Market_MKT_Report"
                    
                    worksheet = workbook.worksheet(worksheet_name)
                    
                    # Clear the worksheet if it's Certo Market Visits Report
                    if process == "Certo Market Visits Report":
                        worksheet.clear()
                        # Add headers
                        headers = ['Name', 'Email', 'Phone', 'Registered Date', 'First Order Date', 'Spent $']
                        worksheet.append_row(headers)
                    
                    # Save to Google Sheets
                    if save_to_gsheets(processed_df, worksheet):
                        st.success(f"✅ Data successfully processed and saved to {worksheet_name}!")
                        
                        # Display statistics
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total Records", len(processed_df))
                        with col2:
                            st.metric("Unique Emails", len(processed_df['Email'].unique()))
                    else:
                        st.error("❌ Failed to save data to Google Sheets.")
                
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")

if __name__ == "__main__":
    main() 
