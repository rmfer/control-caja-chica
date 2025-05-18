import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import locale
import re

# --- Configuración de la página: debe ir primero ---
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

# Configurar locale para formateo de moneda (ajusta según tu sistema)
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
        # Eliminar puntos usados como separadores de miles y reemplazar coma decimal por punto
        texto = re.sub(r'\.', '', texto)
        texto = texto.replace(',', '.')
        return float(texto)
    except ValueError:
        # Sin advertencias, simplemente devolver 0.0 en caso de error
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

# Agregar columna 'Caja' en movimientos si no existe
if "Caja" not in mov_repuestos.columns:
    mov_repuestos["Caja"] = "Repuestos"
if "Caja" not in mov_petroleo.columns:
    mov_petroleo["Caja"] = "Petróleo"

# Agregar columna 'Caja' en resúmenes antes de validar
res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"

# Validar columnas
columnas_esperadas_mov = ["Monto", "Cuatrimestre", "Proveedor", "Caja"]
columnas_esperadas_resumen = ["Cuatrimestre", "Monto", "Total Gastado", "Saldo Actual", "Caja"]

for df in [mov_repuestos, mov_petroleo]:
    validar_columnas(df, columnas_esperadas_mov)

for df in [res_repuestos, res_petroleo]:
    validar_columnas(df, columnas_esperadas_resumen)

# Convertir montos en resúmenes
for col in ["Monto", "Total Gastado", "Saldo Actual"]:
    res_repuestos[col] = res_repuestos[col].apply(lambda x: convertir_monto(x, "Repuestos"))
    res_petroleo[col] = res_petroleo[col].apply(lambda x: convertir_monto(x, "Petróleo"))

# Convertir montos en movimientos
mov_repuestos["Monto"] = mov_repuestos["Monto"].apply(lambda x: convertir_monto(x, "Repuestos"))
mov_petroleo["Monto"] = mov_petroleo["Monto"].apply(lambda x: convertir_monto(x, "Petróleo"))

df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# --- Streamlit UI ---
st.title("Control de Cajas Chicas 2025")

# Filtros
st.sidebar.header("Filtros")

# Selección de cajas
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

# Selección dinámica de proveedores
proveedor_seleccionado = st.sidebar.multiselect(
    "Proveedor",
    options=proveedores_filtrados,
    default=proveedores_filtrados
)

# Selección de cuatrimestres
cuatrimestres = st.sidebar.multiselect(
    "Cuatrimestre",
    options=sorted(df_mov["Cuatrimestre"].dropna().unique()),
    default=sorted(df_mov["Cuatrimestre"].dropna().unique())
)

# Control para evitar error si no se selecciona ninguna caja
if not cajas:
    st.warning("Por favor, selecciona al menos una caja para mostrar los datos.")
else:
    # Aplicar filtros
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
            gastado = resumen["Total Gastado"].sum()
            saldo = resumen["Saldo Actual"].sum()
            pct_usado = (gastado / disponible) * 100 if disponible > 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("Disponible", formatear_moneda(disponible))
            col2.metric("Gastado", formatear_moneda(gastado))
            col3.metric("Saldo", formatear_moneda(saldo))

            # Gráfico de barras con etiquetas
            fig, ax = plt.subplots()
            barras = ax.bar(["Gastado", "Saldo"], [gastado, saldo], color=["#ff4b4b", "#4bffa8"])

            # Desactivar notación científica y usar separadores de miles en eje Y
            ax.get_yaxis().get_major_formatter().set_scientific(False)
            ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:,.0f}'))

            for barra in barras:
                altura = barra.get_height()
                ax.annotate(formatear_moneda(altura),
                            xy=(barra.get_x() + barra.get_width() / 2, altura),
                            xytext=(0, 5),
                            textcoords="offset points",
                            ha='center', va='bottom')
            st.pyplot(fig)
        else:
            st.info(f"No hay resumen disponible para la caja {caja} con los filtros seleccionados.")

    # Gastos por proveedor
    st.header("Gasto por Proveedor")
    if not df_filtrado.empty:
        gastos_proveedor = df_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
        st.bar_chart(gastos_proveedor)
    else:
        st.info("No hay movimientos para los filtros seleccionados.")

    # Tabla de movimientos con formato de moneda local
    st.header("Movimientos filtrados")
    if not df_filtrado.empty:
        df_filtrado_display = df_filtrado.copy()
        df_filtrado_display["Monto"] = df_filtrado_display["Monto"].apply(formatear_moneda)
        st.dataframe(df_filtrado_display)
    else:
        st.info("No hay movimientos para mostrar con los filtros actuales.")
