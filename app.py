import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
import matplotlib.pyplot as plt

# Configuración de la página
st.set_page_config(page_title="Control Caja Chica", layout="wide")

# Autenticación con Google Sheets usando secrets
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
client = gspread.authorize(creds)

# Nombre del documento de Google Sheets
NOMBRE_PLANILLA = "iacajas2025"

# Hojas dentro del documento
HOJAS = {
    "Movimientos Repuestos": "Movimientos Repuestos",
    "Resumen Repuestos": "Resumen Repuestos",
    "Movimientos Petróleo": "Movimientos Petróleo",
    "Resumen Petróleo": "Resumen Petróleo"
}

@st.cache_data
def cargar_hoja(nombre_hoja):
    sheet = client.open(NOMBRE_PLANILLA).worksheet(nombre_hoja)
    df = get_as_dataframe(sheet, evaluate_formulas=True)
    df = df.dropna(how="all")  # Quita filas completamente vacías
    return df

# Carga de datos
df_mov_repuestos = cargar_hoja(HOJAS["Movimientos Repuestos"])
df_resumen_repuestos = cargar_hoja(HOJAS["Resumen Repuestos"])
df_mov_petroleo = cargar_hoja(HOJAS["Movimientos Petróleo"])
df_resumen_petroleo = cargar_hoja(HOJAS["Resumen Petróleo"])

# Interfaz
st.title("Control de Caja Chica")

tab1, tab2 = st.tabs(["Repuestos", "Petróleo"])

def mostrar_resumen(df_resumen, caja):
    st.subheader("Resumen")
    cuatrimestres = df_resumen["Cuatrimestre"].dropna().unique()
    cuatrimestre = st.selectbox("Seleccionar cuatrimestre", cuatrimestres, key=f"cuatri_{caja}")
    filtro = df_resumen["Cuatrimestre"] == cuatrimestre
    datos = df_resumen[filtro].iloc[0]
    monto = datos["Monto"]
    gastado = datos["Total Gastado"]
    saldo = datos["Saldo Actual"]
    porc_gastado = (gastado / monto) * 100 if monto else 0
    porc_saldo = (saldo / monto) * 100 if monto else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Monto Asignado", f"${monto:,.2f}")
    col2.metric("Gastado", f"${gastado:,.2f}", f"{porc_gastado:.1f}%")
    col3.metric("Saldo", f"${saldo:,.2f}", f"{porc_saldo:.1f}%")

    fig, ax = plt.subplots()
    ax.pie([porc_gastado, porc_saldo], labels=["Gastado", "Saldo"], autopct="%1.1f%%", colors=["#e74c3c", "#2ecc71"])
    ax.set_title(f"Distribución del Cuatrimestre {cuatrimestre}")
    st.pyplot(fig)

def mostrar_movimientos(df_mov, caja):
    st.subheader("Movimientos")
    proveedor = st.selectbox("Filtrar por proveedor", ["Todos"] + df_mov["Proveedor"].dropna().unique().tolist(), key=f"prov_{caja}")
    if proveedor != "Todos":
        df_mov = df_mov[df_mov["Proveedor"] == proveedor]

    st.dataframe(df_mov, use_container_width=True)

    # Facturación por proveedor
    st.subheader("Monto facturado por proveedor")
    facturado = df_mov.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
    st.bar_chart(facturado)

with tab1:
    st.header("Caja Chica: Repuestos")
    mostrar_resumen(df_resumen_repuestos, "repuestos")
    mostrar_movimientos(df_mov_repuestos, "repuestos")

with tab2:
    st.header("Caja Chica: Petróleo")
    mostrar_resumen(df_resumen_petroleo, "petroleo")
    mostrar_movimientos(df_mov_petroleo, "petroleo")
