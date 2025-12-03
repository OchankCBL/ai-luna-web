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

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="Luna Professional AI", page_icon="✨", layout="wide")

# --- CSS KUSTOM UNTUK TAMPILAN PROFESIONAL ---
st.markdown("""
<style>
    /* Import Font Modern (Inter) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Menghilangkan Header/Footer Streamlit bawaan */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Styling Kotak Chat */
    .stChatMessage {
        background-color: #1E1E2E; /* Warna latar bubble */
        border: 1px solid #2B2B40; /* Garis pinggir halus */
        border-radius: 15px; /* Sudut membulat */
        padding: 15px; /* Jarak dalam */
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); /* Bayangan tipis */
        margin-bottom: 15px; /* Jarak antar pesan */
    }
    
    /* Khusus pesan User (sedikit lebih terang) */
    div[data-testid="stChatMessage"][data-author="user"] {
         background-color: #252542;
    }

    /* Styling Sidebar */
    [data-testid="stSidebar"] {
        background-color: #121212;
        border-right: 1px solid #2B2B40;
    }

    /* Judul Aplikasi Kustom */
    .custom-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #6C63FF, #4CAF50);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .custom-subtitle {
        font-size: 1rem;
        color: #888;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Setup Koneksi Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Error Koneksi: Cek file secrets.toml Anda!")
    st.stop()

# Ambil API Key Gemini
try:
    API_KEY = st.secrets["API_KEY"]
except:
    API_KEY = "PASTE_KODE_API_KEY_DISINI" 

# --- 2. FUNGSI DATABASE (MEMORI) ---
# (Tidak ada perubahan di fungsi ini)
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
    except Exception as e: st.warning(f"Gagal menyimpan ke memori: {e}")

# --- 3. SIAPKAN OTAK LUNA ---
df_memori = ambil_ingatan()
konteks_lama = ""
if not df_memori.empty:
    for index, row in df_memori.tail(5).iterrows():
        konteks_lama += f"{row['Role']}: {row['Pesan']}\n"

PERSONAS = {
    "Luna (Teman Santai)": "Kamu Luna. Pakai bahasa gaul (lu/gw), emoji, santai.",
    "Asisten Eksekutif": "Anda asisten profesional. Bahasa baku, ringkas, fokus solusi.",
    "Konsultan Ahli": "Anda ahli strategi. Berikan analisis mendalam dan saran taktis.",
}

# --- 4. FUNGSI PENDUKUNG ---
# (Tidak ada perubahan signifikan di fungsi ini)
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

# --- 5. TAMPILAN SIDEBAR (PROFESIONAL) ---
with st.sidebar:
    # Ganti Title Biasa dengan Logo/Gambar Profesional
    st.image("https://cdn-icons-png.flaticon.com/512/9963/9963389.png", width=80) # Ikon Bot Keren
    st.markdown("### **Control Center**")
    
    selected_persona = st.selectbox("Mode Operasi:", list(PERSONAS.keys()))
    
    instruksi_final = f"""{PERSONAS[selected_persona]} INI ADALAH KONTEKS INGATAN LAMA: {konteks_lama}"""
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=instruksi_final)
    except: st.error("Cek API Key!")

    st.divider()
    st.markdown("**Input Multimodal**")
    tab1, tab2, tab3 = st.tabs(["🎤 Suara", "🖼️ Visual", "📄 Dokumen"])
    audio_prompt, image_data, pdf_text = None, None, ""
    
    with tab1:
        audio_input = mic_recorder(start_prompt="Mulai Bicara", stop_prompt="Stop", key='recorder', format="wav")
        if audio_input and ("last_id" not in st.session_state or st.session_state.last_id != audio_input['id']):
            st.session_state.last_id = audio_input['id']
            audio_prompt = transkrip_suara(audio_input['bytes'])
    with tab2:
        if up_img := st.file_uploader("Upload Gambar", type=["jpg", "png"], label_visibility="collapsed"):
            image_data = Image.open(up_img)
            st.image(image_data, use_column_width=True)
    with tab3:
        if up_pdf := st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed"):
            pdf_text = baca_pdf(up_pdf)
            st.success("✅ Dokumen dimuat")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        mode_suara = st.toggle("Respon Audio", value=False)
    with col_b:
        if st.button("Reset Sesi"):
            st.session_state.messages = []
            st.rerun()
            
    # Tombol download ditaruh di bawah
    st.divider()
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
         chat_log = ""
         for msg in st.session_state.messages:
             if msg["type"] == "text": chat_log += f"[{msg['role'].upper()}]: {msg['content']}\n\n"
         st.download_button(label="📥 Export Chat Log", data=chat_log, file_name="luna_log.txt", mime="text/plain", use_container_width=True)

# --- 6. LOGIKA CHAT UTAMA ---

# Header Kustom yang Lebih Keren
col_header1, col_header2 = st.columns([1, 7])
with col_header1:
    # Ikon dinamis berdasarkan persona
    ikon_persona = "✨"
    if "Asisten" in selected_persona: ikon_persona = "💼"
    elif "Konsultan" in selected_persona: ikon_persona = "🧠"
    st.write(f"# {ikon_persona}")
with col_header2:
    st.markdown(f'<div class="custom-title">{selected_persona}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="custom-subtitle">Powered by Gemini Pro & Google Cloud Database</div>', unsafe_allow_html=True)


if "messages" not in st.session_state: st.session_state.messages = []

# Tampilkan Chat dengan Avatar Profesional
# Kita pakai URL gambar untuk avatar agar lebih rapi daripada emoji
bot_avatar = "https://cdn-icons-png.flaticon.com/512/4712/4712109.png"
user_avatar = "https://cdn-icons-png.flaticon.com/512/1144/1144760.png"

for msg in st.session_state.messages:
    avatar_ikon = user_avatar if msg["role"] == "user" else bot_avatar
    with st.chat_message(msg["role"], avatar=avatar_ikon):
        if msg.get("type") == "image_input": st.image(msg["content"], width=250, caption="Input Visual")
        elif msg.get("type") == "image_output": st.image(msg["content"], caption="Generated Result")
        else: st.markdown(msg["content"])

# --- 7. PROSES & SIMPAN ---
final_prompt = audio_prompt if audio_prompt else st.chat_input("Ketik perintah Anda di sini...")

if final_prompt:
    with st.chat_message("user", avatar=user_avatar):
        st.markdown(final_prompt)
        if image_data: st.image(image_data, width=250, caption="Input Visual")
        if pdf_text: st.info("📄 Menggunakan konteks dokumen PDF")
    
    st.session_state.messages.append({"role": "user", "content": final_prompt, "type": "text"})
    if image_data: st.session_state.messages.append({"role": "user", "content": image_data, "type": "image_input"})
    simpan_ingatan("User", final_prompt)

    with st.chat_message("assistant", avatar=bot_avatar):
        placeholder = st.empty()
        # Tampilan loading yang lebih profesional
        placeholder.markdown("""
            <div style="display: flex; align-items: center;">
                <img src="https://i.gifer.com/VAyR.gif" width="30" style="margin-right: 10px;">
                <span style="color: #888;">Sedang memproses permintaan...</span>
            </div>
            """, unsafe_allow_html=True)
        
        try:
            if any(k in final_prompt.lower() for k in ["gambarkan", "lukiskan", "buat gambar"]) and not image_data:
                chat_img = model.start_chat()
                p_en = chat_img.send_message(f"Create a detailed English prompt for an image generator based on: {final_prompt}").text
                url = generate_image_url(p_en)
                placeholder.empty()
                st.image(url, caption=f"Result for: {final_prompt}")
                st.session_state.messages.append({"role": "assistant", "content": url, "type": "image_output"})
                simpan_ingatan("Luna", f"[Generated Image: {final_prompt}]")
            
            else:
                input_content = [final_prompt]
                if image_data: input_content.append(image_data)
                if pdf_text: input_content[0] = f"CONTEXT FROM PDF DOCUMENT:\n{pdf_text[:30000]}\n\nUSER QUERY: {final_prompt}"
                elif ("cari" in final_prompt.lower() or "info" in final_prompt.lower()) and not pdf_text:
                    hasil = cari_internet(final_prompt)
                    input_content[0] = final_prompt + f"\n(Search Result Context: {hasil})"

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