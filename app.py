import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import pandas as pd
import matplotlib.pyplot as plt

# Constantes
NOMBRE_PLANILLA = "iacajas2025"
HOJAS = {
    "Movimientos Repuestos": "Movimientos Repuestos",
    "Resumen Repuestos": "Resumen Repuestos",
    "Movimientos Petróleo": "Movimientos Petróleo",
    "Resumen Petróleo": "Resumen Petróleo",
}

# Autenticación
CRED_JSON = st.secrets["gcp_service_account"]
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
credentials = Credentials.from_service_account_info(CRED_JSON, scopes=scopes)
client = gspread.authorize(credentials)

@st.cache_data
def cargar_hoja(nombre_hoja):
    try:
        sheet = client.open(NOMBRE_PLANILLA).worksheet(nombre_hoja)
        df = get_as_dataframe(sheet, evaluate_formulas=True)
        df = df.dropna(how="all")
        return df
    except SpreadsheetNotFound:
        st.error(f"No se encontró la planilla '{NOMBRE_PLANILLA}'.")
        return None
    except APIError as e:
        st.error("Error de acceso a la planilla.")
        st.code(str(e))
        return None
    except Exception as e:
        st.error("Error inesperado al cargar la hoja.")
        st.code(str(e))
        return None

# Cargar datos
df_mov_repuestos = cargar_hoja(HOJAS["Movimientos Repuestos"])
df_res_repuestos = cargar_hoja(HOJAS["Resumen Repuestos"])
df_mov_petroleo = cargar_hoja(HOJAS["Movimientos Petróleo"])
df_res_petroleo = cargar_hoja(HOJAS["Resumen Petróleo"])

st.title("Control de Caja Chica - Repuestos y Petróleo")

# Función para filtrar por cuatrimestre y proveedor
def filtrar_df(df, cuatrimestre_sel, proveedor_sel):
    if df is None:
        return None
    df_filtered = df.copy()
    if "Cuatrimestre" in df.columns:
        # Ajustamos para que cuatrimestre empiece en 1 si hay ceros
        df_filtered = df_filtered[df_filtered["Cuatrimestre"].isin(cuatrimestre_sel)]
    if proveedor_sel and proveedor_sel != "Todos":
        if "Proveedor" in df.columns:
            df_filtered = df_filtered[df_filtered["Proveedor"] == proveedor_sel]
    return df_filtered

# Función para obtener lista de cuatrimestres válidos (sin ceros ni NaN)
def obtener_cuatrimestres(df):
    if df is None or "Cuatrimestre" not in df.columns:
        return []
    cuatris = df["Cuatrimestre"].dropna().unique()
    # Filtramos para que sean solo valores positivos (1+)
    cuatris = [int(c) for c in cuatris if c and c > 0]
    return sorted(cuatris)

# Función para obtener lista de proveedores
def obtener_proveedores(df):
    if df is None or "Proveedor" not in df.columns:
        return []
    provs = df["Proveedor"].dropna().unique()
    return sorted(provs)

# --- FILTROS ---
st.sidebar.header("Filtros")

# Cuatrimestres válidos combinados para ambos movimientos
cuatris_repuestos = obtener_cuatrimestres(df_mov_repuestos)
cuatris_petroleo = obtener_cuatrimestres(df_mov_petroleo)
cuatrimestres = sorted(set(cuatris_repuestos) | set(cuatris_petroleo))

if not cuatrimestres:
    st.warning("No se encontraron cuatrimestres válidos en los datos.")
    cuatrimestres = [1, 2, 3, 4]  # fallback

cuatrimestre_sel = st.sidebar.multiselect(
    "Seleccioná Cuatrimestre(s)",
    options=cuatrimestres,
    default=cuatrimestres
)

# Proveedores para movimientos combinados (repuestos + petróleo)
provs_repuestos = obtener_proveedores(df_mov_repuestos)
provs_petroleo = obtener_proveedores(df_mov_petroleo)
proveedores = sorted(set(provs_repuestos) | set(provs_petroleo))
proveedores.insert(0, "Todos")  # opción para no filtrar proveedor

proveedor_sel = st.sidebar.selectbox(
    "Seleccioná Proveedor",
    opciones=proveedores,
    index=0
)

# Caja a mostrar: Repuestos o Petróleo
caja_sel = st.sidebar.radio(
    "Seleccioná Caja",
    options=["Repuestos", "Petróleo"],
    index=0
)

# --- Mostrar datos filtrados según selección ---

if caja_sel == "Repuestos":
    df_mov = filtrar_df(df_mov_repuestos, cuatrimestre_sel, proveedor_sel)
    df_res = df_res_repuestos
else:
    df_mov = filtrar_df(df_mov_petroleo, cuatrimestre_sel, proveedor_sel)
    df_res = df_res_petroleo

if df_mov is None or df_res is None:
    st.error("No se pudieron cargar los datos para la caja seleccionada.")
    st.stop()

st.subheader(f"Movimientos {caja_sel}")
st.dataframe(df_mov)

st.subheader(f"Resumen {caja_sel}")
st.dataframe(df_res)

# --- Cálculos de saldo, porcentajes ---

def calcular_resumen(df_resumen, cuatris_seleccionados):
    # Filtrar resumen por cuatrimestres seleccionados
    if "Cuatrimestre" in df_resumen.columns:
        df_filtrado = df_resumen[df_resumen["Cuatrimestre"].isin(cuatris_seleccionados)]
    else:
        df_filtrado = df_resumen.copy()

    monto_total = df_filtrado["Monto"].sum() if "Monto" in df_filtrado.columns else 0
    gastado_total = df_filtrado["Total Gastado"].sum() if "Total Gastado" in df_filtrado.columns else 0
    saldo_total = df_filtrado["Saldo Actual"].sum() if "Saldo Actual" in df_filtrado.columns else 0

    pct_disponible = (saldo_total / monto_total * 100) if monto_total else 0
    pct_consumido = 100 - pct_disponible

    return {
        "Monto Total": monto_total,
        "Total Gastado": gastado_total,
        "Saldo Actual": saldo_total,
        "Porcentaje Disponible": pct_disponible,
        "Porcentaje Consumido": pct_consumido
    }

resumen = calcular_resumen(df_res, cuatrimestre_sel)

st.markdown("---")
st.subheader("Resumen General")

st.write(f"Monto Total: ${resumen['Monto Total']:.2f}")
st.write(f"Total Gastado: ${resumen['Total Gastado']:.2f}")
st.write(f"Saldo Actual: ${resumen['Saldo Actual']:.2f}")
st.write(f"Porcentaje Disponible: {resumen['Porcentaje Disponible']:.2f}%")
st.write(f"Porcentaje Consumido: {resumen['Porcentaje Consumido']:.2f}%")

# --- Gráfico de barras porcentaje consumido vs disponible ---
fig, ax = plt.subplots()
ax.bar(["Disponible", "Consumido"], [resumen['Porcentaje Disponible'], resumen['Porcentaje Consumido']], color=["green", "red"])
ax.set_ylim(0, 100)
ax.set_ylabel("Porcentaje (%)")
ax.set_title(f"Estado de Caja {caja_sel}")
st.pyplot(fig)
