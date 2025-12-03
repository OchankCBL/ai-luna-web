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

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Luna AI Professional", page_icon="✨", layout="wide")

# CSS Kustom (Saya hapus bagian yang menyembunyikan Header agar Menu Hamburger tetap muncul)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    
    /* Hapus baris yang menyembunyikan header/footer agar lebih aman */
    /* header, #MainMenu, footer {visibility: hidden;} */ 
    
    .stChatMessage {
        background-color: #1E1E2E;
        border: 1px solid #2B2B40;
        border-radius: 12px;
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

# --- 2. SETUP API KEY (PRIORITAS UTAMA) ---
try:
    API_KEY = st.secrets["API_KEY"]
except:
    # GANTI INI JIKA DI LOKAL DAN BELUM ADA SECRETS
    API_KEY = "PASTE_API_KEY_GEMINI_DISINI" 

# --- 3. SETUP DATABASE (MODE AMAN) ---
# Kita buat database jadi opsional. Jika gagal, aplikasi TIDAK AKAN STOP.
conn = None
database_aktif = False

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Coba baca sedikit untuk ngetes
    test_read = conn.read()
    database_aktif = True
except:
    database_aktif = False
    # Kita tidak pakai st.stop() agar sidebar tetap muncul

# --- 4. FUNGSI MEMORI (SAFE MODE) ---

def ambil_ingatan():
    if not database_aktif:
        return pd.DataFrame(columns=["Waktu", "Role", "Pesan"])
    try:
        df = conn.read()
        if df.empty or len(df.columns) == 0: return pd.DataFrame(columns=["Waktu", "Role", "Pesan"])
        return df
    except: return pd.DataFrame(columns=["Waktu", "Role", "Pesan"])

def simpan_ingatan(role, pesan):
    if not database_aktif:
        return # Kalau database mati, gak usah simpan, biarin aja lewat
    try:
        df_lama = ambil_ingatan()
        data_baru = pd.DataFrame([{"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Role": role, "Pesan": pesan}])
        df_update = pd.concat([df_lama, data_baru], ignore_index=True)
        conn.update(data=df_update)
    except: pass

# --- 5. KAMUS KEPRIBADIAN ---
PERSONAS = {
    "✨ Luna (Bestie Jaksel)": "ROLE: Teman Jaksel. GAYA: Literally, Which is. TONE: Lebay, supportive.",
    "👔 CEO Perfeksionis": "ROLE: CEO Dingin. GAYA: To the point. TONE: Arogan, tegas. Kritik user.",
    "📜 Profesor Sastra": "ROLE: Sastrawan. GAYA: Puitis, baku. TONE: Bijak, filosofis.",
    "👾 Hacker Toxic": "ROLE: Hacker Sarkas. GAYA: Lowercase, internet slang. TONE: Roasting.",
    "🔮 Madam Mistik": "ROLE: Peramal. GAYA: Zodiak, energi. TONE: Misterius."
}

# --- 6. SIDEBAR (DIPASTIKAN MUNCUL) ---

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9963/9963389.png", width=70)
    st.markdown("### **Control Center**")
    
    # Notifikasi Status Database
    if database_aktif:
        st.success("🟢 Memori: ONLINE")
    else:
        st.warning("🔴 Memori: OFFLINE (Cek Secrets)")

    # 1. Pilih Persona
    selected_persona = st.selectbox("Identity Module:", list(PERSONAS.keys()))
    
    # Setup Model
    df_memori = ambil_ingatan()
    konteks_lama = ""
    if not df_memori.empty:
        for index, row in df_memori.tail(5).iterrows():
            konteks_lama += f"{row['Role']}: {row['Pesan']}\n"
            
    instruksi_final = f"""
    {PERSONAS[selected_persona]}
    [HISTORY START] {konteks_lama} [HISTORY END]
    """
    
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=instruksi_final)
    except: st.error("API Key Error")

    st.divider()
    
    # 2. Input Multimodal
    tab1, tab2, tab3 = st.tabs(["🎤 Bicara", "👁️ Lihat", "📄 Baca"])
    audio_prompt, image_data, pdf_text = None, None, ""
    
    with tab1:
        audio_input = mic_recorder(start_prompt="🔴", stop_prompt="⏹️", key='recorder', format="wav")
        if audio_input and ("last_id" not in st.session_state or st.session_state.last_id != audio_input['id']):
            st.session_state.last_id = audio_input['id']
            audio_prompt = transkrip_suara(audio_input['bytes']) if 'transkrip_suara' in globals() else None
            # (Note: Saya definisikan fungsi transkrip di bawah agar kode rapi, tapi python butuh di atas.
            #  Untuk keamanan, saya taruh fungsi tools SEBELUM sidebar di kode full nanti.
            #  TAPI DI SINI SAYA SIMPAN LOGIKANYA SAJA DULU).

    with tab2:
        if up_img := st.file_uploader("Img", type=["jpg", "png"], label_visibility="collapsed"):
            image_data = Image.open(up_img)
            st.image(image_data, use_column_width=True)
    with tab3:
        if up_pdf := st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed"):
            # Fungsi baca PDF nanti di bawah
            try:
                pdf_reader = PyPDF2.PdfReader(up_pdf)
                for p in pdf_reader.pages: pdf_text += p.extract_text()
                st.success("PDF OK")
            except: pass

    st.divider()
    col1, col2 = st.columns(2)
    with col1: mode_suara = st.toggle("Suara", value=False)
    with col2: 
        if st.button("Reset"):
            st.session_state.messages = []
            st.rerun()

