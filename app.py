import chainlit as cl
from openai import AsyncOpenAI
import os
import base64
import speech_recognition as sr
import io
from pypdf import PdfReader
from docx import Document

# --- 1. KONFIGURASI API ---
API_KEY = os.environ.get("NVIDIA_API_KEY") 
BASE_URL = "https://integrate.api.nvidia.com/v1"

# Menggunakan versi AsyncOpenAI agar lebih kuat menangani ribuan akses bersamaan
client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

# Model sama persis seperti sebelumnya
MODEL_MAPPING = {
    "1. Stabil": "google/gemma-4-31b-it",
    "2. Cepat (Teks Saja)": "thinkingmachines/inkling",
    "3. Analisis Mendalam": "mistralai/mistral-medium-3.5-128b",
    "4. Sangat Cepat (Teks Saja)": "openai/gpt-oss-120b",
    "5. Projek Khusus": "nvidia/nemotron-3-ultra-550b-a55b"
}

# --- 2. PENGATURAN AWAL (SAAT USER MEMBUKA WEB) ---
@cl.on_chat_start
async def start():
    # Membuat menu pengaturan di pojok layar
    settings = await cl.ChatSettings(
        [
            cl.input_widget.Select(
                id="Model",
                label="🧠 Pilih Model AI Aktif",
                values=list(MODEL_MAPPING.keys()),
                initial_index=0,
            )
        ]
    ).send()
    
    cl.user_session.set("model", MODEL_MAPPING[list(MODEL_MAPPING.keys())[0]])
    cl.user_session.set("message_history", [{"role": "system", "content": "Anda adalah Lagos AI 9.1 (Rian Dev), asisten analitik tingkat tinggi."}])
    
    await cl.Message(
        content="### 🔮 Lagos AI 9.1 Active\nSistem siap! Ketik pesan Anda, klik ikon **📎** di sebelah kiri kotak teks untuk melampirkan file/gambar, atau klik ikon **🎙️** di kanan untuk berbicara."
    ).send()

# --- 3. LOGIKA JIKA USER MENGGANTI MODEL ---
@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("model", MODEL_MAPPING[settings["Model"]])
    await cl.Message(content=f"⚙️ Engine beralih ke: **{settings['Model']}**").send()

# --- 4. LOGIKA UTAMA (SAAT USER MENGIRIM PESAN/FILE/SUARA) ---
@cl.on_message
async def main(message: cl.Message):
    message_history = cl.user_session.get("message_history")
    model_name = cl.user_session.get("model")
    
    # Chainlit otomatis menangkap file yang diunggah
    images = [file for file in message.elements if "image" in file.mime]
    docs = [file for file in message.elements if "pdf" in file.mime or "text" in file.mime or "word" in file.mime or "officedocument" in file.mime]
    audios = [file for file in message.elements if "audio" in file.mime]
    
    final_prompt = message.content or ""
    
    # Proses Suara (Menggunakan layanan gratis Google)
    if audios:
        async with cl.Step(name="Menerjemahkan Suara...") as step:
            r = sr.Recognizer()
            try:
                with sr.AudioFile(audios[0].path) as source:
                    audio_data = r.record(source)
                    text_from_voice = r.recognize_google(audio_data, language="id-ID")
                    final_prompt += f" {text_from_voice}"
                    step.output = f"Terdengar: {text_from_voice}"
            except Exception as e:
                step.is_error = True
                step.output = "Maaf, suara tidak terdengar jelas."
    
    # Proses Dokumen
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

    # Siapkan data untuk dikirim ke NVIDIA
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

    # Abaikan jika kosong
    if not final_prompt.strip() and not images:
        return

    message_history.append({"role": "user", "content": content_payload})
    msg = cl.Message(content="")
    await msg.send()

    # Memanggil Engine dengan efek mengetik (Streaming)
    try:
        stream = await client.chat.completions.create(
            messages=message_history,
            model=model_name,
            stream=True,
            temperature=0.3,
            max_tokens=4096
        )

        async for part in stream:
            if part.choices and len(part.choices) > 0:
                token = part.choices[0].delta.content or ""
                await msg.stream_token(token)
                
    except Exception as e:
        await cl.Message(content=f"⚠️ Engine Error: {str(e)}").send()
        message_history.pop() 
        return

    await msg.update()
    message_history.append({"role": "assistant", "content": msg.content})
