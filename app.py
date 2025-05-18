import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
from io import BytesIO

# --- Autenticación con Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["google_service_account"], scope
)
client = gspread.authorize(credentials)

sheet_id = "1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro"

# --- Cargar hojas ---
mov_repuestos = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Movimientos Repuestos").get_all_records())
res_repuestos = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Resumen Repuestos").get_all_records())
mov_petroleo = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Movimientos Petróleo").get_all_records())
res_petroleo = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Resumen Petróleo").get_all_records())

# --- Limpieza diferenciada de montos ---

def limpiar_repuestos(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    # Repuestos: miles con punto, decimales con coma
    texto = texto.replace('.', '').replace(',', '.')
    try:
        return float(texto)
    except:
        return 0.0

def limpiar_petroleo(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    # Petróleo: quitar comas si son miles (asumo)
    texto = texto.replace(',', '')
    try:
        return float(texto)
    except:
        return 0.0

# Limpieza en Movimientos
mov_repuestos['Monto'] = mov_repuestos['Monto'].apply(limpiar_repuestos)
mov_petroleo['Monto'] = mov_petroleo['Monto'].apply(limpiar_petroleo)

# Limpieza en Resúmenes
for col in ['Monto', 'Total Gastado', 'Saldo Actual']:
    res_repuestos[col] = res_repuestos[col].apply(limpiar_repuestos)
    res_petroleo[col] = res_petroleo[col].apply(limpiar_petroleo)

# --- Unificar datos ---
mov_repuestos["Caja"] = "Repuestos"
mov_petroleo["Caja"] = "Petróleo"
df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)

res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# --- Interfaz ---
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

# Función para formatear números estilo europeo (miles con punto, decimales con coma)
def formatear_numero(x):
    try:
        return f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return x

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
        col1.metric("Disponible", f"${formatear_numero(disponible)}")
        col2.metric("Gastado", f"${formatear_numero(gastado)}")
        col3.metric("Saldo", f"${formatear_numero(saldo)}")

        # Gráfico de barras
        fig, ax = plt.subplots()
        ax.bar(["Gastado", "Saldo"], [gastado, saldo], color=["#ff4b4b", "#4bffa8"])
        ax.set_title(f"Distribución: {caja}")
        st.pyplot(fig)

# --- Gastos por proveedor ---
st.header("Gasto por Proveedor")
gastos_proveedor = df_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
st.bar_chart(gastos_proveedor)

# --- Tabla de movimientos con formato ---
st.header("Movimientos filtrados")
df_filtrado_display = df_filtrado.copy()
df_filtrado_display['Monto'] = df_filtrado_display['Monto'].apply(formatear_numero)
st.dataframe(df_filtrado_display)

# --- Exportar a PDF ---
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
            pdf.cell(200, 10, txt=f"Monto disponible: ${formatear_numero(disponible)}", ln=1)
            pdf.cell(200, 10, txt=f"Total gastado: ${formatear_numero(gastado)}", ln=1)
            pdf.cell(200, 10, txt=f"Saldo restante: ${formatear_numero(saldo)}", ln=1)
            pdf.cell(200, 10, txt=f"Porcentaje usado: {pct_usado:.2f}%", ln=1)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

if st.button("📄 Descargar resumen en PDF"):
    pdf_bytes = exportar_pdf()
    st.download_button("Descargar PDF", data=pdf_bytes.getvalue(), file_name="resumen_cajas.pdf", mime="application/pdf")
