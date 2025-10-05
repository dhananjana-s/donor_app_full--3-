import streamlit as st
import json
from pathlib import Path
import hashlib
import binascii
import secrets

st.set_page_config(page_title="Sign In - Donor Availability Predictor", page_icon="🔐", layout="centered")

# Auth helpers
USERS_PATH = Path(__file__).resolve().parent.parent / "users.json"

def load_users():
    if USERS_PATH.exists():
        try:
            return json.loads(USERS_PATH.read_text())
        except Exception:
            return {}
    return {}

def verify_password(stored_salt_hex: str, stored_hash_hex: str, provided_password: str) -> bool:
    salt = binascii.unhexlify(stored_salt_hex.encode())
    pwd_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100_000)
    new_hash = binascii.hexlify(pwd_hash).decode()
    return secrets.compare_digest(new_hash, stored_hash_hex)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None

# Main sign-in page
st.title("🔐 Sign In")
st.markdown("Welcome back! Please sign in to access the Donor Availability Predictor.")
st.markdown("---")

if not st.session_state['logged_in']:
    with st.form("signin_form"):
        st.markdown("### Enter your credentials")
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)
        
        if submit:
            if username and password:
                users = load_users()
                username_lower = username.strip().lower()
                
                if username_lower in users:
                    user_data = users[username_lower]
                    if verify_password(user_data['salt'], user_data['hash'], password):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = username_lower
                        st.success("Successfully signed in!")
                        st.info("Redirecting to the main app...")
                        # Redirect to main page
                        st.switch_page("app.py")
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.error("❌ Invalid username or password")
            else:
                st.error("❌ Please enter both username and password")
    
    st.markdown("---")
    st.markdown("### Don't have an account?")
    if st.button("📝 Create New Account", use_container_width=True):
        st.switch_page("pages/Sign_Up.py")

else:
    st.success(f"You are already signed in as **{st.session_state['username']}**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Go to Main App", use_container_width=True):
            st.switch_page("app.py")
    with col2:
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.info("You have been signed out")
