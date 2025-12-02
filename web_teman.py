import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
import io
import PyPDF2

# --- 1. CONFIG & API KEY ---
st.set_page_config(page_title="Super Luna AI", page_icon="🌙", layout="wide")

try:
    API_KEY = st.secrets["API_KEY"]
except:
    API_KEY = "PASTE_KODE_API_KEY_DISINI" 

# --- 2. KAMUS KEPRIBADIAN ---
PERSONAS = {
    "Luna (Teman Santai)": "Kamu Luna, teman asik. Pakai bahasa gaul (lu/gw).",
    "Asisten Riset (Ahli PDF)": "Anda asisten riset. Jawab detail berdasarkan dokumen. Bahasa formal.",
    "Koki Handal": "Kamu Chef Bintang 5. Berikan resep lengkap dan tips memasak enak.",
    "Komika (Roasting)": "Kamu komika sinis. Roasting user dengan lucu.",
    "Konsultan Bisnis": "Kamu ahli bisnis. Beri saran cuan yang masuk akal."
}

# --- 3. FUNGSI PENDUKUNG ---

def cari_internet(query):
    try:
        ddgs = DDGS()
        results = ddgs.text(query, max_results=1)
        return results[0]['body'] if results else "Nihil."
    except:
        return "Gagal browsing."

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='id')
        filename = "suara_luna.mp3"
        tts.save(filename)
        return filename
    except:
        return None

def generate_image_url(prompt):
    prompt_bersih = prompt.replace(" ", "%20")
    return f"https://image.pollinations.ai/prompt/{prompt_bersih}?nologo=true"

def transkrip_suara(audio_bytes):
    r = sr.Recognizer()
    try:
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language="id-ID")
            return text
    except:
        return None

def baca_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except:
        return None

# --- 4. SIDEBAR (PUSAT KONTROL) ---

with st.sidebar:
    st.title("🎛️ Kontrol Panel")
    
    # PILIH SIFAT
    selected_persona = st.selectbox("Mode:", list(PERSONAS.keys()))
    
    # Logic ganti persona
    if "current_persona" not in st.session_state:
        st.session_state.current_persona = selected_persona
    if st.session_state.current_persona != selected_persona:
        st.session_state.current_persona = selected_persona
        st.session_state.messages = []
        st.rerun()

    # SETUP GEMINI
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=PERSONAS[selected_persona]
        )
    except:
        st.error("Cek API Key!")

    st.divider()
    
    # --- FITUR INPUT (TAB) ---
    tab1, tab2, tab3 = st.tabs(["🎤 Suara", "📸 Foto", "📄 PDF"])
    
    audio_prompt = None
    image_data = None
    pdf_text = ""
    
    with tab1:
        st.caption("Klik Rekam -> Ngomong -> Stop")
        audio_input = mic_recorder(start_prompt="🔴 Rekam", stop_prompt="⏹️ Stop", key='recorder', format="wav")
        if audio_input:
            if "last_id" not in st.session_state or st.session_state.last_id != audio_input['id']:
                st.session_state.last_id = audio_input['id']
                audio_prompt = transkrip_suara(audio_input['bytes'])
                if not audio_prompt: st.error("Suara tak terdengar.")

    with tab2:
        uploaded_img = st.file_uploader("Upload Foto", type=["jpg", "png"])
        if uploaded_img:
            image_data = Image.open(uploaded_img)
            st.image(image_data, caption="Foto", use_column_width=True)

    with tab3:
        uploaded_pdf = st.file_uploader("Upload Dokumen", type=["pdf"])
        if uploaded_pdf:
            with st.spinner("Membaca PDF..."):
                pdf_text = baca_pdf(uploaded_pdf)
                st.success(f"Berhasil: {len(pdf_text)} karakter")
    
    st.divider()
    
    # --- FITUR DOWNLOAD CHAT (BARU!) ---
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
        chat_log = ""
        for msg in st.session_state.messages:
            role = msg["role"].upper()
            content = msg["content"]
            
            # Kita hanya ambil teks, skip gambar agar tidak error
            if msg["type"] == "text":
                chat_log += f"[{role}]: {content}\n\n"
            elif msg["type"] == "image_input":
                chat_log += f"[{role}]: (Mengirim Gambar)\n\n"
        
        st.download_button(
            label="💾 Simpan Chat (.txt)",
            data=chat_log,
            file_name="catatan_luna.txt",
            mime="text/plain"
        )
    
    st.divider()
    mode_suara = st.toggle("🔊 Respon Suara", value=False)
    if st.button("🧹 Reset Chat"):
        st.session_state.messages = []
        st.rerun()

# --- 5. LOGIKA UTAMA ---

st.title(f"🌙 {selected_persona}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("type") == "image_input": st.image(msg["content"], width=200)
        elif msg.get("type") == "image_output": st.image(msg["content"])
        else: st.markdown(msg["content"])

# --- 6. PROSES INPUT ---
final_prompt = audio_prompt if audio_prompt else st.chat_input("Ketik pesan...")

if final_prompt:
    with st.chat_message("user"):
        st.markdown(final_prompt)
        if image_data: st.image(image_data, width=200)
        if pdf_text: st.markdown("*(Mengirim konteks PDF)*")
    
    st.session_state.messages.append({"role": "user", "content": final_prompt, "type": "text"})
    if image_data: st.session_state.messages.append({"role": "user", "content": image_data, "type": "image_input"})

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ *Thinking...*")
        
        try:
            # Skenario 1: Gambar
            if any(k in final_prompt.lower() for k in ["gambarkan", "lukiskan"]) and not image_data:
                chat_img = model.start_chat()
                p_en = chat_img.send_message(f"English prompt image gen: {final_prompt}").text
                url = generate_image_url(p_en)
                placeholder.empty()
                st.image(url)
                st.session_state.messages.append({"role": "assistant", "content": url, "type": "image_output"})
            
            # Skenario 2: Analisa (Vision / PDF / Chat)
            else:
                input_content = [final_prompt]
                if image_data: input_content.append(image_data)
                
                if pdf_text:
                    pdf_sebagian = pdf_text[:30000] 
                    input_content[0] = f"DATA PDF:\n{pdf_sebagian}\n\nUSER: {final_prompt}"
                
                elif ("cari" in final_prompt.lower() or "info" in final_prompt.lower()) and not pdf_text:
                    hasil = cari_internet(final_prompt)
                    input_content[0] = final_prompt + f"\n(Data Internet: {hasil})"

                response = model.generate_content(input_content)
                reply = response.text
                
                placeholder.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply, "type": "text"})
                
                if mode_suara:
                    audio = text_to_speech(reply)
                    if audio: st.audio(audio)

        except Exception as e:
            placeholder.error(f"Error: {e}")