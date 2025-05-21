import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import requests

# --- Configuración ---
st.set_page_config(page_title="Control de Caja Chica", layout="wide")

# --- Autenticación Google Sheets ---
scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope,
)
service = build("sheets", "v4", credentials=creds)

# ID de la planilla de Google Sheets
SPREADSHEET_ID = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

# Función para leer datos de una hoja
def leer_hoja(nombre_hoja):
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=nombre_hoja).execute()
    values = result.get("values", [])
    if not values:
        return pd.DataFrame()
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

# --- Carga datos ---
df_repuestos = leer_hoja("Movimientos Repuestos")
df_petroleo = leer_hoja("Movimientos Petróleo")

# Conversión de columnas numéricas
for df in [df_repuestos, df_petroleo]:
    for col in ["Monto"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

# --- Filtros panel lateral ---
st.sidebar.title("Filtros")

# Cuatrimestres disponibles
cuatrimestres = sorted(df_repuestos["Cuatrimestre"].unique()) if "Cuatrimestre" in df_repuestos.columns else []
cuatrimestre_seleccionado = st.sidebar.selectbox("Cuatrimestre", ["Todos"] + cuatrimestres)

# Proveedores disponibles (combinados)
proveedores_repuestos = df_repuestos["Proveedor"].unique() if "Proveedor" in df_repuestos.columns else []
proveedores_petroleo = df_petroleo["Proveedor"].unique() if "Proveedor" in df_petroleo.columns else []
proveedores = sorted(set(proveedores_repuestos) | set(proveedores_petroleo))
proveedor_seleccionado = st.sidebar.selectbox("Proveedor", ["Todos"] + list(proveedores))

# --- Función para filtrar datos ---
def aplicar_filtros(df):
    if "Cuatrimestre" in df.columns and cuatrimestre_seleccionado != "Todos":
        df = df[df["Cuatrimestre"] == cuatrimestre_seleccionado]
    if "Proveedor" in df.columns and proveedor_seleccionado != "Todos":
        df = df[df["Proveedor"] == proveedor_seleccionado]
    return df

df_repuestos_filtrado = aplicar_filtros(df_repuestos)
df_petroleo_filtrado = aplicar_filtros(df_petroleo)

# --- Mostrar métricas ---
st.title("Control de Caja Chica - Resumen")

col1, col2 = st.columns(2)

with col1:
    st.header("Repuestos")
    total_repuestos = df_repuestos_filtrado["Monto"].sum()
    st.metric("Total Gastado", f"${total_repuestos:,.2f}")

with col2:
    st.header("Petróleo")
    total_petroleo = df_petroleo_filtrado["Monto"].sum()
    st.metric("Total Gastado", f"${total_petroleo:,.2f}")

# --- Mostrar tablas ---
st.subheader("Movimientos Repuestos")
st.dataframe(df_repuestos_filtrado)

st.subheader("Movimientos Petróleo")
st.dataframe(df_petroleo_filtrado)

# --- Chat IA simple con Huggingface ---
st.subheader("Consulta con IA")
user_input = st.text_input("Pregunta sobre las cajas chicas")

if user_input:
    API_URL = "https://api-inference.huggingface.co/models/bigscience/bloom"
    headers = {"Authorization": f"Bearer {st.secrets['huggingface']['api_token']}"}
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
