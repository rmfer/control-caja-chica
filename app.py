import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

st.set_page_config(page_title="Control Caja Chica", layout="wide")

# Definimos el scope para Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Cargamos credenciales desde secrets.toml
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

# ID de la planilla
SPREADSHEET_ID = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

# Nombre de las hojas que querés cargar
HOJAS = [
    "Movimientos Repuestos",
    "Resumen Repuestos",
    "Movimientos Petróleo",
    "Resumen Petróleo"
]

@st.cache_data(ttl=600)
def cargar_datos():
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    datos = {}
    for hoja in HOJAS:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=hoja).execute()
        values = result.get('values', [])
        if not values:
            datos[hoja] = pd.DataFrame()
        else:
            df = pd.DataFrame(values[1:], columns=values[0])
            datos[hoja] = df
    return datos

st.title("Control Caja Chica")

datos = cargar_datos()

# Mostrar resúmenes
for hoja in ["Resumen Repuestos", "Resumen Petróleo"]:
    st.subheader(hoja)
    if not datos[hoja].empty:
        st.dataframe(datos[hoja])
    else:
        st.write("No hay datos disponibles")

# Podés agregar filtros, gráficos o más lógica abajo según tus necesidades.
