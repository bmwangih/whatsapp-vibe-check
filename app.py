import google.generativeai as genai
import streamlit as st

# 1. Setup API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. DEBUG: List all available models for your specific key
# This helps you see if you should use 'gemini-2.5-flash' or 'gemini-3.1-flash-lite'
st.write("### Available Models for your Key:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        st.code(f"Model ID: {m.name}")

# 3. Use the latest 2026 Stable Model
# Based on current documentation, 'gemini-2.5-flash' is the best for trials
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    # If the above fails, it will fall back to listing models for you
except Exception as e:
    st.error(f"Initialization Error: {e}")
