import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import locale
import re
import plotly.graph_objects as go

# --- Configuración de la página ---
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

# Inicializar variable de estado para controlar la página
if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"

def cargar_hoja(nombre_hoja):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["google_service_account"], scope
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key("1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro").worksheet(nombre_hoja)
        df = pd.DataFrame(sheet.get_all_records())
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"No se pudo cargar la hoja '{nombre_hoja}': {e}")
        return pd.DataFrame()

def validar_columnas(df, columnas_requeridas):
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        st.error(f"Faltan columnas en los datos: {', '.join(faltantes)}")
        st.stop()

def convertir_monto(valor, tipo_caja):
    if pd.isna(valor):
        return 0.0
    texto = str(valor).strip()
    try:
        texto = re.sub(r'\.', '', texto)
        texto = texto.replace(',', '.')
        return float(texto)
    except ValueError:
        return 0.0

def formatear_moneda(valor):
    try:
        locale.setlocale(locale.LC_ALL, 'es_AR.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')
    try:
        return locale.currency(valor, grouping=True)
    except Exception:
        return f"${valor:,.2f}"

def normalizar_cuatrimestre(valor):
    if pd.isna(valor):
        return ''
    valor_str = str(valor).strip()
    match = re.match(r'(\d)', valor_str)
    if match:
        return match.group(1)
    return valor_str

# --- Carga de datos ---
mov_repuestos = cargar_hoja("Movimientos Repuestos")
mov_petroleo = cargar_hoja("Movimientos Petróleo")
res_repuestos = cargar_hoja("Resumen Repuestos")
res_petroleo = cargar_hoja("Resumen Petróleo")

# Asegurar columna 'Caja'
if "Caja" not in mov_repuestos.columns:
    mov_repuestos["Caja"] = "Repuestos"
if "Caja" not in mov_petroleo.columns:
    mov_petroleo["Caja"] = "Petróleo"

res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"

# Columnas esperadas (incluyendo 'Área')
columnas_esperadas_mov = ["Monto", "Cuatrimestre", "Proveedor", "Caja", "Área"]
columnas_esperadas_resumen = ["Cuatrimestre", "Monto", "Total Gastado", "Saldo Actual", "Caja"]

for df in [mov_repuestos, mov_petroleo]:
    validar_columnas(df, columnas_esperadas_mov)
for df in [res_repuestos, res_petroleo]:
    validar_columnas(df, columnas_esperadas_resumen)

# Convertir montos a float
for col in ["Monto", "Total Gastado", "Saldo Actual"]:
    res_repuestos[col] = res_repuestos[col].apply(lambda x: convertir_monto(x, "Repuestos"))
    res_petroleo[col] = res_petroleo[col].apply(lambda x: convertir_monto(x, "Petróleo"))

mov_repuestos["Monto"] = mov_repuestos["Monto"].apply(lambda x: convertir_monto(x, "Repuestos"))
mov_petroleo["Monto"] = mov_petroleo["Monto"].apply(lambda x: convertir_monto(x, "Petróleo"))

#
