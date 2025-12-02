import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS

# --- 1. KONFIGURASI HALAMAN & TEMA ---
st.set_page_config(
    page_title="Luna AI - Teman Ngobrol",
    page_icon="🌙",
    layout="centered"
)

# --- 2. SETUP API KEY (DARI BRANKAS RAHASIA) ---
# Kita ambil kunci dari st.secrets agar aman saat online
try:
    API_KEY = st.secrets["API_KEY"]
except:
    # Ini buat jaga-jaga kalau dijalankan di laptop lokal tanpa secrets
    st.error("API Key belum disetting di Secrets!")
    st.stop()

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction="""
        Kamu adalah Luna, teman virtual yang cerdas, agak jahil, tapi sangat membantu.
        Gunakan emoji dalam percakapan agar tidak kaku.
        Gunakan bahasa Indonesia santai (lu/gw) tapi tetap sopan.
        """
    )
except Exception as e:
    st.error(f"⚠️ Error API Key: {e}")

# --- 3. CSS COSTUM (MEMPERCANTIK TAMPILAN) ---
# Kode 'sihir' ini untuk menyembunyikan menu bawaan yang mengganggu
st.markdown("""
<style>
    /* Menyembunyikan menu hamburger di pojok kanan atas */
    #MainMenu {visibility: hidden;}
    /* Menyembunyikan footer 'Made with Streamlit' */
    footer {visibility: hidden;}
    /* Mengubah warna header */
    header {visibility: hidden;}
    
    /* Membuat tampilan chat lebih rapi */
    .stChatMessage {
        border-radius: 15px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR (MENU SAMPING) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=100) # Gambar Robot Lucu
    st.title("Tentang Luna")
    st.write("Luna adalah teman AI yang bisa diajak curhat dan bisa browsing internet.")
    
    st.markdown("---") # Garis pemisah
    
    # Tombol Reset Chat
    if st.button("🗑️ Hapus Ingatan Luna"):
        st.session_state.messages = []
        st.rerun()
    
    st.caption("© 2025 Dibuat dengan Python")

# --- 5. FUNGSI PENCARIAN ---
def cari_internet(query):
    try:
        ddgs = DDGS()
        results = ddgs.text(query, max_results=2)
        if not results: return "Nihil."
        info = ""
        for result in results:
            info += f"• {result['title']}: {result['body']}\n"
        return info
    except:
        return "Gagal koneksi."

# --- 6. LOGIKA CHAT UTAMA ---

# Header Utama
st.markdown("<h1 style='text-align: center;'>🌙 Luna AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Teman ngobrol yang serba tahu</p>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
    # Pesan sapaan awal
    st.session_state.messages.append({"role": "assistant", "content": "Halo! Gue Luna. Mau ngobrol apa hari ini? 😎"})

# Menampilkan Chat
for message in st.session_state.messages:
    # Tentukan Avatar: User pakai 😎, Luna pakai 🌙
    ikon = "😎" if message["role"] == "user" else "🌙"
    
    with st.chat_message(message["role"], avatar=ikon):
        st.markdown(message["content"])

# Input User
if prompt := st.chat_input("Ketik pesanmu di sini..."):
    
    # Tampilkan pesan User
    with st.chat_message("user", avatar="😎"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Proses Jawaban
    with st.chat_message("assistant", avatar="🌙"):
        message_placeholder = st.empty()
        message_placeholder.markdown("typing...") # Efek mengetik
        
        # Cek Internet
        kata_kunci = ["cari", "browsing", "info", "berita", "siapa", "apa itu", "harga", "cuaca", "jam"]
        context_tambah = ""
        
        if any(k in prompt.lower() for k in kata_kunci):
            message_placeholder.markdown("🌐 *Sedang mencari di internet...*")
            hasil = cari_internet(prompt)
            context_tambah = f"\n[Data Internet: {hasil}]\n"

        try:
            # Format History
            chat_history = []
            for msg in st.session_state.messages:
                role = "model" if msg["role"] == "assistant" else "user"
                chat_history.append({"role": role, "parts": [msg["content"]]})

            chat = model.start_chat(history=chat_history)
            response = chat.send_message(prompt + context_tambah)
            
            message_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

        except Exception as e:
            message_placeholder.error("Aduh, Luna lagi pusing (Error API). Coba lagi ya.")