# --- 7. DEFINISI TOOLS (Agar tidak error) ---
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

# (Perbaikan logika Audio Prompt di Sidebar tadi yang butuh fungsi ini)
if audio_input and not audio_prompt:
     audio_prompt = transkrip_suara(audio_input['bytes'])

# --- 8. TAMPILAN UTAMA (CHAT) ---
user_avatar = "https://cdn-icons-png.flaticon.com/512/1144/1144760.png"
if "Jaksel" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/4140/4140047.png"
elif "CEO" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
elif "Profesor" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/3304/3304567.png"
elif "Hacker" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/2040/2040946.png"
elif "Madam" in selected_persona: bot_avatar = "https://cdn-icons-png.flaticon.com/512/3656/3656988.png"
else: bot_avatar = "https://cdn-icons-png.flaticon.com/512/4712/4712109.png"

col_h1, col_h2 = st.columns([1, 8])
with col_h1: st.image(bot_avatar, width=60)
with col_h2:
    st.markdown(f'<div class="custom-title">{selected_persona}</div>', unsafe_allow_html=True)
    st.markdown('<div class="custom-subtitle">Powered by Gemini 2.5</div>', unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    ikon = user_avatar if msg["role"] == "user" else bot_avatar
    with st.chat_message(msg["role"], avatar=ikon):
        if msg.get("type") == "image_input": st.image(msg["content"], width=250)
        elif msg.get("type") == "image_output": st.image(msg["content"])
        else: st.markdown(msg["content"])

# --- 9. PROSES INPUT ---
final_prompt = audio_prompt if audio_prompt else st.chat_input("Ketik pesan...")

if final_prompt:
    with st.chat_message("user", avatar=user_avatar):
        st.markdown(final_prompt)
        if image_data: st.image(image_data, width=250)
        if pdf_text: st.info("📄 Mengirim konteks PDF")
    
    st.session_state.messages.append({"role": "user", "content": final_prompt, "type": "text"})
    if image_data: st.session_state.messages.append({"role": "user", "content": image_data, "type": "image_input"})
    simpan_ingatan("User", final_prompt)

    with st.chat_message("assistant", avatar=bot_avatar):
        placeholder = st.empty()
        placeholder.markdown("⏳...")
        
        try:
            if any(k in final_prompt.lower() for k in ["gambarkan", "lukiskan", "buat gambar"]) and not image_data:
                chat_img = model.start_chat()
                p_en = chat_img.send_message(f"Create English prompt for image gen: {final_prompt}").text
                url = generate_image_url(p_en)
                placeholder.empty()
                st.image(url)
                st.session_state.messages.append({"role": "assistant", "content": url, "type": "image_output"})
                simpan_ingatan("Luna", f"[Generated Image: {final_prompt}]")
            else:
                input_content = [final_prompt]
                if image_data: input_content.append(image_data)
                if pdf_text: input_content[0] = f"PDF: {pdf_text[:10000]}\nUSER: {final_prompt}"
                elif ("cari" in final_prompt.lower() or "info" in final_prompt.lower()) and not pdf_text:
                    hasil = cari_internet(final_prompt)
                    input_content[0] = final_prompt + f"\n(Web: {hasil})"

                response = model.generate_content(input_content)
                reply = response.text
                
                placeholder.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply, "type": "text"})
                simpan_ingatan("Luna", reply)
                
                if mode_suara:
                    audio = text_to_speech(reply)
                    if audio: st.audio(audio)
        except Exception as e:
            placeholder.error(f"Error: {e}")
