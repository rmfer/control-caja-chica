import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
from io import BytesIO

# --- Autenticación ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["google_service_account"], scope
)
client = gspread.authorize(credentials)

sheet_id = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

# --- Cargar hojas ---
ws_repuestos = client.open_by_key(sheet_id).worksheet("Movimientos Repuestos")
mov_repuestos = pd.DataFrame(ws_repuestos.get_all_records())

ws_petroleo = client.open_by_key(sheet_id).worksheet("Movimientos Petróleo")
mov_petroleo = pd.DataFrame(ws_petroleo.get_all_records())

ws_res_repuestos = client.open_by_key(sheet_id).worksheet("Resumen Repuestos")
res_repuestos = pd.DataFrame(ws_res_repuestos.get_all_records())

ws_res_petroleo = client.open_by_key(sheet_id).worksheet("Resumen Petróleo")
res_petroleo = pd.DataFrame(ws_res_petroleo.get_all_records())

# --- Añadir columna "Caja" para diferenciarlos ---
mov_repuestos["Caja"] = "Repuestos"
mov_petroleo["Caja"] = "Petróleo"
df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)

res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# --- Limpiar nombres columnas ---
for df in [df_mov, df_res]:
    df.columns = df.columns.str.strip()

# --- Funciones para limpiar montos ---
def limpiar_monto_repuestos(valor):
    try:
        texto = str(valor).strip()
        # Quitar puntos de miles y cambiar coma por punto decimal
        texto = texto.replace(".", "").replace(",", ".")
        return float(texto)
    except:
        return 0.0

def limpiar_monto_petroleo(valor):
    try:
        texto = str(valor).strip()
        # Quitar comas de miles, punto decimal queda igual
        texto = texto.replace(",", "")
        return float(texto)
    except:
        return 0.0

# --- Aplicar limpieza para df_res ---
for col in ["Monto", "Total Gastado", "Saldo Actual"]:
    mask_repuestos = df_res["Caja"] == "Repuestos"
    df_res.loc[mask_repuestos, col] = df_res.loc[mask_repuestos, col].apply(limpiar_monto_repuestos)

    mask_petroleo = df_res["Caja"] == "Petróleo"
    df_res.loc[mask_petroleo, col] = df_res.loc[mask_petroleo, col].apply(limpiar_monto_petroleo)

# --- Aplicar limpieza para df_mov en columna Monto ---
def limpiar_monto_mov(row):
    if row["Caja"] == "Repuestos":
        return limpiar_monto_repuestos(row["Monto"])
    elif row["Caja"] == "Petróleo":
        return limpiar_monto_petroleo(row["Monto"])
    else:
        return 0.0

df_mov["Monto"] = df_mov.apply(limpiar_monto_mov, axis=1)

# --- Interfaz Streamlit ---
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")
st.title("Control de Cajas Chicas 2025")

# Filtros
st.sidebar.header("Filtros")
cajas = st.sidebar.multiselect("Caja", df_mov["Caja"].unique(), default=df_mov["Caja"].unique())
cuatrimestres = st.sidebar.multiselect("Cuatrimestre", df_mov["Cuatrimestre"].unique(), default=df_mov["Cuatrimestre"].unique())
proveedores = st.sidebar.multiselect("Proveedor", df_mov["Proveedor"].unique(), default=df_mov["Proveedor"].unique())

# Aplicar filtros
df_filtrado = df_mov[
    (df_mov["Caja"].isin(cajas)) &
    (df_mov["Cuatrimestre"].isin(cuatrimestres)) &
    (df_mov["Proveedor"].isin(proveedores))
]

# --- Mostrar resumen por caja ---
st.header("Resumen General")

for caja in cajas:
    resumen = df_res[(df_res["Caja"] == caja) & (df_res["Cuatrimestre"].isin(cuatrimestres))]
    if not resumen.empty:
        disponible = resumen["Monto"].sum()
        gastado = resumen["Total Gastado"].sum()
        saldo = resumen["Saldo Actual"].sum()
        pct_usado = (gastado / disponible) * 100 if disponible > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Disponible", f"${disponible:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        col2.metric("Gastado", f"${gastado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        col3.metric("Saldo", f"${saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        fig, ax = plt.subplots()
        ax.bar(["Gastado", "Saldo"], [gastado, saldo], color=["#ff4b4b", "#4bffa8"])
        ax.set_title(f"Distribución: {caja}")
        st.pyplot(fig)

# --- Gastos por proveedor ---
st.header("Gasto por Proveedor")
gastos_proveedor = df_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
st.bar_chart(gastos_proveedor)

# --- Tabla movimientos ---
st.header("Movimientos filtrados")

def formatear_monto(row):
    try:
        valor = row["Monto"]
        return f'{valor:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return row["Monto"]

df_filtrado_display = df_filtrado.copy()
df_filtrado_display["Monto"] = df_filtrado_display.apply(formatear_monto, axis=1)

st.dataframe(df_filtrado_display)

# --- Exportar PDF ---
def exportar_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Resumen de Control de Cajas Chicas", ln=1, align="C")

    for caja in cajas:
        resumen = df_res[(df_res["Caja"] == caja) & (df_res["Cuatrimestre"].isin(cuatrimestres))]
        if not resumen.empty:
            disponible = resumen["Monto"].sum()
            gastado = resumen["Total Gastado"].sum()
            saldo = resumen["Saldo Actual"].sum()
            pct_usado = (gastado / disponible) * 100 if disponible > 0 else 0

            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Caja: {caja}", ln=1)
            pdf.cell(200, 10, txt=f"Monto disponible: ${str(f'{disponible:,.2f}').replace(',', 'X').replace('.', ',').replace('X', '.')}", ln=1)
            pdf.cell(200, 10, txt=f"Total gastado: ${str(f'{gastado:,.2f}').replace(',', 'X').replace('.', ',').replace('X', '.')}", ln=1)
            pdf.cell(200, 10, txt=f"Saldo restante: ${str(f'{saldo:,.2f}').replace(',', 'X').replace('.', ',').replace('X', '.')}", ln=1)
            pdf.cell(200, 10, txt=f"Porcentaje usado: {pct_usado:.2f}%", ln=1)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

if st.button("📄 Descargar resumen en PDF"):
    pdf_bytes = exportar_pdf()
    st.download_button("Descargar PDF", data=pdf_bytes.getvalue(), file_name="resumen_cajas.pdf", mime="application/pdf")
