import streamlit as st
import pandas as pd
import graphviz
import numpy as np
import uuid
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Relevamiento de Procesos - Lomas de Zamora", layout="wide")

# ==========================================
# --- BARRERA DE SEGURIDAD (LOGIN) ---
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔒 Acceso Restringido")
    st.info("Uso interno - Municipalidad de Lomas de Zamora.")
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        clave_ingresada = st.text_input("Clave de acceso:", type="password")
        if st.button("Ingresar", use_container_width=True):
            if clave_ingresada == st.secrets["APP_PASSWORD"]:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("❌ Clave incorrecta.")
    st.stop()

# ==========================================
# --- INICIALIZACIÓN ---
# ==========================================
if "reset_id" not in st.session_state:
    st.session_state["reset_id"] = 0
if "exito" not in st.session_state:
    st.session_state["exito"] = False
if "balloons_shown" not in st.session_state:
    st.session_state["balloons_shown"] = False

columnas_ordenadas = [
    "Doc. que Ingresa", "Sector Interviniente", "Procesos Realizados", 
    "Días", "Continuidad trámite", "Área de Derivación", "Documento en tránsito"
]

if "pasos_data" not in st.session_state:
    st.session_state["pasos_data"] = pd.DataFrame(
        [{col: None for col in columnas_ordenadas}],
        columns=columnas_ordenadas
    )

def ejecutar_reinicio_suave():
    st.session_state["reset_id"] += 1
    st.session_state["exito"] = False
    st.session_state["balloons_shown"] = False
    st.session_state["pasos_data"] = pd.DataFrame(
        [{col: None for col in columnas_ordenadas}],
        columns=columnas_ordenadas
    )
    st.rerun()

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error de conexión con Google Sheets.")

st.title("🏛️ Relevamiento de Procesos Internos")

# --- SECCIÓN 1: METADATOS ---
col1, col2 = st.columns(2)
with col1:
    direccion = st.selectbox(
        "Su Dirección:",
        ["Fiscalización", "Rentas", "A.R.L.O", "Capacidad contributiva", "Seguridad e higiene", "Ingresos públicos"],
        key=f"input_dir_{st.session_state.reset_id}"
    )
    canal = st.selectbox("Canal del trámite:", ["Presencial", "Online", "Telefónico", "Otros"], key=f"input_canal_{st.session_state.reset_id}")

with col2:
    nombre_tramite = st.text_input("Nombre del trámite:", placeholder="Ej: Alta de comercio", key=f"input_tramite_{st.session_state.reset_id}")
    origen = st.selectbox("Origen del trámite:", ["Contribuyente", "Interno / De Oficio", "Otra Dirección", "Otra Secretaría"], key=f"input_origen_{st.session_state.reset_id}")
    detalle_origen = st.text_input("¿Qué área específica?", key=f"det_or_{st.session_state.reset_id}") if "Otra" in origen else ""

st.divider()

# --- SECCIÓN 2: TABLA DE PASOS ---
st.subheader("Flujo, Tiempos y Continuidad")

# Acá agregamos los tooltips con el parámetro "help"
df_editado = st.data_editor(
    st.session_state["pasos_data"],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Doc. que Ingresa": st.column_config.TextColumn(
            "📄 Recibe", 
            help="El documento físico o digital que recibe el sector para empezar a trabajar (ej: Nota, Expediente, Formulario)."
        ),
        "Sector Interviniente": st.column_config.TextColumn(
            "🏢 Sector",
            help="El nombre de la oficina, área o puesto que realiza la tarea en este paso."
        ),
        "Procesos Realizados": st.column_config.TextColumn(
            "⚙️ Actividad",
            help="Descripción breve de la tarea que hace el sector (ej: Visado, Control de deuda, Inspección)."
        ),
        "Días": st.column_config.NumberColumn(
            "🕒 Días", 
            min_value=0, step=0.5, format="%g d",
            help="Tiempo estimado que demora este sector en completar su parte del proceso."
        ),
        "Continuidad trámite": st.column_config.SelectboxColumn(
            "🔜 Continuidad", 
            options=["Continúa en otro paso", "Continúa en otra secretaría y regresa", "Continúa en otra secretaría (Fin local)", "Finaliza trámite"],
            help="Indica hacia dónde va el trámite después de que este sector termina su parte."
        ),
        "Área de Derivación": st.column_config.TextColumn(
            "🏢 Deriva a...",
            help="Si seleccionó que el trámite continúa en otra secretaría o área, indique el nombre específico aquí."
        ),
        "Documento en tránsito": st.column_config.TextColumn(
            "🚚 En tránsito",
            help="El documento, expediente o resultado que se le envía al siguiente sector para que continúe."
        ),
    },
    hide_index=True,
    disabled=st.session_state["exito"],
    key=f"editor_{st.session_state.reset_id}" 
)

dias_totales = df_editado["Días"].sum()
if dias_totales > 0:
    st.info(f"⏳ **Duración total estimada del proceso:** {dias_totales} días.")

if not st.session_state["exito"]:
    if st.button("➕ Siguiente Paso", type="secondary"):
        df_actual = df_editado.copy()
        nuevo_paso = {col: None for col in columnas_ordenadas}
        if not df_actual.empty:
            u_fila = df_actual.iloc[-1]
            if "Continúa" in str(u_fila.get("Continuidad trámite", "")) and str(u_fila.get("Documento en tránsito", "")).strip():
                nuevo_paso["Doc. que Ingresa"] = u_fila["Documento en tránsito"]
        st.session_state["pasos_data"] = pd.concat([df_actual, pd.DataFrame([nuevo_paso])], ignore_index=True)
        st.rerun()

