import streamlit as st
import pandas as pd
import openai
import matplotlib.pyplot as plt
import openpyxl
import datetime
import pyttsx3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import speech_recognition as sr
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

engine = pyttsx3.init()

def conectar_db():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        st.error(f"No se pudo conectar a la base de datos: {e}")
        return None

def crear_tablas(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario_id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            email TEXT
        );
        """)
        conn.commit()

def insertar_usuario(conn, usuario_id, nombre, email=None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO usuarios (usuario_id, nombre, email)
            VALUES (%s, %s, %s)
            ON CONFLICT (usuario_id) DO NOTHING;
        """, (usuario_id, nombre, email))
        conn.commit()

def capturar_nombre_usuario():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Di tu nombre para que Cerberu lo aprenda...")
        audio = r.listen(source)
    try:
        nombre = r.recognize_google(audio, language="es-ES")
        st.success(f"Hola {nombre}, encantado de conocerte.")
        engine.say(f"Hola {nombre}, encantado de conocerte.")
        engine.runAndWait()
        return nombre
    except sr.UnknownValueError:
        st.warning("No entendí tu nombre. Intenta de nuevo.")
        return None

def cargar_datos(archivo):
    df = pd.read_excel(archivo)
    df['fecha_cancelacion'] = pd.to_datetime(df['fecha_cancelacion'], errors='coerce')
    df['fecha_inicio'] = pd.to_datetime(df['fecha_inicio'], errors='coerce')
    return df

def calcular_churn(df):
    cancelados = df[df['estado'] == 'cancelado']
    total = len(df)
    churn_rate = len(cancelados) / total if total > 0 else 0
    return churn_rate, len(cancelados), total

def graficar_estados(df):
    estado_counts = df['estado'].value_counts()
    fig, ax = plt.subplots()
    estado_counts.plot(kind='bar', ax=ax, color=['green', 'red', 'blue'])
    ax.set_title("Estado de las suscripciones")
    st.pyplot(fig)

def responder_pregunta(df, pregunta):
    contexto = df.head(20).to_csv(index=False)
    prompt = (
        f"Eres un analista de datos. Aquí tienes datos de suscripciones:\n{contexto}\n"
        f"Responde la siguiente pregunta basada en los datos: {pregunta}"
    )
    respuesta = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Eres un experto en análisis de datos."},
            {"role": "user", "content": prompt}
        ]
    )
    return respuesta.choices[0].message['content']

st.set_page_config(page_title="Cerberu", page_icon="🧠")
st.title("🧠 Cerberu - Agente IA de Suscripciones")

if "nombre_usuario" not in st.session_state:
    if st.button("🎤 Di tu nombre para iniciar"):
        nombre = capturar_nombre_usuario()
        if nombre:
            st.session_state.nombre_usuario = nombre
            conn = conectar_db()
            if conn:
                crear_tablas(conn)
                insertar_usuario(conn, usuario_id=nombre.lower(), nombre=nombre)
                conn.close()

if "nombre_usuario" in st.session_state:
    nombre = st.session_state.nombre_usuario
    st.success(f"Bienvenido {nombre}, ¿en qué puedo ayudarte hoy?")
    engine.say(f"Bienvenido {nombre}")
    engine.runAndWait()

    archivo = st.file_uploader("📁 Carga tu archivo Excel con suscripciones", type=["xlsx"])

    if archivo:
        df = cargar_datos(archivo)
        st.subheader("👀 Vista previa")
        st.dataframe(df.head())

        churn, cancelados, total = calcular_churn(df)
        st.metric("📉 Churn Rate", f"{churn:.2%}")
        st.metric("❌ Cancelados", cancelados)
        st.metric("✅ Total suscripciones", total)

        st.subheader("📊 Gráfico")
        graficar_estados(df)

        st.subheader("💬 Pregunta a Cerberu")
        pregunta = st.text_input("¿Qué quieres saber?")
        if pregunta:
            if nombre.lower() in pregunta.lower():
                st.info(f"¡Hola {nombre}, estoy atento a tu pregunta!")
                engine.say(f"Hola {nombre}, dime")
                engine.runAndWait()

            respuesta = responder_pregunta(df, pregunta)
            st.write("🤖 Cerberu:", respuesta)
            engine.say(respuesta)
            engine.runAndWait()

st.markdown("---")
st.caption("Desarrollado por Adolfo D.S")
