import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from gtts import gTTS
import os

# --- 1. CONFIG & API KEY ---
st.set_page_config(page_title="Super Luna AI", page_icon="🌙")

# Coba ambil dari Secrets (untuk Online), kalau gagal ambil manual (untuk Lokal)
try:
    API_KEY = st.secrets["API_KEY"]
except:
    # GANTI INI JIKA DIJALANKAN DI LAPTOP SENDIRI MANUAL
    API_KEY = "PASTE_KODE_API_KEY_DISINI" 

# Setup Gemini
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction="""
        Kamu adalah Luna. 
        Jika user meminta membuat gambar, jawab dengan: "Oke, ini gambarnya:" lalu deskripsikan gambarnya singkat.
        Gunakan bahasa santai.
        """
    )
except Exception as e:
    st.error(f"Error API: {e}")

# --- 2. FUNGSI-FUNGSI CANGGIH ---

def cari_internet(query):
    try:
        ddgs = DDGS()
        results = ddgs.text(query, max_results=1)
        return results[0]['body'] if results else "Nihil."
    except:
        return "Gagal browsing."

def text_to_speech(text):
    """Mengubah teks jadi suara (Bahasa Indonesia)"""
    try:
        tts = gTTS(text=text, lang='id')
        filename = "suara_luna.mp3"
        tts.save(filename)
        return filename
    except:
        return None

def generate_image_url(prompt):
    """Trik membuat gambar pakai Pollinations AI (Gratis & Tanpa API Key)"""
    # Kita bersihkan prompt biar aman di URL
    prompt_bersih = prompt.replace(" ", "%20")
    return f"https://image.pollinations.ai/prompt/{prompt_bersih}?nologo=true"

# --- 3. TAMPILAN UTAMA ---

st.title("🌙 Super Luna AI")
st.caption("Bisa Chat • Bisa Browsing • Bisa Gambar • Bisa Ngomong")

# Tombol Bersih Chat di Sidebar
with st.sidebar:
    st.header("Pengaturan")
    # Fitur Suara (Opsional biar gak berisik terus)
    mode_suara = st.toggle("Aktifkan Suara Luna", value=False)
    
    if st.button("Hapus Ingatan"):
        st.session_state.messages = []
        st.rerun()

# Init Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # Jika kontennya gambar, tampilkan gambar
        if msg.get("type") == "image":
            st.image(msg["content"], caption="Dibuat oleh Luna")
        else:
            st.markdown(msg["content"])

# --- 4. OTAK PEMROSESAN ---
if prompt := st.chat_input("Ketik pesan... (Coba: 'Gambarkan kucing terbang')"):
    
    # User Input
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt, "type": "text"})

    # AI Processing
    with st.chat_message("assistant"):
        placeholder = st.empty()
        
        # A. CEK APAKAH MINTA GAMBAR?
        keyword_gambar = ["gambarkan", "buatkan gambar", "lukiskan", "foto", "image"]
        if any(k in prompt.lower() for k in keyword_gambar):
            placeholder.markdown("🎨 *Sedang melukis... tunggu ya...*")
            
            # Kita minta Gemini menyempurnakan prompt gambarnya dulu (English prompt is better)
            chat_img = model.start_chat()
            prompt_inggris = chat_img.send_message(f"Terjemahkan deskripsi ini ke bahasa Inggris untuk prompt AI image generator, ambil intinya saja jangan pakai kalimat pembuka: '{prompt}'").text
            
            # Generate URL Gambar
            img_url = generate_image_url(prompt_inggris)
            
            # Tampilkan Gambar
            placeholder.empty()
            st.image(img_url, caption=f"Prompt: {prompt}")
            
            # Simpan ke history sebagai tipe gambar
            st.session_state.messages.append({"role": "assistant", "content": img_url, "type": "image"})
            
        # B. JIKA HANYA CHAT BIASA
        else:
            # Cek Internet
            context = ""
            if "cari" in prompt.lower() or "info" in prompt.lower():
                placeholder.markdown("🔍 *Browsing...*")
                hasil = cari_internet(prompt)
                context = f"(Info Internet: {hasil})\n"
            
            # Tanya Gemini
            try:
                placeholder.markdown("Thinking...")
                chat_history = [{"role": "user" if m["role"] == "user" else "model", "parts": [str(m["content"])]} for m in st.session_state.messages if m.get("type") != "image"]
                
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(prompt + context)
                text_reply = response.text
                
                placeholder.markdown(text_reply)
                st.session_state.messages.append({"role": "assistant", "content": text_reply, "type": "text"})
                
                # C. FITUR SUARA (Jika diaktifkan)
                if mode_suara:
                    audio_file = text_to_speech(text_reply)
                    if audio_file:
                        st.audio(audio_file)
                        
            except Exception as e:
                placeholder.error("Luna lagi pusing. Coba lagi.")
