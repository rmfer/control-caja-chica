import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import locale
import re
import plotly.graph_objects as go
import time

# --- Configuración de la página ---
st.set_page_config(page_title="Control de Cajas Chicas 2025", layout="wide")

# Inicializar variable de estado para controlar la página
if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"
if "inicio_timestamp" not in st.session_state:
    st.session_state.inicio_timestamp = None

def cargar_hoja(nombre_hoja):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["google_service_account"], scope
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key("1O-YsM0Aksfl9_JmbAmYUGnj1iunxU9WOXwWPR8E6Yro").worksheet(nombre_hoja)
        df = pd.DataFrame(sheet.get_all_records())
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"No se pudo cargar la hoja '{nombre_hoja}': {e}")
        return pd.DataFrame()

def validar_columnas(df, columnas_requeridas):
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        st.error(f"Faltan columnas en los datos: {', '.join(faltantes)}")
        st.stop()

def convertir_monto(valor, tipo_caja):
    if pd.isna(valor):
        return 0.0
    texto = str(valor).strip()
    try:
        texto = re.sub(r'\.', '', texto)
        texto = texto.replace(',', '.')
        return float(texto)
    except ValueError:
        return 0.0

def formatear_moneda(valor):
    try:
        locale.setlocale(locale.LC_ALL, 'es_AR.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')
    try:
        return locale.currency(valor, grouping=True)
    except Exception:
        return f"${valor:,.2f}"

def normalizar_cuatrimestre(valor):
    if pd.isna(valor):
        return ''
    valor_str = str(valor).strip()
    match = re.match(r'(\d)', valor_str)
    if match:
        return match.group(1)
    return valor_str

# --- Carga de datos ---
mov_repuestos = cargar_hoja("Movimientos Repuestos")
mov_petroleo = cargar_hoja("Movimientos Petróleo")
res_repuestos = cargar_hoja("Resumen Repuestos")
res_petroleo = cargar_hoja("Resumen Petróleo")

# Asegurar columna 'Caja'
if "Caja" not in mov_repuestos.columns:
    mov_repuestos["Caja"] = "Repuestos"
if "Caja" not in mov_petroleo.columns:
    mov_petroleo["Caja"] = "Petróleo"

res_repuestos["Caja"] = "Repuestos"
res_petroleo["Caja"] = "Petróleo"

# Columnas esperadas (incluyendo 'Área')
columnas_esperadas_mov = ["Monto", "Cuatrimestre", "Proveedor", "Caja", "Área"]
columnas_esperadas_resumen = ["Cuatrimestre", "Monto", "Total Gastado", "Saldo Actual", "Caja"]

for df in [mov_repuestos, mov_petroleo]:
    validar_columnas(df, columnas_esperadas_mov)
for df in [res_repuestos, res_petroleo]:
    validar_columnas(df, columnas_esperadas_resumen)

# Convertir montos a float
for col in ["Monto", "Total Gastado", "Saldo Actual"]:
    res_repuestos[col] = res_repuestos[col].apply(lambda x: convertir_monto(x, "Repuestos"))
    res_petroleo[col] = res_petroleo[col].apply(lambda x: convertir_monto(x, "Petróleo"))

mov_repuestos["Monto"] = mov_repuestos["Monto"].apply(lambda x: convertir_monto(x, "Repuestos"))
mov_petroleo["Monto"] = mov_petroleo["Monto"].apply(lambda x: convertir_monto(x, "Petróleo"))

# Concatenar movimientos
df_mov = pd.concat([mov_repuestos, mov_petroleo], ignore_index=True)
df_res = pd.concat([res_repuestos, res_petroleo], ignore_index=True)

# Normalizar columna Cuatrimestre a valores '1', '2', '3', '4'
df_mov['Cuatrimestre'] = df_mov['Cuatrimestre'].apply(normalizar_cuatrimestre)
df_res['Cuatrimestre'] = df_res['Cuatrimestre'].apply(normalizar_cuatrimestre)

# Procesar la columna 'Área' para convertir cadenas separadas por comas en listas sin comillas
df_mov['Área'] = df_mov['Área'].fillna('').apply(lambda x: [area.strip() for area in x.split(',')] if x else [])

# --- Mostrar pantalla de inicio con solo título y redirección automática ---
def mostrar_inicio():
    st.markdown(
        """
        <h1 style="text-align:center; margin-top: 40vh; font-size: 4rem;">
            ¡Bienvenido a Control de Cajas Chicas 2025!
        </h1>
        """,
        unsafe_allow_html=True,
    )

