import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF

# --- Configuración de la página ---
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

# --- Autenticación con Google Sheets usando Streamlit Secrets ---
service_account_info = st.secrets["gcp_service_account"]
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
client = gspread.authorize(creds)

# --- ID de la planilla ---
sheet_id = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

# --- Funciones para limpiar y convertir montos ---

def limpiar_monto_repuestos(valor):
    """
    Convierte texto como '625.500,00' a float 625500.00 para la hoja de Repuestos.
    """
    if isinstance(valor, str):
        valor = valor.replace('.', '').replace(',', '.').replace('$', '').strip()
        try:
            return float(valor)
        except:
            return 0.0
    elif pd.isna(valor):
        return 0.0
    else:
        return float(valor)

def limpiar_monto_petroleo(valor):
    """
    Convierte texto como '625.500,00' a float 625500.00 para la hoja de Petróleo.
    """
    # En Petróleo parece que ya está bien, solo limpiamos símbolos y espacios.
    if isinstance(valor, str):
        valor = valor.replace('$', '').replace(' ', '').replace('.', '').replace(',', '.')
        try:
            return float(valor)
        except:
            return 0.0
    elif pd.isna(valor):
        return 0.0
    else:
        return float(valor)

# --- Cargar datos desde Google Sheets ---
ws_repuestos = client.open_by_key(sheet_id).worksheet("Movimientos Repuestos")
ws_petroleo = client.open_by_key(sheet_id).worksheet("Movimientos Petróleo")

df_repuestos = pd.DataFrame(ws_repuestos.get_all_records())
df_petroleo = pd.DataFrame(ws_petroleo.get_all_records())

# --- Limpiar columnas 'Monto' según cada caja ---
df_repuestos["Monto"] = df_repuestos["Monto"].apply(limpiar_monto_repuestos)
df_petroleo["Monto"] = df_petroleo["Monto"].apply(limpiar_monto_petroleo)

# --- Resúmenes ---
def calcular_resumen(df):
    total_gastado = df["Monto"].sum()
    saldo = df["Saldo Actual"].iloc[0] if "Saldo Actual" in df.columns and not df["Saldo Actual"].empty else 0
    disponible = saldo + total_gastado  # asumiendo que saldo + gastado es el total asignado
    pct_usado = (total_gastado / disponible) * 100 if disponible > 0 else 0
    pct_disponible = 100 - pct_usado
    return total_gastado, saldo, disponible, pct_usado, pct_disponible

# --- Cargar hojas resumen para datos precisos ---
ws_res_repuestos = client.open_by_key(sheet_id).worksheet("Resumen Repuestos")
ws_res_petroleo = client.open_by_key(sheet_id).worksheet("Resumen Petróleo")

res_repuestos = pd.DataFrame(ws_res_repuestos.get_all_records())
res_petroleo = pd.DataFrame(ws_res_petroleo.get_all_records())

# --- Aplicar limpieza a resúmenes también ---
for col in ["Monto", "Total Gastado", "Saldo Actual"]:
    if col in res_repuestos.columns:
        res_repuestos[col] = res_repuestos[col].apply(limpiar_monto_repuestos)
    if col in res_petroleo.columns:
        res_petroleo[col] = res_petroleo[col].apply(limpiar_monto_petroleo)

# --- Interfaz Streamlit ---

st.title("Control de Cajas Chicas 2025")

caja_seleccionada = st.selectbox("Selecciona la caja", ["Repuestos", "Petróleo"])

if caja_seleccionada == "Repuestos":
    st.header("Movimientos Caja Repuestos")
    st.dataframe(df_repuestos)

    total_gastado, saldo, disponible, pct_usado, pct_disponible = calcular_resumen(res_repuestos)
else:
    st.header("Movimientos Caja Petróleo")
    st.dataframe(df_petroleo)

    total_gastado, saldo, disponible, pct_usado, pct_disponible = calcular_resumen(res_petroleo)

# Mostrar resumen
st.markdown(f"**Total Gastado:** ${total_gastado:,.2f}")
st.markdown(f"**Saldo Actual:** ${saldo:,.2f}")
st.markdown(f"**Total Asignado:** ${disponible:,.2f}")
st.markdown(f"**% Usado:** {pct_usado:.2f}%")
st.markdown(f"**% Disponible:** {pct_disponible:.2f}%")

# --- Exportar a PDF (opcional) ---
if st.button("Exportar resumen a PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Resumen Caja {caja_seleccionada} 2025", ln=True)
    pdf.cell(200, 10, txt=f"Total Gastado: ${total_gastado:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Saldo Actual: ${saldo:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Total Asignado: ${disponible:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"% Usado: {pct_usado:.2f}%", ln=True)
    pdf.cell(200, 10, txt=f"% Disponible: {pct_disponible:.2f}%", ln=True)

    pdf_output_path = "resumen_caja.pdf"
    pdf.output(pdf_output_path)

    with open(pdf_output_path, "rb") as f:
        st.download_button(label="Descargar PDF", data=f, file_name=pdf_output_path, mime="application/pdf")
