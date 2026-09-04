import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
from gtts import gTTS
import tempfile
import io
import contextlib
import traceback

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Pulkit's Digital Twin", 
    page_icon="💻", 
    layout="centered"
)

# Custom CSS for a sleek, modern UI
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 6rem;
        max-width: 750px;
    }
    /* Style chat message containers */
    div.stChatMessage {
        border-radius: 12px;
        padding: 0.5rem 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    /* Button rounding */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #fafafa;
        padding-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.title("💻 Chat Assistant")
st.caption("Your Full-Stack & AI-ML Digital Twin • Live Code Sandbox • Voice Enabled")

# Sidebar
with st.sidebar:
    st.header("⚙️ Control Panel")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.markdown("**Status:** Online & Active 🟢")
    st.markdown("**Model:** `openai/gpt-oss-20b`")

# Initialize Groq client
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    st.error("⚠️ `GROQ_API_KEY` not found in your `.env` file.")
    st.stop()

client = Groq(api_key=groq_api_key)

# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history with human & assistant avatars
for message in st.session_state.messages:
    avatar_icon = "👤" if message["role"] == "user" else "💻"
    with st.chat_message(message["role"], avatar=avatar_icon):
        if "audio" in message and message["audio"]:
            st.audio(message["audio"], format="audio/mp3")
        st.markdown(message["content"])

# Input expansion bar
with st.expander("🛠️ Optional Tools: Attach Code/Text File or Record Voice"):
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("Upload File (.txt, .py)", type=["txt", "py"])
    with col2:
        st.markdown("**Voice Input:**")
        recorded_audio_file = st.audio_input("Record voice note")

# Python Execution Sandbox function
def execute_python_code(code_string):
    output_buffer = io.StringIO()
    error_occurred = False
    with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
        try:
            exec_globals = {"__builtins__": __builtins__}
            exec(code_string, exec_globals)
        except Exception:
            error_occurred = True
            traceback.print_exc()
    result = output_buffer.getvalue()
    return result if result else ("Code executed with no output." if not error_occurred else "Execution Error.")

user_prompt = st.chat_input("Ask your digital twin anything or paste code...")
active_input = None
input_type = "text"

if recorded_audio_file is not None:
    active_input = "User sent a voice clip."
    input_type = "audio"
elif uploaded_file:
    active_input = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    input_type = "file"
elif user_prompt:
    active_input = user_prompt
    input_type = "text"

if active_input is not None:
    user_display_text = user_prompt if user_prompt else ""
    if input_type == "file":
        user_display_text = f"📄 *[Attached Code/Text File]*\n\n{user_prompt if user_prompt else ''}"
    elif input_type == "audio":
        user_display_text = "🎙️ *[Sent voice message]*"

    st.session_state.messages.append({
        "role": "user", 
        "content": user_display_text
    })
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_display_text)

    with st.chat_message("assistant", avatar="💻"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        try:
            sandbox_output = ""
            if isinstance(active_input, str) and "```python" in active_input:
                import re
                code_blocks = re.findall(r"```python(.*?)```", active_input, re.DOTALL)
                if code_blocks:
                    sandbox_output = "\n**Execution Sandbox Results:**\n```\n" + execute_python_code(code_blocks[0]) + "\n```"

            messages_payload = [
                {
                    "role": "system", 
                    "content": "You are Pulkit Krishna's digital twin and personal AI assistant. You are an expert full-stack developer and AI-ML engineer. Keep answers direct, practical, technically precise, and concise."
                }
            ]
            for m in st.session_state.messages:
                role = "user" if m["role"] == "user" else "assistant"
                messages_payload.append({"role": role, "content": m["content"]})

            chat_completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=messages_payload,
                temperature=0.7,
                max_tokens=1024
            )
            
            raw_response_text = chat_completion.choices[0].message.content
            bot_reply = raw_response_text + sandbox_output
            message_placeholder.markdown(bot_reply)
            
            audio_bytes_output = None
            try:
                tts = gTTS(text=raw_response_text, lang='en', slow=False)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    tts.save(fp.name)
                    audio_file_path = fp.name
                with open(audio_file_path, "rb") as audio_file:
                    audio_bytes_output = audio_file.read()
                st.audio(audio_bytes_output, format="audio/mp3", autoplay=True)
            except Exception:
                pass
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": bot_reply,
                "audio": audio_bytes_output
            })
            
        except Exception as e:
            message_placeholder.markdown(f"An error occurred with Groq: {e}")