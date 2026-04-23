import streamlit as st
import pandas as pd
import requests
import graphviz

st.set_page_config(page_title="Relevamiento de Procesos - Lomas de Zamora", layout="wide")

st.title("🏛️ Relevamiento de Procesos Internos")
st.write("Complete los datos generales y luego detalle cada paso del flujo de trabajo.")

# --- SECCIÓN 1: DATOS GENERALES ---
col1, col2 = st.columns(2)

with col1:
    direccion = st.selectbox(
        "Dirección:",
        ["Fiscalización", "Rentas", "A.R.L.O", "Capacidad contributiva", "Seguridad e higiene", "Ingresos públicos"]
    )
    canal = st.selectbox("Canal:", ["Presencial", "Online", "Telefónico", "Otros"])

with col2:
    nombre_tramite = st.text_input("Nombre del trámite:", placeholder="Ej: Alta de comercio")

st.divider()

# --- SECCIÓN 2: DETALLE DEL TRÁMITE (TABLA DINÁMICA) ---
st.subheader("Pasos del Proceso")

# Estructura inicial de la tabla
if "pasos_data" not in st.session_state:
    st.session_state["pasos_data"] = pd.DataFrame(
        columns=["Documentación", "Sector Interviniente", "Procesos Realizados", "Salida", "Certificación", "¿Cuál?"]
    )

# Configuración de columnas para que la tabla tenga desplegables
config_columnas = {
    "Salida": st.column_config.SelectboxColumn(
        "Salida",
        options=[
            "Continúa en otro paso", 
            "Continúa en otra secretaría y regresa", 
            "Continúa en otra secretaría (Fin del flujo local)",
            "Finaliza trámite"
        ],
        required=True,
    ),
    "Certificación": st.column_config.SelectboxColumn(
        "Certificación",
        options=["No", "Sí"],
        required=True,
    ),
    "Documentación": st.column_config.TextColumn("Documentación recibida"),
    "Sector Interviniente": st.column_config.TextColumn("Sector que actúa"),
    "Procesos Realizados": st.column_config.TextColumn("Actividad realizada"),
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
    
    # Lógica para dibujar el flujo
    lista_pasos = df_pasos.values.tolist()
    for i, paso in enumerate(lista_pasos):
        documentacion, sector, proceso, salida, cert, cual = paso
        
        if sector and str(sector) != 'None':
            # Estilo del nodo (Sector)
            label_nodo = f"{sector}\n({proceso})" if proceso else sector
            grafo.node(str(i), label_nodo, shape='box', style='filled', fillcolor='#E3F2FD')
            
            # Conexión con el siguiente paso
            if i < len(lista_pasos) - 1:
                proximo_sector = lista_pasos[i+1][1]
                if proximo_sector:
                    # Si hay salida especial, la anotamos en la flecha
                    etiqueta_flecha = f"Salida: {salida}" if salida else ""
                    grafo.edge(str(i), str(i+1), label=etiqueta_flecha)

    if not df_pasos.empty:
        st.graphviz_chart(grafo)
    else:
        st.info("Cargue pasos en la tabla para ver el diagrama.")

with c2:
    st.subheader("Finalizar")
    if st.button("🚀 Enviar a n8n", use_container_width=True, type="primary"):
        # Armamos el paquete de datos completo
        payload = {
            "meta": {
                "municipio": "Lomas de Zamora",
                "direccion": direccion,
                "canal": canal,
                "tramite": nombre_tramite
            },
            "pasos": df_pasos.to_dict(orient="records")
        }
        
        url_n8n = "https://tu-n8n-url.com/webhook/relevamiento" # Reemplazar por la tuya
        
        try:
            res = requests.post(url_n8n, json=payload)
            if res.status_code == 200:
                st.success("¡Datos enviados correctamente!")
            else:
                st.error("Error en la conexión con n8n.")
        except:
            st.warning("Webhook no configurado. Se muestra el JSON:")
            st.json(payload)
