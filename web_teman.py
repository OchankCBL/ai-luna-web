import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import google.generativeai as genai
from duckduckgo_search import DDGS
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
import io
import PyPDF2
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN & CSS ---
st.set_page_config(page_title="Luna AI Professional", page_icon="✨", layout="wide")

# CSS Kustom untuk Tampilan Premium
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    header, #MainMenu, footer {visibility: hidden;}
    
    .stChatMessage {
        background-color: #1E1E2E;
        border: 1px solid #2B2B40;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    div[data-testid="stChatMessage"][data-author="user"] {background-color: #252542;}
    
    [data-testid="stSidebar"] {background-color: #121212; border-right: 1px solid #2B2B40;}
    
    .custom-title {
        font-size: 2.2rem; font-weight: 700;
        background: -webkit-linear-gradient(45deg, #6C63FF, #00C9FF);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .custom-subtitle {font-size: 0.9rem; color: #888; margin-bottom: 2rem;}
</style>
""", unsafe_allow_html=True)

# --- 2. SETUP KONEKSI (DATABASE & API) ---

# Cek Koneksi Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("⚠️ Error Database: Pastikan 'secrets.toml' sudah diisi dengan benar.")
    st.stop()

# Cek API Key Gemini
try:
    API_KEY = st.secrets["API_KEY"]
except:
    # Fallback untuk mode lokal tanpa secrets
    API_KEY = "PASTE_API_KEY_DISINI_JIKA_LOKAL"

# --- 3. FUNGSI DATABASE (MEMORI) ---

def ambil_ingatan():
    try:
        df = conn.read()
        if df.empty or len(df.columns) == 0: return pd.DataFrame(columns=["Waktu", "Role", "Pesan"])
        return df
    except: return pd.DataFrame(columns=["Waktu", "Role", "Pesan"])

def simpan_ingatan(role, pesan):
    try:
        df_lama = ambil_ingatan()
        data_baru = pd.DataFrame([{"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Role": role, "Pesan": pesan}])
        df_update = pd.concat([df_lama, data_baru], ignore_index=True)
        conn.update(data=df_update)
    except: pass

# --- 4. DATA KEPRIBADIAN (LEVEL 10) ---

PERSONAS = {
    "✨ Luna (Bestie Jaksel)": """
        ROLE: Teman wanita muda Jaksel.
        GAYA: Campur Indo-Inggris (Literally, Which is, Honestly).
        TONE: Seru, lebay, supportive, banyak emoji.
        ATURAN: Panggil user "Bestie". Validasi perasaan user. Jangan formal.
    """,
    "👔 CEO Perfeksionis": """
        ROLE: CEO Teknologi yang sibuk dan dingin.
        GAYA: Singkat, padat, pedas, to the point.
        TONE: Arogan, berorientasi hasil.
        ATURAN: Hapus basa-basi. Kritik jika pertanyaan bodoh. Panggil "Karyawan".
    """,
    "📜 Profesor Sastra": """
        ROLE: Sastrawan tua bijaksana.
        GAYA: Puitis, baku, metaforis, ejaan lama.
        TONE: Tenang, filosofis.
        ATURAN: Gunakan kata indah (senja, niscaya). Berikan nasihat hidup.
    """,
    "👾 Hacker Toxic": """
        ROLE: Hacker jenius yang sarkas.
        GAYA: Bahasa internet, lowercase, roasting.
        TONE: Meremehkan tapi membantu.
        ATURAN: Panggil "Noob". Ejek user sebelum menjawab.
    """,
    "🔮 Madam Mistik": """
        ROLE: Peramal Tarot Misterius.
        GAYA: Penuh teka-teki, zodiak, energi semesta.
        ATURAN: Hubungkan jawaban dengan takdir/bintang. Panggil "Jiwa Tersesat".
    """
}

# --- 5. FUNGSI PENDUKUNG (TOOLS) ---

def cari_internet(query):
    try:
        ddgs = DDGS()
        results = ddgs.text(query, max_results=1)
        return results[0]['body'] if results else "Nihil."
    except: return "Gagal browsing."

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='id')
        filename = "suara_luna.mp3"
        tts.save(filename)
        return filename
    except: return None

def generate_image_url(prompt):
    prompt_bersih = prompt.replace(" ", "%20")
    return f"https://image.pollinations.ai/prompt/{prompt_bersih}?nologo=true"

def transkrip_suara(audio_bytes):
    r = sr.Recognizer()
    try:
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            return r.recognize_google(audio_data, language="id-ID")
    except: return None

def baca_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages: text += page.extract_text()
        return text
    except: return None

# --- 6. SIDEBAR (CONTROLLER) ---

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9963/9963389.png", width=70)
    st.markdown("### **Control Center**")
    
    # 1. Pilih Persona
    selected_persona = st.selectbox("Identity Module:", list(PERSONAS.keys()))
    
    # 2. Setup Otak & Memori
    df_memori = ambil_ingatan()
    konteks_lama = ""
    if not df_memori.empty:
        for index, row in df_memori.tail(5).iterrows(): # Ambil 5 chat terakhir
            konteks_lama += f"{row['Role']}: {row['Pesan']}\n"
            
    instruksi_final = f"""
    {PERSONAS[selected_persona]}
    
    [SYSTEM MEMORY START]
    Gunakan konteks percakapan masa lalu ini jika relevan:
    {konteks_lama}
    [SYSTEM MEMORY END]
    """
    
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=instruksi_final)
    except: st.error("API Key Bermasalah.")

    st.divider()
    
    # 3. Input Multimodal Tabs
    tab1, tab2, tab3 = st.tabs(["🎤 Bicara", "👁️ Lihat", "📄 Baca"])
    
    audio_prompt, image_data, pdf_text = None, None, ""
    
    with tab1:
        audio_input = mic_recorder(start_prompt="🔴 Rekam", stop_prompt="⏹️ Stop", key='recorder', format="wav")
        if audio_input and ("last_id" not in st.session_state or st.session_state.last_id != audio_input['id']):
            st.session_state.last_id = audio_input['id']
            audio_prompt = transkrip_suara(audio_input['bytes'])
            
    with tab2:
        if up_img := st.file_uploader("Upload", type=["jpg", "png"], label_visibility="collapsed"):
            image_data = Image.open(up_img)
            st.image(image_data, use_column_width=True)
            
    with tab3:
        if up_pdf := st.file_uploader("Upload", type=["pdf"], label_visibility="collapsed"):
            pdf_text = baca_pdf(up_pdf)
            st.success("PDF Terbaca")

    st.divider()
    col1, col2 = st.columns(2)
    with col1: mode_suara = st.toggle("Audio Respon", value=False)
    with col2: 
        if st.button("Reset"):
            st.session_state.messages = []
            st.rerun()

    # 4. Download Chat Log
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
        chat_log = ""
        for msg in st.session_state.messages:
             if msg["type"] == "text": chat_log += f"[{msg['role']}]: {msg['content']}\n"
        st.download_button("📥 Save Chat", data=chat_log, file_name="luna_chat.txt", use_container_width=True)

# --- 7. TAMPILAN UTAMA (CHAT) ---

# Tentukan Avatar Berdasarkan Persona
user_avatar = "https://cdn-icons-png.flaticon.com/512/1144/1144760.png"
if "Jaksel" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/4140/4140047.png"
elif "CEO" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
elif "Profesor" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/3304/3304567.png"
elif "Hacker" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/2040/2040946.png"
elif "Madam" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/3656/3656988.png"
else: bot_avatar = "https://cdn-icons-png.flaticon.com/512/4712/4712109.png"

# Header Dinamis
col_h1, col_h2 = st.columns([1, 8])
with col_h1: st.image(bot_avatar, width=60)
with col_h2:
    st.markdown(f'<div class="custom-title">{selected_persona}</div>', unsafe_allow_html=True)
    st.markdown('<div class="custom-subtitle">Powered by Gemini 2.5 • Google Cloud Memory • Vision AI</div>', unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []

# Loop Chat History
for msg in st.session_state.messages:
    ikon = user_avatar if msg["role"] == "user" else bot_avatar
    with st.chat_message(msg["role"], avatar=ikon):
        if msg.get("type") == "image_input": st.image(msg["content"], width=250, caption="Visual Input")
        elif msg.get("type") == "image_output": st.image(msg["content"], caption="Generated by AI")
        else: st.markdown(msg["content"])

# --- 8. PROSES INPUT & OUTPUT ---

final_prompt = audio_prompt if audio_prompt else st.chat_input("Ketik pesan...")

if final_prompt:
    # A. USER SECTION
    with st.chat_message("user", avatar=user_avatar):
        st.markdown(final_prompt)
        if image_data: st.image(image_data, width=250)
        if pdf_text: st.info("📄 Mengirim konteks PDF")
    
    st.session_state.messages.append({"role": "user", "content": final_prompt, "type": "text"})
    if image_data: st.session_state.messages.append({"role": "user", "content": image_data, "type": "image_input"})
    simpan_ingatan("User", final_prompt)

    # B. AI SECTION
    with st.chat_message("assistant", avatar=bot_avatar):
        placeholder = st.empty()
        placeholder.markdown("⏳ *Sedang memproses...*")
        
        try:
            # 1. Image Generation
            if any(k in final_prompt.lower() for k in ["gambarkan", "lukiskan", "buat gambar"]) and not image_data:
                chat_img = model.start_chat()
                p_en = chat_img.send_message(f"Create English prompt for image gen: {final_prompt}").text
                url = generate_image_url(p_en)
                placeholder.empty()
                st.image(url, caption=f"Result: {final_prompt}")
                st.session_state.messages.append({"role": "assistant", "content": url, "type": "image_output"})
                simpan_ingatan("Luna", f"[Generated Image: {final_prompt}]")
            
            # 2. Vision / PDF / Text Chat
            else:
                input_content = [final_prompt]
                if image_data: input_content.append(image_data)
                if pdf_text: input_content[0] = f"PDF CONTEXT:\n{pdf_text[:30000]}\n\nUSER QUERY: {final_prompt}"
                elif ("cari" in final_prompt.lower() or "info" in final_prompt.lower()) and not pdf_text:
                    hasil = cari_internet(final_prompt)
                    input_content[0] = final_prompt + f"\n(Search Result: {hasil})"

                response = model.generate_content(input_content)
                reply = response.text
                
                placeholder.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply, "type": "text"})
                simpan_ingatan("Luna", reply)
                
                if mode_suara:
                    audio = text_to_speech(reply)
                    if audio: st.audio(audio)

        except Exception as e:
            placeholder.error(f"System Error: {e}")
