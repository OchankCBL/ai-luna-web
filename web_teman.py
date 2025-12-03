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
st.set_page_config(page_title="Super Luna AI", page_icon="🌙", layout="wide")

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

def ambil_ingatan():
    """Membaca data dari Google Sheet"""
    try:
        # Kita baca sheetnya. Kalau kosong, bikin DataFrame baru.
        df = conn.read()
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=["Waktu", "Role", "Pesan"])
        return df
    except:
        return pd.DataFrame(columns=["Waktu", "Role", "Pesan"])

def simpan_ingatan(role, pesan):
    """Menulis pesan baru ke Google Sheet"""
    try:
        df_lama = ambil_ingatan()
        
        # Buat baris baru
        data_baru = pd.DataFrame([{
            "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Role": role,
            "Pesan": pesan
        }])
        
        # Gabung dan Update Sheet
        df_update = pd.concat([df_lama, data_baru], ignore_index=True)
        conn.update(data=df_update)
    except Exception as e:
        st.warning(f"Gagal menyimpan ke memori: {e}")

# --- 3. SIAPKAN OTAK LUNA (DENGAN KONTEKS LAMA) ---

# Kita ambil 5 percakapan terakhir dari database untuk jadi 'konteks'
df_memori = ambil_ingatan()
konteks_lama = ""
if not df_memori.empty:
    # Ambil 5 baris terakhir
    terakhir = df_memori.tail(5)
    for index, row in terakhir.iterrows():
        konteks_lama += f"{row['Role']}: {row['Pesan']}\n"

# Kamus Kepribadian
PERSONAS = {
    "Luna (Teman Santai)": "Kamu Luna. Pakai bahasa gaul (lu/gw).",
    "Asisten Pribadi": "Anda asisten profesional. Bahasa baku.",
    "Komika": "Kamu komika. Roasting user.",
}

# --- 4. FUNGSI PENDUKUNG LAINNYA ---
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

# --- 5. TAMPILAN SIDEBAR ---
with st.sidebar:
    st.title("🎛️ Panel Kontrol")
    selected_persona = st.selectbox("Mode:", list(PERSONAS.keys()))
    
    # INJEKSI MEMORI KE SYSTEM INSTRUCTION
    instruksi_final = f"""
    {PERSONAS[selected_persona]}
    
    INI ADALAH INGATAN MASA LALU KITA (GUNAKAN SEBAGAI KONTEKS):
    {konteks_lama}
    """
    
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=instruksi_final)
    except: st.error("Cek API Key!")

    st.divider()
    tab1, tab2, tab3 = st.tabs(["🎤", "📸", "📄"])
    audio_prompt, image_data, pdf_text = None, None, ""
    
    with tab1:
        audio_input = mic_recorder(start_prompt="🔴", stop_prompt="⏹️", key='recorder', format="wav")
        if audio_input and ("last_id" not in st.session_state or st.session_state.last_id != audio_input['id']):
            st.session_state.last_id = audio_input['id']
            audio_prompt = transkrip_suara(audio_input['bytes'])
    with tab2:
        if up_img := st.file_uploader("Foto", type=["jpg", "png"]):
            image_data = Image.open(up_img)
            st.image(image_data, use_column_width=True)
    with tab3:
        if up_pdf := st.file_uploader("PDF", type=["pdf"]):
            pdf_text = baca_pdf(up_pdf)
            st.success("PDF Terbaca")

    st.divider()
    mode_suara = st.toggle("🔊 Suara", value=False)
    if st.button("Hapus Layar Chat"):
        st.session_state.messages = []
        st.rerun()

# --- 6. LOGIKA CHAT UTAMA ---
st.title(f"🌙 {selected_persona}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan Chat di Layar
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("type") == "image_input": st.image(msg["content"], width=200)
        elif msg.get("type") == "image_output": st.image(msg["content"])
        else: st.markdown(msg["content"])

# --- 7. PROSES & SIMPAN ---
final_prompt = audio_prompt if audio_prompt else st.chat_input("Ketik pesan...")

if final_prompt:
    # 1. Tampilkan & Simpan User Input
    with st.chat_message("user"):
        st.markdown(final_prompt)
        if image_data: st.image(image_data, width=200)
        if pdf_text: st.markdown("*(PDF)*")
    
    st.session_state.messages.append({"role": "user", "content": final_prompt, "type": "text"})
    if image_data: st.session_state.messages.append({"role": "user", "content": image_data, "type": "image_input"})
    
    # SIMPAN KE GOOGLE SHEET (USER)
    simpan_ingatan("User", final_prompt)

    # 2. Proses AI
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳...")
        
        try:
            # Logic Gambar/Vision/Teks (Sama seperti sebelumnya)
            if any(k in final_prompt.lower() for k in ["gambarkan", "lukiskan"]) and not image_data:
                chat_img = model.start_chat()
                p_en = chat_img.send_message(f"English prompt image gen: {final_prompt}").text
                url = generate_image_url(p_en)
                placeholder.empty()
                st.image(url)
                st.session_state.messages.append({"role": "assistant", "content": url, "type": "image_output"})
                simpan_ingatan("Luna", f"[Mengirim Gambar: {final_prompt}]")
            
            else:
                input_content = [final_prompt]
                if image_data: input_content.append(image_data)
                if pdf_text: input_content[0] = f"DATA PDF:\n{pdf_text[:30000]}\n\nUSER: {final_prompt}"
                elif ("cari" in final_prompt.lower() or "info" in final_prompt.lower()) and not pdf_text:
                    hasil = cari_internet(final_prompt)
                    input_content[0] = final_prompt + f"\n(Data Internet: {hasil})"

                response = model.generate_content(input_content)
                reply = response.text
                
                placeholder.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply, "type": "text"})
                
                # SIMPAN KE GOOGLE SHEET (LUNA)
                simpan_ingatan("Luna", reply)
                
                if mode_suara:
                    audio = text_to_speech(reply)
                    if audio: st.audio(audio)

        except Exception as e:
            placeholder.error(f"Error: {e}")
