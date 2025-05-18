# --- Cargar hojas ---
mov_repuestos = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Movimientos Repuestos").get_all_records())
res_repuestos = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Resumen Repuestos").get_all_records())
mov_petroleo = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Movimientos Petróleo").get_all_records())
res_petroleo = pd.DataFrame(client.open_by_key(sheet_id).worksheet("Resumen Petróleo").get_all_records())

# Mostrar columnas para verificar nombres exactos
st.write("Columnas Resumen Repuestos:", res_repuestos.columns.tolist())
st.write("Columnas Resumen Petróleo:", res_petroleo.columns.tolist())

# --- Funciones de limpieza según caja ---
def limpiar_repuestos(valor):
    try:
        texto = str(valor).strip()
        # Para repuestos, elimina puntos de miles y cambia coma decimal por punto
        texto = texto.replace(".", "").replace(",", ".")
        return float(texto)
    except:
        return None

def limpiar_petroleo(valor):
    try:
        texto = str(valor).strip()
        # Para petróleo, elimina comas de miles y cambia punto decimal por coma (si necesitas otro formato ajusta aquí)
        texto = texto.replace(",", "")
        return float(texto)
    except:
        return None

# Limpiar y convertir solo si la columna existe
cols_a_limpiar = ['Monto', 'Total Gastado', 'Saldo Actual']
for col in cols_a_limpiar:
    if col in res_repuestos.columns:
        res_repuestos[col] = res_repuestos[col].apply(limpiar_repuestos)
    if col in res_petroleo.columns:
        res_petroleo[col] = res_petroleo[col].apply(limpiar_petroleo)

# Luego continuar con el resto de código como antes...
