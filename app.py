# ... (código anterior)

for caja in cajas:
    st.subheader(f"Caja: {caja}")
    resumen = df_res[(df_res["Caja"] == caja) & (df_res["Cuatrimestre"].isin(cuatrimestres))]
    if not resumen.empty:
        disponible = resumen["Monto"].sum()
        gastado = resumen["Total Gastado"].sum()
        saldo = resumen["Saldo Actual"].sum()
        pct_usado = (gastado / disponible) * 100 if disponible > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Disponible", formatear_moneda(disponible))
        col2.metric("Gastado", formatear_moneda(gastado))
        col3.metric("Saldo", formatear_moneda(saldo))

        # Gráfico de barras con etiquetas
        fig, ax = plt.subplots()
        barras = ax.bar(["Gastado", "Saldo"], [gastado, saldo], color=["#ff4b4b", "#4bffa8"])
        # Se elimina la línea que asigna el título para no mostrar leyenda
        # ax.set_title(f"Distribución: {caja}")
        for barra in barras:
            altura = barra.get_height()
            ax.annotate(formatear_moneda(altura),
                        xy=(barra.get_x() + barra.get_width() / 2, altura),
                        xytext=(0, 5),
                        textcoords="offset points",
                        ha='center', va='bottom')
        st.pyplot(fig)
    else:
        st.info(f"No hay resumen disponible para la caja {caja} con los filtros seleccionados.")

# ... (resto del código)
