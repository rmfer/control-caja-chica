import streamlit as st
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

import pandas as pd
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
from io import BytesIO

# Autenticación Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["google_service_account"], scope
)
client = gspread.authorize(credentials)

sheet_id = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

mov_repuestos = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Movimientos Repuestos").get_all_records())
res_repuestos = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Resumen Repuestos").get_all_records())
mov_petroleo = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Movimientos Petróleo").get_all_records())
res_petroleo = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Resumen Petróleo").get_all_records())

for df in [mov_repuestos, mov_petroleo, res_repuestos, res_petroleo]:
    df.columns = df.columns.str.strip()

# Función para Repuestos (eliminar puntos miles excepto el decimal final)
def convertir_monto_repuestos(valor):
    try:
        texto = str(valor).strip()
        texto = texto.replace(",", ".")  # coma decimal a punto
        # eliminar todos los puntos menos el último (decimal)
        if texto.count(".") > 1:
            partes = texto.split(".")
            texto = "".join(partes[:-1]) + "." + partes[-1]
        return float(texto)
    except:
        return 0.0

def convertir_monto_petroleo(valor):
    try:
        texto = str(valor).strip()
        texto = texto.replace(".", "").replace(",", ".")
        return float(texto)
    except:
        return 0.0

# Aplicar conversiones
for col in ["Monto", "Total Gastado", "Saldo Actual"]:
    if col in res_repuestos.columns:
        res_repuestos[col] = res_repuestos[col].apply(convertir_monto_repuestos)
    if col in res_petroleo.columns:
        res_petroleo[col] = res_petroleo[col].apply(convertir_monto_petroleo)

if "Monto" in mov_repuestos.columns:
    mov_repuestos["Monto"] = mov_repuestos["Monto"].apply(convertir_monto_repuestos)
if "Monto" in mov_petroleo.columns:
    mov_petroleo["Monto"] = mov_petroleo["Monto"].apply(convertir_monto_petroleo)

mov_repuestos["Caja"] = "Repuestos"
mov_petroleo["Caja"] = "Petróleo"
res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"

df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# Interfaz
st.title("Control de Cajas Chicas 2025")

cajas = st.sidebar.multiselect("Caja", df_mov["Caja"].unique(), default=df_mov["Caja"].unique())
cuatrimestres = st.sidebar.multiselect("Cuatrimestre", df_mov["Cuatrimestre"].unique(), default=df_mov["Cuatrimestre"].unique())
proveedores = st.sidebar.multiselect("Proveedor", df_mov["Proveedor"].unique(), default=df_mov["Proveedor"].unique())

df_filtrado = df_mov[
    (df_mov["Caja"].isin(cajas)) &
    (df_mov["Cuatrimestre"].isin(cuatrimestres)) &
    (df_mov["Proveedor"].isin(proveedores))
]

st.header("Resumen General")
for caja in cajas:
    st.subheader(f"Caja: {caja}")
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

st.header("Gasto por Proveedor")
gastos_proveedor = df_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
st.bar_chart(gastos_proveedor)

st.header("Movimientos filtrados")
df_filtrado_display = df_filtrado.copy()
df_filtrado_display["Monto"] = df_filtrado_display["Monto"].apply(
    lambda x: f"${x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
)
st.dataframe(df_filtrado_display)

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
            pdf.cell(200, 10, txt=f"Monto disponible: ${disponible:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), ln=1)
            pdf.cell(200, 10, txt=f"Total gastado: ${gastado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), ln=1)
            pdf.cell(200, 10, txt=f"Saldo restante: ${saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), ln=1)
            pdf.cell(200, 10, txt=f"Porcentaje usado: {pct_usado:.2f}%", ln=1)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

if st.button("📄 Descargar resumen en PDF"):
    pdf_bytes = exportar_pdf()
    st.download_button("Descargar PDF", data=pdf_bytes.getvalue(), file_name="resumen_cajas.pdf", mime="application/pdf")
