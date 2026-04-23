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

# --- SECCIÓN 2: DETALLE DEL TRÁMITE (TABLA DINÁMICA) ---
st.subheader("Pasos del Proceso")
st.info("💡 Consejo: Para agregar un nuevo paso, escriba el 'Sector que actúa' en la fila vacía y presione Enter. El documento de ingreso se autocompletará si el paso anterior indica que el trámite continúa.")

# Estructura de la tabla en memoria
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

# Llave dinámica para forzar el refresco de pantalla
if "editor_key" not in st.session_state:
    st.session_state["editor_key"] = 0

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

# 1. Mostramos el editor de datos (Usando la llave dinámica)
df_editado = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config=config_columnas,
    hide_index=True,
    key=f"tabla_flujo_{st.session_state['editor_key']}" # LA MAGIA DEL REFRESCO ESTÁ ACÁ
)

# 2. LÓGICA DE AUTOCOMPLETADO (Efecto dominó)
hubo_cambios_automaticos = False

# Solo evaluamos si hay más de una fila cargada
if len(df_editado) > 1:
    for i in range(1, len(df_editado)):
        # Miramos qué pasó en la fila de arriba (i-1)
        salida_anterior = str(df_editado.iloc[i-1].get("Salida", ""))
        doc_generado_anterior = str(df_editado.iloc[i-1].get("Doc. que se Genera", "")).strip()
        
        # Si la fila de arriba continúa y generó un documento válido...
        if "Continúa" in salida_anterior and doc_generado_anterior and doc_generado_anterior.lower() not in ["none", "nan"]:
            
            # Miramos el documento de ingreso de la fila actual (i)
            # Usamos pd.isna() para detectar valores nulos nativos de pandas también
            valor_actual = df_editado.iloc[i].get("Doc. que Ingresa")
            doc_ingresa_actual = str(valor_actual).strip()
            
            # Si está vacío o es nulo, lo autocompletamos
            if pd.isna(valor_actual) or doc_ingresa_actual.lower() in ["", "none", "nan", "<na>"]:
                df_editado.at[i, "Doc. que Ingresa"] = doc_generado_anterior
                hubo_cambios_automaticos = True

# Actualizamos memoria y recargamos SI Y SOLO SI hubo cambios automáticos
if hubo_cambios_automaticos:
    st.session_state["pasos_data"] = df_editado
    st.session_state["editor_key"] += 1 # Cambiamos la llave para forzar el redibujado
    st.rerun()
else:
    st.session_state["pasos_data"] = df_editado

st.divider()

# --- SECCIÓN 3: VISUALIZACIÓN Y ENVÍO ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Visualización del Workflow")
    grafo = graphviz.Digraph(graph_attr={'rankdir': 'LR'})
    
    # Lógica de dibujo del flujograma
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

    # Validamos que haya al menos un sector cargado para mostrar el gráfico
    sectores_cargados = [s for s in df_editado["Sector Interviniente"].astype(str) if s.lower() not in ['none', 'nan', '', '<na>']]
    
    if sectores_cargados:
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
            
            # Validamos que si el trámite sigue, no dejen en blanco qué documento mandan
            if "Continúa" in salida_actual and doc_genera.lower() in ["", "none", "nan", "<na>"]:
                errores.append(f"Fila {idx+1}: Falta indicar qué documento 'entrega' para que el trámite continúe.")
        
        if errores:
            for err in errores:
                st.error(err)
        elif len(sectores_cargados) == 0:
            st.warning("No hay pasos válidos cargados en el proceso.")
        elif not nombre_tramite:
            st.warning("Por favor, asigne un nombre al trámite en la parte superior.")
        else:
            # Limpiamos valores nulos de pandas (NaN, NaT, etc) reemplazándolos por strings vacíos
            df_limpio = df_editado.replace({np.nan: None}).fillna("")
            
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
            
            # ATENCIÓN: Reemplazá esto por tu URL de webhook de n8n
            url_n8n = "https://tu-n8n-instancia.com/webhook/relevamiento-procesos"
            
            try:
                res = requests.post(url_n8n, json=payload)
                if res.status_code == 200:
                    st.success("¡Relevamiento enviado con éxito!")
                    st.balloons() # Festejo visual
                else:
                    st.error(f"Error al enviar a n8n (Código: {res.status_code})")
            except Exception as e:
                st.warning("Aviso: El Webhook de n8n no está configurado o alcanzable. Esta es la estructura que se enviará:")
                st.json(payload)
