import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from gtts import gTTS
from PIL import Image # Ini alat baru untuk pengolah gambar

# --- 1. CONFIG & API KEY ---
st.set_page_config(page_title="Super Luna AI", page_icon="🌙")

try:
    API_KEY = st.secrets["API_KEY"]
except:
    API_KEY = "PASTE_KODE_API_KEY_DISINI" 

try:
    genai.configure(api_key=API_KEY)
    # Kita tetap pakai model Flash karena dia sudah Multimodal (Bisa lihat & baca)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction="""
        Kamu adalah Luna. Teman yang asik dan serba tahu.
        Jika user mengirim gambar, komentari gambar itu dengan detail tapi santai.
        Gunakan bahasa Indonesia gaul (lu/gw).
        """
    )
except Exception as e:
    st.error(f"Error API: {e}")

# --- 2. FUNGSI-FUNGSI PENDUKUNG ---

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

# --- 3. UI: SIDEBAR (TEMPAT UPLOAD FOTO) ---

with st.sidebar:
    st.header("📸 Mata Luna")
    # Widget untuk upload file
    uploaded_file = st.file_uploader("Upload foto untuk dilihat Luna:", type=["jpg", "jpeg", "png"])
    
    image_data = None
    if uploaded_file is not None:
        # Tampilkan preview kecil di sidebar
        image_data = Image.open(uploaded_file)
        st.image(image_data, caption="Foto siap dikirim!", use_column_width=True)
    
    st.divider()
    
    st.header("Pengaturan")
    mode_suara = st.toggle("Aktifkan Suara Luna", value=False)
    if st.button("Hapus Ingatan"):
        st.session_state.messages = []
        st.rerun()

# --- 4. LOGIKA CHAT UTAMA ---

st.title("🌙 Super Luna AI")
st.caption("Kirim teks atau upload foto di menu samping (👈)")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan History Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("type") == "image_input":
            st.image(msg["content"], caption="Foto yang kamu kirim")
        elif msg.get("type") == "image_output":
            st.image(msg["content"], caption="Dibuat oleh Luna")
        else:
            st.markdown(msg["content"])

# --- 5. PEMROSESAN INPUT ---
if prompt := st.chat_input("Ketik pesan tentang foto itu..."):
    
    # A. Tampilkan Pesan User
    with st.chat_message("user"):
        st.markdown(prompt)
        # Jika ada foto yang sedang diupload, tampilkan juga di chat utama
        if image_data:
            st.image(image_data, width=200)
    
    # Simpan ke history
    st.session_state.messages.append({"role": "user", "content": prompt, "type": "text"})
    if image_data:
         # Kita simpan "jejak" bahwa user kirim foto (tapi tidak simpan datanya biar hemat memori)
        st.session_state.messages.append({"role": "user", "content": image_data, "type": "image_input"})

    # B. Proses Jawaban Luna
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Thinking...")
        
        try:
            # Skenario 1: Minta Buat Gambar (Text-to-Image)
            keyword_gambar = ["gambarkan", "buatkan gambar", "lukiskan"]
            if any(k in prompt.lower() for k in keyword_gambar) and not image_data:
                chat_img = model.start_chat()
                prompt_inggris = chat_img.send_message(f"Translate to English prompt for image generator: {prompt}").text
                img_url = generate_image_url(prompt_inggris)
                placeholder.empty()
                st.image(img_url)
                st.session_state.messages.append({"role": "assistant", "content": img_url, "type": "image_output"})
            
            # Skenario 2: Analisa Foto (Vision) atau Chat Biasa
            else:
                # Siapkan "history" (Sayangnya Gemini Vision belum support history panjang sempurna)
                # Jadi untuk fitur Vision, kita pakai mode 'generate_content' (sekali tanya)
                # agar lebih akurat memproses gambarnya.
                
                input_ke_gemini = [prompt]
                if image_data:
                    input_ke_gemini.append(image_data)
                    placeholder.markdown("👁️ *Sedang melihat foto...*")
                
                # Cek internet jika perlu (Hanya kalau tidak ada gambar)
                if not image_data and ("cari" in prompt.lower() or "info" in prompt.lower()):
                     hasil = cari_internet(prompt)
                     input_ke_gemini[0] = prompt + f"\n(Data Internet: {hasil})"

                # KIRIM KE GEMINI!
                response = model.generate_content(input_ke_gemini)
                text_reply = response.text
                
                placeholder.markdown(text_reply)
                st.session_state.messages.append({"role": "assistant", "content": text_reply, "type": "text"})
                
                if mode_suara:
                    audio = text_to_speech(text_reply)
                    if audio: st.audio(audio)

        except Exception as e:
            placeholder.error(f"Error: {e}")
