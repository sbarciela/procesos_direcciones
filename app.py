import streamlit as st
import pandas as pd
import requests
import graphviz
import numpy as np
from streamlit_gsheets import GSheetsConnection

# Configuración inicial
st.set_page_config(page_title="Relevamiento de Procesos - Lomas de Zamora", layout="wide")

st.title("🏛️ Relevamiento de Procesos Internos")
st.write("Cargue los datos del proceso. La información se guardará directamente en la planilla institucional.")

# --- CONEXIÓN A GOOGLE SHEETS ---
# Esto busca automáticamente las credenciales en st.secrets
conn = st.connection("gsheets", type=GSheetsConnection)

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

# --- SECCIÓN 2: TABLA DE PASOS ---
st.subheader("Pasos del Proceso")

columnas_ordenadas = [
    "Doc. que Ingresa", 
    "Sector Interviniente", 
    "Procesos Realizados", 
    "Salida", 
    "Documento en tránsito", 
    "Certificación", 
    "¿Cuál?"
]

if "pasos_data" not in st.session_state:
    st.session_state["pasos_data"] = pd.DataFrame(
        [{col: None for col in columnas_ordenadas}],
        columns=columnas_ordenadas
    )

config_columnas = {
    "Doc. que Ingresa": st.column_config.TextColumn("📄 Doc. que recibe"),
    "Sector Interviniente": st.column_config.TextColumn("🏢 Sector que actúa"),
    "Procesos Realizados": st.column_config.TextColumn("⚙️ Actividad"),
    "Salida": st.column_config.SelectboxColumn(
        "🔜 Salida",
        options=["Continúa en otro paso", "Continúa en otra secretaría y regresa", "Continúa en otra secretaría (Fin local)", "Finaliza trámite"]
    ),
    "Documento en tránsito": st.column_config.TextColumn("🚚 Documento en tránsito"),
    "Certificación": st.column_config.SelectboxColumn("Certificación", options=["No", "Sí"]),
    "¿Cuál?": st.column_config.TextColumn("Nombre Certificado"),
}

df_editado = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config=config_columnas,
    hide_index=True,
    key="editor_procesos" 
)

if st.button("➕ Autocompletar y Agregar Siguiente Paso", type="secondary"):
    df_actual = df_editado.copy()
    nuevo_paso = {col: None for col in columnas_ordenadas}
    if not df_actual.empty:
        ultima_fila = df_actual.iloc[-1]
        salida_previa = str(ultima_fila.get("Salida", ""))
        doc_previo = str(ultima_fila.get("Documento en tránsito", "")).strip()
        if "Continúa" in salida_previa and doc_previo.lower() not in ["", "none", "nan", "<na>"]:
            nuevo_paso["Doc. que Ingresa"] = doc_previo
    st.session_state["pasos_data"] = pd.concat([df_actual, pd.DataFrame([nuevo_paso])], ignore_index=True)
    st.rerun()

st.divider()

# --- SECCIÓN 3: VISUALIZACIÓN ---
st.subheader("Visualización del Workflow")
st.markdown(f"**Relevamiento:** {nombre_tramite if nombre_tramite else '---'} | **Dirección:** {direccion} | **Canal:** {canal}")

grafo = graphviz.Digraph(graph_attr={'rankdir': 'TB', 'nodesep': '0.5', 'ranksep': '0.5'}) 

