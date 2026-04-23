import streamlit as st
import pandas as pd
import requests
import graphviz
import numpy as np

# Configuración inicial
st.set_page_config(page_title="Relevamiento de Procesos - Lomas de Zamora", layout="wide")

st.title("🏛️ Relevamiento de Procesos Internos")
st.write("Complete los datos generales y detalle el flujo documental de cada paso.")

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

st.subheader("Pasos del Proceso")
st.info("💡 Consejo: Agregue un sector en la fila nueva y presione Enter. El documento de ingreso se completará solo.")

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

if "editor_key" not in st.session_state:
    st.session_state["editor_key"] = 0

# --- EL ARREGLO ESTÁ ACÁ ---
# Quitamos required=True para que Streamlit libere la fila inmediatamente
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

df_editado = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config=config_columnas,
    hide_index=True,
    key=f"tabla_flujo_{st.session_state['editor_key']}"
)

# Reseteamos el índice para que Pandas no se confunda con las filas nuevas
df_editado = df_editado.reset_index(drop=True)

hubo_cambios_automaticos = False

# Lógica de autocompletado a prueba de fallos
if len(df_editado) > 1:
    for i in range(1, len(df_editado)):
        salida_anterior = str(df_editado.loc[i-1, "Salida"])
        doc_generado_anterior = str(df_editado.loc[i-1, "Doc. que se Genera"]).strip()
        
        # Si el paso anterior marca "Continúa..." y tiene un documento generado
        if "Continúa" in salida_anterior and doc_generado_anterior.lower() not in ["", "none", "nan", "<na>"]:
            
            doc_ingresa_actual = str(df_editado.loc[i, "Doc. que Ingresa"]).strip()
            
            # Si la celda actual está vacía, inyectamos el documento
            if doc_ingresa_actual.lower() in ["", "none", "nan", "<na>"]:
                df_editado.loc[i, "Doc. que Ingresa"] = doc_generado_anterior
                hubo_cambios_automaticos = True

if hubo_cambios_automaticos:
    st.session_state["pasos_data"] = df_editado
    st.session_state["editor_key"] += 1
    st.rerun()
else:
    st.session_state["pasos_data"] = df_editado

st.divider()

# --- VISUALIZACIÓN Y ENVÍO ---
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
            
            # Validamos que no dejen filas por la mitad
            if sector_act and sector_act.lower() not in ['none', 'nan', '']:
                if "Continúa" in salida_actual and doc_genera.lower() in ["", "none", "nan", "<na>"]:
                    errores.append(f"Fila {idx+1}: Falta indicar el 'Doc. que entrega' antes de continuar.")
                if salida_actual.lower() in ["", "none", "nan", "<na>"]:
                    errores.append(f"Fila {idx+1}: Debe seleccionar un tipo de 'Salida'.")
        
        if errores:
            for err in errores:
                st.error(err)
        elif len(sectores_cargados) == 0:
            st.warning("No hay pasos válidos cargados en el proceso.")
        elif not nombre_tramite:
            st.warning("Por favor, asigne un nombre al trámite en la parte superior.")
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
            
            url_n8n = "https://tu-n8n-instancia.com/webhook/relevamiento-procesos"
            
            try:
                res = requests.post(url_n8n, json=payload)
                if res.status_code == 200:
                    st.success("¡Relevamiento enviado con éxito!")
                    st.balloons()
                else:
                    st.error(f"Error al enviar a n8n (Código: {res.status_code})")
            except Exception as e:
                st.warning("Aviso: El Webhook de n8n no está configurado. JSON generado:")
                st.json(payload)
