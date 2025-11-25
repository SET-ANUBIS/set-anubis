import streamlit as st
import requests
import plotly.express as px
import pandas as pd
import numpy as np

BASE_URL = "http://127.0.0.1:8000"

def app():
    st.title("Branching Ratio Calculation")

    if 'token' not in st.session_state or st.session_state.token is None:
        st.error("Please login first")
        return

    st.write("Adjust the parameters and view the results of the simulation.")

    if st.session_state.token:
        st.sidebar.success("You are logged in.")

    x_min = st.sidebar.slider('x_min', 0.01, 100., 0.1)
    x_max = st.sidebar.slider('x_max', 0.01, 100., 50.)
    y_min = st.sidebar.slider('y_min', 0.01, 100., 0.1)
    y_max = st.sidebar.slider('y_max', 0.01, 100., 50.)
    step = st.sidebar.number_input('Step', value=1.0, step=0.1)

    scale_option = st.sidebar.selectbox('Scale', ['Linear', 'Logarithmic'])

    if scale_option == 'Logarithmic':
        x_vals = list(np.logspace(np.log10(x_min), np.log10(x_max), num=step))
    else:
        x_vals = list(np.arange(x_min, x_max + step, step))

    particles_options = [[14, -14, 14], [11, -11, 12],[11,-11,14], [11,-11,16], [22, 23, 24], [12,12,-12], [13, -11,12], [11,-13,14], [111,12], [111,14], [111,16],
                        [211, 11], [13,-13, 12], [13,-13, 14], [13,-13, 16], [211, 13], [221, 12], [221, 14], [221, 16], [113, 12], [113, 14], [113, 16], [213, 11],
                        [223, 12], [223, 14], [223, 16], [213, 13], [331, 12], [331,14], [331, 16], [333, 12], [333,14], [333, 16], [11, -15, 16], [15, -11, 12],
                        [13,-15,16], [15,-13, 14], [431, 11], [431, 13], [433, 11], [433, 13], [441, 12], [441, 14], [441, 16]]
    selected_particles = st.sidebar.multiselect('Select Channels', options=particles_options, format_func=lambda x: f"Channel {x}")
    
    V1 = st.sidebar.number_input('V1', value=1.0, step=0.1)
    V2 = st.sidebar.number_input('V2', value=1.0, step=0.1)
    V3 = st.sidebar.number_input('V3', value=1.0, step=0.1)

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    config = {
        "x_min": x_min,
        "y_min": y_min,
        "x_max": x_max,
        "y_max": y_max,
        "step": step,
        "x_vals": x_vals,
        "calculation_type": "BR",
        "particles": selected_particles,
        "model": "HNL",
        "params": {"Ve": V1, "Vmu": V2, "Vta": V3},
        "masses": {"N1": 1}
    }

    if st.button("Run Simulation"):
        try:
            response = requests.post(f"{BASE_URL}/br/init", json=config, headers=headers)
            response.raise_for_status()
            st.success("BR API initialized successfully")
            
            response = requests.get(f"{BASE_URL}/br/get_y_vals", headers=headers)
            response.raise_for_status()
            
            try:
                y_vals = response.json().get('y_vals', {})
                if y_vals:
                    data = []
                    for channel, values in y_vals.items():
                        for x, y in zip(x_vals, values):
                            data.append({"x": x, "y": y, "channel": str(channel)})
                    df = pd.DataFrame(data)

                    fig = px.line(df, x="x", y="y", color="channel", title="Branching Ratios",
                                  labels={"x": "X-axis", "y": "Y-axis", "channel": "Channel"},
                                  template="plotly_dark")
                    
                    if scale_option == 'Logarithmic':
                        fig.update_xaxes(type="log")
                        fig.update_yaxes(type="log")

                    fig.update_layout(
                        xaxis_title="particle mass [GeV]",
                        yaxis_title="Branching Ratios",
                        legend_title="Channels",
                        font=dict(size=18),
                        margin=dict(l=0, r=0, t=50, b=0),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("No data available for the selected parameters.")
            except ValueError:
                st.error("Error decoding JSON response.")
        except requests.exceptions.ConnectionError:
            st.error("Failed to connect to the BR API server. Please ensure the server is running.")
        except requests.exceptions.HTTPError as http_err:
            try:
                st.error(f"HTTP error occurred: {http_err.response.json()}")
            except ValueError:
                st.error(f"HTTP error occurred: {http_err.response.text}")
        except Exception as err:
            st.error(f"An error occurred: {err}")

if __name__ == "__main__":
    app()
