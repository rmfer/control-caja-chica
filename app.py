import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import locale
import re
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

# Mensajes de bienvenida y título
st.title("¡Bienvenido!")
st.header("Control de Cajas Chicas 2025")

# Configurar locale para formateo de moneda
try:
    locale.setlocale(locale.LC_ALL, 'es_AR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

# Funciones auxiliares
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

def normalizar_cuatrimestre(valor):
    if pd.isna(valor):
        return ''
    valor_str = str(valor).strip()
    match = re.match(r'(\d)', valor_str)
    if match:
        return match.group(1)
    return valor_str

# Carga de datos desde Google Sheets
@st.cache_data(ttl=3600)
def cargar_hoja(nombre_hoja):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key("1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro").worksheet(nombre_hoja)
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip()
    return df

# Cargar datos
mov_repuestos = cargar_hoja("Movimientos Repuestos")
mov_petroleo = cargar_hoja("Movimientos Petróleo")
res_repuestos = cargar_hoja("Resumen Repuestos")
res_petroleo = cargar_hoja("Resumen Petróleo")

# Añadir columna Caja
mov_repuestos["Caja"] = "Repuestos"
mov_petroleo["Caja"] = "Petróleo"
res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"

# Convertir montos a float
for df in [mov_repuestos, mov_petroleo]:
    df["Monto"] = df["Monto"].apply(convertir_monto)
for df in [res_repuestos, res_petroleo]:
    for col in ["Monto", "Total Gastado", "Saldo Actual"]:
        df[col] = df[col].apply(convertir_monto)

# Concatenar datos
df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# Normalizar cuatrimestres
df_mov['Cuatrimestre'] = df_mov['Cuatrimestre'].apply(normalizar_cuatrimestre)
df_res['Cuatrimestre'] = df_res['Cuatrimestre'].apply(normalizar_cuatrimestre)

# Procesar área (convertir string a lista)
df_mov['Área'] = df_mov['Área'].fillna('').apply(lambda x: [a.strip() for a in x.split(',')] if x else [])

# Sidebar - filtros
st.sidebar.header("Filtros")

cajas = st.sidebar.multiselect(
    "Caja",
    options=sorted(df_mov["Caja"].unique()),
    default=sorted(df_mov["Caja"].unique())
)

proveedores_disponibles = sorted(df_mov[df_mov["Caja"].isin(cajas)]["Proveedor"].dropna().unique())
proveedores = st.sidebar.multiselect(
    "Proveedor",
    options=proveedores_disponibles,
    default=proveedores_disponibles
)

areas_disponibles = sorted({area for sublist in df_mov[df_mov["Caja"].isin(cajas)]["Área"] for area in sublist if area})
areas = st.sidebar.multiselect(
    "Área",
    options=areas_disponibles,
    default=areas_disponibles
)

cuatrimestres_disponibles = sorted(df_mov['Cuatrimestre'].dropna().unique())
cuatrimestres = st.sidebar.multiselect(
    "Cuatrimestre",
    options=cuatrimestres_disponibles,
    default=cuatrimestres_disponibles
)

# Filtrar datos según selección
df_filtrado = df_mov[
    (df_mov["Caja"].isin(cajas)) &
    (df_mov["Proveedor"].isin(proveedores)) &
    (df_mov["Cuatrimestre"].isin(cuatrimestres)) &
    (df_mov["Área"].apply(lambda x: any(area in x for area in areas)))
]

# Mostrar métricas por caja
for caja in cajas:
    st.subheader(f"Caja: {caja}")
    asignado_anual = df_res[df_res["Caja"] == caja]["Monto"].sum()
    st.markdown(f"**Anual Asignado:** {formatear_moneda(asignado_anual)}")

    resumen_caja = df_res[(df_res["Caja"] == caja) & (df_res["Cuatrimestre"].isin(cuatrimestres))]
    disponible = resumen_caja["Monto"].sum() if not resumen_caja.empty else 0.0
    saldo = resumen_caja["Saldo Actual"].sum() if not resumen_caja.empty else 0.0
    consumo = df_filtrado[df_filtrado["Caja"] == caja]["Monto"].sum() if not df_filtrado.empty else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Disponible", formatear_moneda(disponible))
    col2.metric("Consumo", formatear_moneda(consumo))
    col3.metric("Saldo", formatear_moneda(saldo))

# Mostrar gráfico y tabla solo si hay una caja seleccionada
if len(cajas) == 1 and not df_filtrado.empty:
    st.header("Consumo por Proveedor")
    consumo_proveedor = df_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
    fig = go.Figure(data=[go.Bar(x=consumo_proveedor.index, y=consumo_proveedor.values, marker_color='steelblue')])
    fig.update_layout(
        width=800,
        height=400,
        margin=dict(l=40, r=40, t=40, b=40),
        dragmode=False,
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
        xaxis_title="Proveedor",
        yaxis_title="Consumo"
    )
    st.plotly_chart(fig, use_container_width=False)

    st.header("Movimientos filtrados")
    df_tabla = df_filtrado.copy()
    df_tabla['Área'] = df_tabla['Área'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
    df_tabla["Monto"] = df_tabla["Monto"].apply(formatear_moneda)
    if 'Caja' in df_tabla.columns:
        df_tabla = df_tabla.drop(columns=['Caja'])
    st.table(df_tabla)
else:
    st.info("Selecciona una caja y filtros para mostrar datos.")