def mostrar_filtros():
    st.title("Control de Cajas Chicas 2025")

    st.sidebar.header("Filtros")

    cajas = st.sidebar.multiselect(
        "Caja",
        options=sorted(df_mov["Caja"].unique()),
        default=sorted(df_mov["Caja"].unique())
    )

    if set(cajas) == {"Repuestos", "Petróleo"}:
        st.title("¡Bienvenido!")

    proveedores_repuestos = mov_repuestos["Proveedor"].dropna().unique().tolist()
    proveedores_petroleo = mov_petroleo["Proveedor"].dropna().unique().tolist()

    proveedores_filtrados = []
    if "Repuestos" in cajas:
        proveedores_filtrados.extend(proveedores_repuestos)
    if "Petróleo" in cajas:
        proveedores_filtrados.extend(proveedores_petroleo)

    proveedores_filtrados = sorted(set(proveedores_filtrados))

    proveedor_seleccionado = st.sidebar.multiselect(
        "Proveedor",
        options=proveedores_filtrados,
        default=proveedores_filtrados
    )

    df_areas_filtrado = df_mov[df_mov["Caja"].isin(cajas)]

    areas_disponibles = sorted({area for sublist in df_areas_filtrado['Área'] for area in sublist if area})

    areas_seleccionadas = st.sidebar.multiselect(
        "Área",
        options=areas_disponibles,
        default=areas_disponibles
    )

    cuatrimestres_posibles = ['1', '2', '3', '4']

    cuatrimestres_existentes = df_mov['Cuatrimestre'].dropna().unique().tolist()

    cuatrimestres_numericos = []
    for c in cuatrimestres_existentes:
        try:
            cuatrimestres_numericos.append(int(c))
        except ValueError:
            pass

    ultimo_cuatrimestre = max(cuatrimestres_numericos) if cuatrimestres_numericos else None

    cuatrimestres_totales = sorted(set(cuatrimestres_posibles) | set(cuatrimestres_existentes))

    if ultimo_cuatrimestre is not None and str(ultimo_cuatrimestre) in cuatrimestres_totales:
        default_cuatrimestre = [str(ultimo_cuatrimestre)]
    else:
        default_cuatrimestre = cuatrimestres_totales

    cuatrimestres_seleccionados = st.sidebar.multiselect(
        "Cuatrimestre",
        options=cuatrimestres_totales,
        default=default_cuatrimestre
    )

    if not cajas:
        st.warning("Por favor, selecciona al menos una caja para mostrar los datos.")
    else:
        resumen_filtrado = df_res[
            (df_res["Caja"].isin(cajas)) &
            (df_res["Cuatrimestre"].isin(cuatrimestres_seleccionados))
        ]

        df_consumo_filtrado = df_mov[
            (df_mov["Caja"].isin(cajas)) &
            (df_mov["Proveedor"].isin(proveedor_seleccionado)) &
            (df_mov["Cuatrimestre"].isin(cuatrimestres_seleccionados)) &
            (df_mov["Área"].apply(lambda areas: any(area in areas for area in areas_seleccionadas)))
        ]

        for caja in cajas:
            st.subheader(f"Caja: {caja}")

            asignado_anual = df_res[df_res["Caja"] == caja]["Monto"].sum()
            st.markdown(f"**Anual Asignado:** {formatear_moneda(asignado_anual)}")

            resumen_caja = resumen_filtrado[resumen_filtrado["Caja"] == caja]

            disponible = resumen_caja["Monto"].sum() if not resumen_caja.empty else 0.0
            saldo = resumen_caja["Saldo Actual"].sum() if not resumen_caja.empty else 0.0

            consumo = df_consumo_filtrado[df_consumo_filtrado["Caja"] == caja]["Monto"].sum() if not df_consumo_filtrado.empty else 0.0

            col1, col2, col3 = st.columns(3)
            col1.metric("Disponible", formatear_moneda(disponible))
            col2.metric("Consumo", formatear_moneda(consumo))
            col3.metric("Saldo", formatear_moneda(saldo))

        if len(cajas) == 1 and consumo > 0:
            st.header("Consumo por Proveedor")
            consumo_proveedor = df_consumo_filtrado.groupby("Proveedor")["Monto"].sum().sort_values(ascending=False)

            fig = go.Figure(data=[
                go.Bar(
                    x=consumo_proveedor.index,
                    y=consumo_proveedor.values,
                    marker_color='steelblue'
                )
            ])

            fig.update_layout(
                width=800,
                height=400,
                margin=dict(l=40, r=40, t=40, b=40),
                dragmode=False,
                xaxis=dict(fixedrange=True),
                yaxis=dict(fixedrange=True),
                xaxis_title="Proveedor",
                yaxis_title="Consumo"
            )

            st.plotly_chart(fig, use_container_width=False)

            st.header("Movimientos filtrados")
            df_filtrado_display = df_consumo_filtrado.copy()

            if 'Caja' in df_filtrado_display.columns:
                df_filtrado_display = df_filtrado_display.drop(columns=['Caja'])

            df_filtrado_display = df_filtrado_display.reset_index(drop=True)

            df_filtrado_display['Área'] = df_filtrado_display['Área'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)

            df_filtrado_display["Monto"] = df_filtrado_display["Monto"].apply(formatear_moneda)

            st.table(df_filtrado_display)

        elif len(cajas) == 1 and consumo == 0:
            st.info("No hay consumos para mostrar en el gráfico ni en la tabla con los filtros actuales.")

# --- Lógica principal ---
if st.session_state.pagina == "inicio":
    mostrar_inicio()
    if st.session_state.inicio_timestamp is None:
        st.session_state.inicio_timestamp = time.time()
    elif time.time() - st.session_state.inicio_timestamp > 3:
        st.session_state.pagina = "filtros"
        st.experimental_rerun()
elif st.session_state.pagina == "filtros":
    mostrar_filtros()
