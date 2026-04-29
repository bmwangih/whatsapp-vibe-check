import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIG ---
st.set_page_config(page_title="WhatsApp Intel AI", layout="wide", page_icon="📟")

# --- SECURE SETUP ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing Gemini API Key in Secrets!")

# 1. CACHING 
@st.cache_data(show_spinner=False, ttl=3600)
def get_ai_insight(text, prompt_type="summary"):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompts = {
            "summary": f"Summarize these messages in 3 bullets: {text}",
            "personality": f"Describe this sender's vibe in a witty way: {text}"
        }
        response = model.generate_content(prompts[prompt_type])
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# 2. PERMANENT LOGGING
def log_to_sheets(action, details=""):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        new_row = pd.DataFrame([{
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Action": action,
            "Details": str(details)
        }])
        existing = conn.read(ttl=0)
        updated = pd.concat([existing, new_row], ignore_index=True)
        conn.update(data=updated)
    except:
        pass 

def parse_whatsapp(file_contents):
    pattern = r'^(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2})\s-\s(.*?):\s(.*)'
    data = []
    lines = file_contents.split('\n')
    current_date, current_author, current_msg = None, None, ""
    for line in lines:
        match = re.match(pattern, line)
        if match:
            if current_author:
                data.append({"DateTime": current_date, "Author": current_author, "Message": current_msg})
            current_date, current_author, current_msg = match.groups()
        elif current_author:
            current_msg += " " + line.strip()
    if current_author:
        data.append({"DateTime": current_date, "Author": current_author, "Message": current_msg})
    return pd.DataFrame(data)

# --- UI ---
st.title("📟 WhatsApp Intelligence AI")

with st.sidebar:
    if st.button("🔄 HARD REFRESH APP"):
        st.cache_data.clear()
        st.rerun()
    st.info("⚠️ **System Status:** Using Free Tier.")
    st.markdown("---")
    sidebar_placeholder = st.empty()

uploaded_file = st.file_uploader("Upload Chat Export (.txt)", type="txt")

if uploaded_file:
    file_bytes = uploaded_file.getvalue().decode("utf-8")
    df = parse_whatsapp(file_bytes)
    
    log_to_sheets("File Upload", f"Analyzed chat with {len(df)} messages")
    
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Feed", "🤖 Summary", "🧠 Vibe Check", "📈 Live Stats"])

    authors = sorted(df['Author'].unique().tolist())
    sel_author = sidebar_placeholder.selectbox("Select Person", ["All Authors"] + authors)
    
    filtered = df.copy()
    if sel_author != "All Authors":
        filtered = filtered[filtered['Author'] == sel_author]

    with tab1:
        st.metric("Total Messages", len(filtered))
        for idx, row in filtered.tail(20).iterrows():
            with st.chat_message("user" if row['Author'] == sel_author else "assistant"):
                st.write(f"**{row['Author']}**: {row['Message']}")

    with tab2:
        if st.button("✨ Summarize Latest"):
            log_to_sheets("AI Summary", f"Author: {sel_author}")
            with st.spinner("Summarizing..."):
                # REDUCED TO 15 MESSAGES to avoid 429 Quota errors on large files
                chat_snippet = " ".join(filtered['Message'].tail(15).astype(str))
                st.info(get_ai_insight(chat_snippet, "summary"))

    with tab3:
        if sel_author != "All Authors":
            if st.button(f"🧠 Analyze {sel_author}"):
                log_to_sheets("Vibe Check", f"Target: {sel_author}")
                with st.spinner("Decoding vibe..."):
                    # REDUCED TO 20 MESSAGES for safety
                    vibe_snippet = " ".join(df[df['Author'] == sel_author]['Message'].tail(20).astype(str))
                    st.success(get_ai_insight(vibe_snippet, "personality"))
        else:
            st.info("Pick a person in the sidebar for a Vibe Check!")

    with tab4:
        st.subheader("Global Uptake Log")
        if st.button("📊 Update Table"):
            st.cache_data.clear()
            
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            activity_df = conn.read(ttl=0) 
            st.dataframe(activity_df.sort_values(by="Time", ascending=False), use_container_width=True)
        except Exception as e:
            st.error(f"Sheet Error: {e}")
