
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

st.set_page_config(layout="wide", page_title="Plataforma Predial Municipal")
st.title("📊 Plataforma de Análisis Predial Municipal")

uploaded_file = st.file_uploader("Cargar archivo Excel con datos prediales", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    df.columns = (
        df.columns.str.strip().str.lower()
        .str.replace(" ", "_")
        .str.replace("á", "a").str.replace("é", "e")
        .str.replace("í", "i").str.replace("ó", "o").str.replace("ú", "u")
    )

    df['saldo'] = df['valor_impuesto_a_pagar'] - df['recaudo_predial']
    df['cumplimiento'] = df['pago_impuesto_predial'].str.lower() == 'si'

    with st.sidebar:
        st.header("Filtros Globales")
        sector = st.selectbox("Sector (urbano/rural)", ["Todos"] + sorted(df["sector"].dropna().unique().tolist()))
        sector_urbano = st.selectbox("Sector Urbano", ["Todos"] + sorted(df["sector_urbano"].dropna().unique().tolist()))
        vereda = st.selectbox("Vereda", ["Todas"] + sorted(df["vereda"].dropna().unique().tolist()))
        uso = st.selectbox("Uso del predio", ["Todos"] + sorted(df["destino_economico_predio"].dropna().unique().tolist()))
        ph = st.selectbox("Propiedad horizontal", ["Todos", "Sí", "No"])

    def aplicar_filtros(data):
        dff = data.copy()
        if sector != "Todos":
            dff = dff[dff["sector"] == sector]
        if sector_urbano != "Todos":
            dff = dff[dff["sector_urbano"] == sector_urbano]
        if vereda != "Todas":
            dff = dff[dff["vereda"] == vereda]
        if uso != "Todos":
            dff = dff[dff["destino_economico_predio"] == uso]
        if ph != "Todos":
            dff = dff[dff["propiedad_horizontal"].str.lower() == ph.lower()]
        return dff

    df_filtrado = aplicar_filtros(df)

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
    urbano = resumen_tabla(df_filtrado[df_filtrado['sector'] == 'URBANO'])
    rural = resumen_tabla(df_filtrado[df_filtrado['sector'] == 'RURAL'])

    resumen_df = pd.DataFrame([total, urbano, rural], index=["Total", "Urbano", "Rural"]).T
    try:
        st.dataframe(
            resumen_df.style.format(
        )
    except Exception as e:
        st.warning("No se pudo aplicar formato de estilo a la tabla.")
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
        st.metric("Recaudo / Facturado", f"{pagados['recaudo_predial'].sum() / df_filtrado['valor_impuesto_a_pagar'].sum() * 100:.2f}%" if df_filtrado['valor_impuesto_a_pagar'].sum() > 0 else "0%")
    with col3:
        st.metric("Predios Pagados", f"{len(pagados):,}")

    # Mapa
    m = folium.Map(location=[df_filtrado['latitud'].mean(), df_filtrado['longitud'].mean()], zoom_start=13)
    for _, row in pagados.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=5,
            color='green',
            fill=True,
            fill_opacity=0.6,
            popup=f"IGAC: {row['codigo_igac']}\nPagado: ${row['recaudo_predial']:,.0f}"
        ).add_to(m)
    for _, row in no_pagados.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=5,
            color='red',
            fill=True,
            fill_opacity=0.6,
            popup=f"IGAC: {row['codigo_igac']}\nPendiente: ${row['valor_impuesto_a_pagar']:,.0f}"
        ).add_to(m)

    st_folium(m, width=1000, height=500)

    st.markdown("### Tabla de Predios que Pagaron")
    tabla_pagados = pagados.sort_values(by="recaudo_predial", ascending=False)[
        ["codigo_igac", "vereda", "sector", "valor_impuesto_a_pagar", "recaudo_predial"]
    ]
    st.dataframe(tabla_pagados.reset_index(drop=True).style.format("${:,.0f}"))



with tabs[2]:
    st.subheader("📉 Segmentación de Cartera Morosa")

    morosos = df_filtrado[df_filtrado['cumplimiento'] == False]

    st.markdown(f"**Número total de predios morosos:** {len(morosos):,}")
    st.markdown(f"**Valor total en mora:** ${morosos['valor_impuesto_a_pagar'].sum():,.0f}")

    # Mapa de morosos
    m_mora = folium.Map(location=[morosos['latitud'].mean(), morosos['longitud'].mean()], zoom_start=13)
    for _, row in morosos.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=5,
            color='red',
            fill=True,
            fill_opacity=0.6,
            popup=f"IGAC: {row['codigo_igac']}\nImpuesto: ${row['valor_impuesto_a_pagar']:,.0f}"
        ).add_to(m_mora)

    st_folium(m_mora, width=1000, height=500)

    st.markdown("### Tabla de Predios Morosos")
    tabla_morosos = morosos[
        ["codigo_igac", "vereda", "sector", "destino_economico_predio", "avaluo_catastral", "valor_impuesto_a_pagar", "area_construida"]
    ]
    st.dataframe(tabla_morosos.reset_index(drop=True).style.format("${:,.0f}"))



