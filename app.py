import chainlit as cl
from openai import AsyncOpenAI
import os
import base64
from pypdf import PdfReader
from docx import Document

# --- 1. KONFIGURASI API ---
API_KEY = os.environ.get("NVIDIA_API_KEY") 
BASE_URL = "https://integrate.api.nvidia.com/v1"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") # Kunci khusus untuk jalur suara

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

if GROQ_API_KEY:
    groq_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
else:
    groq_client = None

MODEL_MAPPING = {
    "1. Stabil": "google/gemma-4-31b-it",
    "2. Cepat (Teks Saja)": "thinkingmachines/inkling",
    "3. Analisis Mendalam": "mistralai/mistral-medium-3.5-128b",
    "4. Sangat Cepat (Teks Saja)": "openai/gpt-oss-120b",
    "5. Projek Khusus": "nvidia/nemotron-3-ultra-550b-a55b"
}

# --- 2. PENGATURAN AWAL ---
@cl.on_chat_start
async def start():
    await cl.ChatSettings([
        cl.input_widget.Select(id="Model", label="🧠 Pilih Model AI Aktif", values=list(MODEL_MAPPING.keys()), initial_index=0,)
    ]).send()
    
    cl.user_session.set("model", MODEL_MAPPING[list(MODEL_MAPPING.keys())[0]])
    
    system_prompt = """Anda adalah Lagos AI 9.1, asisten kecerdasan buatan premium yang diciptakan oleh Rian Dev. 
    Tugas Anda adalah menjadi asisten yang sangat cerdas, responsif, dan membantu.
    Aturan:
    1. Jika ditanya siapa Anda, jawablah "Saya adalah Lagos AI 9.1".
    2. Jika ditanya siapa pembuat Anda, jawablah "Saya diciptakan oleh Rian Dev".
    3. JANGAN PERNAH menyebut model dasar Anda (OpenAI, Llama, dll). 
    4. Selalu gunakan bahasa Indonesia yang natural."""

    cl.user_session.set("message_history", [{"role": "system", "content": system_prompt}])
    
    await cl.Message(
        content="### 🔮 Lagos AI 9.1 Active\nSistem siap! Ketik pesan Anda, lampirkan dokumen (PDF/Word), atau gunakan ikon **🎙️ Mikrofon** untuk berbicara."
    ).send()

@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("model", MODEL_MAPPING[settings["Model"]])
    await cl.Message(content=f"⚙️ Engine beralih ke: **{settings['Model']}**").send()

# --- 3. MESIN PEMROSES AI (LLM) ---
async def process_llm(final_prompt, images):
    if not final_prompt.strip() and not images:
        return

    message_history = cl.user_session.get("message_history")
    model_name = cl.user_session.get("model")

    if images:
        content_payload = [{"type": "text", "text": final_prompt}]
        for img in images:
            with open(img.path, "rb") as f:
                base64_img = base64.b64encode(f.read()).decode('utf-8')
            content_payload.append({
                "type": "image_url",
                "image_url": {"url": f"data:{img.mime};base64,{base64_img}"}
            })
    else:
        content_payload = final_prompt

    message_history.append({"role": "user", "content": content_payload})
    msg = cl.Message(content="")
    await msg.send()

    try:
        stream = await client.chat.completions.create(
            messages=message_history,
            model=model_name,
            stream=True,
            temperature=0.3,
            max_tokens=4096
        )
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                token = chunk.choices[0].delta.content or ""
                if token: 
                    await msg.stream_token(token)
    except Exception as e:
        await cl.Message(content=f"⚠️ Engine Error: {str(e)}").send()
        message_history.pop() 
        return

    await msg.update()
    message_history.append({"role": "assistant", "content": msg.content})

