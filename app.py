import streamlit as st
import pandas as pd
import requests
import graphviz
import numpy as np
import uuid
import streamlit.components.v1 as components  # Agregamos esto para el F5 automático
from streamlit_gsheets import GSheetsConnection

# Configuración de página
st.set_page_config(page_title="Relevamiento de Procesos - Lomas de Zamora", layout="wide")

st.title("🏛️ Relevamiento de Procesos Internos")
st.write("Cargue los datos del proceso. La información se guardará en la planilla institucional de la Secretaría.")

# --- INICIALIZACIÓN DE ESTADOS ---
if "exito" not in st.session_state:
    st.session_state["exito"] = False
if "balloons_shown" not in st.session_state:
    st.session_state["balloons_shown"] = False

columnas_ordenadas = [
    "Doc. que Ingresa", "Sector Interviniente", "Procesos Realizados", 
    "Salida", "Documento en tránsito", "Certificación", "¿Cuál?"
]

if "pasos_data" not in st.session_state:
    st.session_state["pasos_data"] = pd.DataFrame(
        [{col: None for col in columnas_ordenadas}],
        columns=columnas_ordenadas
    )

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error de conexión con Google Sheets. Verificá los Secrets.")

# --- SECCIÓN 1: DATOS GENERALES ---
col1, col2 = st.columns(2)
with col1:
    direccion = st.selectbox(
        "Dirección:",
        ["Fiscalización", "Rentas", "A.R.L.O", "Capacidad contributiva", "Seguridad e higiene", "Ingresos públicos"],
        key="input_direccion"
    )
    canal = st.selectbox("Canal:", ["Presencial", "Online", "Telefónico", "Otros"], key="input_canal")
with col2:
    nombre_tramite = st.text_input("Nombre del trámite:", placeholder="Ej: Alta de comercio", key="input_tramite")

st.divider()

# --- SECCIÓN 2: TABLA DE PASOS ---
st.subheader("Pasos del Proceso")

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

tabla_deshabilitada = st.session_state["exito"]

df_editado = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config=config_columnas,
    hide_index=True,
    disabled=tabla_deshabilitada,
    key="editor_procesos" 
)

if not st.session_state["exito"]:
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
            grafo.node('inicio', 'Inicio de Trámite', shape='ellipse', style='filled', fillcolor='#FFF9C4')
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
    st.info("Cargue sectores para generar el diagrama.")

st.divider()

# --- SECCIÓN 4: PERSISTENCIA Y REINICIO ---
_, col_btn, _ = st.columns([1, 2, 1])
with col_btn:
    st.subheader("Finalizar Relevamiento")
    
    if st.session_state["exito"]:
        st.success(f"✅ ¡Datos guardados en la Secretaría!\n**Ticket de operación:** {st.session_state.get('ticket_id')}")
        
        if not st.session_state["balloons_shown"]:
            st.balloons()
            st.session_state["balloons_shown"] = True
            
        if st.button("🔄 Cargar nuevo proceso/trámite", use_container_width=True):
            # LA MAGIA DEL F5: Esto le dice al navegador web que recargue la página completa
            components.html("<script>window.parent.location.reload();</script>", height=0)
            
    else:
        if st.button("🚀 Guardar en Google Sheets", use_container_width=True, type="primary"):
            if not nombre_tramite or not sectores_cargados:
                st.error("Complete el nombre del trámite y al menos un paso.")
            else:
                try:
                    id_unico = str(uuid.uuid4().hex)[:8].upper()
                    fecha_hora = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

                    df_to_save = df_editado.copy()
                    
                    df_to_save["ID_Relevamiento"] = id_unico
                    df_to_save["Nro_Paso"] = range(1, len(df_to_save) + 1)
                    df_to_save["Dirección"] = direccion
                    df_to_save["Canal"] = canal
                    df_to_save["Trámite"] = nombre_tramite
                    df_to_save["Timestamp"] = fecha_hora
                    
                    columnas_finales = [
                        "Timestamp", "ID_Relevamiento", "Dirección", "Canal", "Trámite",
                        "Nro_Paso", "Doc. que Ingresa", "Sector Interviniente", 
                        "Procesos Realizados", "Salida", "Documento en tránsito", 
                        "Certificación", "¿Cuál?"
                    ]
                    
                    df_to_save = df_to_save[df_to_save["Sector Interviniente"].astype(str).str.lower().isin(['none', 'nan', '', '<na>']) == False]
                    df_to_save = df_to_save[columnas_finales]
                    df_to_save = df_to_save.replace({np.nan: None}).fillna("")
                    
                    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    
                    # EL ARREGLO CRÍTICO: ttl=0 fuerza a leer el Excel real y no el de caché
                    existing_data = conn.read(spreadsheet=url_hoja, ttl=0)
                    
                    updated_data = pd.concat([existing_data, df_to_save], ignore_index=True)
                    conn.update(spreadsheet=url_hoja, data=updated_data)
                    
                    st.session_state["exito"] = True
                    st.session_state["ticket_id"] = id_unico
                    st.rerun() 
                    
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
