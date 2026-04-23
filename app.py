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
st.info("💡 Consejo: Agregue un sector y presione Enter o haga clic fuera. El sistema autocompletará el documento recibido si el paso anterior continúa.")

# 1. Inicializamos la memoria base (SOLO la primera vez que se carga la página)
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

# 2. Renderizamos la tabla. 
# Streamlit ahora se encarga de guardar lo que escribas sin que nosotros nos metamos.
df_editado = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config=config_columnas,
    hide_index=True,
    key="editor_procesos" 
)

# 3. Lógica de Autocompletado (El "Efecto Dominó")
hubo_cambio_automatico = False
temp_df = df_editado.copy()

if len(temp_df) > 1:
    for i in range(1, len(temp_df)):
        salida_previa = str(temp_df.loc[i-1, "Salida"])
        doc_previo = str(temp_df.loc[i-1, "Doc. que se Genera"]).strip()
        doc_actual = str(temp_df.loc[i, "Doc. que Ingresa"]).strip()
        
        # Si el anterior sigue y tiene documento, pero el actual está vacío...
        if "Continúa" in salida_previa and doc_previo.lower() not in ["", "none", "nan", "<na>"]:
            if doc_actual.lower() in ["", "none", "nan", "<na>"]:
                # ¡Inyectamos el documento!
                temp_df.at[i, "Doc. que Ingresa"] = doc_previo
                hubo_cambio_automatico = True

# 4. LA SOLUCIÓN AL BUG:
# Solo actualizamos la memoria si el sistema hizo un autocompletado.
# Si el usuario está escribiendo manualmente, no tocamos nada para no borrarle el texto.
if hubo_cambio_automatico:
    st.session_state["pasos_data"] = temp_df
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
        
        if sector and sector.lower() not in ['none', 'nan', '']:
            label_nodo = f"{sector}\n({proceso})" if proceso and proceso.lower() not in ['none', 'nan', ''] else sector
            grafo.node(str(i), label_nodo, shape='box', style='filled', fillcolor='#E3F2FD')
            
            if i < len(df_editado) - 1:
                sig_sector = str(df_editado.loc[i+1, "Sector Interviniente"]).strip()
                if sig_sector and sig_sector.lower() not in ['none', 'nan', '']:
                    etiqueta_flecha = f"Envía: {entrega}" if entrega and entrega.lower() not in ['none', 'nan', ''] else ""
                    grafo.edge(str(i), str(i+1), label=etiqueta_flecha)

    sectores_cargados = [s for s in df_editado["Sector Interviniente"].astype(str) if s.lower() not in ['none', 'nan', '', '<na>']]
    
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