with tabs[3]:
    st.subheader("🏗️ Oportunidades de Actualización Catastral")

    sin_construccion = df_filtrado[df_filtrado['area_construida'] == 0]
    alto_avaluo = sin_construccion[sin_construccion['avaluo_catastral'] > sin_construccion['avaluo_catastral'].median()]

    sin_pago_alto = df_filtrado[
        (df_filtrado['cumplimiento'] == False) &
        (df_filtrado['valor_impuesto_a_pagar'] > df_filtrado['valor_impuesto_a_pagar'].median())
    ]

    oportunidades = pd.concat([alto_avaluo, sin_pago_alto]).drop_duplicates()

    st.markdown(f"**Total de predios con posibles oportunidades catastrales:** {len(oportunidades):,}")

    # Mapa
    mapa_opp = folium.Map(location=[oportunidades['latitud'].mean(), oportunidades['longitud'].mean()], zoom_start=13)
    for _, row in oportunidades.iterrows():
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

    st.markdown("### Tabla de Predios con Oportunidades Catastrales")
    st.dataframe(oportunidades[[
        "codigo_igac", "vereda", "sector", "avaluo_catastral", "valor_impuesto_a_pagar", "area_construida"
    ]].reset_index(drop=True).style.format("${:,.0f}"))



with tabs[4]:
    st.subheader("💼 Estrategias de Cobro")

    morosos = df_filtrado[df_filtrado['cumplimiento'] == False]
    predios_focalizables = morosos.sort_values(by="valor_impuesto_a_pagar", ascending=False).head(50)

    st.markdown(f"**Top 50 predios con mayor valor de impuesto en mora:**")

    # Mapa focalizado
    mapa_cobro = folium.Map(location=[predios_focalizables['latitud'].mean(), predios_focalizables['longitud'].mean()], zoom_start=13)
    for _, row in predios_focalizables.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=6,
            color='blue',
            fill=True,
            fill_opacity=0.6,
            popup=f"IGAC: {row['codigo_igac']}\nMora: ${row['valor_impuesto_a_pagar']:,.0f}"
        ).add_to(mapa_cobro)

    st_folium(mapa_cobro, width=1000, height=500)

    st.markdown("### Tabla de Predios Focalizados para Cobro")
    st.dataframe(predios_focalizables[[
        "codigo_igac", "vereda", "sector", "avaluo_catastral", "valor_impuesto_a_pagar", "area_construida"
    ]].reset_index(drop=True).style.format("${:,.0f}"))

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

    mapa_sim = folium.Map(location=[top_simulados['latitud'].mean(), top_simulados['longitud'].mean()], zoom_start=13)
    for _, row in top_simulados.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=5,
            color='blue',
            fill=True,
            fill_opacity=0.4,
            popup=f"IGAC: {row['codigo_igac']}\nImpuesto: ${row['valor_impuesto_a_pagar']:,.0f}"
        ).add_to(mapa_sim)

    st_folium(mapa_sim, width=1000, height=500)

    st.markdown("### Tabla de Predios Involucrados en Simulación")
    st.dataframe(top_simulados[[
        "codigo_igac", "vereda", "sector", "valor_impuesto_a_pagar"
    ]].reset_index(drop=True).style.format("${:,.0f}"))



with tabs[6]:
    st.subheader("🗺️ Mapa de Riesgo Tributario Geoespacial")

    df_riesgo = df_filtrado.copy()

    # Riesgo fiscal
    df_riesgo['riesgo_fiscal'] = pd.qcut(df_riesgo['valor_impuesto_a_pagar'].rank(method='first'), 5, labels=[1,2,3,4,5])

    # Riesgo catastral
    df_riesgo['riesgo_catastral'] = 1
    sin_construccion = (df_riesgo['area_construida'] == 0) & (df_riesgo['avaluo_catastral'] > df_riesgo['avaluo_catastral'].median())
    bajo_construccion = (df_riesgo['area_construida'] < df_riesgo['area_construida'].quantile(0.2)) & (df_riesgo['avaluo_catastral'] > df_riesgo['avaluo_catastral'].quantile(0.6))
    df_riesgo.loc[sin_construccion, 'riesgo_catastral'] = 5
    df_riesgo.loc[bajo_construccion, 'riesgo_catastral'] = 3

    # Riesgo comportamental
    df_riesgo['riesgo_comportamental'] = 1
    df_riesgo.loc[
        (df_riesgo['cumplimiento'] == False) & (df_riesgo['financiacion_impuesto_predial'].str.lower() == 'no'),
        'riesgo_comportamental'
    ] = 5
    df_riesgo.loc[
        (df_riesgo['cumplimiento'] == False) & (df_riesgo['financiacion_impuesto_predial'].str.lower() == 'si'),
        'riesgo_comportamental'
    ] = 3

    # Cálculo total
    df_riesgo['riesgo_total'] = (
        0.5 * df_riesgo['riesgo_fiscal'].astype(float) +
        0.3 * df_riesgo['riesgo_catastral'].astype(float) +
        0.2 * df_riesgo['riesgo_comportamental'].astype(float)
    )

    df_riesgo = df_riesgo.sort_values(by="riesgo_total", ascending=False)

    # Mapa de riesgo
    mapa_riesgo = folium.Map(location=[df_riesgo['latitud'].mean(), df_riesgo['longitud'].mean()], zoom_start=13)
    for _, row in df_riesgo.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=5,
            color='darkred',
            fill=True,
            fill_opacity=0.5,
            popup=f"IGAC: {row['codigo_igac']}\nRiesgo Total: {row['riesgo_total']:.2f}"
        ).add_to(mapa_riesgo)

    st_folium(mapa_riesgo, width=1000, height=500)

    st.markdown("### Tabla de Predios con Mayor Riesgo")
    st.dataframe(df_riesgo[[
        "codigo_igac", "vereda", "sector", "valor_impuesto_a_pagar", "avaluo_catastral", "area_construida", "riesgo_total"
    ]].reset_index(drop=True).style.format({"valor_impuesto_a_pagar": "${:,.0f}", "avaluo_catastral": "${:,.0f}", "riesgo_total": "{:.2f}"}))
