import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib

st.set_page_config(page_title="Movies Dashboard", layout="wide")

@st.cache_resource
def get_db():
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_db()

@st.cache_data
def read_movies_as_df(collection_name="movies") -> pd.DataFrame:
    docs = db.collection(collection_name).stream()
    data = []
    for doc in docs:
        row = doc.to_dict()
        row["doc_id"] = doc.id
        data.append(row)
    return pd.DataFrame(data)

def make_doc_id(name, company, director, genre):
    raw = f"{name}|{company}|{director}|{genre}".lower().strip()
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def insert_movie(name, company, director, genre, collection_name="movies"):
    doc_id = make_doc_id(name, company, director, genre)
    db.collection(collection_name).document(doc_id).set({
        "name": name,
        "company": company,
        "director": director,
        "genre": genre
    })

df = read_movies_as_df("movies")

st.title("🎬 Movies Dashboard (Firestore + Streamlit)")
st.caption("Base de 1000 filmes migrados desde CSV a Firestore.")

st.sidebar.header("Controles")

show_all = st.sidebar.checkbox("Mostrar todos los filmes")
if show_all:
    st.subheader("📋 Todos los filmes")
    st.dataframe(df.drop(columns=["doc_id"], errors="ignore"), use_container_width=True)

st.divider()

st.sidebar.subheader("🔎 Buscar por título")
title_query = st.sidebar.text_input("Escribe parte del título")
search_btn = st.sidebar.button("Buscar")
if search_btn:
    q = (title_query or "").strip().lower()
    results = df[df["name"].str.lower().str.contains(q, na=False)] if q else df.iloc[0:0]
    st.subheader(f"Resultados por título: {len(results)}")
    st.dataframe(results.drop(columns=["doc_id"], errors="ignore"), use_container_width=True)

st.divider()

st.sidebar.subheader("🎥 Filtrar por director")
directors = sorted(df["director"].dropna().unique().tolist()) if not df.empty else []
director_sel = st.sidebar.selectbox("Selecciona un director", directors) if directors else None
filter_btn = st.sidebar.button("Filtrar director")
if filter_btn and director_sel:
    results = df[df["director"] == director_sel]
    st.subheader(f"Filmes de {director_sel}: {len(results)}")
    st.dataframe(results.drop(columns=["doc_id"], errors="ignore"), use_container_width=True)

st.divider()

st.sidebar.subheader("➕ Insertar filme")
with st.sidebar.form("insert_form"):
    name = st.text_input("Título (name)")
    company = st.text_input("Compañía (company)")
    director = st.text_input("Director (director)")
    genre = st.text_input("Género (genre)")
    submitted = st.form_submit_button("Guardar")

if submitted:
    if not all([name.strip(), company.strip(), director.strip(), genre.strip()]):
        st.sidebar.error("Completa todos los campos.")
    else:
        insert_movie(name.strip(), company.strip(), director.strip(), genre.strip())
        st.sidebar.success("Filme insertado ✅")
        st.cache_data.clear()
        st.rerun()

if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total filmes", len(df))
    c2.metric("Directores únicos", df["director"].nunique())
    c3.metric("Géneros únicos", df["genre"].nunique())
