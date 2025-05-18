import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import locale
import re

# --- Configuración de la página ---
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

# Configurar locale para formateo de moneda (ajustar según sistema)
try:
    locale.setlocale(locale.LC_ALL, 'es_AR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

# --- Autenticación con Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["google_service_account"], scope
)
client = gspread.authorize(credentials)

sheet_id = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

# --- Funciones ---
@st.cache_data(ttl=3600)
def cargar_hoja(nombre_hoja):
    try:
        sheet = client.open_by_key(sheet_id).worksheet(nombre_hoja)
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

def convertir_monto(valor):
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
        return locale.currency(valor, grouping=True)
    except Exception:
        return f"${valor:,.2f}"

# --- Carga de datos ---
mov_repuestos = cargar_hoja("Movimientos Repuestos")
mov_petroleo = cargar_hoja("Movimientos Petróleo")
res_repuestos = cargar_hoja("Resumen Repuestos")
res_petroleo = cargar_hoja("Resumen Petróleo")

# Añadir columna 'Caja' si no existe
if "Caja" not in mov_repuestos.columns:
    mov_repuestos["Caja"] = "Repuestos"
if "Caja" not in mov_petroleo.columns:
    mov_petroleo["Caja"] = "Petróleo"

res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"

# Validar columnas requeridas
columnas_esperadas_mov = ["Monto", "Cuatrimestre", "Proveedor", "Caja"]
columnas_esperadas_resumen = ["Cuatrimestre", "Monto", "Total Gastado", "Saldo Actual", "Caja"]

for df in [mov_repuestos, mov_petroleo]:
    validar_columnas(df, columnas_esperadas_mov)
for df in [res_repuestos, res_petroleo]:
    validar_columnas(df, columnas_esperadas_resumen)

# Convertir columnas monetarias a float
for df in [res_repuestos, res_petroleo]:
    for col in ["Monto", "Total Gastado", "Saldo Actual"]:
        df[col] = df[col].apply(convertir_monto)

for df in [mov_repuestos, mov_petroleo]:
    df["Monto"] = df["Monto"].apply(convertir_monto)

# Concatenar datos
df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# --- Streamlit UI ---
st.title("Control de Cajas Chicas 2025")

st.sidebar.header("Filtros")

# Filtro por caja
cajas = st.sidebar.multiselect(
    "Caja",
    options=sorted(df_mov["Caja"].unique()),
    default=sorted(df_mov["Caja"].unique())
)

# Filtrar proveedores según cajas seleccionadas
proveedores_repuestos = mov_repuestos["Proveedor"].dropna().unique().tolist()
proveedores_petroleo = mov_petroleo["Proveedor"].dropna().unique().tolist()

proveedores_filtrados = []
if "Repuestos" in cajas:
    proveedores_filtrados.extend(proveedores_repuestos)
if "Petróleo" in cajas:
    proveedores_filtrados.extend(proveedores_petroleo)

proveedores_filtrados = sorted(set(proveedores_filtrados))

proveedor_seleccionado = st.sidebar.multiselect(
    "Proveedor",
    options=proveedores_filtrados,
    default=proveedores_filtrados
)

# Filtro por cuatrimestre
cuatrimestres = st.sidebar.multiselect(
    "Cuatrimestre",
    options=sorted(df_mov["Cuatrimestre"].dropna().unique()),
    default=sorted(df_mov["Cuatrimestre"].dropna().unique())
)

if not cajas:
    st.warning("Por favor, selecciona al menos una caja para mostrar los datos.")
else:
    # Filtrar datos según selección
    df_filtrado = df_mov[
        (df_mov["Caja"].isin(cajas)) &
        (df_mov["Proveedor"].isin(proveedor_seleccionado)) &
        (df_mov["Cuatrimestre"].isin(cuatrimestres))
    ]

    # Mostrar métricas por caja
    for caja in cajas:
        st.subheader(f"Caja: {caja}")
        resumen = df_res[(df_res["Caja"] == caja) & (df_res["Cuatrimestre"].isin(cuatrimestres))]
        if not resumen.empty:
            disponible = resumen["Monto"].sum()
            gastado = resumen["Total Gastado"].sum()
            saldo = resumen["Saldo Actual"].sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("Disponible", formatear_moneda(disponible))
            col2.metric("Gastado", formatear_moneda(gastado))
            col3.metric("Saldo", formatear_moneda(saldo))
        else:
            st.info(f"No hay resumen disponible para la caja {caja} con los filtros seleccionados.")

    # Gráfico de gasto por proveedor (solo si hay una caja seleccionada)
    st.header("Gasto por Proveedor")
    if len(cajas) == 1:
        if not df_filtrado.empty:
            gastos_proveedor = df_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
            st.bar_chart(gastos_proveedor)
        else:
            st.info("No hay movimientos para los filtros seleccionados.")
    else:
        st.info("Selecciona una única caja para visualizar el gráfico de gasto por proveedor.")

    # Mostrar tabla de movimientos filtrados
    st.header("Movimientos filtrados")
    if not df_filtrado.empty:
        df_filtrado_display = df_filtrado.copy()
        df_filtrado_display["Monto"] = df_filtrado_display["Monto"].apply(formatear_moneda)
        st.dataframe(df_filtrado_display)
    else:
        st.info("No hay movimientos para mostrar con los filtros actuales.")
