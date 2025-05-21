import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import requests

# Función para cargar datos desde Google Sheets
def cargar_datos(sheet_name, worksheet_name):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"])
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

# Función para crear un resumen simple de los datos
def resumen_caja_chica(df):
    resumen = ""
    for _, row in df.iterrows():
        resumen += f"Cuatrimestre {row.get('Cuatrimestre', '')}, Saldo Actual {row.get('Saldo Actual', '')}, Total Gastado {row.get('Total Gastado', '')}.\n"
    return resumen

# Crear prompt para la IA
def construir_prompt(resumen: str, pregunta: str) -> str:
    prompt = f"""
Estos son los datos de la caja chica:
{resumen}

Con base en esos datos, responde la siguiente pregunta:
{pregunta}

Respuesta:
"""
    return prompt

# Función para consultar la API de Huggingface
def consultar_huggingface(prompt: str):
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

# App principal Streamlit
def main():
    st.title("Consulta con IA sobre Cajas Chicas")

    hoja = st.selectbox("Seleccioná la hoja de resumen que querés consultar:", [
        "Resumen Repuestos", "Resumen Petróleo"
    ])

    st.write("Cargando datos desde Google Sheets...")
    df = cargar_datos("iacajas2025", hoja)

    resumen = resumen_caja_chica(df)
    st.text_area("Resumen de datos cargados", resumen, height=150)

    pregunta = st.text_input("Escribí tu pregunta sobre la caja chica:")

    if pregunta:
        with st.spinner("Consultando IA..."):
            prompt = construir_prompt(resumen, pregunta)
            respuesta = consultar_huggingface(prompt)
            st.markdown("### Respuesta de la IA:")
            st.write(respuesta)

if __name__ == "__main__":
    main()
