import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import requests

# Configuraciones iniciales
st.set_page_config(page_title="Control Caja Chica", layout="wide")

# Variables
SCOPE = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

# Autenticación con credenciales en secrets
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPE
)

service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Función para leer datos desde Google Sheets
@st.cache_data(ttl=300)
def cargar_datos(nombre_hoja):
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range=nombre_hoja).execute()
    values = result.get('values', [])
    if not values:
        return pd.DataFrame()
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

# Función para convertir columnas numéricas
def convertir_monto(valor):
    try:
        return float(valor)
    except:
        return 0.0

# Cargar datos de las 4 hojas
mov_repuestos = cargar_datos('Movimientos Repuestos')
res_repuestos = cargar_datos('Resumen Repuestos')
mov_petroleo = cargar_datos('Movimientos Petróleo')
res_petroleo = cargar_datos('Resumen Petróleo')

# Convertir columnas 'Monto' y 'Total Gastado' a float en resumen
for df in [res_repuestos, res_petroleo]:
    for col in ['Monto', 'Total Gastado', 'Saldo Actual']:
        if col in df.columns:
            df[col] = df[col].apply(convertir_monto)

# Panel lateral: filtros
st.sidebar.header("Filtros")

# Cuatrimestres disponibles (de ambas hojas de resumen)
cuatrimestres_repuestos = res_repuestos['Cuatrimestre'].unique() if not res_repuestos.empty else []
cuatrimestres_petroleo = res_petroleo['Cuatrimestre'].unique() if not res_petroleo.empty else []
cuatrimestres = sorted(set(cuatrimestres_repuestos).union(set(cuatrimestres_petroleo)))

cuatrimestre_seleccionado = st.sidebar.selectbox("Selecciona Cuatrimestre", options=['Todos'] + list(cuatrimestres))

# Proveedores disponibles (de movimientos)
proveedores_repuestos = mov_repuestos['Proveedor'].unique() if not mov_repuestos.empty else []
proveedores_petroleo = mov_petroleo['Proveedor'].unique() if not mov_petroleo.empty else []
proveedores = sorted(set(proveedores_repuestos).union(set(proveedores_petroleo)))

proveedor_seleccionado = st.sidebar.selectbox("Selecciona Proveedor", options=['Todos'] + list(proveedores))

# Filtrar datos según selección
def filtrar_df(df):
    if df.empty:
        return df
    dff = df.copy()
    if cuatrimestre_seleccionado != 'Todos' and 'Cuatrimestre' in dff.columns:
        dff = dff[dff['Cuatrimestre'] == cuatrimestre_seleccionado]
    if proveedor_seleccionado != 'Todos' and 'Proveedor' in dff.columns:
        dff = dff[dff['Proveedor'] == proveedor_seleccionado]
    return dff

mov_repuestos_filtrado = filtrar_df(mov_repuestos)
mov_petroleo_filtrado = filtrar_df(mov_petroleo)

# Mostrar resumen en columnas
st.title("Control de Caja Chica - Resumen")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Repuestos")
    if not res_repuestos.empty:
        resumen_repuestos_filtrado = filtrar_df(res_repuestos)
        st.dataframe(resumen_repuestos_filtrado)
    else:
        st.write("No hay datos de repuestos.")

with col2:
    st.subheader("Petróleo")
    if not res_petroleo.empty:
        resumen_petroleo_filtrado = filtrar_df(res_petroleo)
        st.dataframe(resumen_petroleo_filtrado)
    else:
        st.write("No hay datos de petróleo.")

# Mostrar movimientos filtrados en tablas plegables
st.subheader("Movimientos Repuestos filtrados")
st.dataframe(mov_repuestos_filtrado)

st.subheader("Movimientos Petróleo filtrados")
st.dataframe(mov_petroleo_filtrado)

# Chat IA con Huggingface para consultas
st.sidebar.header("Consulta IA")

def consultar_huggingface(prompt):
    API_URL = "https://api-inference.huggingface.co/models/gpt2"
    headers = {"Authorization": f"Bearer {st.secrets['huggingface_api_token']}"}
    payload = {"inputs": prompt}
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        # El resultado puede ser una lista con texto generado en 'generated_text'
        if isinstance(result, list) and 'generated_text' in result[0]:
            return result[0]['generated_text']
        else:
            return str(result)
    except Exception as e:
        return f"Error en consulta IA: {e}"

prompt_usuario = st.sidebar.text_area("Escribe tu consulta aquí:")

if st.sidebar.button("Consultar IA"):
    if prompt_usuario.strip():
        with st.spinner("Consultando IA..."):
            respuesta_ia = consultar_huggingface(prompt_usuario)
            st.sidebar.write("Respuesta IA:")
            st.sidebar.info(respuesta_ia)
    else:
        st.sidebar.warning("Por favor ingresa una consulta.")

