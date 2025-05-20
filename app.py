import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import locale
import re

# --- Configuración de la página ---
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

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

def asegurar_columnas(df, columnas_requeridas):
    for col in columnas_requeridas:
        if col not in df.columns:
            df[col] = 0
    return df

def validar_columnas(df, columnas_requeridas):
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        st.error(f"Faltan columnas en los datos: {', '.join(faltantes)}")
        st.stop()

def convertir_monto(valor):
    if pd.isna(valor):
        return 0.0
    texto = str(valor).strip()
    texto = re.sub(r'[^0-9,.\-]', '', texto)
    if texto.count(',') > 0 and texto.count('.') > 0:
        texto = texto.replace('.', '').replace(',', '.')
    else:
        texto = texto.replace(',', '')
    try:
        return float(texto)
    except ValueError:
        return 0.0

def formatear_moneda(valor):
    try:
        return locale.currency(valor, grouping=True)
    except Exception:
        return f"${valor:,.2f}"

mov_repuestos = cargar_hoja("Movimientos Repuestos")
mov_petroleo = cargar_hoja("Movimientos Petróleo")
res_repuestos = cargar_hoja("Resumen Repuestos")
res_petroleo = cargar_hoja("Resumen Petróleo")

if "Caja" not in mov_repuestos.columns:
    mov_repuestos["Caja"] = "Repuestos"
if "Caja" not in mov_petroleo.columns:
    mov_petroleo["Caja"] = "Petróleo"

res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"

columnas_esperadas_mov = ["Monto", "Cuatrimestre", "Proveedor", "Caja"]
columnas_esperadas_resumen = ["Cuatrimestre", "Monto", "Consumo", "Saldo Actual", "Caja"]

res_repuestos = asegurar_columnas(res_repuestos, columnas_esperadas_resumen)
res_petroleo = asegurar_columnas(res_petroleo, columnas_esperadas_resumen)

for df in [mov_repuestos, mov_petroleo]:
    validar_columnas(df, columnas_esperadas_mov)
for df in [res_repuestos, res_petroleo]:
    validar_columnas(df, columnas_esperadas_resumen)

for col in ["Monto", "Consumo", "Saldo Actual"]:
    res_repuestos[col] = res_repuestos[col].apply(convertir_monto)
    res_petroleo[col] = res_petroleo[col].apply(convertir_monto)

mov_repuestos["Monto"] = mov_repuestos["Monto"].apply(convertir_monto)
mov_petroleo["Monto"] = mov_petroleo["Monto"].apply(convertir_monto)

df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

st.title("Control de Cajas Chicas 2025")

st.sidebar.header("Filtros")

cajas = st.sidebar.multiselect(
    "Caja",
    options=sorted(df_mov["Caja"].unique()),
    default=sorted(df_mov["Caja"].unique())
)

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

cuatrimestres = st.sidebar.multiselect(
    "Cuatrimestre",
    options=sorted(df_mov["Cuatrimestre"].dropna().unique()),
    default=sorted(df_mov["Cuatrimestre"].dropna().unique())
)

if not cajas:
    st.warning("Por favor, selecciona al menos una caja para mostrar los datos.")
else:
    df_filtrado = df_mov[
        (df_mov["Caja"].isin(cajas)) &
        (df_mov["Proveedor"].isin(proveedor_seleccionado)) &
        (df_mov["Cuatrimestre"].isin(cuatrimestres))
    ]

    for caja in cajas:
        st.subheader(f"Caja: {caja}")
        resumen = df_res[(df_res["Caja"] == caja) & (df_res["Cuatrimestre"].isin(cuatrimestres))]
        if not resumen.empty:
            disponible = resumen["Monto"].sum()
            gastado = resumen["Consumo"].sum()
            saldo = resumen["Saldo Actual"].sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("Monto Asignado", formatear_moneda(disponible))
            col2.metric("Consumo", formatear_moneda(gastado))
            col3.metric("Saldo", formatear_moneda(saldo))
        else:
            st.info(f"No hay resumen disponible para la caja {caja} con los filtros seleccionados.")

    if not df_filtrado.empty:
        st.header("Facturación")
        df_filtrado_display = df_filtrado.copy()
        df_filtrado_display["Monto"] = df_filtrado_display["Monto"].apply(formatear_moneda)
        df_filtrado_display = df_filtrado_display.reset_index(drop=True)

        st.dataframe(df_filtrado_display, hide_index=True)

        st.markdown(
            """
            <style>
            /* Centrar la columna Cuatrimestre (4ta columna) en la tabla de Streamlit */
            div[data-testid="stDataFrame"] table tbody tr td:nth-child(4),
            div[data-testid="stDataFrame"] table thead tr th:nth-child(4) {
                text-align: center;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No hay movimientos para mostrar con los filtros actuales.")
