import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe

# Constantes
NOMBRE_PLANILLA = "iacajas2025"
HOJAS = {
    "Movimientos Repuestos": "Movimientos Repuestos",
    "Resumen Repuestos": "Resumen Repuestos",
    "Movimientos Petróleo": "Movimientos Petróleo",
    "Resumen Petróleo": "Resumen Petróleo",
}

# Autenticación con Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

@st.cache_data(ttl=3600)
def autenticar():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client

client = autenticar()

@st.cache_data(ttl=3600)
def cargar_hoja(nombre_hoja):
    sheet = client.open(NOMBRE_PLANILLA).worksheet(nombre_hoja)
    df = get_as_dataframe(sheet, evaluate_formulas=True, dtype=str)
    df = df.dropna(how='all')  # eliminar filas vacías
    return df

df_mov_repuestos = cargar_hoja(HOJAS["Movimientos Repuestos"])
df_mov_petroleo = cargar_hoja(HOJAS["Movimientos Petróleo"])

# Funciones para obtener listas únicas limpias
def obtener_cuatrimestres(df):
    if "Cuatrimestre" in df.columns:
        cuatri = pd.to_numeric(df["Cuatrimestre"], errors='coerce').dropna().unique()
        return sorted(int(x) for x in cuatri if not pd.isna(x))
    return []

def obtener_proveedores(df):
    if "Proveedor" in df.columns:
        provs = df["Proveedor"].dropna().unique()
        provs = [p for p in provs if p.strip() != ""]
        return sorted(provs)
    return []

# Sidebar y filtros
st.title("Control de Caja Chica 2025")

st.sidebar.header("Filtros")

cuatrimestres_default = [1, 2, 3, 4]

cuatrimestres_repuestos = obtener_cuatrimestres(df_mov_repuestos)
cuatrimestres_petroleo = obtener_cuatrimestres(df_mov_petroleo)
cuatrimestres = sorted(set(cuatrimestres_repuestos) | set(cuatrimestres_petroleo))
if not cuatrimestres:
    cuatrimestres = cuatrimestres_default

cuatri_sel = st.sidebar.selectbox("Seleccione Cuatrimestre", cuatrimestres, index=0)

proveedores_repuestos = obtener_proveedores(df_mov_repuestos)
proveedores_petroleo = obtener_proveedores(df_mov_petroleo)
proveedores = sorted(set(proveedores_repuestos) | set(proveedores_petroleo))
if not proveedores:
    proveedores = ["Todos"]

proveedor_sel = st.sidebar.selectbox("Seleccione Proveedor", proveedores, index=0)

cajas = ["Repuestos", "Petróleo"]
caja_sel = st.sidebar.selectbox("Seleccione Caja", cajas, index=0)

st.sidebar.markdown("---")

# Filtrar los datos según selección

def filtrar_datos(df, cuatri, proveedor):
    df_filtered = df.copy()
    df_filtered["Cuatrimestre"] = pd.to_numeric(df_filtered["Cuatrimestre"], errors='coerce')
    df_filtered = df_filtered[df_filtered["Cuatrimestre"] == cuatri]
    if proveedor != "Todos":
        df_filtered = df_filtered[df_filtered["Proveedor"] == proveedor]
    return df_filtered

if caja_sel == "Repuestos":
    df_filtrado = filtrar_datos(df_mov_repuestos, cuatri_sel, proveedor_sel)
else:
    df_filtrado = filtrar_datos(df_mov_petroleo, cuatri_sel, proveedor_sel)

st.subheader(f"Movimientos {caja_sel} - Cuatrimestre {cuatri_sel} - Proveedor: {proveedor_sel}")
st.dataframe(df_filtrado)

# Aquí puedes continuar agregando gráficos, cálculos de saldo, porcentajes, etc.
