import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import requests

st.set_page_config(page_title="Control de Caja Chica", layout="wide")

# --- Autenticación Google Sheets ---
scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope,
)
service = build("sheets", "v4", credentials=creds)

SPREADSHEET_ID = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

def leer_hoja(rango):
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=rango).execute()
    values = result.get("values", [])
    if not values:
        return pd.DataFrame()
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

# Sidebar para elegir hoja
hojas = ["Movimientos Repuestos", "Movimientos Petróleo"]
hoja_sel = st.sidebar.selectbox("Seleccionar hoja", hojas)

df = leer_hoja(hoja_sel)

# Convertir columnas numéricas si existen
for col in ["Monto"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

st.title("Datos de la hoja: " + hoja_sel)
st.dataframe(df)

# --- Chat IA simple con Huggingface ---
st.subheader("Consulta con IA")
user_input = st.text_input("Pregunta sobre las cajas chicas")

if user_input:
    API_URL = "https://api-inference.huggingface.co/models/bigscience/bloom"
    headers = {"Authorization": f"Bearer {st.secrets['huggingface_api_token']}"}
    payload = {"inputs": user_input}
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        respuesta = response.json()
        if isinstance(respuesta, list) and "generated_text" in respuesta[0]:
            st.write(respuesta[0]["generated_text"])
        else:
            st.write("No se pudo obtener una respuesta clara.")
    else:
        st.write(f"Error en la API: {response.status_code}")
