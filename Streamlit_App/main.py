import streamlit as st
from pages import login, simulate, results, br

# Page navigation
PAGES = {
    "Login": login,
    "Branching Ratio":br,
    "Simulate": simulate,
    "Results": results,
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", list(PAGES.keys()))

# Display the selected page
page = PAGES[selection]
page.app()
