import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
import time
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIG ---
st.set_page_config(page_title="WhatsApp Intel AI", layout="wide", page_icon="📟")

# --- SECURE SETUP ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing Gemini API Key in Secrets!")

# 1. VISITOR GEOLOCATION (Country Only)
def get_visitor_country():
    try:
        response = requests.get('http://ip-api.com/json/', timeout=2)
        return response.json().get('country', 'Unknown')
    except:
        return "Unknown"

# 2. PRIVATE LOGGING
def log_to_sheets(action):
    try:
        country = get_visitor_country()
        conn = st.connection("gsheets", type=GSheetsConnection)
        new_row = pd.DataFrame([{
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Action": action,
            "Location": country
        }])
        existing = conn.read(ttl=0)
        updated = pd.concat([existing, new_row], ignore_index=True)
        conn.update(data=updated)
    except:
        pass 

# 3. AI LOGIC (Updated to 20 messages)
@st.cache_data(show_spinner=False, ttl=3600)
def get_ai_insight(text, prompt_type="summary"):
    try:
        # Using the model ID confirmed in your previous logs
        model = genai.GenerativeModel("gemini-2.5-flash") 
        prompts = {
            "summary": f"Summarize these messages in 3-5 clear bullets: {text}",
            "personality": f"Analyze the tone and personality of this sender: {text}"
        }
        time.sleep(1) 
        response = model.generate_content(prompts[prompt_type])
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ System Busy (Quota Limit). Please wait 30 seconds and try again."
        return f"AI Error: {e}"

def parse_whatsapp(file_contents):
    pattern = r'^(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2})\s-\s(.*?):\s(.*)'
    data = []
    lines = file_contents.split('\n')
    current_author = None
    for line in lines:
        match = re.match(pattern, line)
        if match:
            current_date, current_author, current_msg = match.groups()
            data.append({"DateTime": current_date, "Author": current_author, "Message": current_msg})
        elif current_author:
            data[-1]["Message"] += " " + line.strip()
    return pd.DataFrame(data)

# --- UI LOGIC ---
st.title("📟 WhatsApp Intelligence AI")

with st.sidebar:
    st.header("Settings")
    if st.button("🔄 Clear Cache"):
        st.cache_data.clear()
        st.rerun()
    st.info("Analyzing latest 20 messages for accuracy.")
    sidebar_placeholder = st.empty()
    st.markdown("---")
    # Admin input
    admin_key = st.text_input("Admin Access", type="password", help="Enter password to view logs")

uploaded_file = st.file_uploader("Upload Chat Export (.txt)", type="txt")

if uploaded_file:
    file_bytes = uploaded_file.getvalue().decode("utf-8")
    df = parse_whatsapp(file_bytes)
    
    log_to_sheets("File Uploaded")
    
    tab1, tab2, tab3 = st.tabs(["💬 Chat Feed", "🤖 AI Summary", "🧠 Personality Check"])

    authors = sorted(df['Author'].unique().tolist())
    sel_author = sidebar_placeholder.selectbox("Select Person", ["Group Conversation"] + authors)
    
    filtered = df.copy()
    if sel_author != "Group Conversation":
        filtered = filtered[filtered['Author'] == sel_author]

    with tab1:
        st.metric("Messages Found", len(filtered))
        for idx, row in filtered.tail(20).iterrows():
            with st.chat_message("user" if row['Author'] == sel_author else "assistant"):
                st.write(f"**{row['Author']}**: {row['Message']}")

    with tab2:
        if st.button("Generate Summary"):
            log_to_sheets("AI Summary Requested")
            with st.spinner("Analyzing 20 messages..."):
                chat_snippet = " ".join(filtered['Message'].tail(20).astype(str))
                st.markdown(get_ai_insight(chat_snippet, "summary"))

    with tab3:
        if sel_author != "Group Conversation":
            if st.button(f"Analyze {sel_author}"):
                log_to_sheets("Personality Check Requested")
                with st.spinner("Decoding vibe..."):
                    vibe_snippet = " ".join(df[df['Author'] == sel_author]['Message'].tail(20).astype(str))
                    st.success(get_ai_insight(vibe_snippet, "personality"))
        else:
            st.warning("Please select a specific person for Personality Check.")

# --- SECURE ADMIN VIEW ---
# This checks the password against your Streamlit Secrets
if "ADMIN_PASSWORD" in st.secrets and admin_key == st.secrets["ADMIN_PASSWORD"]:
    st.markdown("---")
    st.subheader("🛡️ Internal Usage Log (Admin Only)")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        activity_df = conn.read(ttl=0) 
        st.dataframe(activity_df.sort_values(by="Time", ascending=False), use_container_width=True)
    except Exception as e:
        st.error(f"Log Error: {e}")
