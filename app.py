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

# Concatenar movimientos
df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# Normalizar columna Cuatrimestre a valores '1', '2', '3', '4'
df_mov['Cuatrimestre'] = df_mov['Cuatrimestre'].apply(normalizar_cuatrimestre)
df_res['Cuatrimestre'] = df_res['Cuatrimestre'].apply(normalizar_cuatrimestre)

# Procesar la columna 'Área' para convertir cadenas separadas por comas en listas sin comillas
df_mov['Área'] = df_mov['Área'].fillna('').apply(lambda x: [area.strip() for area in x.split(',')] if x else [])

# --- Streamlit UI ---
st.title("Control de Cajas Chicas 2025")

st.sidebar.header("Filtros")

# Filtro por cajas
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

# --- FILTRAR ÁREAS DINÁMICAMENTE SEGÚN CAJAS SELECCIONADAS ---

# Filtrar df_mov solo por cajas seleccionadas para obtener áreas válidas
df_areas_filtrado = df_mov[df_mov["Caja"].isin(cajas)]

# Extraer todas las áreas únicas de las filas filtradas (recordando que 'Área' es lista)
areas_disponibles = sorted({area for sublist in df_areas_filtrado['Área'] for area in sublist if area})

# Mostrar filtro de áreas con solo las áreas disponibles
areas_seleccionadas = st.sidebar.multiselect(
    "Área",
    options=areas_disponibles,
    default=areas_disponibles
)

# --- FILTRO DE CUATRIMESTRE NORMALIZADO ---

cuatrimestres_posibles = ['1', '2', '3', '4']

# Obtener cuatrimestres existentes en los datos
cuatrimestres_existentes = df_mov['Cuatrimestre'].dropna().unique().tolist()

# Combinar y ordenar sin duplicados
cuatrimestres_totales = sorted(set(cuatrimestres_posibles) | set(cuatrimestres_existentes))

cuatrimestres_seleccionados = st.sidebar.multiselect(
    "Cuatrimestre",
    options=cuatrimestres_totales,
    default=cuatrimestres_existentes if cuatrimestres_existentes else cuatrimestres_posibles
)

# --- Aplicar todos los filtros ---
if not cajas:
    st.warning("Por favor, selecciona al menos una caja para mostrar los datos.")
else:
    # Filtrar resumen por cajas y cuatrimestres seleccionados
    resumen_filtrado = df_res[
        (df_res["Caja"].isin(cajas)) &
        (df_res["Cuatrimestre"].isin(cuatrimestres_seleccionados))
    ]

    # Filtrar movimientos para calcular gastado
    df_gastos_filtrado = df_mov[
        (df_mov["Caja"].isin(cajas)) &
        (df_mov["Proveedor"].isin(proveedor_seleccionado)) &
        (df_mov["Cuatrimestre"].isin(cuatrimestres_seleccionados)) &
        (df_mov["Área"].apply(lambda areas: any(area in areas for area in areas_seleccionadas)))
    ]

    # Mostrar métricas por caja
    for caja in cajas:
        st.subheader(f"Caja: {caja}")
        resumen_caja = resumen_filtrado[resumen_filtrado["Caja"] == caja]

        disponible = resumen_caja["Monto"].sum() if not resumen_caja.empty else 0.0
        saldo = resumen_caja["Saldo Actual"].sum() if not resumen_caja.empty else 0.0

        gastado = df_gastos_filtrado[df_gastos_filtrado["Caja"] == caja]["Monto"].sum() if not df_gastos_filtrado.empty else 0.0

        col1, col2, col3 = st.columns(3)
        col1.metric("Disponible", formatear_moneda(disponible))
        col2.metric("Gastado", formatear_moneda(gastado))
        col3.metric("Saldo", formatear_moneda(saldo))

    # Mostrar gráfico y tabla solo si hay consumos y una única caja seleccionada
    if len(cajas) == 1 and gastado > 0:
        st.header("Gasto por Proveedor")
        gastos_proveedor = df_gastos_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
        st.bar_chart(gastos_proveedor)

        st.header("Movimientos filtrados")
        df_filtrado_display = df_gastos_filtrado.copy()
        df_filtrado_display["Monto"] = df_filtrado_display["Monto"].apply(formatear_moneda)
        st.dataframe(df_filtrado_display)
    else:
        st.info("No hay consumos para mostrar en el gráfico ni en la tabla con los filtros actuales.")
