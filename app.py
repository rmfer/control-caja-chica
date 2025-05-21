import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests

# Autenticación con Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

# Cargar hojas de cálculo
SHEET_NAME = "iacajas2025"
hoja_mov_repuestos = client.open(SHEET_NAME).worksheet("Movimientos Repuestos")
hoja_res_repuestos = client.open(SHEET_NAME).worksheet("Resumen Repuestos")
hoja_mov_petroleo = client.open(SHEET_NAME).worksheet("Movimientos Petróleo")
hoja_res_petroleo = client.open(SHEET_NAME).worksheet("Resumen Petróleo")

# Convertir a DataFrames
df_mov_repuestos = pd.DataFrame(hoja_mov_repuestos.get_all_records())
df_res_repuestos = pd.DataFrame(hoja_res_repuestos.get_all_records())
df_mov_petroleo = pd.DataFrame(hoja_mov_petroleo.get_all_records())
df_res_petroleo = pd.DataFrame(hoja_res_petroleo.get_all_records())

# Función para consultar Hugging Face
def consultar_huggingface(prompt: str):
    API_URL = "https://api-inference.huggingface.co/models/bigscience/bloom-560m"
    headers = {"Authorization": f"Bearer {st.secrets['huggingface']['token']}"}
    payload = {"inputs": prompt}
    response = requests.post(API_URL, headers=headers, json=payload)

    try:
        respuesta = response.json()
    except Exception:
        st.error("No se pudo decodificar la respuesta como JSON.")
        st.text("Respuesta cruda de HuggingFace:")
        st.text(response.text)
        return "Error al procesar la respuesta de la IA."

    if isinstance(respuesta, list) and len(respuesta) > 0 and "generated_text" in respuesta[0]:
        return respuesta[0]["generated_text"]
    elif isinstance(respuesta, dict) and "error" in respuesta:
        return "Error de la API: " + respuesta["error"]
    else:
        return str(respuesta)

# Interfaz principal
def main():
    st.title("Control de Caja Chica con IA 🤖💸")

    st.subheader("Movimientos - Repuestos")
    st.dataframe(df_mov_repuestos)

    st.subheader("Resumen - Repuestos")
    st.dataframe(df_res_repuestos)

    st.subheader("Movimientos - Petróleo")
    st.dataframe(df_mov_petroleo)

    st.subheader("Resumen - Petróleo")
    st.dataframe(df_res_petroleo)

    st.subheader("Consultá a la IA 🤔")
    pregunta = st.text_input("¿Qué querés saber?")
    if st.button("Consultar"):
        if pregunta.strip():
            respuesta = consultar_huggingface(pregunta)
            st.subheader("Respuesta:")
            st.write(respuesta)
        else:
            st.warning("Por favor escribí una pregunta.")

if __name__ == "__main__":
    main()
