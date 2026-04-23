import streamlit as st
import pandas as pd
import requests
import graphviz

st.set_page_config(page_title="Relevamiento de Procesos - Lomas de Zamora", layout="wide")

st.title("🏛️ Relevamiento de Procesos Internos")
st.write("Complete los datos generales y detalle el flujo documental de cada paso.")

# --- SECCIÓN 1: DATOS GENERALES ---
col1, col2 = st.columns(2)

with col1:
    direccion = st.selectbox(
        "Dirección:",
        ["Fiscalización", "Rentas", "A.R.L.O", "Capacidad contributiva", "Seguridad e higiene", "Ingresos públicos"]
    )
    canal = st.selectbox("Canal:", ["Presencial", "Online", "Telefónico", "Otros"])

with col2:
    nombre_tramite = st.text_input("Nombre del trámite:", placeholder="Ej: Alta de inmueble")

st.divider()

# --- SECCIÓN 2: DETALLE DEL TRÁMITE (TABLA DINÁMICA) ---
st.subheader("Pasos del Proceso")
st.info("💡 Consejo: Si el trámite continúa en otro paso, asegúrese de indicar qué documento se genera para que el siguiente sector lo reciba.")

# Estructura de la tabla con las nuevas columnas de trazabilidad documental
if "pasos_data" not in st.session_state:
    st.session_state["pasos_data"] = pd.DataFrame(
        columns=[
            "Doc. que Ingresa", 
            "Sector Interviniente", 
            "Procesos Realizados", 
            "Doc. que se Genera", 
            "Salida", 
            "Certificación", 
            "¿Cuál?"
        ]
    )

# Configuración avanzada de columnas
config_columnas = {
    "Doc. que Ingresa": st.column_config.TextColumn("📄 Doc. que recibe"),
    "Sector Interviniente": st.column_config.TextColumn("🏢 Sector que actúa"),
    "Procesos Realizados": st.column_config.TextColumn("⚙️ Actividad"),
    "Doc. que se Genera": st.column_config.TextColumn("📝 Doc. que entrega"),
    "Salida": st.column_config.SelectboxColumn(
        "🔜 Salida",
        options=[
            "Continúa en otro paso", 
            "Continúa en otra secretaría y regresa", 
            "Continúa en otra secretaría (Fin local)",
            "Finaliza trámite"
        ],
        required=True,
    ),
    "Certificación": st.column_config.SelectboxColumn("Certificación", options=["No", "Sí"]),
    "¿Cuál?": st.column_config.TextColumn("Nombre Certificado"),
}

df_pasos = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config=config_columnas,
    hide_index=True
)

st.divider()

# --- SECCIÓN 3: VISUALIZACIÓN Y ENVÍO ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Visualización del Workflow")
    grafo = graphviz.Digraph(graph_attr={'rankdir': 'LR'})
    
    # Lógica de dibujo mejorada
    for i, row in df_pasos.iterrows():
        sector = str(row["Sector Interviniente"]).strip()
        proceso = str(row["Procesos Realizados"]).strip()
        entrega = str(row["Doc. que se Genera"]).strip()
        
        if sector and sector.lower() != 'none' and sector != "":
            # Nodo del sector
            label_nodo = f"{sector}\n({proceso})" if proceso and proceso != "None" else sector
            grafo.node(str(i), label_nodo, shape='box', style='filled', fillcolor='#E3F2FD')
            
            # Flecha al siguiente paso
            if i < len(df_pasos) - 1:
                sig_sector = str(df_pasos.iloc[i+1]["Sector Interviniente"]).strip()
                if sig_sector and sig_sector != "None":
                    etiqueta_flecha = f"Envía: {entrega}" if entrega and entrega != "None" else ""
                    grafo.edge(str(i), str(i+1), label=etiqueta_flecha)

    if not df_pasos.empty:
        st.graphviz_chart(grafo)
    else:
        st.info("El diagrama se dibujará a medida que cargue los sectores.")

with c2:
    st.subheader("Finalizar Relevamiento")
    
    if st.button("🚀 Enviar a n8n", use_container_width=True, type="primary"):
        # Validación de datos antes de enviar
        errores = []
        for idx, row in df_pasos.iterrows():
            if row["Salida"] == "Continúa en otro paso" and (not row["Doc. que se Genera"] or str(row["Doc. que se Genera"]) == 'None'):
                errores.append(f"Fila {idx+1}: Falta indicar qué documento se genera para continuar.")
        
        if errores:
            for err in errores:
                st.error(err)
        elif df_pasos.empty:
            st.warning("No hay pasos cargados en el proceso.")
        elif not nombre_tramite:
            st.warning("Por favor, asigne un nombre al trámite.")
        else:
            # Preparación del JSON final
            payload = {
                "meta": {
                    "municipio": "Lomas de Zamora",
                    "direccion": direccion,
                    "canal": canal,
                    "tramite": nombre_tramite
                },
                "pasos": df_pasos.to_dict(orient="records")
            }
            
            # Reemplazar por tu URL de webhook real en n8n
            url_n8n = "https://tu-n8n-instancia.com/webhook/relevamiento-procesos"
            
            try:
                res = requests.post(url_n8n, json=payload)
                if res.status_code == 200:
                    st.success("¡Relevamiento enviado con éxito!")
                else:
                    st.error(f"Error en n8n (Código: {res.status_code})")
            except:
                st.warning("No se pudo conectar con el Webhook. Copie el JSON para n8n:")
                st.json(payload)
