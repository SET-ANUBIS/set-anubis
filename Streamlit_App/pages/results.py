import streamlit as st

def app():
    st.title("Simulation Results")

    if 'token' not in st.session_state or st.session_state.token is None:
        st.error("Please login first")
        return

    st.write("This is where the results of the simulation would be displayed.")
    st.write("You can use st.write(), st.table(), st.plotly_chart(), etc., to display the results.")

    if st.session_state.token:
        st.sidebar.success("You are logged in.")
