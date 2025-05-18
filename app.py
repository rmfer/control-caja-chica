import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF

# Configuración página
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

# Credenciales Google desde Streamlit secrets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
client = gspread.authorize(creds)

# Parámetros constantes
NOMBRE_PLANILLA = "iacajas2025"
HOJAS = {
    "Movimientos Repuestos": "Movimientos Repuestos",
    "Resumen Repuestos": "Resumen Repuestos",
    "Movimientos Petróleo": "Movimientos Petróleo",
    "Resumen Petróleo": "Resumen Petróleo"
}

# Función para cargar hoja y devolver DataFrame
@st.cache_data(ttl=600)
def cargar_hoja(worksheet_name):
    sheet = client.open(NOMBRE_PLANILLA)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# Funciones para limpiar y convertir montos
def limpiar_monto_repuestos(monto_str):
    if pd.isna(monto_str) or monto_str == "":
        return 0.0
    monto_str = monto_str.replace(".", "").replace(",", ".")
    try:
        return float(monto_str)
    except:
        return 0.0

def limpiar_monto_petroleo(monto_str):
    if pd.isna(monto_str) or monto_str == "":
        return 0.0
    monto_str = monto_str.replace(",", "")
    try:
        return float(monto_str)
    except:
        return 0.0

# Cargar datos
df_mov_repuestos = cargar_hoja(HOJAS["Movimientos Repuestos"])
df_res_repuestos = cargar_hoja(HOJAS["Resumen Repuestos"])
df_mov_petroleo = cargar_hoja(HOJAS["Movimientos Petróleo"])
df_res_petroleo = cargar_hoja(HOJAS["Resumen Petróleo"])

# Limpiar montos
if "Monto" in df_mov_repuestos.columns:
    df_mov_repuestos["Monto"] = df_mov_repuestos["Monto"].apply(limpiar_monto_repuestos)
if "Monto" in df_mov_petroleo.columns:
    df_mov_petroleo["Monto"] = df_mov_petroleo["Monto"].apply(limpiar_monto_petroleo)

# Título
st.title("Control de Cajas Chicas 2025")

# Selección caja
caja = st.selectbox("Selecciona la caja chica:", ["Repuestos", "Petróleo"])

# Selección cuatrimestre
df_mov = df_mov_repuestos.copy() if caja == "Repuestos" else df_mov_petroleo.copy()
df_res = df_res_repuestos.copy() if caja == "Repuestos" else df_res_petroleo.copy()

cuatrimestres = df_mov["Cuatrimestre"].unique()
cuatrimestre_seleccionado = st.selectbox("Selecciona cuatrimestre:", sorted(cuatrimestres))
df_mov_filtrado = df_mov[df_mov["Cuatrimestre"] == cuatrimestre_seleccionado]

# Resumen
if "Saldo Actual" in df_res.columns and "Cuatrimestre" in df_res.columns:
    saldo_actual = df_res.loc[df_res["Cuatrimestre"] == cuatrimestre_seleccionado, "Saldo Actual"].values
    total_gastado = df_res.loc[df_res["Cuatrimestre"] == cuatrimestre_seleccionado, "Total Gastado"].values
    monto_total = df_res.loc[df_res["Cuatrimestre"] == cuatrimestre_seleccionado, "Monto"].values
else:
    saldo_actual = [0]
    total_gastado = [0]
    monto_total = [0]

st.subheader(f"Resumen {caja} - Cuatrimestre {cuatrimestre_seleccionado}")
st.markdown(f"- **Monto Total:** ${monto_total[0]:,.2f}")
st.markdown(f"- **Total Gastado:** ${total_gastado[0]:,.2f}")
st.markdown(f"- **Saldo Actual:** ${saldo_actual[0]:,.2f}")

# Tabla movimientos
st.subheader(f"Movimientos {caja} - Cuatrimestre {cuatrimestre_seleccionado}")
st.dataframe(df_mov_filtrado)

# Gráfico gastos por proveedor
st.subheader("Gastos por Proveedor")

if "Proveedor" in df_mov_filtrado.columns and "Monto" in df_mov_filtrado.columns:
    gastos_proveedor = df_mov_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    gastos_proveedor.plot(kind="bar", ax=ax)
    ax.set_ylabel("Monto")
    ax.set_title(f"Gastos por Proveedor - {caja} - {cuatrimestre_seleccionado}")
    st.pyplot(fig)
else:
    st.write("No hay datos de proveedor o monto para mostrar.")

# --- Exportar PDF ---
def generar_pdf(resumen, df_movimientos, fig, caja, cuatrimestre):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Resumen {caja} - Cuatrimestre {cuatrimestre}", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.ln(5)
    pdf.cell(0, 10, f"Monto Total: ${resumen['Monto Total']:,.2f}", ln=True)
    pdf.cell(0, 10, f"Total Gastado: ${resumen['Total Gastado']:,.2f}", ln=True)
    pdf.cell(0, 10, f"Saldo Actual: ${resumen['Saldo Actual']:,.2f}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Movimientos:", ln=True)
    pdf.set_font("Arial", "", 10)

    # Tabla movimientos simplificada en PDF
    col_width = pdf.epw / len(df_movimientos.columns)  # Equal column width
    row_height = 6

    # Headers
    for col_name in df_movimientos.columns:
        pdf.cell(col_width, row_height, str(col_name), border=1)
    pdf.ln(row_height)

    # Rows (limitar a 20 filas para no llenar mucho)
    for i, row in df_movimientos.head(20).iterrows():
        for item in row:
            txt = str(item)
            if len(txt) > 15:
                txt = txt[:12] + "..."
            pdf.cell(col_width, row_height, txt, border=1)
        pdf.ln(row_height)

    # Agregar gráfico como imagen PNG en memoria
    img_bytes = BytesIO()
    fig.savefig(img_bytes, format='PNG')
    img_bytes.seek(0)
    pdf.add_page()
    pdf.image(img_bytes, x=10, y=20, w=pdf.epw*0.9)

    return pdf.output(dest='S').encode('latin1')

# Botón para descargar PDF
if st.button("Exportar resumen y movimientos a PDF"):
    resumen_dict = {
        "Monto Total": monto_total[0],
        "Total Gastado": total_gastado[0],
        "Saldo Actual": saldo_actual[0]
    }

    pdf_bytes = generar_pdf(resumen_dict, df_mov_filtrado, fig, caja, cuatrimestre_seleccionado)

    st.download_button(
        label="Descargar PDF",
        data=pdf_bytes,
        file_name=f"Resumen_{caja}_{cuatrimestre_seleccionado}.pdf",
        mime="application/pdf"
    )
