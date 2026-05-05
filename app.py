import streamlit as st
import anthropic
import io
from pathlib import Path

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document as DocxDocument
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

# ─── Configuración de la página ───────────────────────────────────────────────
st.set_page_config(
    page_title="ChatDocs · UPC Física",
    page_icon="⚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS científico ───────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Space+Grotesk:wght@300;400;600;700&family=Crimson+Pro:ital,wght@0,400;1,400&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

.stApp {
    background: #050d1a;
    color: #c8d8f0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #07111f !important;
    border-right: 1px solid #0e2a4a;
}

[data-testid="stSidebar"] * {
    color: #a0bcdc !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* Header principal */
.sci-header {
    padding: 2.5rem 0 1.5rem 0;
    border-bottom: 1px solid #0e2a4a;
    margin-bottom: 2rem;
}

.sci-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2.2rem;
    font-weight: 600;
    color: #e8f4ff;
    letter-spacing: -0.02em;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}

.sci-title .accent {
    color: #00c8ff;
}

.sci-subtitle {
    font-family: 'Crimson Pro', serif;
    font-size: 1.05rem;
    color: #4a7ab5;
    font-style: italic;
    margin-top: 0.3rem;
    letter-spacing: 0.01em;
}

.sci-badge {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    padding: 0.2rem 0.6rem;
    border: 1px solid #0e2a4a;
    border-radius: 2px;
    color: #00c8ff;
    background: #00c8ff12;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-left: 0.5rem;
    vertical-align: middle;
}

/* Status bar */
.status-bar {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: #2a5a8a;
    border: 1px solid #0e2a4a;
    border-radius: 2px;
    padding: 0.5rem 1rem;
    background: #07111f;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.status-ok { color: #00e676; }
.status-warn { color: #ffab00; }

/* Mensajes del chat */
[data-testid="stChatMessage"] {
    background: #07111f !important;
    border: 1px solid #0e2a4a !important;
    border-radius: 4px !important;
    padding: 1rem 1.2rem !important;
    margin-bottom: 0.8rem !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

[data-testid="stChatMessage"][data-testid*="user"] {
    border-left: 3px solid #00c8ff !important;
}

[data-testid="stChatMessage"][data-testid*="assistant"] {
    border-left: 3px solid #4a7ab5 !important;
}

/* Input chat */
[data-testid="stChatInput"] {
    border: 1px solid #0e2a4a !important;
    background: #07111f !important;
    border-radius: 4px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    color: #c8d8f0 !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: #00c8ff !important;
    box-shadow: 0 0 0 1px #00c8ff33 !important;
}

/* Botones */
.stButton > button {
    background: transparent !important;
    border: 1px solid #0e2a4a !important;
    color: #4a7ab5 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important;
    border-radius: 2px !important;
    transition: all 0.2s !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

.stButton > button:hover {
    border-color: #00c8ff !important;
    color: #00c8ff !important;
    background: #00c8ff0d !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    border: 1px dashed #0e2a4a !important;
    border-radius: 4px !important;
    background: #07111f !important;
    padding: 0.5rem !important;
}

/* Warnings y success */
.stAlert {
    border-radius: 2px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.78rem !important;
}

/* Divider */
hr {
    border-color: #0e2a4a !important;
}

/* Sidebar labels */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #00c8ff !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #050d1a; }
::-webkit-scrollbar-thumb { background: #0e2a4a; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #00c8ff44; }

/* Spinner */
.stSpinner > div { border-top-color: #00c8ff !important; }

/* Decoración atómica SVG */
.atom-deco {
    position: fixed;
    top: 0; right: 0;
    width: 320px; height: 320px;
    opacity: 0.04;
    pointer-events: none;
    z-index: 0;
}
</style>

<!-- Decoración científica de fondo -->
<svg class="atom-deco" viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="160" cy="160" rx="140" ry="55" fill="none" stroke="#00c8ff" stroke-width="1.5"/>
  <ellipse cx="160" cy="160" rx="140" ry="55" fill="none" stroke="#00c8ff" stroke-width="1.5" transform="rotate(60 160 160)"/>
  <ellipse cx="160" cy="160" rx="140" ry="55" fill="none" stroke="#00c8ff" stroke-width="1.5" transform="rotate(120 160 160)"/>
  <circle cx="160" cy="160" r="12" fill="#00c8ff"/>
  <circle cx="300" cy="160" r="5" fill="#00c8ff"/>
  <circle cx="230" cy="57" r="5" fill="#00c8ff"/>
  <circle cx="90" cy="57" r="5" fill="#00c8ff"/>
</svg>

<div class="sci-header">
  <div class="sci-title">
    <span>⚛</span>
    <span>Chat<span class="accent">Docs</span></span>
    <span class="sci-badge">UPC · Física</span>
  </div>
  <div class="sci-subtitle">Sistema de consulta documental asistido por inteligencia artificial</div>
</div>
""", unsafe_allow_html=True)


# ─── Cliente Anthropic ────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

client = get_client()

# ─── Carpeta de documentos base ───────────────────────────────────────────────
BASE_DOCS_DIR = Path("base_docs")
BASE_DOCS_DIR.mkdir(exist_ok=True)

# ─── Extracción de texto ──────────────────────────────────────────────────────
def extraer_texto_pdf(file_bytes: bytes) -> str:
    if not PDF_SUPPORT:
        return "[pdfplumber no disponible]"
    texto = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for pagina in pdf.pages:
            texto += (pagina.extract_text() or "") + "\n"
    return texto

def extraer_texto_docx(file_bytes: bytes) -> str:
    if not DOCX_SUPPORT:
        return "[python-docx no disponible]"
    doc = DocxDocument(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def extraer_texto(archivo) -> str:
    nombre = archivo.name.lower()
    contenido = archivo.read()
    if nombre.endswith(".pdf"):
        return extraer_texto_pdf(contenido)
    elif nombre.endswith(".docx"):
        return extraer_texto_docx(contenido)
    elif nombre.endswith((".txt", ".md")):
        return contenido.decode("utf-8", errors="ignore")
    return ""

# ─── Documentos base ──────────────────────────────────────────────────────────
@st.cache_data
def cargar_docs_base() -> dict:
    docs = {}
    for archivo in BASE_DOCS_DIR.iterdir():
        sufijo = archivo.suffix.lower()
        if sufijo in [".txt", ".md"]:
            docs[archivo.name] = archivo.read_text(encoding="utf-8", errors="ignore")
        elif sufijo == ".pdf" and PDF_SUPPORT:
            docs[archivo.name] = extraer_texto_pdf(archivo.read_bytes())
        elif sufijo == ".docx" and DOCX_SUPPORT:
            docs[archivo.name] = extraer_texto_docx(archivo.read_bytes())
    return docs

# ─── Contexto para el modelo ──────────────────────────────────────────────────
MAX_CHARS = 4000

def construir_contexto(docs_base: dict, docs_sesion: dict) -> str:
    partes = []
    if docs_base:
        partes.append("=== DOCUMENTOS BASE (repositorio institucional) ===")
        for nombre, texto in docs_base.items():
            partes.append(f"\n[{nombre}]\n{texto[:MAX_CHARS]}")
    if docs_sesion:
        partes.append("\n=== DOCUMENTOS SUBIDOS POR EL USUARIO ===")
        for nombre, texto in docs_sesion.items():
            partes.append(f"\n[{nombre}]\n{texto[:MAX_CHARS]}")
    return "\n".join(partes)

# ─── Session state ────────────────────────────────────────────────────────────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "docs_sesion" not in st.session_state:
    st.session_state.docs_sesion = {}

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📚 Base de conocimiento")
    docs_base = cargar_docs_base()
    if docs_base:
        for nombre in docs_base:
            st.markdown(f"`{nombre}`")
    else:
        st.info("Sin documentos base.\nAgregá archivos a `base_docs/` en GitHub.")

    st.divider()

    st.markdown("### ⬆ Subí tu documento")
    archivos_subidos = st.file_uploader(
        "PDF · TXT · DOCX · MD",
        type=["pdf", "txt", "docx", "md"],
        accept_multiple_files=True,
        key="uploader",
    )

    if archivos_subidos:
        for archivo in archivos_subidos:
            if archivo.name not in st.session_state.docs_sesion:
                with st.spinner(f"Procesando {archivo.name}..."):
                    texto = extraer_texto(archivo)
                    if texto.strip():
                        st.session_state.docs_sesion[archivo.name] = texto
                        st.success(f"✓ {archivo.name}")
                    else:
                        st.warning(f"Sin texto: {archivo.name}")

    if st.session_state.docs_sesion:
        st.markdown("### 📂 Documentos en sesión")
        for nombre in list(st.session_state.docs_sesion.keys()):
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"`{nombre}`")
            if col2.button("✕", key=f"del_{nombre}"):
                del st.session_state.docs_sesion[nombre]
                st.rerun()

    st.divider()
    if st.button("↺  Nueva conversación", use_container_width=True):
        st.session_state.mensajes = []
        st.rerun()
    if st.button("⊘  Limpiar todo", use_container_width=True):
        st.session_state.docs_sesion = {}
        st.session_state.mensajes = []
        st.rerun()

# ─── Área principal ───────────────────────────────────────────────────────────
docs_base = cargar_docs_base()
total_docs = len(docs_base) + len(st.session_state.docs_sesion)

if total_docs == 0:
    st.markdown("""
    <div class="status-bar">
        <span class="status-warn">◉</span>
        SYS · Sin documentos cargados — el sistema responderá con conocimiento general.
        Cargá archivos desde el panel lateral.
    </div>
    """, unsafe_allow_html=True)
else:
    nombres = list(docs_base.keys()) + list(st.session_state.docs_sesion.keys())
    lista = " · ".join(f"`{n}`" for n in nombres)
    st.markdown(f"""
    <div class="status-bar">
        <span class="status-ok">◉</span>
        SYS · {total_docs} documento(s) indexados — {', '.join(nombres)}
    </div>
    """, unsafe_allow_html=True)

# Historial
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

# Input
if pregunta := st.chat_input("Ingresá tu consulta sobre los documentos..."):
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    contexto = construir_contexto(docs_base, st.session_state.docs_sesion)

    system_prompt = """Sos un asistente académico especializado en física y ciencias.
Respondés preguntas basándote en los documentos proporcionados.

Reglas:
1. Respondé siempre en español, con precisión y claridad científica.
2. Citá el documento fuente entre corchetes: [Fuente: nombre_archivo].
3. Si la información no está en los documentos, indicalo y respondé con conocimiento general.
4. Sé pedagógico, preciso y conciso. Usá fórmulas o conceptos cuando sea pertinente.
5. Si te preguntan qué documentos hay, listálos claramente.

""" + (f"Documentos disponibles:\n{contexto}" if contexto else "No hay documentos cargados.")

    mensajes_api = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.mensajes
    ]

    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            try:
                respuesta = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=mensajes_api,
                )
                texto_respuesta = respuesta.content[0].text
            except Exception as e:
                texto_respuesta = f"⚠ Error de conexión: {str(e)}"
        st.markdown(texto_respuesta)

    st.session_state.mensajes.append({"role": "assistant", "content": texto_respuesta})
