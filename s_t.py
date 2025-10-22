import os
import time
import glob
import streamlit as st
from PIL import Image

from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events

from gtts import gTTS
from googletrans import Translator


# =========================
# UI — Encabezados bacanos
# =========================
st.title("🎧 TRADUCTOR · Voz → Texto → Audio")
st.subheader("Escucho lo que quieras traducir y te lo devuelvo hablado 😎")

# Imagen (déjala como la tienes)
image = Image.open('traductor.jp')
st.image(image, width=300, caption="Interfaces multimodales en acción")

with st.sidebar:
    st.subheader("🗣️ ¿Cómo funciona?")
    st.write(
        "1) Presiona **Escuchar 🎤**.\n"
        "2) Cuando oigas la señal, **habla** lo que quieras traducir.\n"
        "3) Revisa/edita el texto capturado.\n"
        "4) Elige idiomas y acento, y dale a **Convertir**."
    )
    st.info("Tip: Si no captura voz, puedes pegar el texto manualmente en el área de edición.")


st.write("Toca el botón y habla lo que quieres traducir:")

# Botón de escucha (Bokeh + Web Speech API)
stt_button = Button(label=" Escuchar  🎤", width=300, height=50)
stt_button.js_on_event("button_click", CustomJS(code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = function (e) {
        var value = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                value += e.results[i][0].transcript;
            }
        }
        if (value != "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
        }
    }
    recognition.start();
"""))

result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT",
    key="listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0
)

# =========================
# Captura y edición de texto
# =========================
captured_text = ""
if result and "GET_TEXT" in result:
    captured_text = result.get("GET_TEXT", "") or ""

# Área para que el usuario edite o pegue texto
texto_input = st.text_area(
    "📝 Texto detectado (puedes editarlo o pegar tu propio texto):",
    value=captured_text,
    height=120,
    placeholder="Aquí aparecerá lo que dijiste… o pega tu texto manualmente."
)

# =========================
# Configuración de idiomas y acento
# =========================
st.markdown("### 🌍 Configuración de idiomas")

language_options = ["Inglés", "Español", "Bengali", "Coreano", "Mandarín", "Japonés"]
lang_map = {
    "Inglés": "en",
    "Español": "es",
    "Bengali": "bn",
    "Coreano": "ko",
    "Mandarín": "zh-cn",
    "Japonés": "ja",
}

col1, col2 = st.columns(2)
with col1:
    in_lang = st.selectbox("Lenguaje de entrada", language_options, index=1)
with col2:
    out_lang = st.selectbox("Lenguaje de salida", language_options, index=0)

input_language = lang_map[in_lang]
output_language = lang_map[out_lang]

st.markdown("### 🎙️ Acento (solo influye al sintetizar en inglés)")
accent_options = [
    "Defecto", "Español", "Reino Unido", "Estados Unidos",
    "Canada", "Australia", "Irlanda", "Sudáfrica"
]
tld_map = {
    "Defecto": "com",
    "Español": "com.mx",
    "Reino Unido": "co.uk",
    "Estados Unidos": "com",
    "Canada": "ca",
    "Australia": "com.au",
    "Irlanda": "ie",
    "Sudáfrica": "co.za",
}
english_accent = st.selectbox("Selecciona el acento", accent_options, index=0)
tld = tld_map[english_accent]

# =========================
# Traducción y TTS
# =========================
translator = Translator()
st.markdown("### 🔊 Texto a audio")

display_output_text = st.checkbox("Mostrar el texto traducido", value=True)

# Asegura carpeta temporal
os.makedirs("temp", exist_ok=True)

def safe_filename(s: str, fallback: str = "audio"):
    s = (s or "").strip()
    if not s:
        return fallback
    base = "".join(c for c in s[:32] if c.isalnum() or c in ("-", "_"))
    return base or fallback

def text_to_speech(input_language, output_language, text, tld):
    translation = translator.translate(text, src=input_language, dest=output_language)
    trans_text = translation.text
    file_stub = safe_filename(text) or "audio"
    file_path = f"temp/{file_stub}.mp3"
    # Si no es inglés, gTTS ignora tld; lo dejamos por compatibilidad cuando sea 'en'
    tts = gTTS(trans_text, lang=output_language, tld=tld, slow=False)
    tts.save(file_path)
    return file_stub, trans_text, file_path

convert = st.button("🚀 Convertir a audio")
if convert:
    if not texto_input.strip():
        st.warning("Primero escribe o dicta algún texto para traducir.")
    else:
        try:
            file_stub, output_text, file_path = text_to_speech(
                input_language, output_language, texto_input, tld
            )
            st.success("¡Listo! Tu audio está abajo.")
            with open(file_path, "rb") as audio_file:
                audio_bytes = audio_file.read()
            st.markdown("#### 🎧 Tu audio:")
            st.audio(audio_bytes, format="audio/mp3", start_time=0)
            st.download_button("⬇️ Descargar MP3", data=audio_bytes, file_name=f"{file_stub}.mp3")

            if display_output_text:
                st.markdown("#### 🗒️ Texto de salida:")
                st.write(output_text)
        except Exception as e:
            st.error(f"Ocurrió un problema al generar el audio: {e}")

# =========================
# Limpieza de archivos viejos
# =========================
def remove_files(n_days: int):
    mp3_files = glob.glob("temp/*.mp3")
    if not mp3_files:
        return
    now = time.time()
    horizon = now - n_days * 86400
    for f in mp3_files:
        try:
            if os.stat(f).st_mtime < horizon:
                os.remove(f)
        except Exception:
            pass

remove_files(7)
