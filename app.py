import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import requests

# Función para cargar datos desde Google Sheets
def cargar_datos(sheet_name, worksheet_name):
    google_creds = st.secrets["google_service_account"]
    creds = Credentials.from_service_account_info(google_creds, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    gc = gspread.authorize(creds)
    spreadsheet = gc.open(sheet_name)
    worksheet = spreadsheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

# Crear prompt para IA
def construir_prompt(df, pregunta):
    # Puedes crear un resumen o usar datos completos según tamaño
    resumen = df.head(10).to_string()  # ejemplo: primeros 10 registros en texto
    prompt = f"""
Estos son algunos datos de la caja chica:
{resumen}

Basado en estos datos, responde la siguiente pregunta:
{pregunta}

Respuesta:
"""
    return prompt

# Consultar API Huggingface
def consultar_huggingface(prompt):
    API_URL = "https://api-inference.huggingface.co/models/gpt2"
    headers = {"Authorization": f"Bearer {st.secrets['huggingface']['token']}"}
    payload = {"inputs": prompt}
    response = requests.post(API_URL, headers=headers, json=payload)
    respuesta = response.json()

    if isinstance(respuesta, list) and len(respuesta) > 0 and "generated_text" in respuesta[0]:
        return respuesta[0]["generated_text"]
    elif isinstance(respuesta, dict) and "error" in respuesta:
        return "Error de la API: " + respuesta["error"]
    else:
        return str(respuesta)

# App principal
def main():
    st.title("Consulta IA sobre Cajas Chicas")

    st.write("Cargando datos desde Google Sheets...")
    df = cargar_datos("iacajas2025", "Movimientos Repuestos")

    st.write("Primeros 5 registros:")
    st.dataframe(df.head())

    pregunta = st.text_input("Escribe tu pregunta sobre la caja chica:")

    if pregunta:
        with st.spinner("Consultando IA..."):
            prompt = construir_prompt(df, pregunta)
            respuesta = consultar_huggingface(prompt)
            st.markdown("### Respuesta de la IA:")
            st.write(respuesta)

if __name__ == "__main__":
    main()
