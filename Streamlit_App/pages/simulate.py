import streamlit as st
import requests

BASE_URL = "http://localhost:8000"

def app():
    st.title("Run Simulation")

    if 'token' not in st.session_state or st.session_state.token is None:
        st.error("Please login first")
        return

    step = st.number_input("Step number", min_value=1, max_value=10, value=1)

    if st.button("Run Step"):
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{BASE_URL}/simulate", params={"step": step}, headers=headers)
        if response.status_code == 200:
            st.success(f"Step {step} executed")
        else:
            st.error("Failed to run simulation step")

    if st.session_state.token:
        st.sidebar.success("You are logged in.")
