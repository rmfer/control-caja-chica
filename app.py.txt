import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
from io import BytesIO
from PIL import Image

# ---------------------------
# Configuración de página
# ---------------------------
st.set_page_config(
    page_title="Control de Caja Chica",
    layout="centered",
    page_icon="💰"
)

# ---------------------------
# Cargar imagen del logo
# ---------------------------
st.image("logo.png", width=150)
st.title("Control de Caja Chica")
st.markdown("Visualización de saldos y movimientos por cuatrimestre.")

# ---------------------------
# Autenticación con Google
# ---------------------------
sheet_id = st.secrets["GOOGLE_SHEET_ID"]
credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
client = gspread.authorize(credentials)
sheet = client.open_by_key(sheet_id)

# ---------------------------
# Función para leer datos
# ---------------------------
@st.cache_data
def cargar_datos(nombre_hoja):
    hoja = sheet.worksheet(nombre_hoja)
    datos = hoja.get_all_records()
    df = pd.DataFrame(datos)
    columnas = df.columns.str.strip()
    df.columns = columnas
    return df

# ---------------------------
# Mostrar datos por tipo de caja
# ---------------------------
opciones = ["Resumen Repuestos", "Resumen Petróleo"]
seleccion = st.selectbox("Seleccioná una caja:", opciones)

df = cargar_datos(seleccion)

if not df.empty:
    st.dataframe(df)

    # Mostrar métricas clave
    for index, row in df.iterrows():
        cuatrimestre = row["Cuatrimestre"]
        monto = float(row["Monto"])
        gastado = float(row["Total Gastado"])
        saldo = float(row["Saldo Actual"])

        porcentaje_usado = (gastado / monto) * 100 if monto > 0 else 0
        porcentaje_restante = 100 - porcentaje_usado

        with st.expander(f"📌 {cuatrimestre}"):
            st.metric("Monto asignado", f"${monto:,.2f}")
            st.metric("Total gastado", f"${gastado:,.2f}")
            st.metric("Saldo restante", f"${saldo:,.2f}")
            st.progress(porcentaje_usado / 100, text=f"{porcentaje_usado:.1f}% utilizado")

else:
    st.warning("No hay datos disponibles.")

