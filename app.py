import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
from datetime import datetime

# --- CONFIG & STYLING ---
st.set_page_config(page_title="WhatsApp Intel AI", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00FFAA; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; background-color: #1E2130; 
        border-radius: 10px; color: white; padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #00FFAA !important; color: #0E1117 !important; }
    </style>
""", unsafe_allow_html=True)

# --- SECURE AI SETUP ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key not found! Please set GEMINI_API_KEY in Streamlit Secrets.")

def get_ai_insight(text, prompt_type="summary"):
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        selected_model = "models/gemini-1.5-flash-latest" if "models/gemini-1.5-flash-latest" in available_models else available_models[0]
        model = genai.GenerativeModel(selected_model)
        
        prompts = {
            "summary": f"Summarize the main topics of these messages in 3 bullets: {text}",
            "personality": f"Describe this sender's vibe in a witty, youthful way based on these: {text}"
        }
        response = model.generate_content(prompts[prompt_type])
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

def log_activity(action, details=""):
    if "activity_log" not in st.session_state:
        st.session_state.activity_log = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.activity_log.append({"Time": timestamp, "Action": action, "Details": details})

def parse_whatsapp(file_contents):
    pattern = r'^(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2})\s-\s(.*?):\s(.*)'
    data = []
    lines = file_contents.split('\n')
    current_date, current_author, current_msg = None, None, ""

    for line in lines:
        match = re.match(pattern, line)
        if match:
            if current_author: data.append({"DateTime": current_date, "Author": current_author, "Message": current_msg})
            current_date, current_author, current_msg = match.groups()
        elif current_author:
            current_msg += " " + line.strip()
            
    if current_author: data.append({"DateTime": current_date, "Author": current_author, "Message": current_msg})
    return pd.DataFrame(data)

st.title("📟 WhatsApp Intelligence AI")

uploaded_file = st.file_uploader("Upload Chat Export (.txt)", type="txt")

if uploaded_file:
    df = parse_whatsapp(uploaded_file.getvalue().decode("utf-8"))
    log_activity("File Upload", f"{len(df)} messages processed")
    
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Feed", "🤖 Summary", "🧠 Vibe Check", "📈 Stats"])

    st.sidebar.header("Control Panel")
    authors = sorted(df['Author'].unique().tolist())
    sel_author = st.sidebar.selectbox("Select Person", ["All"] + authors)
    
    filtered = df.copy()
    if sel_author != "All": filtered = filtered[filtered['Author'] == sel_author]

    with tab1:
        st.metric("Total Messages", len(filtered))
        for idx, row in filtered.tail(30).iterrows():
            with st.chat_message("user" if row['Author'] == sel_author else "assistant"):
                st.write(f"**{row['Author']}**: {row['Message']}")

    with tab2:
        if st.button("✨ Summarize Latest"):
            log_activity("AI Summary", f"Author: {sel_author}")
            with st.spinner("Reading the room..."):
                st.info(get_ai_insight(" ".join(filtered['Message'].tail(30).astype(str))))

    with tab3:
        if sel_author != "All":
            if st.button(f"🧠 Analyze {sel_author}"):
                log_activity("Vibe Check", f"Target: {sel_author}")
                with st.spinner("Decoding personality..."):
                    st.success(get_ai_insight(" ".join(df[df['Author'] == sel_author]['Message'].tail(40).astype(str)), "personality"))
        else:
            st.info("Pick a person in the sidebar to run a Vibe Check!")

    with tab4:
        st.subheader("Uptake & Activity")
        if "activity_log" in st.session_state:
            st.table(pd.DataFrame(st.session_state.activity_log))
        else:
            st.write("No activity recorded yet.")
