import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- Configuración ---
SPREADSHEET_ID = "tu_id_de_planilla_aqui"  # <-- Pon tu ID real
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

@st.cache_data(show_spinner=False)
def cargar_hoja(nombre_hoja):
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SPREADSHEET_ID, range=nombre_hoja)
        .execute()
    )
    values = result.get("values", [])
    if not values:
        return pd.DataFrame()
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

def main():
    st.title("Control de Caja Chica - Streamlit")

    tabs = st.tabs(
        [
            "Movimientos Repuestos",
            "Resumen Repuestos",
            "Movimientos Petróleo",
            "Resumen Petróleo",
        ]
    )

    # Movimientos Repuestos con filtro
    with tabs[0]:
        df_rep_mov = cargar_hoja("Movimientos Repuestos")
        if df_rep_mov.empty:
            st.warning("No hay datos en Movimientos Repuestos.")
        else:
            cuatrimestres = df_rep_mov["Cuatrimestre"].unique()
            filtro_cuatrimestre = st.selectbox(
                "Filtrar por Cuatrimestre", options=["Todos"] + list(cuatrimestres)
            )
            if filtro_cuatrimestre != "Todos":
                df_rep_mov = df_rep_mov[df_rep_mov["Cuatrimestre"] == filtro_cuatrimestre]

            st.dataframe(df_rep_mov)

    # Resumen Repuestos con métricas
    with tabs[1]:
        df_rep_res = cargar_hoja("Resumen Repuestos")
        if df_rep_res.empty:
            st.warning("No hay datos en Resumen Repuestos.")
        else:
            st.dataframe(df_rep_res)
            try:
                saldo = float(df_rep_res["Saldo Actual"].iloc[-1])
                total_gastado = float(df_rep_res["Total Gastado"].iloc[-1])
                st.metric("Saldo Actual Repuestos", f"${saldo:,.2f}")
                st.metric("Total Gastado Repuestos", f"${total_gastado:,.2f}")
            except Exception:
                st.info("No se pudieron mostrar métricas numéricas.")

    # Movimientos Petróleo con filtro
    with tabs[2]:
        df_pet_mov = cargar_hoja("Movimientos Petróleo")
        if df_pet_mov.empty:
            st.warning("No hay datos en Movimientos Petróleo.")
        else:
            cuatrimestres = df_pet_mov["Cuatrimestre"].unique()
            filtro_cuatrimestre = st.selectbox(
                "Filtrar por Cuatrimestre", options=["Todos"] + list(cuatrimestres), key="pet_mov"
            )
            if filtro_cuatrimestre != "Todos":
                df_pet_mov = df_pet_mov[df_pet_mov["Cuatrimestre"] == filtro_cuatrimestre]

            st.dataframe(df_pet_mov)

    # Resumen Petróleo con métricas
    with tabs[3]:
        df_pet_res = cargar_hoja("Resumen Petróleo")
        if df_pet_res.empty:
            st.warning("No hay datos en Resumen Petróleo.")
        else:
            st.dataframe(df_pet_res)
            try:
                saldo = float(df_pet_res["Saldo Actual"].iloc[-1])
                total_gastado = float(df_pet_res["Total Gastado"].iloc[-1])
                st.metric("Saldo Actual Petróleo", f"${saldo:,.2f}")
                st.metric("Total Gastado Petróleo", f"${total_gastado:,.2f}")
            except Exception:
                st.info("No se pudieron mostrar métricas numéricas.")

if __name__ == "__main__":
    main()
