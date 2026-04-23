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
st.info("💡 Consejo: Complete la fila y presione el botón para agregar el siguiente paso. El sistema heredará el documento automáticamente.")

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
        options=[
            "Continúa en otro paso", 
            "Continúa en otra secretaría y regresa", 
            "Continúa en otra secretaría (Fin local)",
            "Finaliza trámite"
        ]
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

# --- SECCIÓN 3: VISUALIZACIÓN DEL WORKFLOW (Ancho Total) ---
st.subheader("Visualización del Workflow")
st.markdown(f"**Relevamiento:** {nombre_tramite if nombre_tramite else '---'} | **Dirección:** {direccion} | **Canal:** {canal}")

# CAMBIO CLAVE: rankdir='TB' significa Top-to-Bottom (De arriba hacia abajo)
grafo = graphviz.Digraph(graph_attr={'rankdir': 'TB'}) 

for i, row in df_editado.iterrows():
    doc_ingresa = str(row.get("Doc. que Ingresa", "")).strip()
    sector = str(row.get("Sector Interviniente", "")).strip()
    proceso = str(row.get("Procesos Realizados", "")).strip()
    entrega = str(row.get("Documento en tránsito", "")).strip()
    salida = str(row.get("Salida", "")).strip()
    certificacion = str(row.get("Certificación", "")).strip()
    nombre_cert = str(row.get("¿Cuál?", "")).strip()
    
    if sector.lower() not in ['none', 'nan', '', '<na>']:
        
        # Nodo de Inicio
        if i == 0:
            grafo.node('inicio', 'Inicio de Trámite', shape='ellipse', style='filled', fillcolor='#FFF9C4')
            etiqueta_inicio = f"Ingresa:\n{doc_ingresa}" if doc_ingresa.lower() not in ['none', 'nan', '', '<na>'] else "Inicia"
            grafo.edge('inicio', str(0), label=etiqueta_inicio)

        # Nodo del sector normal
        label_nodo = f"{sector}\n({proceso})" if proceso.lower() not in ['none', 'nan', '', '<na>'] else sector
        grafo.node(str(i), label_nodo, shape='box', style='filled', fillcolor='#E3F2FD')
        
        # Flecha hacia el siguiente sector
        if i < len(df_editado) - 1 and "Continúa" in salida:
            sig_sector = str(df_editado.iloc[i+1].get("Sector Interviniente", "")).strip()
            if sig_sector.lower() not in ['none', 'nan', '', '<na>']:
                etiqueta_flecha = f"Hacia {sig_sector}\n({entrega})" if entrega.lower() not in ['none', 'nan', '', '<na>'] else ""
                grafo.edge(str(i), str(i+1), label=etiqueta_flecha)

        # Nodo de Fin
        if salida == "Finaliza trámite":
            id_fin = f"fin_{i}" 
            if certificacion == "Sí" and nombre_cert.lower() not in ['none', 'nan', '', '<na>']:
                texto_cert = f"Certificado: {nombre_cert}"
            else:
                texto_cert = "Sin certificado"
            
            label_fin = f"Fin de Trámite\n({texto_cert})"
            grafo.node(id_fin, label_fin, shape='ellipse', style='filled', fillcolor='#C8E6C9')
            
            etiqueta_flecha_fin = f"Entrega: {entrega}" if entrega.lower() not in ['none', 'nan', '', '<na>'] else ""
            grafo.edge(str(i), id_fin, label=etiqueta_flecha_fin)

sectores_cargados = [str(s) for s in df_editado["Sector Interviniente"] if str(s).lower() not in ['none', 'nan', '', '<na>']]

if sectores_cargados:
    # use_container_width centra el gráfico y usa el espacio disponible
    st.graphviz_chart(grafo, use_container_width=True)
else:
    st.info("Cargue sectores en la tabla para ver el diagrama del proceso.")

st.divider()

# --- SECCIÓN 4: FINALIZAR RELEVAMIENTO (Reubicado al fondo) ---
# Usamos columnas solo para centrar el botón y que no ocupe toda la pantalla de largo a largo
_, col_btn, _ = st.columns([1, 2, 1])

with col_btn:
    st.subheader("Finalizar Relevamiento")
    
    if st.button("🚀 Enviar a n8n", use_container_width=True, type="primary"):
        errores = []
        for idx, row in df_editado.iterrows():
            salida_actual = str(row.get("Salida", ""))
            doc_genera = str(row.get("Documento en tránsito", "")).strip()
            sector_act = str(row.get("Sector Interviniente", "")).strip()
            
            if sector_act.lower() not in ['none', 'nan', '', '<na>']:
                if "Continúa" in salida_actual and doc_genera.lower() in ["", "none", "nan", "<na>"]:
                    errores.append(f"Fila {idx+1}: Indique el 'Documento en tránsito' que se entrega.")
                if salida_actual.lower() in ["", "none", "nan", "<na>"]:
                    errores.append(f"Fila {idx+1}: Falta seleccionar 'Salida'.")
        
        if errores:
            for err in errores:
                st.error(err)
        elif not sectores_cargados:
            st.warning("No hay pasos válidos para enviar.")
        elif not nombre_tramite:
            st.warning("Falta el nombre del trámite en la parte superior.")
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
                    st.success("¡Relevamiento enviado con éxito a n8n!")
                    st.balloons()
                else:
                    st.error(f"Error en la conexión con n8n: Código {res.status_code}")
            except:
                st.warning("El Webhook de n8n no está configurado o alcanzable. JSON generado:")
                st.json(payload)
