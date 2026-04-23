import streamlit as st
import pandas as pd
import requests
import graphviz

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

# --- SECCIÓN 2: DETALLE DEL TRÁMITE (TABLA DINÁMICA) ---
st.subheader("Pasos del Proceso")
st.info("💡 Consejo: Si el trámite continúa en otro paso, indique qué documento genera. El sistema lo cargará automáticamente como ingreso del paso siguiente.")

# Estructura de la tabla
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

# 1. Mostramos el editor de datos
df_editado = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config=config_columnas,
    hide_index=True
)

# 2. LÓGICA DE AUTOCOMPLETADO (Efecto dominó)
hubo_cambios_automaticos = False

# Recorremos desde la segunda fila en adelante
if len(df_editado) > 1:
    for i in range(1, len(df_editado)):
        # Miramos qué pasó en la fila de arriba (i-1)
        salida_anterior = str(df_editado.iloc[i-1]["Salida"])
        doc_generado_anterior = str(df_editado.iloc[i-1]["Doc. que se Genera"]).strip()
        
        # Si la fila de arriba continúa y generó un documento válido...
        if "Continúa" in salida_anterior and doc_generado_anterior and doc_generado_anterior != "None":
            
            # Miramos el documento de ingreso de la fila actual (i)
            doc_ingresa_actual = str(df_editado.iloc[i]["Doc. que Ingresa"]).strip()
            
            # Si está vacío, lo autocompletamos con el generado en el paso anterior
            if doc_ingresa_actual in ["", "None", "nan"]:
                df_editado.at[i, "Doc. que Ingresa"] = doc_generado_anterior
                hubo_cambios_automaticos = True

# Actualizamos memoria y recargamos si hubo cambios automáticos
if hubo_cambios_automaticos:
    st.session_state["pasos_data"] = df_editado
    st.rerun()
else:
    st.session_state["pasos_data"] = df_editado

st.divider()

# --- SECCIÓN 3: VISUALIZACIÓN Y ENVÍO ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Visualización del Workflow")
    grafo = graphviz.Digraph(graph_attr={'rankdir': 'LR'})
    
    # Lógica de dibujo mejorada
    for i, row in df_editado.iterrows():
        sector = str(row.get("Sector Interviniente", "")).strip()
        proceso = str(row.get("Procesos Realizados", "")).strip()
        entrega = str(row.get("Doc. que se Genera", "")).strip()
        
        if sector and sector.lower() not in ['none', 'nan', '']:
            # Nodo del sector
            label_nodo = f"{sector}\n({proceso})" if proceso and proceso.lower() not in ['none', 'nan', ''] else sector
            grafo.node(str(i), label_nodo, shape='box', style='filled', fillcolor='#E3F2FD')
            
            # Flecha al siguiente paso
            if i < len(df_editado) - 1:
                sig_sector = str(df_editado.iloc[i+1].get("Sector Interviniente", "")).strip()
                if sig_sector and sig_sector.lower() not in ['none', 'nan', '']:
                    etiqueta_flecha = f"Envía: {entrega}" if entrega and entrega.lower() not in ['none', 'nan', ''] else ""
                    grafo.edge(str(i), str(i+1), label=etiqueta_flecha)

    if not df_editado.empty and not df_editado["Sector Interviniente"].isna().all():
        st.graphviz_chart(grafo)
    else:
        st.info("Cargue sectores en la tabla para ver el diagrama del proceso.")

with c2:
    st.subheader("Finalizar Relevamiento")
    
    if st.button("🚀 Enviar a n8n", use_container_width=True, type="primary"):
        # Validación de datos antes de enviar
        errores = []
        for idx, row in df_editado.iterrows():
            salida_actual = str(row.get("Salida", ""))
            doc_genera = str(row.get("Doc. que se Genera", "")).strip()
            
            if "Continúa" in salida_actual and doc_genera in ["", "None", "nan"]:
                errores.append(f"Fila {idx+1}: Falta indicar qué documento 'entrega' para que el trámite continúe.")
        
        if errores:
            for err in errores:
                st.error(err)
        elif df_editado.empty or df_editado["Sector Interviniente"].isna().all():
            st.warning("No hay pasos válidos cargados en el proceso.")
        elif not nombre_tramite:
            st.warning("Por favor, asigne un nombre al trámite en la parte superior.")
        else:
            # Limpiamos valores nulos de pandas para que el JSON quede prolijo
            df_limpio = df_editado.fillna("")
            
            # Preparación del JSON final
            payload = {
                "meta": {
                    "municipio": "Lomas de Zamora",
                    "direccion": direccion,
                    "canal": canal,
                    "tramite": nombre_tramite
                },
                "pasos": df_limpio.to_dict(orient="records")
            }
            
            # Reemplazá por tu URL de webhook real en n8n
            url_n8n = "https://tu-n8n-instancia.com/webhook/relevamiento-procesos"
            
            try:
                res = requests.post(url_n8n, json=payload)
                if res.status_code == 200:
                    st.success("¡Relevamiento enviado con éxito!")
                    st.balloons() # Pequeño detalle visual de éxito
                else:
                    st.error(f"Error al enviar a n8n (Código: {res.status_code})")
            except Exception as e:
                st.warning("Aviso: El Webhook de n8n no está configurado o alcanzable. Estructura que se enviará:")
                st.json(payload)
