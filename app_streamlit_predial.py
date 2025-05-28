import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import numpy as np # Importar numpy para manejo de NaN

st.set_page_config(layout="wide", page_title="Plataforma Predial Municipal")
st.title("📊 Plataforma de Análisis Predial Municipal")

uploaded_file = st.file_uploader("Cargar archivo Excel con datos prediales", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Normalización de nombres de columnas
    df.columns = (
        df.columns.str.strip().str.lower()
        .str.replace(" ", "_")
        .str.replace("á", "a").str.replace("é", "e")
        .str.replace("í", "i").str.replace("ó", "o").str.replace("ú", "u")
        .str.replace("ñ", "n") # Añadir ñ si es necesario
    )

    # Validar que las columnas necesarias existan
    required_columns = [
        "valor_impuesto_a_pagar", "recaudo_predial", "pago_impuesto_predial",
        "avaluo_catastral", "descuentos_impuesto_predial", "sector",
        "sector_urbano", "vereda", "destino_economico_predio",
        "propiedad_horizontal", "latitud", "longitud", "codigo_igac",
        "area_construida", "financiacion_impuesto_predial"
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"El archivo Excel cargado no contiene las siguientes columnas requeridas: {', '.join(missing_columns)}. Por favor, asegúrese de que el archivo sea correcto.")
        st.stop() # Detener la ejecución si faltan columnas

    # Conversión de tipos y creación de nuevas columnas
    for col in ["valor_impuesto_a_pagar", "recaudo_predial", "avaluo_catastral",
                "descuentos_impuesto_predial", "latitud", "longitud", "area_construida"]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) # Convertir a numérico, NaN a 0

    df['saldo'] = df['valor_impuesto_a_pagar'] - df['recaudo_predial']
    df['cumplimiento'] = df['pago_impuesto_predial'].astype(str).str.lower().isin(['si', 'sí']) # Manejar 'si' y 'sí'

    with st.sidebar:
        st.header("Filtros Globales")
        # Asegurar que las listas de opciones no contengan NaN antes de unique() y que 'Todos' esté al principio
        sector_options = ["Todos"] + sorted(df["sector"].dropna().astype(str).unique().tolist())
        sector_urbano_options = ["Todos"] + sorted(df["sector_urbano"].dropna().astype(str).unique().tolist())
        vereda_options = ["Todas"] + sorted(df["vereda"].dropna().astype(str).unique().tolist())
        uso_options = ["Todos"] + sorted(df["destino_economico_predio"].dropna().astype(str).unique().tolist())

        sector = st.selectbox("Sector (urbano/rural)", sector_options)
        sector_urbano = st.selectbox("Sector Urbano", sector_urbano_options)
        vereda = st.selectbox("Vereda", vereda_options)
        uso = st.selectbox("Uso del predio", uso_options)
        ph = st.selectbox("Propiedad horizontal", ["Todos", "Sí", "No"])

    def aplicar_filtros(data):
        dff = data.copy()
        if sector != "Todos":
            dff = dff[dff["sector"].astype(str) == sector]
        if sector_urbano != "Todos":
            dff = dff[dff["sector_urbano"].astype(str) == sector_urbano]
        if vereda != "Todas":
            dff = dff[dff["vereda"].astype(str) == vereda]
        if uso != "Todos":
            dff = dff[dff["destino_economico_predio"].astype(str) == uso]
        if ph != "Todos":
            # Asegurarse de que la columna existe y manejar NaN
            if 'propiedad_horizontal' in dff.columns:
                dff = dff[dff["propiedad_horizontal"].astype(str).str.lower() == ph.lower()]
        return dff

    df_filtrado = aplicar_filtros(df)

    if df_filtrado.empty:
        st.warning("Los filtros seleccionados no arrojaron ningún resultado. Por favor, ajuste los filtros.")
        st.stop() # Detener la ejecución si no hay datos filtrados

    tabs = st.tabs([
        "📊 Información General",
        "📌 Cumplimiento Tributario",
        "📉 Cartera Morosa",
        "🏗️ Oportunidades Catastrales",
        "💼 Estrategias de Cobro",
        "🔮 Simulación de Escenarios",
        "🗺️ Riesgo Geoespacial"
    ])

    with tabs[0]:
        st.subheader("📊 Información General")

        def resumen_tabla(df_sub):
            return {
                "Número de predios": len(df_sub),
                "Avalúo total": df_sub['avaluo_catastral'].sum(),
                "Impuesto total": df_sub['valor_impuesto_a_pagar'].sum(),
                "Recaudo total": df_sub['recaudo_predial'].sum(),
                "Descuento total": df_sub['descuentos_impuesto_predial'].sum(),
                "Saldo por pagar": df_sub['saldo'].sum()
            }

        total = resumen_tabla(df_filtrado)
        urbano = resumen_tabla(df_filtrado[df_filtrado['sector'].astype(str).str.upper() == 'URBANO'])
        rural = resumen_tabla(df_filtrado[df_filtrado['sector'].astype(str).str.upper() == 'RURAL'])

        resumen_df = pd.DataFrame([total, urbano, rural], index=["Total", "Urbano", "Rural"]).T
        
        # Formato de dinero a las columnas relevantes
        format_mapping = {
            "Avalúo total": "${:,.0f}",
            "Impuesto total": "${:,.0f}",
            "Recaudo total": "${:,.0f}",
            "Descuento total": "${:,.0f}",
            "Saldo por pagar": "${:,.0f}"
        }
        
        # Corrección del error aquí: st.dataframe.style.format necesita un diccionario
        try:
            st.dataframe(
                resumen_df.style.format(format_mapping)
            )
        except Exception as e:
            st.warning(f"No se pudo aplicar formato de estilo a la tabla: {e}. Mostrando tabla sin formato.")
            st.dataframe(resumen_df)


    with tabs[1]:
        st.subheader("📌 Cumplimiento Tributario")

        pagados = df_filtrado[df_filtrado['cumplimiento'] == True]
        no_pagados = df_filtrado[df_filtrado['cumplimiento'] == False]

        # KPIs
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tasa de Cumplimiento", f"{len(pagados) / len(df_filtrado) * 100:.2f}%" if len(df_filtrado) > 0 else "0%")
        with col2:
            # Evitar división por cero
            total_impuesto_facturado = df_filtrado['valor_impuesto_a_pagar'].sum()
            recaudo_porcentaje = f"{pagados['recaudo_predial'].sum() / total_impuesto_facturado * 100:.2f}%" if total_impuesto_facturado > 0 else "0%"
            st.metric("Recaudo / Facturado", recaudo_porcentaje)
        with col3:
            st.metric("Predios Pagados", f"{len(pagados):,}")

        # Mapa: Asegurar que hay datos de latitud y longitud válidos para centrar el mapa
        if not df_filtrado.empty and not df_filtrado[['latitud', 'longitud']].isnull().all().all():
            map_center_lat = df_filtrado['latitud'].mean() if not df_filtrado['latitud'].isnull().all() else 4.710989
            map_center_lon = df_filtrado['longitud'].mean() if not df_filtrado['longitud'].isnull().all() else -74.072090
            m = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=13)

            for _, row in pagados.iterrows():
                if pd.notnull(row['latitud']) and pd.notnull(row['longitud']):
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=5,
                        color='green',
                        fill=True,
                        fill_opacity=0.6,
                        popup=f"IGAC: {row['codigo_igac']}\nPagado: ${row['recaudo_predial']:,.0f}"
                    ).add_to(m)
            for _, row in no_pagados.iterrows():
                if pd.notnull(row['latitud']) and pd.notnull(row['longitud']):
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=5,
                        color='red',
                        fill=True,
                        fill_opacity=0.6,
                        popup=f"IGAC: {row['codigo_igac']}\nPendiente: ${row['valor_impuesto_a_pagar']:,.0f}"
                    ).add_to(m)
            st_folium(m, width=1000, height=500)
        else:
            st.warning("No hay datos de latitud/longitud para mostrar en el mapa de Cumplimiento Tributario o los datos filtrados están vacíos.")


        st.markdown("### Tabla de Predios que Pagaron")
        if not tabla_pagados.empty:
            tabla_pagados = pagados.sort_values(by="recaudo_predial", ascending=False)[
                ["codigo_igac", "vereda", "sector", "valor_impuesto_a_pagar", "recaudo_predial"]
            ]
            st.dataframe(tabla_pagados.reset_index(drop=True).style.format({"valor_impuesto_a_pagar": "${:,.0f}", "recaudo_predial": "${:,.0f}"}))
        else:
            st.info("No hay predios pagados para mostrar con los filtros actuales.")


    with tabs[2]:
        st.subheader("📉 Segmentación de Cartera Morosa")

        morosos = df_filtrado[df_filtrado['cumplimiento'] == False]

        st.markdown(f"**Número total de predios morosos:** {len(morosos):,}")
        st.markdown(f"**Valor total en mora:** ${morosos['valor_impuesto_a_pagar'].sum():,.0f}")

        # Mapa de morosos
        if not morosos.empty and not morosos[['latitud', 'longitud']].isnull().all().all():
            map_center_lat_mora = morosos['latitud'].mean() if not morosos['latitud'].isnull().all() else 4.710989
            map_center_lon_mora = morosos['longitud'].mean() if not morosos['longitud'].isnull().all() else -74.072090
            m_mora = folium.Map(location=[map_center_lat_mora, map_center_lon_mora], zoom_start=13)
            for _, row in morosos.iterrows():
                if pd.notnull(row['latitud']) and pd.notnull(row['longitud']):
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=5,
                        color='red',
                        fill=True,
                        fill_opacity=0.6,
                        popup=f"IGAC: {row['codigo_igac']}\nImpuesto: ${row['valor_impuesto_a_pagar']:,.0f}"
                    ).add_to(m_mora)
            st_folium(m_mora, width=1000, height=500)
        else:
            st.warning("No hay datos de latitud/longitud para mostrar en el mapa de Cartera Morosa o no hay predios morosos con los filtros actuales.")


        st.markdown("### Tabla de Predios Morosos")
        if not morosos.empty:
            tabla_morosos = morosos[
                ["codigo_igac", "vereda", "sector", "destino_economico_predio", "avaluo_catastral", "valor_impuesto_a_pagar", "area_construida"]
            ]
            st.dataframe(tabla_morosos.reset_index(drop=True).style.format({"avaluo_catastral": "${:,.0f}", "valor_impuesto_a_pagar": "${:,.0f}"}))
        else:
            st.info("No hay predios morosos para mostrar con los filtros actuales.")


    with tabs[3]:
        st.subheader("🏗️ Oportunidades de Actualización Catastral")

        # Asegurarse de que el avalúo catastral y el área construida sean numéricos
        df_filtrado['avaluo_catastral'] = pd.to_numeric(df_filtrado['avaluo_catastral'], errors='coerce').fillna(0)
        df_filtrado['area_construida'] = pd.to_numeric(df_filtrado['area_construida'], errors='coerce').fillna(0)


        # Condición para sin_construccion
        sin_construccion = df_filtrado[df_filtrado['area_construida'] == 0]
        # Asegurarse de que haya valores en avaluo_catastral antes de calcular la mediana
        if not sin_construccion['avaluo_catastral'].empty:
            alto_avaluo = sin_construccion[sin_construccion['avaluo_catastral'] > sin_construccion['avaluo_catastral'].median()]
        else:
            alto_avaluo = pd.DataFrame() # DataFrame vacío si no hay datos

        # Condición para sin_pago_alto
        if not df_filtrado['valor_impuesto_a_pagar'].empty:
            sin_pago_alto = df_filtrado[
                (df_filtrado['cumplimiento'] == False) &
                (df_filtrado['valor_impuesto_a_pagar'] > df_filtrado['valor_impuesto_a_pagar'].median())
            ]
        else:
            sin_pago_alto = pd.DataFrame()

        oportunidades = pd.concat([alto_avaluo, sin_pago_alto]).drop_duplicates()

        st.markdown(f"**Total de predios con posibles oportunidades catastrales:** {len(oportunidades):,}")

        # Mapa
        if not oportunidades.empty and not oportunidades[['latitud', 'longitud']].isnull().all().all():
            map_center_opp_lat = oportunidades['latitud'].mean() if not oportunidades['latitud'].isnull().all() else 4.710989
            map_center_opp_lon = oportunidades['longitud'].mean() if not oportunidades['longitud'].isnull().all() else -74.072090
            mapa_opp = folium.Map(location=[map_center_opp_lat, map_center_opp_lon], zoom_start=13)
            for _, row in oportunidades.iterrows():
                if pd.notnull(row['latitud']) and pd.notnull(row['longitud']):
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=5,
                        color='orange',
                        fill=True,
                        fill_opacity=0.6,
                        popup=(f"IGAC: {row['codigo_igac']}\nÁrea: {row['area_construida']}\n"
                               f"Avalúo: ${row['avaluo_catastral']:,.0f}\nImpuesto: ${row['valor_impuesto_a_pagar']:,.0f}")
                    ).add_to(mapa_opp)
            st_folium(mapa_opp, width=1000, height=500)
        else:
            st.warning("No hay datos de latitud/longitud para mostrar en el mapa de Oportunidades Catastrales o no hay oportunidades con los filtros actuales.")

        st.markdown("### Tabla de Predios con Oportunidades Catastrales")
        if not oportunidades.empty:
            st.dataframe(oportunidades[[
                "codigo_igac", "vereda", "sector", "avaluo_catastral", "valor_impuesto_a_pagar", "area_construida"
            ]].reset_index(drop=True).style.format({"avaluo_catastral": "${:,.0f}", "valor_impuesto_a_pagar": "${:,.0f}"}))
        else:
            st.info("No hay predios con oportunidades catastrales para mostrar con los filtros actuales.")


    with tabs[4]:
        st.subheader("💼 Estrategias de Cobro")

        morosos = df_filtrado[df_filtrado['cumplimiento'] == False]
        predios_focalizables = morosos.sort_values(by="valor_impuesto_a_pagar", ascending=False).head(50)

        st.markdown(f"**Top 50 predios con mayor valor de impuesto en mora:**")

        # Mapa focalizado
        if not predios_focalizables.empty and not predios_focalizables[['latitud', 'longitud']].isnull().all().all():
            map_center_cobro_lat = predios_focalizables['latitud'].mean() if not predios_focalizables['latitud'].isnull().all() else 4.710989
            map_center_cobro_lon = predios_focalizables['longitud'].mean() if not predios_focalizables['longitud'].isnull().all() else -74.072090
            mapa_cobro = folium.Map(location=[map_center_cobro_lat, map_center_cobro_lon], zoom_start=13)
            for _, row in predios_focalizables.iterrows():
                if pd.notnull(row['latitud']) and pd.notnull(row['longitud']):
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=6,
                        color='blue',
                        fill=True,
                        fill_opacity=0.6,
                        popup=f"IGAC: {row['codigo_igac']}\nMora: ${row['valor_impuesto_a_pagar']:,.0f}"
                    ).add_to(mapa_cobro)
            st_folium(mapa_cobro, width=1000, height=500)
        else:
            st.warning("No hay datos de latitud/longitud para mostrar en el mapa de Estrategias de Cobro o no hay predios focalizables con los filtros actuales.")

        st.markdown("### Tabla de Predios Focalizados para Cobro")
        if not predios_focalizables.empty:
            st.dataframe(predios_focalizables[[
                "codigo_igac", "vereda", "sector", "avaluo_catastral", "valor_impuesto_a_pagar", "area_construida"
            ]].reset_index(drop=True).style.format({"avaluo_catastral": "${:,.0f}", "valor_impuesto_a_pagar": "${:,.0f}"}))
        else:
            st.info("No hay predios focalizados para cobro con los filtros actuales.")


        st.markdown("### 📌 Recomendaciones Estratégicas")
        st.markdown("""
    - Iniciar acuerdos de pago con predios con mora mayor a $10 millones en sectores urbanos con alta valorización.
    - Priorizar visitas de notificación en veredas con concentración de predios morosos.
    - Enviar comunicaciones formales a predios con más de 2 años consecutivos de mora.
    - Implementar campañas de condonación parcial de intereses para predios pequeños rurales.
    - Generar alertas automáticas para predios con alta mora y sin pago ni financiación.
    """)


    with tabs[5]:
        st.subheader("🔮 Simulación de Escenarios de Recaudo")

        morosos = df_filtrado[df_filtrado['cumplimiento'] == False]
        total_morosidad = morosos['valor_impuesto_a_pagar'].sum()
        escenarios = [10, 30, 50, 100]

        st.markdown(f"**Valor total en mora:** ${total_morosidad:,.0f}")

        for e in escenarios:
            valor = total_morosidad * (e / 100)
            st.markdown(f"**→ {e}% cobertura:** ${valor:,.0f}")

        # Tabla y mapa de predios incluidos en el escenario
        st.markdown("### Mapa y Tabla de Predios Simulados (100%)")
        top_simulados = morosos.sort_values(by='valor_impuesto_a_pagar', ascending=False)

        if not top_simulados.empty and not top_simulados[['latitud', 'longitud']].isnull().all().all():
            map_center_sim_lat = top_simulados['latitud'].mean() if not top_simulados['latitud'].isnull().all() else 4.710989
            map_center_sim_lon = top_simulados['longitud'].mean() if not top_simulados['longitud'].isnull().all() else -74.072090
            mapa_sim = folium.Map(location=[map_center_sim_lat, map_center_sim_lon], zoom_start=13)
            for _, row in top_simulados.iterrows():
                if pd.notnull(row['latitud']) and pd.notnull(row['longitud']):
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=5,
                        color='blue',
                        fill=True,
                        fill_opacity=0.4,
                        popup=f"IGAC: {row['codigo_igac']}\nImpuesto: ${row['valor_impuesto_a_pagar']:,.0f}"
                    ).add_to(mapa_sim)
            st_folium(mapa_sim, width=1000, height=500)
        else:
            st.warning("No hay datos de latitud/longitud para mostrar en el mapa de Simulación de Escenarios o no hay predios para simular con los filtros actuales.")

        st.markdown("### Tabla de Predios Involucrados en Simulación")
        if not top_simulados.empty:
            st.dataframe(top_simulados[[
                "codigo_igac", "vereda", "sector", "valor_impuesto_a_pagar"
            ]].reset_index(drop=True).style.format({"valor_impuesto_a_pagar": "${:,.0f}"}))
        else:
            st.info("No hay predios para simular con los filtros actuales.")


    with tabs[6]:
        st.subheader("🗺️ Mapa de Riesgo Tributario Geoespacial")

        df_riesgo = df_filtrado.copy()

        # Asegurarse de que las columnas sean numéricas antes de usarlas en qcut y comparaciones
        df_riesgo['valor_impuesto_a_pagar'] = pd.to_numeric(df_riesgo['valor_impuesto_a_pagar'], errors='coerce').fillna(0)
        df_riesgo['avaluo_catastral'] = pd.to_numeric(df_riesgo['avaluo_catastral'], errors='coerce').fillna(0)
        df_riesgo['area_construida'] = pd.to_numeric(df_riesgo['area_construida'], errors='coerce').fillna(0)
        df_riesgo['financiacion_impuesto_predial'] = df_riesgo['financiacion_impuesto_predial'].astype(str).str.lower()


        # Riesgo fiscal
        if not df_riesgo['valor_impuesto_a_pagar'].empty and df_riesgo['valor_impuesto_a_pagar'].nunique() > 1:
            df_riesgo['riesgo_fiscal'] = pd.qcut(df_riesgo['valor_impuesto_a_pagar'].rank(method='first'), 5, labels=[1,2,3,4,5])
        else:
            df_riesgo['riesgo_fiscal'] = 1 # Asignar un valor por defecto si no hay suficientes valores únicos


        # Riesgo catastral
        df_riesgo['riesgo_catastral'] = 1
        # Asegurarse de que haya suficientes valores para calcular la mediana y los quantiles
        if not df_riesgo['avaluo_catastral'].empty and not df_riesgo['area_construida'].empty:
            sin_construccion_cond = (df_riesgo['area_construida'] == 0) & (df_riesgo['avaluo_catastral'] > df_riesgo['avaluo_catastral'].median())
            bajo_construccion_cond = (df_riesgo['area_construida'] < df_riesgo['area_construida'].quantile(0.2)) & (df_riesgo['avaluo_catastral'] > df_riesgo['avaluo_catastral'].quantile(0.6))
            df_riesgo.loc[sin_construccion_cond, 'riesgo_catastral'] = 5
            df_riesgo.loc[bajo_construccion_cond, 'riesgo_catastral'] = 3

        # Riesgo comportamental
        df_riesgo['riesgo_comportamental'] = 1
        df_riesgo.loc[
            (df_riesgo['cumplimiento'] == False) & (df_riesgo['financiacion_impuesto_predial'] == 'no'),
            'riesgo_comportamental'
        ] = 5
        df_riesgo.loc[
            (df_riesgo['cumplimiento'] == False) & (df_riesgo['financiacion_impuesto_predial'] == 'si'),
            'riesgo_comportamental'
        ] = 3

        # Cálculo total (asegurarse de que las columnas sean numéricas antes de la suma)
        df_riesgo['riesgo_total'] = (
            0.5 * df_riesgo['riesgo_fiscal'].astype(float) +
            0.3 * df_riesgo['riesgo_catastral'].astype(float) +
            0.2 * df_riesgo['riesgo_comportamental'].astype(float)
        )

        df_riesgo = df_riesgo.sort_values(by="riesgo_total", ascending=False)

        # Mapa de riesgo
        if not df_riesgo.empty and not df_riesgo[['latitud', 'longitud']].isnull().all().all():
            map_center_riesgo_lat = df_riesgo['latitud'].mean() if not df_riesgo['latitud'].isnull().all() else 4.710989
            map_center_riesgo_lon = df_riesgo['longitud'].mean() if not df_riesgo['longitud'].isnull().all() else -74.072090
            mapa_riesgo = folium.Map(location=[map_center_riesgo_lat, map_center_riesgo_lon], zoom_start=13)
            for _, row in df_riesgo.iterrows():
                if pd.notnull(row['latitud']) and pd.notnull(row['longitud']):
                    folium.CircleMarker(
                        location=[row['latitud'], row['longitud']],
                        radius=5,
                        color='darkred',
                        fill=True,
                        fill_opacity=0.5,
                        popup=f"IGAC: {row['codigo_igac']}\nRiesgo Total: {row['riesgo_total']:.2f}"
                    ).add_to(mapa_riesgo)
            st_folium(mapa_riesgo, width=1000, height=500)
        else:
            st.warning("No hay datos de latitud/longitud para mostrar en el mapa de Riesgo Tributario o los datos filtrados están vacíos.")

        st.markdown("### Tabla de Predios con Mayor Riesgo")
        if not df_riesgo.empty:
            st.dataframe(df_riesgo[[
                "codigo_igac", "vereda", "sector", "valor_impuesto_a_pagar", "avaluo_catastral", "area_construida", "riesgo_total"
            ]].reset_index(drop=True).style.format({"valor_impuesto_a_pagar": "${:,.0f}", "avaluo_catastral": "${:,.0f}", "riesgo_total": "{:.2f}"}))
        else:
            st.info("No hay predios con mayor riesgo para mostrar con los filtros actuales.")

else:
    st.info("Por favor, cargue un archivo Excel para comenzar el análisis.")
