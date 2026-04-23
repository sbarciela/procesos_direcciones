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
st.info("💡 Consejo: Complete la fila actual y luego presione el botón gris de abajo para agregar el siguiente paso de forma automática.")

# Inicializamos la memoria con 1 fila vacía
if "pasos_data" not in st.session_state:
    st.session_state["pasos_data"] = pd.DataFrame(
        [{"Doc. que Ingresa": None, "Sector Interviniente": None, "Procesos Realizados": None, "Doc. que se Genera": None, "Salida": None, "Certificación": None, "¿Cuál?": None}],
        columns=["Doc. que Ingresa", "Sector Interviniente", "Procesos Realizados", "Doc. que se Genera", "Salida", "Certificación", "¿Cuál?"]
    )

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

# 1. Renderizamos la tabla (Ahora es 100% libre de interrupciones)
df_editado = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config=config_columnas,
    hide_index=True,
    key="editor_procesos" 
)

# 2. EL BOTÓN MÁGICO (Acá hacemos el autocompletado seguro)
if st.button("➕ Autocompletar y Agregar Siguiente Paso", type="secondary"):
    df_actual = df_editado.copy()
    nuevo_paso = {col: None for col in df_actual.columns}
    
    # Revisamos la última fila para ver si hay que heredar el documento
    if not df_actual.empty:
        ultima_fila = df_actual.iloc[-1]
        salida_previa = str(ultima_fila.get("Salida", ""))
        doc_previo = str(ultima_fila.get("Doc. que se Genera", "")).strip()
        
        # Si el trámite continúa, inyectamos el documento en la fila nueva
        if "Continúa" in salida_previa and doc_previo.lower() not in ["", "none", "nan", "<na>"]:
            nuevo_paso["Doc. que Ingresa"] = doc_previo

    # Guardamos y recargamos la pantalla una sola vez
    st.session_state["pasos_data"] = pd.concat([df_actual, pd.DataFrame([nuevo_paso])], ignore_index=True)
    st.rerun()

st.divider()

# --- SECCIÓN 3: VISUALIZACIÓN Y ENVÍO ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Visualización del Workflow")
    grafo = graphviz.Digraph(graph_attr={'rankdir': 'LR'})
    
    for i, row in df_editado.iterrows():
        sector = str(row.get("Sector Interviniente", "")).strip()
        proceso = str(row.get("Procesos Realizados", "")).strip()
        entrega = str(row.get("Doc. que se Genera", "")).strip()
        
        if sector.lower() not in ['none', 'nan', '', '<na>']:
            label_nodo = f"{sector}\n({proceso})" if proceso.lower() not in ['none', 'nan', '', '<na>'] else sector
            grafo.node(str(i), label_nodo, shape='box', style='filled', fillcolor='#E3F2FD')
            
            if i < len(df_editado) - 1:
                sig_sector = str(df_editado.loc[i+1, "Sector Interviniente"]).strip()
                if sig_sector.lower() not in ['none', 'nan', '', '<na>']:
                    etiqueta_flecha = f"Envía: {entrega}" if entrega.lower() not in ['none', 'nan', '', '<na>'] else ""
                    grafo.edge(str(i), str(i+1), label=etiqueta_flecha)

    # CORRECCIÓN DEL ERROR DE PANDAS (.astype)
    # Convertimos cada valor a string puro de Python antes de evaluarlo
    sectores_cargados = [str(s) for s in df_editado["Sector Interviniente"] if str(s).lower() not in ['none', 'nan', '', '<na>']]
    
    if sectores_cargados:
        st.graphviz_chart(grafo)
    else:
        st.info("Cargue sectores en la tabla para ver el diagrama del proceso.")

with c2:
    st.subheader("Finalizar Relevamiento")
    
    if st.button("🚀 Enviar a n8n", use_container_width=True, type="primary"):
        errores = []
        for idx, row in df_editado.iterrows():
            salida_actual = str(row.get("Salida", ""))
            doc_genera = str(row.get("Doc. que se Genera", "")).strip()
            sector_act = str(row.get("Sector Interviniente", "")).strip()
            
            if sector_act.lower() not in ['none', 'nan', '', '<na>']:
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
            df_limpio = df_editado.replace({np.nan: None}).fillna("")
            payload = {
                "meta": {
                    "municipio": "Lomas de Zamora",
                    "direccion": direccion,
                    "canal": canal,
                    "tramite": nombre_tramite
                },
                "pasos": df_limpio.to_dict(orient="records")
            }
            
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
