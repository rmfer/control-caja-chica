import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF

# Configuración de la página Streamlit (debe ser la primera línea relacionada con st)
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

# Autenticación Google Sheets
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet_id = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

# Funciones para convertir montos correctamente
def convertir_monto_repuestos(valor):
    if pd.isna(valor):
        return 0.0
    texto = str(valor).strip()
    texto = texto.replace(".", "")  # Quitar separador de miles
    texto = texto.replace(",", ".")  # Reemplazar decimal
    try:
        return float(texto)
    except:
        return 0.0

def convertir_monto_petroleo(valor):
    if pd.isna(valor):
        return 0.0
    texto = str(valor).strip()
    texto = texto.replace(",", ".")  # Reemplazar decimal
    try:
        return float(texto)
    except:
        return 0.0

# Cargar datos desde Google Sheets
mov_repuestos = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Movimientos Repuestos").get_all_records())
res_repuestos = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Resumen Repuestos").get_all_records())
mov_petroleo = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Movimientos Petróleo").get_all_records())
res_petroleo = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Resumen Petróleo").get_all_records())

# Convertir columnas numéricas con formato correcto
for col in ["Monto", "Total Gastado", "Saldo Actual"]:
    if col in res_repuestos.columns:
        res_repuestos[col] = res_repuestos[col].apply(convertir_monto_repuestos)
    if col in res_petroleo.columns:
        res_petroleo[col] = res_petroleo[col].apply(convertir_monto_petroleo)

if "Monto" in mov_repuestos.columns:
    mov_repuestos["Monto"] = mov_repuestos["Monto"].apply(convertir_monto_repuestos)
if "Monto" in mov_petroleo.columns:
    mov_petroleo["Monto"] = mov_petroleo["Monto"].apply(convertir_monto_petroleo)

# Aquí continúa tu lógica para mostrar datos, gráficos, filtros, etc.

# Ejemplo básico de mostrar DataFrames corregidos
st.title("Control de Cajas Chicas 2025")

st.header("Movimientos Repuestos")
st.dataframe(mov_repuestos)

st.header("Resumen Repuestos")
st.dataframe(res_repuestos)

st.header("Movimientos Petróleo")
st.dataframe(mov_petroleo)

st.header("Resumen Petróleo")
st.dataframe(res_petroleo)

# Resto del código para cálculos, gráficos y exportación PDF
# ...

