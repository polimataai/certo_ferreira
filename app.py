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
    """Save dataframe to Google Sheets."""
    try:
        # Clear existing content
        worksheet.clear()
        
        # Replace NaN values with empty strings
        df_clean = df.fillna('')
        
        # Update with new content
        worksheet.update([df_clean.columns.values.tolist()] + df_clean.values.tolist())
        return True
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {str(e)}")
        return False

def main():
    if not check_password():
        st.error("⚠️ Password incorrect. Please try again.")
        return

    # Header
    st.title("🌾 Harvesting Media")
    st.subheader("Data Processor")
    
    # Process selection
    process = st.selectbox(
        "Select Process",
        ["Certo Market", "Ferreira"],
        help="Choose which process to run"
    )
    
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
            
            col1, col2 = st.columns(2)
            
            with col1:
                email_col = st.selectbox("Email Column", df.columns.tolist())
                first_name_col = st.selectbox("First Name Column", df.columns.tolist())
            
            with col2:
                phone_col = st.selectbox("Phone Column", df.columns.tolist())
            
            # Process button
            if st.button("Process Data"):
                with st.spinner("Processing data and updating Google Sheets..."):
                    # Create a new dataframe with the mapped columns
                    processed_df = pd.DataFrame({
                        'Email': df[email_col],
                        'First Name': df[first_name_col],
                        'Phone': df[phone_col]
                    })
                    
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
                    worksheet_name = "Certo_Market" if process == "Certo Market" else "Ferreira"
                    worksheet = workbook.worksheet(worksheet_name)
                    
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
