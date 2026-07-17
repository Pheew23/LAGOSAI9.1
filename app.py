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

# --- 5. JALUR MIKROFON (Pemicu Munculnya Tombol) ---
@cl.on_audio_end
async def on_audio_end(elements: list):
    if not groq_client:
        await cl.Message(content="⚠️ Kunci API Groq belum diatur di Render.").send()
        return
        
    audio_file = elements[0]
    
    async with cl.Step(name="Mendengarkan...") as step:
        try:
            with open(audio_file.path, "rb") as f:
                transcription = await groq_client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=f
                )
            text_from_voice = transcription.text
            step.output = f"Berhasil menerjemahkan audio."
        except Exception as e:
            step.is_error = True
            step.output = f"Gagal memproses suara: {str(e)}"
            return

    # Tampilkan teks hasil suara di layar seolah-olah user mengetiknya
    await cl.Message(content=f'🎙️ *"{text_from_voice}"*', author="User").send()
    
    # Teruskan teks tersebut ke AI
    await process_llm(text_from_voice, [])
