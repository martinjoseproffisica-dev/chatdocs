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
    page_title="ChatDocs · UPC - Física",
    page_icon="⚛️",
    layout="wide",
)

# ─── Fondo científico + título ────────────────────────────────────────────────
st.markdown("""
<style>
/* Fondo con grilla científica y moléculas */
[data-testid="stAppViewContainer"] {
    background-color: #f0f4fa;
    background-image:
        /* Grilla de puntos */
        radial-gradient(circle, #b0c4de 1px, transparent 1px),
        /* Moléculas decorativas - círculos grandes difusos */
        radial-gradient(ellipse 340px 340px at 92% 8%, #c8daf244 0%, transparent 70%),
        radial-gradient(ellipse 280px 280px at 5% 95%, #d0e4f244 0%, transparent 70%),
        radial-gradient(ellipse 200px 200px at 50% 50%, #e8f0fa22 0%, transparent 80%);
    background-size: 28px 28px, 100% 100%, 100% 100%, 100% 100%;
}

/* Sidebar con fondo levemente distinto */
[data-testid="stSidebar"] {
    background-color: #e8eef8 !important;
    border-right: 1px solid #c8d8ec;
}

/* SVG átomos fijo en fondo */
.sci-bg {
    position: fixed;
    pointer-events: none;
    z-index: 0;
}
.sci-bg-tr { top: -30px; right: -30px; opacity: 0.07; width: 320px; }
.sci-bg-bl { bottom: -30px; left: 280px; opacity: 0.05; width: 240px; }
</style>

<!-- Átomo esquina superior derecha -->
<svg class="sci-bg sci-bg-tr" viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="160" cy="160" rx="145" ry="58" fill="none" stroke="#2563eb" stroke-width="2.5"/>
  <ellipse cx="160" cy="160" rx="145" ry="58" fill="none" stroke="#2563eb" stroke-width="2.5" transform="rotate(60 160 160)"/>
  <ellipse cx="160" cy="160" rx="145" ry="58" fill="none" stroke="#2563eb" stroke-width="2.5" transform="rotate(120 160 160)"/>
  <circle cx="160" cy="160" r="14" fill="#2563eb"/>
  <circle cx="305" cy="160" r="6" fill="#2563eb"/>
  <circle cx="233" cy="54"  r="6" fill="#2563eb"/>
  <circle cx="87"  cy="54"  r="6" fill="#2563eb"/>
  <circle cx="15"  cy="160" r="6" fill="#2563eb"/>
  <circle cx="87"  cy="266" r="6" fill="#2563eb"/>
  <circle cx="233" cy="266" r="6" fill="#2563eb"/>
</svg>

<!-- Átomo esquina inferior izquierda -->
<svg class="sci-bg sci-bg-bl" viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="160" cy="160" rx="130" ry="52" fill="none" stroke="#2563eb" stroke-width="2"/>
  <ellipse cx="160" cy="160" rx="130" ry="52" fill="none" stroke="#2563eb" stroke-width="2" transform="rotate(60 160 160)"/>
  <ellipse cx="160" cy="160" rx="130" ry="52" fill="none" stroke="#2563eb" stroke-width="2" transform="rotate(120 160 160)"/>
  <circle cx="160" cy="160" r="12" fill="#2563eb"/>
</svg>
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
        return "[Error: pdfplumber no instalado]"
    texto = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for pagina in pdf.pages:
            texto += (pagina.extract_text() or "") + "\n"
    return texto

def extraer_texto_docx(file_bytes: bytes) -> str:
    if not DOCX_SUPPORT:
        return "[Error: python-docx no instalado]"
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
    extensiones = [".txt", ".md", ".pdf", ".docx"]
    for archivo in BASE_DOCS_DIR.iterdir():
        if archivo.suffix.lower() in extensiones:
            if archivo.suffix.lower() in [".txt", ".md"]:
                docs[archivo.name] = archivo.read_text(encoding="utf-8", errors="ignore")
            elif archivo.suffix.lower() == ".pdf" and PDF_SUPPORT:
                docs[archivo.name] = extraer_texto_pdf(archivo.read_bytes())
            elif archivo.suffix.lower() == ".docx" and DOCX_SUPPORT:
                docs[archivo.name] = extraer_texto_docx(archivo.read_bytes())
    return docs

# ─── Contexto para el modelo ──────────────────────────────────────────────────
MAX_CHARS_POR_DOC = 4000

def construir_contexto(docs_base: dict, docs_sesion: dict) -> str:
    partes = []
    if docs_base:
        partes.append("=== DOCUMENTOS BASE (cargados por el administrador) ===")
        for nombre, texto in docs_base.items():
            partes.append(f"\n[Documento: {nombre}]\n{texto[:MAX_CHARS_POR_DOC]}")
    if docs_sesion:
        partes.append("\n=== DOCUMENTOS SUBIDOS POR EL USUARIO ===")
        for nombre, texto in docs_sesion.items():
            partes.append(f"\n[Documento: {nombre}]\n{texto[:MAX_CHARS_POR_DOC]}")
    return "\n".join(partes)

# ─── Session state ────────────────────────────────────────────────────────────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "docs_sesion" not in st.session_state:
    st.session_state.docs_sesion = {}

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📁 Documentos")

    st.subheader("📚 Base de conocimiento")
    docs_base = cargar_docs_base()
    if docs_base:
        for nombre in docs_base:
            st.write(f"📄 {nombre}")
    else:
        st.info("No hay documentos base todavía.\nAgregá archivos a la carpeta `base_docs/`.")

    st.divider()

    st.subheader("⬆️ Subí tu documento")
    archivos_subidos = st.file_uploader(
        "Formatos: PDF, TXT, DOCX",
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
                        st.success(f"✅ {archivo.name} cargado")
                    else:
                        st.warning(f"⚠️ No se pudo extraer texto de {archivo.name}")

    if st.session_state.docs_sesion:
        st.subheader("📂 Tus documentos")
        for nombre in list(st.session_state.docs_sesion.keys()):
            col1, col2 = st.columns([4, 1])
            col1.write(f"📄 {nombre}")
            if col2.button("🗑️", key=f"del_{nombre}", help=f"Eliminar {nombre}"):
                del st.session_state.docs_sesion[nombre]
                st.rerun()

    st.divider()

    if st.button("🔄 Nueva conversación", use_container_width=True):
        st.session_state.mensajes = []
        st.rerun()
    if st.button("🗑️ Limpiar todo (docs + chat)", use_container_width=True):
        st.session_state.docs_sesion = {}
        st.session_state.mensajes = []
        st.rerun()

# ─── Área principal ───────────────────────────────────────────────────────────
st.title("🤖 ChatDocs · UPC - Física")
st.caption("Consultá información de los documentos cargados — Base de conocimiento compartida + tus propios archivos")

total_docs = len(docs_base) + len(st.session_state.docs_sesion)
if total_docs == 0:
    st.warning("⚠️ No hay documentos cargados. El chatbot responderá con su conocimiento general. Cargá documentos desde el panel izquierdo.")
else:
    st.success(f"✅ {total_docs} documento(s) disponibles para consultar.")

st.divider()

for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.write(mensaje["content"])

if pregunta := st.chat_input("Hacé tu pregunta sobre los documentos..."):
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.write(pregunta)

    contexto = construir_contexto(docs_base, st.session_state.docs_sesion)

    system_prompt = """Sos un asistente educativo que responde preguntas basándose en los documentos proporcionados.

Reglas:
1. Respondé siempre en español.
2. Si la respuesta está en los documentos, usá esa información y mencioná el nombre del documento fuente entre corchetes: [Fuente: nombre_del_archivo].
3. Si la pregunta no puede responderse con los documentos disponibles, decilo claramente e intentá dar una respuesta general útil.
4. Sé claro, preciso y pedagógico en tus respuestas.
5. Si el usuario pregunta qué documentos hay disponibles, listálos.

""" + (f"Documentos disponibles para consultar:\n{contexto}" if contexto else "No hay documentos cargados actualmente.")

    mensajes_api = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.mensajes
    ]

    with st.chat_message("assistant"):
        with st.spinner("Analizando documentos..."):
            try:
                respuesta = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=mensajes_api,
                )
                texto_respuesta = respuesta.content[0].text
            except Exception as e:
                texto_respuesta = f"❌ Error al conectar con la API: {str(e)}"
        st.write(texto_respuesta)

    st.session_state.mensajes.append({"role": "assistant", "content": texto_respuesta})
