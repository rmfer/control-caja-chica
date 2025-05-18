import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError

# Constantes invariables
NOMBRE_PLANILLA = "iacajas2025"
HOJAS = {
    "Movimientos Repuestos": "Movimientos Repuestos",
    "Resumen Repuestos": "Resumen Repuestos",
    "Movimientos Petróleo": "Movimientos Petróleo",
    "Resumen Petróleo": "Resumen Petróleo",
}

# Cargar credenciales de servicio desde Streamlit secrets
CRED_JSON = st.secrets["gcp_service_account"]

# Autenticación con Google Sheets usando credenciales y scopes
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
        df = df.dropna(how="all")  # Elimina filas vacías
        return df
    except SpreadsheetNotFound:
        st.error(f"No se encontró la planilla '{NOMBRE_PLANILLA}'. Verificá el nombre y que la cuenta tenga acceso.")
        return None
    except APIError as e:
        st.error("Error de acceso a la planilla. Verificá permisos y conexión.")
        st.code(str(e))
        return None
    except Exception as e:
        st.error("Error inesperado al cargar la hoja.")
        st.code(str(e))
        return None

# Cargar cada hoja con control de errores
df_mov_repuestos = cargar_hoja(HOJAS["Movimientos Repuestos"])
df_res_repuestos = cargar_hoja(HOJAS["Resumen Repuestos"])
df_mov_petroleo = cargar_hoja(HOJAS["Movimientos Petróleo"])
df_res_petroleo = cargar_hoja(HOJAS["Resumen Petróleo"])

# Mostrar datos si se cargaron correctamente
if df_mov_repuestos is not None:
    st.subheader("Movimientos Repuestos")
    st.dataframe(df_mov_repuestos)

if df_res_repuestos is not None:
    st.subheader("Resumen Repuestos")
    st.dataframe(df_res_repuestos)

if df_mov_petroleo is not None:
    st.subheader("Movimientos Petróleo")
    st.dataframe(df_mov_petroleo)

if df_res_petroleo is not None:
    st.subheader("Resumen Petróleo")
    st.dataframe(df_res_petroleo)
