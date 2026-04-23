import streamlit as st
import pandas as pd
import requests
import graphviz
import numpy as np

# Configuración inicial de la página
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

# --- SECCIÓN 2: DETALLE DEL TRÁMITE ---
st.subheader("Pasos del Proceso")

# Inicializamos el estado de los datos si no existe
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

# Configuración de columnas
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
        ]
    ),
    "Certificación": st.column_config.SelectboxColumn("Certificación", options=["No", "Sí"]),
    "¿Cuál?": st.column_config.TextColumn("Nombre Certificado"),
}

# 1. Mostramos el editor con una KEY FIJA para evitar reseteos visuales
df_editado = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config=config_columnas,
    hide_index=True,
    key="tabla_estable" # Key fija para mantener el foco
)

# 2. Lógica de Autocompletado Silenciosa
# En lugar de rerun instantáneo, procesamos los datos para la siguiente renderización
def procesar_trazabilidad(df):
    temp_df = df.copy()
    cambio = False
    if len(temp_df) > 1:
        for i in range(1, len(temp_df)):
            salida_previa = str(temp_df.loc[i-1, "Salida"])
            doc_previo = str(temp_df.loc[i-1, "Doc. que se Genera"]).strip()
            doc_actual = str(temp_df.loc[i, "Doc. que Ingresa"]).strip()
            
            # Si el anterior sigue y el actual está vacío, completamos
            if "Continúa" in salida_previa and doc_previo.lower() not in ["", "none", "nan", "<na>"]:
                if doc_actual.lower() in ["", "none", "nan", "<na>"]:
                    temp_df.at[i, "Doc. que Ingresa"] = doc_previo
                    cambio = True
    return temp_df, cambio

# Guardamos el estado actual
df_actualizado, hubo_cambio = procesar_trazabilidad(df_editado)

if hubo_cambio:
    st.session_state["pasos_data"] = df_actualizado
    # Solo refrescamos si es estrictamente necesario para mostrar el dato nuevo
    st.rerun()
else:
    st.session_state["pasos_data"] = df_editado

st.divider()

# --- SECCIÓN 3: VISUALIZACIÓN Y ENVÍO ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Visualización del Workflow")
    grafo = graphviz.Digraph(graph_attr={'rankdir': 'LR'})
    
    for i, row in df_actualizado.iterrows():
        sector = str(row.get("Sector Interviniente", "")).strip()
        proceso = str(row.get("Procesos Realizados", "")).strip()
        entrega = str(row.get("Doc. que se Genera", "")).strip()
        
        if sector and sector.lower() not in ['none', 'nan', '']:
            label_nodo = f"{sector}\n({proceso})" if proceso and proceso.lower() not in ['none', 'nan', ''] else sector
            grafo.node(str(i), label_nodo, shape='box', style='filled', fillcolor='#E3F2FD')
            
            if i < len(df_actualizado) - 1:
                sig_sector = str(df_actualizado.loc[i+1, "Sector Interviniente"]).strip()
                if sig_sector and sig_sector.lower() not in ['none', 'nan', '']:
                    etiqueta_flecha = f"Envía: {entrega}" if entrega and entrega.lower() not in ['none', 'nan', ''] else ""
                    grafo.edge(str(i), str(i+1), label=etiqueta_flecha)

    sectores_cargados = [s for s in df_actualizado["Sector Interviniente"].astype(str) if s.lower() not in ['none', 'nan', '', '<na>']]
    
    if sectores_cargados:
        st.graphviz_chart(grafo)
    else:
        st.info("Cargue sectores en la tabla para ver el diagrama del proceso.")

with c2:
    st.subheader("Finalizar Relevamiento")
    
    if st.button("🚀 Enviar a n8n", use_container_width=True, type="primary"):
        errores = []
        for idx, row in df_actualizado.iterrows():
            salida_actual = str(row.get("Salida", ""))
            doc_genera = str(row.get("Doc. que se Genera", "")).strip()
            sector_act = str(row.get("Sector Interviniente", "")).strip()
            
            if sector_act and sector_act.lower() not in ['none', 'nan', '']:
                if "Continúa" in salida_actual and doc_genera.lower() in ["", "none", "nan", "<na>"]:
                    errores.append(f"Fila {idx+1}: Falta el 'Doc. que entrega'.")
                if salida_actual.lower() in ["", "none", "nan", "<na>"]:
                    errores.append(f"Fila {idx+1}: Falta seleccionar 'Salida'.")
        
        if errores:
            for err in errores:
                st.error(err)
        elif not sectores_cargados:
            st.warning("No hay pasos válidos.")
        elif not nombre_tramite:
            st.warning("Falta el nombre del trámite.")
        else:
            df_limpio = df_actualizado.replace({np.nan: None}).fillna("")
            payload = {
                "meta": {
                    "municipio": "Lomas de Zamora",
                    "direccion": direccion,
                    "canal": canal,
                    "tramite": nombre_tramite
                },
                "pasos": df_limpio.to_dict(orient="records")
            }
            
            # URL de tu n8n
            url_n8n = "https://tu-n8n.com/webhook/relevamiento"
            
            try:
                res = requests.post(url_n8n, json=payload)
                if res.status_code == 200:
                    st.success("¡Enviado con éxito!")
                    st.balloons()
                else:
                    st.error(f"Error n8n: {res.status_code}")
            except:
                st.warning("Webhook no configurado. JSON:")
                st.json(payload)
