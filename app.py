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

# --- Añadir columna "Caja" ---
mov_repuestos["Caja"] = "Repuestos"
mov_petroleo["Caja"] = "Petróleo"
df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)

res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# --- Limpiar nombres de columnas ---
for df in [mov_repuestos, mov_petroleo, df_mov, res_repuestos, res_petroleo, df_res]:
    df.columns = df.columns.str.strip()

# --- Funciones de limpieza de valores numéricos según caja ---
def limpiar_valor_repuestos(valor):
    # Repuestos usa formato con punto como miles y coma decimal
    try:
        texto = str(valor).strip()
        texto = texto.replace(".", "").replace(",", ".")
        return float(texto)
    except:
        return None

def limpiar_valor_petroleo(valor):
    # Petróleo usa formato con coma como miles y punto decimal
    try:
        texto = str(valor).strip()
        texto = texto.replace(",", "")
        return float(texto)
    except:
        return None

# --- Aplicar limpieza a df_res según la caja ---
for col in ["Monto", "Total Gastado", "Saldo Actual"]:
    # Para Repuestos
    mask_repuestos = df_res["Caja"] == "Repuestos"
    df_res.loc[mask_repuestos, col] = df_res.loc[mask_repuestos, col].apply(limpiar_valor_repuestos)
    # Para Petróleo
    mask_petroleo = df_res["Caja"] == "Petróleo"
    df_res.loc[mask_petroleo, col] = df_res.loc[mask_petroleo, col].apply(limpiar_valor_petroleo)

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

# Convertir 'Monto' en df_filtrado a float, limpiando puntos y comas para cada caja
def limpiar_monto_filtros(row):
    valor = str(row["Monto"]).strip()
    if row["Caja"] == "Repuestos":
        try:
            valor = valor.replace(".", "").replace(",", ".")
            return float(valor)
        except:
            return None
    elif row["Caja"] == "Petróleo":
        try:
            valor = valor.replace(",", "")
            return float(valor)
        except:
            return None
    else:
        return None

df_filtrado["Monto"] = df_filtrado.apply(limpiar_monto_filtros, axis=1)

# Mostrar resumen
st.header("Resumen General")
for caja in cajas:
    resumen = df_res[(df_res["Caja"] == caja) & (df_res["Cuatrimestre"].isin(cuatrimestres))]
    if not resumen.empty:
        disponible = resumen["Monto"].sum()
        gastado = resumen["Total Gastado"].sum()
        saldo = resumen["Saldo Actual"].sum()
        pct_usado = (gastado / disponible) * 100 if pd.notna(disponible) and disponible > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Disponible", f"${disponible:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        col2.metric("Gastado", f"${gastado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        col3.metric("Saldo", f"${saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # Gráfico de barras
        fig, ax = plt.subplots()
        ax.bar(["Gastado", "Saldo"], [gastado, saldo], color=["#ff4b4b", "#4bffa8"])
        ax.set_title(f"Distribución: {caja}")
        st.pyplot(fig)

# --- Gastos por proveedor ---
st.header("Gasto por Proveedor")
gastos_proveedor = df_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)
st.bar_chart(gastos_proveedor)

# --- Tabla de movimientos ---
st.header("Movimientos filtrados")

def formatear_monto_tabla(row):
    try:
        if pd.isna(row["Monto"]):
            return ""
        # Usar formato con punto para miles y coma decimal
        return f'{row["Monto"]:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return row["Monto"]

df_filtrado_display = df_filtrado.copy()
df_filtrado_display["Monto"] = df_filtrado_display.apply(formatear_monto_tabla, axis=1)

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
