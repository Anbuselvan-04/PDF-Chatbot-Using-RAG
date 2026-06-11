import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# ==========================================
# GEMINI API CONFIGURATION
# ==========================================

GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

genai.configure(api_key=GEMINI_API_KEY)

model_gemini = genai.GenerativeModel(
    "gemini-2.5-flash"
)

# ==========================================
# TEXT EXTRACTION
# ==========================================

def extract_text(pdf_file):
    text = ""

    reader = PdfReader(pdf_file)

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


# ==========================================
# TEXT CHUNKING
# ==========================================

def split_text(text, chunk_size=500):
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])

    return chunks


# ==========================================
# EMBEDDING MODEL
# ==========================================

@st.cache_resource
def load_embedding_model():
    return SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

embedding_model = load_embedding_model()


# ==========================================
# CREATE FAISS INDEX
# ==========================================

def create_vector_store(chunks):

    embeddings = embedding_model.encode(
        chunks
    )

    embeddings = np.array(
        embeddings,
        dtype=np.float32
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(
        dimension
    )

    index.add(embeddings)

    return index, embeddings


# ==========================================
# RETRIEVE RELEVANT CHUNKS
# ==========================================

def retrieve_chunks(question,
                    chunks,
                    index):

    question_embedding = embedding_model.encode(
        [question]
    )

    question_embedding = np.array(
        question_embedding,
        dtype=np.float32
    )

    k = min(3, len(chunks))

    distances, indices = index.search(
        question_embedding,
        k
    )

    relevant_chunks = []

    for idx in indices[0]:
        relevant_chunks.append(
            chunks[idx]
        )

    return relevant_chunks


# ==========================================
# GEMINI RESPONSE
# ==========================================

def get_answer(question,
               relevant_chunks):

    context = "\n".join(
        relevant_chunks
    )

    prompt = f"""
You are a PDF Question Answering Assistant.

Answer ONLY using the provided context.

If the answer is not available in the context,
reply:
"Answer not found in the document."

CONTEXT:
{context}

QUESTION:
{question}
"""

    response = model_gemini.generate_content(
        prompt
    )

    return response.text


# ==========================================
# STREAMLIT UI
# ==========================================

st.set_page_config(
    page_title="PDF RAG Chatbot",
    page_icon="📄"
)

st.title(
    "📄 PDF Question Answering using RAG"
)

uploaded_file = st.file_uploader(
    "Upload PDF",
    type="pdf"
)

if uploaded_file:

    with st.spinner(
        "Reading PDF..."
    ):

        text = extract_text(
            uploaded_file
        )

        chunks = split_text(
            text
        )

        index, embeddings = create_vector_store(
            chunks
        )

    st.success(
        "PDF Processed Successfully!"
    )

    question = st.text_input(
        "Ask a Question from PDF"
    )

    if question:

        with st.spinner(
            "Searching Answer..."
        ):

            relevant_chunks = retrieve_chunks(
                question,
                chunks,
                index
            )

            answer = get_answer(
                question,
                relevant_chunks
            )

        st.subheader(
            "Answer"
        )

        st.write(
            answer
        )

        with st.expander(
            "Retrieved Context"
        ):
            for chunk in relevant_chunks:
                st.write(chunk)
                st.write("---")