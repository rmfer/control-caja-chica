import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Autenticación ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["google_service_account"], scope
)
client = gspread.authorize(credentials)

sheet_id = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

# --- Leer hojas ---
ws_repuestos = client.open_by_key(sheet_id).worksheet("Movimientos Repuestos")
mov_repuestos = pd.DataFrame(ws_repuestos.get_all_records())

ws_petroleo = client.open_by_key(sheet_id).worksheet("Movimientos Petróleo")
mov_petroleo = pd.DataFrame(ws_petroleo.get_all_records())

ws_res_repuestos = client.open_by_key(sheet_id).worksheet("Resumen Repuestos")
res_repuestos = pd.DataFrame(ws_res_repuestos.get_all_records())

ws_res_petroleo = client.open_by_key(sheet_id).worksheet("Resumen Petróleo")
res_petroleo = pd.DataFrame(ws_res_petroleo.get_all_records())

# --- Funciones limpieza ---
def limpiar_monto_repuestos(valor):
    try:
        s = str(valor).strip()
        s = s.replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

def limpiar_monto_petroleo(valor):
    try:
        s = str(valor).strip()
        s = s.replace(',', '')  # quitar comas si las hubiera
        return float(s)
    except:
        return 0.0

# --- Limpiar columna 'Monto' movimientos ---
mov_repuestos["Monto"] = mov_repuestos["Monto"].apply(limpiar_monto_repuestos)
mov_petroleo["Monto"] = mov_petroleo["Monto"].apply(limpiar_monto_petroleo)

# --- Limpiar columnas resumen ---
for col in ["Monto", "Total Gastado", "Saldo Actual"]:
    res_repuestos[col] = res_repuestos[col].apply(limpiar_monto_repuestos)
    res_petroleo[col] = res_petroleo[col].apply(limpiar_monto_petroleo)

# --- Concatenar datos y añadir columna 'Caja' para filtro ---
mov_repuestos["Caja"] = "Repuestos"
mov_petroleo["Caja"] = "Petróleo"
df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)

res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# --- Mostrar para verificar que los valores ya están correctos ---
st.title("Prueba limpieza de montos")

st.subheader("Movimientos Repuestos")
st.write(mov_repuestos[["Monto"]].head())

st.subheader("Movimientos Petróleo")
st.write(mov_petroleo[["Monto"]].head())

st.subheader("Resumen Repuestos")
st.write(res_repuestos[["Monto", "Total Gastado", "Saldo Actual"]].head())

st.subheader("Resumen Petróleo")
st.write(res_petroleo[["Monto", "Total Gastado", "Saldo Actual"]].head())
