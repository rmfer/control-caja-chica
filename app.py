import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe
import matplotlib.pyplot as plt

# Configuración inicial
st.set_page_config(page_title="Control de Caja Chica", layout="wide")

# Nombre de la planilla
NOMBRE_PLANILLA = "iacajas2025"

# Nombres de hojas
HOJAS = {
    "Movimientos Repuestos": "Movimientos Repuestos",
    "Resumen Repuestos": "Resumen Repuestos",
    "Movimientos Petróleo": "Movimientos Petróleo",
    "Resumen Petróleo": "Resumen Petróleo"
}

# Autenticación con Google Sheets desde st.secrets
@st.cache_resource
def autenticar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    return client

# Cargar hoja de cálculo
@st.cache_data
def cargar_hoja(nombre_hoja):
    client = autenticar_google()
    sheet = client.open(NOMBRE_PLANILLA).worksheet(nombre_hoja)
    df = get_as_dataframe(sheet, evaluate_formulas=True)
    df = df.dropna(how="all")  # Eliminar filas completamente vacías
    return df

# Título principal
st.title("📊 Control de Caja Chica 2025")

# Cargar hojas
df_mov_repuestos = cargar_hoja(HOJAS["Movimientos Repuestos"])
df_resumen_repuestos = cargar_hoja(HOJAS["Resumen Repuestos"])
df_mov_petroleo = cargar_hoja(HOJAS["Movimientos Petróleo"])
df_resumen_petroleo = cargar_hoja(HOJAS["Resumen Petróleo"])

# Mostrar resumen de cada caja
st.subheader("Resumen General")
col1, col2 = st.columns(2)

with col1:
    st.metric("💡 Repuestos - Saldo Actual", f"$ {df_resumen_repuestos['Saldo Actual'].iloc[-1]:,.2f}")
    st.metric("🔧 Repuestos - Total Gastado", f"$ {df_resumen_repuestos['Total Gastado'].iloc[-1]:,.2f}")

with col2:
    st.metric("⛽ Petróleo - Saldo Actual", f"$ {df_resumen_petroleo['Saldo Actual'].iloc[-1]:,.2f}")
    st.metric("🧾 Petróleo - Total Gastado", f"$ {df_resumen_petroleo['Total Gastado'].iloc[-1]:,.2f}")

# Filtro por cuatrimestre y proveedor
st.subheader("🔎 Filtro de Movimientos")
cuatrimestre = st.selectbox("Seleccionar cuatrimestre", sorted(df_mov_repuestos["Cuatrimestre"].dropna().unique()))
proveedor = st.selectbox("Seleccionar proveedor", sorted(df_mov_repuestos["Proveedor"].dropna().unique()))

# Filtros aplicados
df_filtro_rep = df_mov_repuestos[
    (df_mov_repuestos["Cuatrimestre"] == cuatrimestre) &
    (df_mov_repuestos["Proveedor"] == proveedor)
]

df_filtro_pet = df_mov_petroleo[
    (df_mov_petroleo["Cuatrimestre"] == cuatrimestre) &
    (df_mov_petroleo["Proveedor"] == proveedor)
]

# Mostrar resultados
st.subheader("🧾 Movimientos Filtrados")
st.write("### Repuestos")
st.dataframe(df_filtro_rep)
st.write("### Petróleo")
st.dataframe(df_filtro_pet)

# Gráfico simple (opcional)
st.subheader("📈 Consumo por proveedor (Repuestos)")
fig, ax = plt.subplots()
df_mov_repuestos.groupby("Proveedor")["Monto"].sum().plot(kind="bar", ax=ax)
ax.set_ylabel("Monto Total")
st.pyplot(fig)
