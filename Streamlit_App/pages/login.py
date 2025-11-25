import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"

def app():
    st.title("Login")

    if 'token' not in st.session_state:
        st.session_state.token = None

    if st.session_state.token is None:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            response = requests.post(f"{BASE_URL}/token", data={"username": username, "password": password})
            if response.status_code == 200:
                st.session_state.token = response.json().get("access_token")
                st.success("Login successful")
            else:
                st.error("Login failed")
    else:
        st.success("Already logged in")

    if st.session_state.token:
        st.sidebar.success("You are logged in.")

