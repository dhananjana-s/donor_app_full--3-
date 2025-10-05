import streamlit as st
import json
from pathlib import Path
import hashlib
import binascii
import secrets

st.set_page_config(page_title="Sign Up - Donor Availability Predictor", page_icon="📝", layout="centered")

# Auth helpers
USERS_PATH = Path(__file__).resolve().parent.parent / "users.json"

def load_users():
    if USERS_PATH.exists():
        try:
            return json.loads(USERS_PATH.read_text())
        except Exception:
            return {}
    return {}

def save_users(users: dict):
    USERS_PATH.write_text(json.dumps(users, indent=2))

def _hash_password(password: str, salt: bytes = None) -> tuple:
    if salt is None:
        salt = secrets.token_bytes(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return binascii.hexlify(salt).decode(), binascii.hexlify(pwd_hash).decode()

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

# Main sign-up page
st.title("📝 Create Account")
st.markdown("Join us! Create your account to access the Donor Availability Predictor.")
st.markdown("---")

with st.form("signup_form"):
    st.markdown("### Account Information")
    username = st.text_input("Choose Username", placeholder="Enter a unique username")
    password = st.text_input("Choose Password", type="password", placeholder="Enter a secure password")
    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")
    
    # Add some basic validation info
    st.markdown("**Password Requirements:**")
    st.markdown("- At least 6 characters long")
    st.markdown("- Username must be unique")
    
    col1, col2 = st.columns(2)
    with col1:
        submit = st.form_submit_button("Create Account", type="primary", use_container_width=True)
    
    if submit:
        if not username or not password or not confirm_password:
            st.error("❌ Please fill in all fields")
        elif len(password) < 6:
            st.error("❌ Password must be at least 6 characters long")
        elif password != confirm_password:
            st.error("❌ Passwords do not match")
        elif len(username.strip()) < 3:
            st.error("❌ Username must be at least 3 characters long")
        else:
            if create_user(username, password):
                st.success("🎉 Account created successfully!")
                st.info("You can now sign in with your new account.")
            else:
                st.error("❌ Username already exists. Please choose a different username.")

st.markdown("---")
st.markdown("### Already have an account?")
if st.button("🔐 Sign In Instead", use_container_width=True):
    st.switch_page("pages/Sign_In.py")