st.divider()

# --- SECCIÓN 3: CIERRE DEL TRÁMITE ---
finaliza_marcado = "Finaliza trámite" in df_editado["Continuidad trámite"].values
posee_certificacion = "No"
nombre_certificacion = "N/A"
destinatario_final = "N/A"

if finaliza_marcado:
    st.subheader("🏁 Información de Finalización")
    c_fin1, c_fin2 = st.columns(2)
    with c_fin1:
        posee_certificacion = st.selectbox(
            "¿El trámite emite un certificado o documento final?",
            ["No", "Sí"],
            key=f"cert_final_{st.session_state.reset_id}"
        )
        if posee_certificacion == "Sí":
            nombre_certificacion = st.text_input(
                "Nombre del certificado/documento:",
                placeholder="Ej: Certificado de Habilitación",
                key=f"nom_cert_{st.session_state.reset_id}"
            )
    with c_fin2:
        destinatario_final = st.selectbox(
            "¿A quién se le entrega el resultado final?",
            ["Al Contribuyente", "A otra Dirección", "A otra Secretaría", "Queda en archivo local"],
            key=f"dest_fin_{st.session_state.reset_id}"
        )

st.divider()

# --- SECCIÓN 4: VISUALIZACIÓN ---
st.subheader("Workflow Detallado")
grafo = graphviz.Digraph(graph_attr={'rankdir': 'TB', 'nodesep': '0.5', 'ranksep': '0.5'}) 
for i, row in df_editado.iterrows():
    sector = str(row.get("Sector Interviniente", "")).strip()
    if sector.lower() not in ['none', 'nan', '', '<na>']:
        if i == 0:
            grafo.node('inicio', f"Inicio: {origen}", shape='ellipse', style='filled', fillcolor='#FFF9C4')
            grafo.edge('inicio', str(0), label=f"Ingresa:\n{row['Doc. que Ingresa']}")
        
        tiempo = f"\n({row['Días']} d)" if row['Días'] is not None and not pd.isna(row['Días']) else ""
        grafo.node(str(i), f"{sector}\n{row['Procesos Realizados']}{tiempo}", shape='box', style='filled', fillcolor='#E3F2FD')
        
        continua = str(row['Continuidad trámite'])
        deriva = str(row['Área de Derivación']).strip()
        
        if i < len(df_editado) - 1 and "Continúa" in continua:
            label_flecha = f"Envía:\n{row['Documento en tránsito']}"
            if "otra secretaría" in continua.lower() and deriva.lower() not in ['', 'nan', 'none']:
                label_flecha += f"\n(Hacia {deriva})"
            grafo.edge(str(i), str(i+1), label=label_flecha)

        if continua == "Finaliza trámite":
            id_fin = f"fin_{i}" 
            cert_text = f"\n📄 {nombre_certificacion}" if posee_certificacion == "Sí" else "\n(Sin certificado)"
            label_fin = f"FIN DEL TRÁMITE{cert_text}\nEntrega a: {destinatario_final}"
            grafo.node(id_fin, label_fin, shape='ellipse', style='filled', fillcolor='#C8E6C9')
            grafo.edge(str(i), id_fin)

if sectores_cargados := [s for s in df_editado["Sector Interviniente"] if str(s).lower() not in ['none', 'nan', '', '<na>']]:
    _, c_centro, _ = st.columns([1, 2, 1])
    with c_centro: st.graphviz_chart(grafo)

st.divider()

# --- SECCIÓN 5: PERSISTENCIA ---
_, col_btn, _ = st.columns([1, 2, 1])
with col_btn:
    if st.session_state["exito"]:
        st.success(f"✅ Guardado. Ticket: {st.session_state.get('ticket_id')}")
        if not st.session_state["balloons_shown"]:
            st.balloons(); st.session_state["balloons_shown"] = True
        if st.button("🔄 Nuevo Trámite", use_container_width=True): ejecutar_reinicio_suave()
    else:
        if st.button("🚀 Guardar en Google Sheets", use_container_width=True, type="primary"):
            if not nombre_tramite or not sectores_cargados:
                st.error("Faltan datos obligatorios.")
            else:
                try:
                    tid = str(uuid.uuid4().hex)[:8].upper()
                    df_to_save = df_editado.copy()
                    df_to_save["ID_Relevamiento"] = tid
                    df_to_save["Timestamp"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    df_to_save["Dirección_Relevante"] = direccion
                    df_to_save["Trámite"] = nombre_tramite
                    df_to_save["Origen"] = origen
                    df_to_save["Detalle_Origen"] = detalle_origen
                    df_to_save["Duración_Total_Tramite"] = dias_totales
                    
                    df_to_save["Posee_Certificacion"] = posee_certificacion
                    df_to_save["Nombre_Certificado"] = nombre_certificacion
                    df_to_save["Destinatario_Final"] = destinatario_final
                    
                    df_to_save["Nro_Paso"] = range(1, len(df_to_save) + 1)
                    
                    df_to_save = df_to_save[df_to_save["Sector Interviniente"].astype(str).str.lower().isin(['none', 'nan', '', '<na>']) == False]
                    df_to_save = df_to_save.replace({np.nan: None}).fillna("")
                    
                    url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    existing_data = conn.read(spreadsheet=url_hoja, ttl=0)
                    updated_data = pd.concat([existing_data, df_to_save], ignore_index=True)
                    conn.update(spreadsheet=url_hoja, data=updated_data)
                    
                    st.session_state["exito"] = True; st.session_state["ticket_id"] = tid; st.rerun() 
                except Exception as e: st.error(f"Error: {e}")