for i, row in df_editado.iterrows():
    doc_ingresa = str(row.get("Doc. que Ingresa", "")).strip()
    sector = str(row.get("Sector Interviniente", "")).strip()
    proceso = str(row.get("Procesos Realizados", "")).strip()
    entrega = str(row.get("Documento en tránsito", "")).strip()
    salida = str(row.get("Salida", "")).strip()
    certificacion = str(row.get("Certificación", "")).strip()
    nombre_cert = str(row.get("¿Cuál?", "")).strip()
    
    if sector.lower() not in ['none', 'nan', '', '<na>']:
        if i == 0:
            grafo.node('inicio', 'Inicio', shape='ellipse', style='filled', fillcolor='#FFF9C4')
            etiqueta_inicio = f"Ingresa:\n{doc_ingresa}" if doc_ingresa.lower() not in ['none', 'nan', '', '<na>'] else "Inicia"
            grafo.edge('inicio', str(0), label=etiqueta_inicio)

        label_nodo = f"{sector}\n({proceso})" if proceso.lower() not in ['none', 'nan', '', '<na>'] else sector
        grafo.node(str(i), label_nodo, shape='box', style='filled', fillcolor='#E3F2FD')
        
        if i < len(df_editado) - 1 and "Continúa" in salida:
            sig_sector = str(df_editado.iloc[i+1].get("Sector Interviniente", "")).strip()
            if sig_sector.lower() not in ['none', 'nan', '', '<na>']:
                etiqueta_flecha = f"Hacia {sig_sector}\n({entrega})" if entrega.lower() not in ['none', 'nan', '', '<na>'] else ""
                grafo.edge(str(i), str(i+1), label=etiqueta_flecha)

        if salida == "Finaliza trámite":
            id_fin = f"fin_{i}" 
            texto_cert = f"Certificado: {nombre_cert}" if (certificacion == "Sí" and nombre_cert.lower() not in ['', 'nan', 'none']) else "Sin certificado"
            grafo.node(id_fin, f"Fin de Trámite\n({texto_cert})", shape='ellipse', style='filled', fillcolor='#C8E6C9')
            grafo.edge(str(i), id_fin, label=f"Entrega: {entrega}" if entrega.lower() not in ['', 'nan', 'none'] else "")

sectores_cargados = [str(s) for s in df_editado["Sector Interviniente"] if str(s).lower() not in ['none', 'nan', '', '<na>']]

if sectores_cargados:
    c_izq, c_centro, c_der = st.columns([1, 2, 1])
    with c_centro:
        st.graphviz_chart(grafo)
else:
    st.info("Cargue sectores para ver el diagrama.")

st.divider()

# --- SECCIÓN 4: PERSISTENCIA EN GOOGLE SHEETS ---
_, col_btn, _ = st.columns([1, 2, 1])
with col_btn:
    st.subheader("Finalizar Relevamiento")
    if st.button("🚀 Guardar en Google Sheets", use_container_width=True, type="primary"):
        # Validaciones
        if not nombre_tramite or not sectores_cargados:
            st.error("Por favor, complete el nombre del trámite y al menos un paso.")
        else:
            try:
                # 1. Preparamos el DataFrame para anexar
                df_to_save = df_editado.copy()
                df_to_save["Municipio"] = "Lomas de Zamora"
                df_to_save["Dirección"] = direccion
                df_to_save["Canal"] = canal
                df_to_save["Nombre del Trámite"] = nombre_tramite
                df_to_save["Timestamp"] = pd.Timestamp.now()
                
                # Limpieza de nulos para la planilla
                df_to_save = df_to_save.replace({np.nan: ""})

                # 2. Leemos los datos existentes en la hoja (para no pisar nada)
                # IMPORTANTE: La URL de la hoja debe estar en tus Secrets de Streamlit
                url_hoja = st.secrets["gsheets"]["public_url"] 
                existing_data = conn.read(spreadsheet=url_hoja)
                
                # 3. Concatenamos lo nuevo y actualizamos la hoja
                updated_data = pd.concat([existing_data, df_to_save], ignore_index=True)
                conn.update(spreadsheet=url_hoja, data=updated_data)
                
                st.success("¡Datos guardados correctamente en Google Sheets!")
                st.balloons()
            except Exception as e:
                st.error(f"Error al conectar con Google Sheets: {e}")
                st.info("Asegurate de haber configurado correctamente los Secrets en Streamlit.")
