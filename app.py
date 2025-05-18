import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
import matplotlib.pyplot as plt

# Parámetros fijos (nunca cambian)
NOMBRE_PLANILLA = "iacajas2025"
HOJAS = {
    "Movimientos Repuestos": "Movimientos Repuestos",
    "Resumen Repuestos": "Resumen Repuestos",
    "Movimientos Petróleo": "Movimientos Petróleo",
    "Resumen Petróleo": "Resumen Petróleo",
}
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Clave JSON completa (sin cambiar)
SERVICE_ACCOUNT_INFO = {
  "type": "service_account",
  "project_id": "control-caja-chica",
  "private_key_id": "08c8553d3666062055e19b08ca08f3c06e9bd469",
  "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCXfFYK2pQCqX/E
tO3kKB4+BU8cBxYA58wiwHDEV/XU/I0UCr61RO0svnncVgMuqzqGavO710NrUvFi
EZOFn9G7xpgED/Oy6z8smBeb6k+nsSIqBpzT0pmMEBNwBhfuUoP4F0sFfQcYENEB
uYg7C0dCwhoAWmAq7UOpyKVH5w93o/ZSYjIFFZAo9KyCVj2pj+Fas44lH6lusl78
CX7rzM37A13Iw2rm4gAcbGfpikIBCQV7WbPv7UB89NCWMJSKdtOjtO+ySWnuT+OJ
2eNI7rYdh5t9nt18DZa/BJgqXVZFs0MlbD+cDTxnbM9lhee6J1nINIxkwrjLO/9r
qifSmsv9AgMBAAECggEAL1EMdSZx/eTgvln/RnlLfPbej3QdKNo+VoqCjqmk5Uqf
bGewyuEFLiku2iZZpx2f0bWdfQpPijnloMq5qA7UDZGKERbEeZnmaTD2iuJk0A3R
jIv1N2q8QFYTJDYbCntmsjrgWY4Ehb1W83F2vm6W6yDCy2JvUGk87c745V0kZSts
HiMfdeWcN7li2P3ExWXrNapdT352JCCRNU0zVUIXaxlz0qJwfBoHl0JkxTSpJfjw
1Be7iYmCx+mdkh9Wy23ZupVg/oTzR9x9X68JUB4vhbXijTNNFca1tcNHgyP3Qzcm
wu00nh9BQ5jmNms68pZkdGix+bxUcTfL7wwJ5pR7lwKBgQDMN1CvoRtJrVeAmJs4
U6Dgk1icz+bD0BrvCqEv/X2RwMp8ajGgRVjvHaYAjXdQPAHm4Q/4gStbyKZmmnD/
J7OU8+WxDKDqTqT/7zcDjr/UjDnmLGJHnyANhTU79bnLaBjH9seBn585Vbyr+pM4
rG/XJrZ5BJHGQ2iu0sIBjjcG6wKBgQC95gc9qI1kYuUaoBHm0CzpYrUnUnyAakoo
5JcUDdmfS8aUC4JKAiFKdKx0LuD/gW7OwLLl57zn5O4emgkRk9o1tVrCKmbW3dSb
AXXFlPwRfCBKSQ2vYU+DTf6XVYRREVwaP67fDBt7O6FlecY6M5+5RWqpcKHsLVFn
Fa10Q6wOtwKBgF0xBPYQzBYUL3E0sujCaRDyzKZKzaEgD5p0PFhdEnd4Bi8+esUL
wGjmG8H2zLLln2yP2izqLTImX6FE6znVEUNxBamE/M3P88YDkRRjiTDiiO175aGP
gR4KYt+o5A9pwp1GBYcmo4+Ti5TjtVlQf30sYmrZZfiW/GeDMBtrnbrfAoGBAJvO
/OnuPfS739a0t3t2GyNyxcf5ugVzMF3VENB3fLNi7Q/TUZd/n+kDSewZ+qopfM1O
9noEZc6u22FoaUBu239tyYW+XJq3cBWuYP84eomuGqBYyE25vg+yEs4AcIxDfhpb
XhPMT1ARYR9thuOCL+9HsXhM3c52cG/wLV1TmPyJAoGAQqHtIusFocw+GYDBkRqF
t9xpjJAoiCLW8vzGoqH49ECmq9hVd51+GLk8KOtSf/J3FdChcbXSg4frkWM/p+vw
g1ejtvy9jObJOIbq5nWFRmBYozcyjCL7N0M9NcQzkcA+uQ0KxBAmEb2eKcnMNbnP
4pOsfhR2+/tv0sA0bvGCY/Y=
-----END PRIVATE KEY-----"""
  ,
  "client_email": "acceso-caja-chica@control-caja-chica.iam.gserviceaccount.com",
  "client_id": "101482543412506505259",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/acceso-caja-chica%40control-caja-chica.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# Autenticación y cliente gspread
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(credentials)

@st.cache_data(ttl=300)
def cargar_hoja(nombre_hoja):
    sheet = client.open(NOMBRE_PLANILLA).worksheet(nombre_hoja)
    df = get_as_dataframe(sheet, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")  # eliminar filas vacías
    return df

def obtener_proveedores(df):
    if df is None or "Proveedor" not in df.columns:
        return []
    provs = df["Proveedor"].dropna().unique()
    return sorted(provs) if len(provs) > 0 else []

def obtener_cuatrimestres(df):
    if df is None or "Cuatrimestre" not in df.columns:
        return []
    cuatris = df["Cuatrimestre"].dropna().unique()
    cuatris = sorted([int(c) for c in cuatris if str(c).isdigit()])
    return cuatris if len(cuatris) > 0 else []

# Cargar datos
df_mov_repuestos = cargar_hoja(HOJAS["Movimientos Repuestos"])
df_res_repuestos = cargar_hoja(HOJAS["Resumen Repuestos"])
df_mov_petroleo = cargar_hoja(HOJAS["Movimientos Petróleo"])
df_res_petroleo = cargar_hoja(HOJAS["Resumen Petróleo"])

st.title("Control de Caja Chica 2025")

# Obtener filtros válidos
cuatrimestres_repuestos = obtener_cuatrimestres(df_mov_repuestos)
cuatrimestres_petroleo = obtener_cuatrimestres(df_mov_petroleo)
cuatrimestres = sorted(set(cuatrimestres_repuestos) | set(cuatrimestres_petroleo))
if not cuatrimestres:
    cuatrimestres = [1, 2, 3, 4]  # Por defecto si no hay datos

proveedores_repuestos = obtener_proveedores(df_mov_repuestos)
proveedores_petroleo = obtener_proveedores(df_mov_petroleo)
proveedores = sorted(set(proveedores_repuestos) | set(proveedores_petroleo))
if not proveedores:
    proveedores