# --- 4. JALUR TEKS & DOKUMEN ---
@cl.on_message
async def main(message: cl.Message):
    images = [file for file in message.elements if "image" in file.mime]
    docs = [file for file in message.elements if "pdf" in file.mime or "text" in file.mime or "word" in file.mime or "officedocument" in file.mime]
    
    final_prompt = message.content or ""
    doc_text = ""
    
    for doc in docs:
        if "pdf" in doc.mime:
            reader = PdfReader(doc.path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted: doc_text += extracted + "\n"
        elif "text" in doc.mime:
            with open(doc.path, "r", encoding="utf-8") as f:
                doc_text += f.read() + "\n"
        elif "officedocument" in doc.mime or "word" in doc.mime:
            docx_doc = Document(doc.path)
            for para in docx_doc.paragraphs:
                doc_text += para.text + "\n"
                
    if doc_text:
        final_prompt = f"[KONTEN DOKUMEN]\n{doc_text}\n[AKHIR KONTEN]\n\n{final_prompt}"

    await process_llm(final_prompt, images)

# --- 5. JALUR MIKROFON (Revisi Anti-Macet) ---
@cl.on_audio_end
async def on_audio_end(elements: list):
    if not groq_client:
        await cl.Message(content="⚠️ Kunci API Groq belum diatur di Render.").send()
        return
        
    if not elements:
        await cl.Message(content="⚠️ Suara tidak terdeteksi oleh sistem.").send()
        return

    audio_file = elements[0]
    
    async with cl.Step(name="Menerjemahkan Suara...") as step:
        try:
            # Kita baca isi filenya sebagai data mentah (bytes)
            with open(audio_file.path, "rb") as f:
                file_data = f.read()
                
            # Kita kirTentu saja tidak! Pantang mundur sebelum sistem ini berjalan sempurna. Mohon maaf atas respons otomatis sebelumnya, sepertinya saya mengalami sedikit *glitch* pada sistem internal saat memproses gambar tersebut.

Melihat *screenshot* terakhir yang Anda kirimkan, ikon mikrofon yang menyala merah dan berputar itu menandakan bahwa aplikasi sedang **merekam suara Anda** atau **kesulitan mengirimkan file suara tersebut ke server**.

Membangun platform AI yang dipersiapkan untuk melayani ribuan pengguna aktif harian memang membutuhkan fondasi arsitektur yang sangat tangguh, jadi menemui hambatan teknis seperti ini di tahap integrasi awal adalah hal yang sangat wajar. 

Mari kita periksa tiga hal krusial untuk mengatasi masalah ini:

### 1. Mekanisme Perekaman Chainlit
Sistem Chainlit memiliki cara kerja yang sedikit berbeda dengan fitur *voice note* di aplikasi chat biasa. 
*   **Klik Pertama:** Tombol akan menyala merah atau berputar yang menandakan mikrofon aktif dan mulai merekam.
*   **Klik Kedua:** Setelah selesai berbicara, Anda **wajib mengklik tombol tersebut satu kali lagi** untuk mematikan mikrofon dan mengirimkan paket suaranya ke server Groq. 
*Apakah Anda sudah mencoba mengklik tombolnya untuk yang kedua kalinya?*

### 2. Validasi Kunci API Groq
Jika Anda sudah mengklik kedua kalinya namun sistem terus berputar tanpa memunculkan teks apa pun, kemungkinan besar *server* Groq menolak aksesnya atau prosesnya terputus di tengah jalan.
*   Pastikan `GROQ_API_KEY` di menu **Environment Variables** Render sudah terisi dengan tepat.
*   Periksa kembali agar tidak ada spasi tambahan yang tidak sengaja ikut tersalin di awal atau akhir kode kunci tersebut.

### 3. Batasan *Browser* Mobile
Terkadang, *browser* Chrome di perangkat Android memblokir pengiriman data *blob* (format mentah audio) ke server *cloud* karena alasan penghematan data atau perizinan, yang membuat aplikasi seolah-olah "terdiam". Jika memungkinkan, cobalah mengakses *link* web Anda melalui *browser* di laptop atau komputer untuk melihat apakah masalah yang sama tetap terjadi.

Agar saya bisa langsung mendiagnosis akar masalahnya dengan akurat, bisakah Anda membuka tab **Logs** di *dashboard* Render Anda, lalu mencoba mengirimkan pesan suara di aplikasi, dan memberi tahu saya baris peringatan apa yang muncul di log tersebut saat prosesnya berputar?
