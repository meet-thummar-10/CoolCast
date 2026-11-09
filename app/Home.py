
import streamlit as st

st.set_page_config(
    page_title="CoolCast",
    page_icon="❄️",
    layout="wide"
)

st.title("❄️ CoolCast")
st.subheader("Green AI for Data-Centre Energy Efficiency")

st.write(
    """
    CoolCast analyses data-centre power and weather data,
    forecasts cooling energy using machine learning, and
    measures the energy consumed by each model.
    """
)

st.divider()

st.header("Understanding CoolCast")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📊 Measured")
    st.write("Actual power consumption and weather readings.")

with col2:
    st.subheader("🤖 Modelled")
    st.write("Forecasted energy and cooling requirements.")

with col3:
    st.subheader("🌱 Green AI")
    st.write("Understand the energy impact of AI models.")

st.divider()

st.info("Use the sidebar to explore CoolCast features.")
