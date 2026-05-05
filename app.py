import streamlit as st
import anthropic
import io
from pathlib import Path

# Intentamos importar librerías opcionales
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
    page_title="ChatDocs UPC - Física",
    page_icon="📚",
    layout="wide",
)

# ─── Cliente Anthropic ────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

client = get_client()

# ─── Carpeta de documentos base ───────────────────────────────────────────────
BASE_DOCS_DIR = Path("base_docs")
BASE_DOCS_DIR.mkdir(exist_ok=True)

# ─── Funciones de extracción de texto ─────────────────────────────────────────
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
    elif nombre.endswith(".txt") or nombre.endswith(".md"):
        return contenido.decode("utf-8", errors="ignore")
    return ""

# ─── Carga de documentos base (desde la carpeta del proyecto) ─────────────────
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

# ─── Construcción del contexto para el modelo ─────────────────────────────────
MAX_CHARS_POR_DOC = 4000  # límite por documento para no exceder el contexto

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

    # Documentos base
    st.subheader("📚 Base de conocimiento")
    docs_base = cargar_docs_base()
    if docs_base:
        for nombre in docs_base:
            st.write(f"📄 {nombre}")
    else:
        st.info("No hay documentos base todavía.\nAgregá archivos a la carpeta `base_docs/`.")

    st.divider()

    # Subida de documentos por el usuario
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

    # Lista de documentos de sesión
    if st.session_state.docs_sesion:
        st.subheader("📂 Tus documentos")
        for nombre in st.session_state.docs_sesion:
            col1, col2 = st.columns([4, 1])
            col1.write(f"📄 {nombre}")
            if col2.button("🗑️", key=f"del_{nombre}", help=f"Eliminar {nombre}"):
                del st.session_state.docs_sesion[nombre]
                st.rerun()

    st.divider()

    # Botón de limpiar sesión
    if st.button("🔄 Nueva conversación", use_container_width=True):
        st.session_state.mensajes = []
        st.rerun()

    if st.button("🗑️ Limpiar todo (docs + chat)", use_container_width=True):
        st.session_state.docs_sesion = {}
        st.session_state.mensajes = []
        st.rerun()

# ─── Área principal ───────────────────────────────────────────────────────────
st.title("🤖 ChatDocs - UPC - FÍSICA")
st.caption("Consultá información de los documentos cargados — Base de conocimiento compartida + tus propios archivos")

# Mostrar estado de documentos disponibles
total_docs = len(docs_base) + len(st.session_state.docs_sesion)
if total_docs == 0:
    st.warning("⚠️ No hay documentos cargados. El chatbot responderá con su conocimiento general. Cargá documentos desde el panel izquierdo.")
else:
    st.success(f"✅ {total_docs} documento(s) disponibles para consultar.")

st.divider()

# Mostrar historial de mensajes
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.write(mensaje["content"])

# Input del usuario
if pregunta := st.chat_input("Hacé tu pregunta sobre los documentos..."):
    # Agregar al historial
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.write(pregunta)

    # Construir el contexto con todos los documentos disponibles
    contexto = construir_contexto(docs_base, st.session_state.docs_sesion)

    system_prompt = """Sos un asistente educativo que responde preguntas basándose en los documentos proporcionados.

Reglas:
1. Respondé siempre en español.
2. Si la respuesta está en los documentos, usá esa información y mencioná entre corchetes el nombre del documento fuente, por ejemplo: [Fuente: nombre_del_archivo.pdf].
3. Si la pregunta no puede responderse con los documentos disponibles, decilo claramente e intentá dar una respuesta general útil.
4. Sé claro, preciso y pedagógico en tus respuestas.
5. Si el usuario pregunta qué documentos hay disponibles, listálos.

""" + (f"Documentos disponibles para consultar:\n{contexto}" if contexto else "No hay documentos cargados actualmente.")

    # Preparar mensajes para la API (historial completo)
    mensajes_api = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.mensajes
    ]

    # Llamada a la API
    with st.chat_message("assistant"):
        with st.spinner("Analizando documentos..."):
            try:
                respuesta = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=mensajes_api,
                )
                texto_respuesta = respuesta.content[0].text
            except Exception as e:
                texto_respuesta = f"❌ Error al conectar con la API: {str(e)}"

        st.write(texto_respuesta)

    # Guardar respuesta en el historial
    st.session_state.mensajes.append({"role": "assistant", "content": texto_respuesta})
