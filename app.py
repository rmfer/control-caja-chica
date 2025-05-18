import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe

# =========================
# Constantes y Configuración
# =========================
NOMBRE_PLANILLA = "iacajas2025"
HOJAS = {
    "Movimientos Repuestos": "Movimientos Repuestos",
    "Resumen Repuestos": "Resumen Repuestos",
    "Movimientos Petróleo": "Movimientos Petróleo",
    "Resumen Petróleo": "Resumen Petróleo",
}
COLUMNAS_REQUERIDAS = ["Cuatrimestre", "Proveedor", "Monto"]

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# =========================
# Autenticación y Carga de Datos
# =========================
@st.cache_data(ttl=3600, show_spinner="🔑 Autenticando con Google Sheets...")
def autenticar():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    return client

client = autenticar()

@st.cache_data(ttl=3600, show_spinner="📥 Cargando datos desde Google Sheets...")
def cargar_hoja(nombre_hoja):
    try:
        sheet = client.open(NOMBRE_PLANILLA).worksheet(nombre_hoja)
        df = get_as_dataframe(sheet, evaluate_formulas=True, dtype=str)
        df = df.dropna(how='all').dropna(axis=1, how='all')  # Elimina filas y columnas vacías
        df = df.replace('', pd.NA)  # Celdas vacías a NA
        return df
    except gspread.WorksheetNotFound:
        st.error(f"Hoja '{nombre_hoja}' no encontrada en la planilla.")
        return pd.DataFrame()

df_mov_repuestos = cargar_hoja(HOJAS["Movimientos Repuestos"])
df_mov_petroleo = cargar_hoja(HOJAS["Movimientos Petróleo"])

# =========================
# Funciones de Utilidad
# =========================
def obtener_cuatrimestres(df):
    if "Cuatrimestre" in df.columns:
        cuatri = pd.to_numeric(df["Cuatrimestre"], errors='coerce')
        cuatri = cuatri[(cuatri >= 1) & (cuatri <= 4)].dropna().unique()
        return sorted(cuatri.astype(int))
    return []

def obtener_proveedores(df):
    if "Proveedor" in df.columns:
        provs = df["Proveedor"].dropna().unique()
        provs = [p.strip() for p in provs if p and p.strip() != ""]
        return sorted(provs)
    return []

def filtrar_datos(df, cuatri, proveedor):
    df_filtered = df.copy()
    if "Cuatrimestre" in df_filtered.columns:
        df_filtered.loc[:, "Cuatrimestre"] = pd.to_numeric(df_filtered["Cuatrimestre"], errors='coerce')
        df_filtered = df_filtered[df_filtered["Cuatrimestre"] == cuatri]
    if proveedor != "Todos" and "Proveedor" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Proveedor"] == proveedor]
    return df_filtered

# =========================
# Sidebar y Filtros
# =========================
st.title("Control de Caja Chica 2025")
st.sidebar.header("Filtros")

cuatrimestres_default = [1, 2, 3, 4]
cuatrimestres_repuestos = obtener_cuatrimestres(df_mov_repuestos)
cuatrimestres_petroleo = obtener_cuatrimestres(df_mov_petroleo)
cuatrimestres = sorted(set(cuatrimestres_repuestos) | set(cuatrimestres_petroleo))
if not cuatrimestres:
    cuatrimestres = cuatrimestres_default

cuatri_sel = st.sidebar.selectbox(
    "Seleccione Cuatrimestre",
    cuatrimestres,
    index=0,
    help="Filtra los movimientos por cuatrimestre"
)

proveedores_repuestos = obtener_proveedores(df_mov_repuestos)
proveedores_petroleo = obtener_proveedores(df_mov_petroleo)
proveedores = sorted(set(proveedores_repuestos) | set(proveedores_petroleo))
if not proveedores:
    proveedores = []

proveedor_sel = st.sidebar.selectbox(
    "Seleccione Proveedor",
    options=["Todos"] + proveedores,
    index=0,
    help="Filtra los movimientos por proveedor específico"
)

cajas = ["Repuestos", "Petróleo"]
caja_sel = st.sidebar.selectbox(
    "Seleccione Caja",
    cajas,
    index=0,
    help="Elija la caja a analizar"
)

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Actualizar Datos desde Google Sheets"):
    st.cache_data.clear()
    st.experimental_memo.clear()
    st.experimental_rerun()

# =========================
# Filtrado y Validación de Datos
# =========================
if caja_sel == "Repuestos":
    df_filtrado = filtrar_datos(df_mov_repuestos, cuatri_sel, proveedor_sel)
else:
    df_filtrado = filtrar_datos(df_mov_petroleo, cuatri_sel, proveedor_sel)

# Validación de columnas requeridas
missing = [col for col in COLUMNAS_REQUERIDAS if col not in df_filtrado.columns]
if missing:
    st.error(f"Columnas faltantes en la hoja seleccionada: {', '.join(missing)}")
    st.stop()

# =========================
# Visualización de Datos
# =========================
st.subheader(f"Movimientos {caja_sel}")
st.caption(f"Cuatrimestre {cuatri_sel} | Proveedor: {proveedor_sel}")

if not df_filtrado.empty:
    df_display = df_filtrado.copy()
    # Conversión de columna 'Monto' a numérico para cálculos y formato
    df_display["Monto"] = pd.to_numeric(df_display["Monto"], errors="coerce").fillna(0)
    st.dataframe(
        df_display.style.format({"Monto": "ARS ${:,.2f}"}),
        use_container_width=True,
        hide_index=True
    )

    # =========================
    # Resumen Estadístico
    # =========================
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Gastado", f"${df_display['Monto'].sum():,.2f} ARS")
    with col2:
        st.metric("Promedio por Movimiento", f"${df_display['Monto'].mean():,.2f} ARS")
    with col3:
        st.metric("Movimientos Registrados", len(df_display))
else:
    st.info("No hay movimientos para los filtros seleccionados.")

# =========================
# (Aquí puedes agregar más gráficos, análisis, etc.)
# =========================
