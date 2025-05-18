import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
from io import BytesIO

# --- Función para formatear números estilo europeo (6.076.994,30)
def formatear_numero(numero):
    if pd.isna(numero):
        return "0,00"
    entero = int(numero)
    decimales = abs(numero - entero)
    entero_str = f"{entero:,}".replace(",", ".")
    decimales_str = f"{decimales:.2f}"[1:].replace(".", ",")
    return entero_str + decimales_str

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

# --- Unificar datos ---
mov_repuestos["Caja"] = "Repuestos"
mov_petroleo["Caja"] = "Petróleo"
df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)

res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# Limpiar nombres de columnas
for df in [mov_repuestos, mov_petroleo, df_mov, res_repuestos, res_petroleo, df_res]:
    df.columns = df.columns.str.strip()

# Limpiar y convertir valores numéricos en df_res
def convertir_valores(valor):
    try:
        texto = str(valor).strip()
        texto = texto.replace(".", "").replace(",", ".")  # elimina separador de miles, cambia coma por punto
        return float(texto)
    except:
        return None

df_res["Monto"] = df_res["Monto"].apply(convertir_valores)
df_res["Total Gastado"] = df_res["Total Gastado"].apply(convertir_valores)
df_res["Saldo Actual"] = df_res["Saldo Actual"].apply(convertir_valores)

# Convertir a float (por seguridad)
df_res["Monto"] = pd.to_numeric(df_res["Monto"], errors="coerce")
df_res["Total Gastado"] = pd.to_numeric(df_res["Total Gastado"], errors="coerce")
df_res["Saldo Actual"] = pd.to_numeric(df_res["Saldo Actual"], errors="coerce")

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

# Convertir Monto en df_filtrado a float, limpiando formato si es necesario
def limpiar_monto(valor):
    try:
        texto = str(valor).strip()
        texto = texto.replace(".", "").replace(",", ".")
        return float(texto)
    except:
        return 0

df_filtrado["Monto"] = df_filtrado["Monto"].apply(limpiar_monto)

st.header("Resumen General")

for caja in cajas:
    st.subheader(f"Caja: {caja}")
    resumen = df_res[(df_res["Caja"] == caja) & (df_res["Cuatrimestre"].isin(cuatrimestres))]

    if not resumen.empty:
        disponible = resumen["Monto"].sum()
        gastado = resumen["Total Gastado"].sum()
        saldo = resumen["Saldo Actual"].sum()
        pct_usado = (gastado / disponible) * 100 if pd.notna(disponible) and disponible > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Disponible", f"$ {formatear_numero(disponible)}")
        col2.metric("Gastado", f"$ {formatear_numero(gastado)}")
        col3.metric("Saldo", f"$ {formatear_numero(saldo)}")

        # Gráfico de barras
        fig, ax = plt.subplots()
        ax.bar(["Gastado", "Saldo"], [gastado, saldo], color=["#ff4b4b", "#4bffa8"])
        ax.set_title(f"Distribución: {caja}")
        st.pyplot(fig)

# --- Gastos por proveedor ---
st.header("Gasto por Proveedor")

gastos_proveedor = df_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
gastos_proveedor_fmt = gastos_proveedor.apply(formatear_numero)
st.bar_chart(gastos_proveedor)

# --- Tabla de movimientos ---
st.header("Movimientos filtrados")

# Formatear columna "Monto" para mostrarla con separadores y coma decimal en la tabla
df_filtrado_display = df_filtrado.copy()
df_filtrado_display["Monto"] = df_filtrado_display["Monto"].apply(formatear_numero)
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
            pct_usado = (gastado / disponible) * 100 if pd.notna(disponible) and disponible > 0 else 0

            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Caja: {caja}", ln=1)
            pdf.cell(200, 10, txt=f"Monto disponible: $ {formatear_numero(disponible)}", ln=1)
            pdf.cell(200, 10, txt=f"Total gastado: $ {formatear_numero(gastado)}", ln=1)
            pdf.cell(200, 10, txt=f"Saldo restante: $ {formatear_numero(saldo)}", ln=1)
            pdf.cell(200, 10, txt=f"Porcentaje usado: {pct_usado:.2f}%", ln=1)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer

if st.button("📄 Descargar resumen en PDF"):
    pdf_bytes = exportar_pdf()
    st.download_button("Descargar PDF", data=pdf_bytes.getvalue(), file_name="resumen_cajas.pdf", mime="application/pdf")
