import json
from pathlib import Path

import pandas as pd
import numpy as np
import streamlit as st
import joblib

# PDF generation imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import io

st.set_page_config(page_title="Donor Availability Predictor", page_icon="🩸", layout="wide")

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "final_model.pkl"
METRICS_PATH = MODELS_DIR / "metrics.json"

@st.cache_resource
def load_model():
    if not MODEL_PATH.exists():
        st.error("Model file not found. Run the notebook to create models/final_model.pkl")
        st.stop()
    return joblib.load(MODEL_PATH)

@st.cache_data
def load_metrics():
    if METRICS_PATH.exists():
        return json.loads(METRICS_PATH.read_text())
    return {"model":"(unknown)","f1_macro":None,"roc_auc":None,"threshold":0.50}

model = load_model()
metrics = load_metrics()

# Simple local auth helpers (file-based). Not for production.
USERS_PATH = Path(__file__).resolve().parent / "users.json"

def load_users():
    if USERS_PATH.exists():
        try:
            return json.loads(USERS_PATH.read_text())
        except Exception:
            return {}
    return {}

def save_users(users: dict):
    USERS_PATH.write_text(json.dumps(users, indent=2))

import hashlib, binascii, secrets

def _hash_password(password: str, salt: bytes = None) -> tuple:
    if salt is None:
        salt = secrets.token_bytes(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return binascii.hexlify(salt).decode(), binascii.hexlify(pwd_hash).decode()

def verify_password(stored_salt_hex: str, stored_hash_hex: str, provided_password: str) -> bool:
    salt = binascii.unhexlify(stored_salt_hex.encode())
    _, new_hash = _hash_password(provided_password, salt)
    return secrets.compare_digest(new_hash, stored_hash_hex)

def create_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    if not username or not password:
        return False
    users = load_users()
    if username in users:
        return False
    salt_hex, hash_hex = _hash_password(password)
    users[username] = {"salt": salt_hex, "hash": hash_hex}
    save_users(users)
    return True

def generate_prediction_pdf(input_data: dict, prediction_result: dict, username: str) -> bytes:
    """Generate a PDF report with prediction inputs and outputs"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.darkblue,
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkred
    )
    
    # Title and header
    story.append(Paragraph("🩸 Donor Availability Prediction Report", title_style))
    story.append(Spacer(1, 20))
    
    # Report info
    report_info = [
        ['Report Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['User:', username],
        ['Prediction ID:', f"PRED-{datetime.now().strftime('%Y%m%d-%H%M%S')}"]
    ]
    
    info_table = Table(report_info, colWidths=[2*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 30))
    
    # Input Data Section
    story.append(Paragraph("📋 Input Data", heading_style))
    
    input_table_data = [['Field', 'Value']]
    for key, value in input_data.items():
        input_table_data.append([key, str(value)])
    
    input_table = Table(input_table_data, colWidths=[2.5*inch, 3*inch])
    input_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(input_table)
    story.append(Spacer(1, 30))
    
    # Prediction Results Section
    story.append(Paragraph("🎯 Prediction Results", heading_style))
    
    result_color = colors.green if prediction_result['decision'] == 'Available (Yes)' else colors.red
    
    result_table_data = [
        ['Metric', 'Value'],
        ['Availability Probability', f"{prediction_result['probability']:.2f}%"],
        ['Decision', prediction_result['decision']],
        ['Model Used', prediction_result['model']]
    ]
    
    result_table = Table(result_table_data, colWidths=[2.5*inch, 3*inch])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('TEXTCOLOR', (1, 2), (1, 2), result_color),  # Color the decision text
        ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold')  # Bold the decision
    ]))
    
    story.append(result_table)
    story.append(Spacer(1, 30))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    
    story.append(Spacer(1, 50))
    story.append(Paragraph("Generated by Donor Availability Predictor | Powered by Machine Learning", footer_style))
    story.append(Paragraph("This report is for informational purposes only.", footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None

# Check if user is logged in
if not st.session_state['logged_in']:
    st.title("🩸 Donor Availability Predictor")
    st.markdown("### 🔐 Authentication Required")
    st.info("Please sign in to access the Donor Availability Predictor.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔐 Sign In", use_container_width=True, type="primary"):
            st.switch_page("pages/Sign_In.py")
    with col2:
        if st.button("📝 Sign Up", use_container_width=True):
            st.switch_page("pages/Sign_Up.py")
    
    st.markdown("---")
    st.markdown("### About the App")
    st.markdown("This application predicts donor availability based on specifications using a Machine Learning model.")
    

    
    # Stop execution here if not logged in
    st.stop()

# User is logged in - show the main app
st.sidebar.header("🩸 Enter Donor Specifications")

# Main content area
st.title("🩸 Donor Availability Predictor")
st.markdown(f"Welcome back, **{st.session_state['username']}**! Predict donor availability using our ML model.")

# User info and sign out in top right
col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🚪 Sign Out"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.switch_page("pages/Sign_In.py")




st.markdown("---")

# Sidebar inputs (only shown when logged in)
with st.sidebar:
    st.markdown("### Donor Information")
    cities = ["", "Adelaide", "Brisbane", "Canberra", "Darwin", "Hobart", "Melbourne", "Perth", "Sydney", "Others"]
    city = st.selectbox("City", cities, index=0)
    blood_groups = ["", "A+", "A-", "AB+", "AB-", "B+", "B-", "O+", "O-"]
    blood_group = st.selectbox("Blood Group", blood_groups, index=0)
    
    st.markdown("### Donation History")
    months_since_first_donation = st.number_input("Months Since First Donation", min_value=0, step=1, value=0)
    number_of_donation = st.number_input("Number of Donations", min_value=0, step=1, value=0)
    pints_donated = st.number_input("Pints Donated", min_value=0, step=1, value=0)
    
    st.markdown("### Additional Info")
    created_at = st.date_input("Created Date", value=None)
    
    st.markdown("---")
    predict_button = st.button("Predict", type="primary", use_container_width=True)

# Main prediction area (only accessible when logged in)
if predict_button and st.session_state['logged_in']:
    # Handle date components for the model (simple version to match notebook)
    if created_at:
        created_at_ts = pd.Timestamp(created_at)
        created_at_month = int(created_at_ts.month)
        created_at_year = int(created_at_ts.year)
        created_at_day = int(created_at_ts.day)
    else:
        created_at_month = None
        created_at_year = None
        created_at_day = None

    # Map "Others" to "Unknown" for the model
    city_for_model = "Unknown" if city == "Others" else (city or None)

    X = pd.DataFrame([{
        "city": city_for_model,
        "blood_group": blood_group or None,
        "months_since_first_donation": months_since_first_donation if months_since_first_donation != "" else None,
        "number_of_donation": number_of_donation if number_of_donation != "" else None,
        "pints_donated": pints_donated if pints_donated != "" else None,
        "created_at_year": created_at_year,
        "created_at_month": created_at_month,
        "created_at_day": created_at_day
    }])
    
    try:
        proba = float(model.predict_proba(X)[:,1][0])
        
        # Display results in a nice format
        st.markdown("## 📊 Prediction Results")
        
        # Create columns for metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                label="Probability of 'Yes' (Available)", 
                value=f"{proba*100:.2f}%"
            )
        
        with col2:
            # Model predicts probability of "Yes" (Available)
            # Use the model's probability directly for Yes/No decision
            if proba >= 0.5:
                availability_text = "✅ Available (Yes)"
                availability_color = "green"
                decision_result = "Available (Yes)"
            else:
                availability_text = "❌ Not Available (No)"
                availability_color = "red"
                decision_result = "Not Available (No)"
            
            st.markdown(f"### Decision")
            st.markdown(f"<h3 style='color: {availability_color};'>{availability_text}</h3>", unsafe_allow_html=True)
        
        # Prepare data for PDF
        pdf_input_data = {
            "City": city_for_model or "Not specified",
            "Blood Group": blood_group or "Not specified", 
            "Months Since First Donation": months_since_first_donation,
            "Number of Donations": number_of_donation,
            "Pints Donated": pints_donated,
            "Created Date": created_at.strftime("%Y-%m-%d") if created_at else "Not specified"
        }
        
        pdf_prediction_result = {
            "probability": proba * 100,
            "decision": decision_result,
            "model": metrics.get('model', '(unknown)')
        }
        
        # Generate PDF download button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                pdf_data = generate_prediction_pdf(pdf_input_data, pdf_prediction_result, st.session_state['username'])
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_data,
                    file_name=f"donor_prediction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="secondary"
                )
            except Exception as pdf_error:
                st.error(f"PDF generation failed: {pdf_error}")
        
        # Additional info
        st.markdown("---")
        st.markdown("### Input Summary")
        input_data = {
            "City": city_for_model or "Not specified",
            "Blood Group": blood_group or "Not specified", 
            "Months Since First Donation": months_since_first_donation,
            "Number of Donations": number_of_donation,
            "Pints Donated": pints_donated,
            "Created Date": created_at.strftime("%Y-%m-%d") if created_at else "Not specified"
        }
        
        for key, value in input_data.items():
            st.write(f"**{key}:** {value}")
            
    except Exception as e:
        st.error(f"❌ Prediction failed: {e}")
        st.markdown("Please check your input values and try again.")

else:
    # Default display when no prediction made
    st.markdown("## 🎯 Ready to Predict")
    st.markdown("Enter donor specifications in the sidebar and click **Predict** to get availability prediction.")
    
    # Show sample data or instructions
    st.markdown("### How to use:")
    st.markdown("""
    1. **Enter donor information** in the sidebar
    2. **Click Predict** to get the availability probability
    3. **Review the results** including probability and confidence metrics
    """)