import streamlit as st
import pandas as pd
import requests
import graphviz

st.set_page_config(page_title="Relevamiento de Procesos", layout="centered")

st.title("Relevamiento de Procesos")
st.write("Cargá los pasos del flujo en la tabla. El diagrama se actualizará automáticamente.")

# 1. Creamos la estructura inicial vacía en el session_state
if "datos_proceso" not in st.session_state:
    st.session_state["datos_proceso"] = pd.DataFrame(
        columns=["Tramite", "Origen", "Destino"]
    )

# 2. El data_editor permite agregar filas dinámicamente
df_editado = st.data_editor(
    st.session_state["datos_proceso"], 
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True
)

st.divider()

# 3. DIBUJO DEL DIAGRAMA DE FLUJO (Graphviz)
st.subheader("Visualización del Flujo")

# Creamos el lienzo del gráfico (rankdir='LR' lo hace de izquierda a derecha)
grafo = graphviz.Digraph(graph_attr={'rankdir': 'LR'})
hay_datos = False

# Recorremos la tabla para dibujar los nodos y flechas
for index, row in df_editado.iterrows():
    # Convertimos a string y limpiamos espacios vacíos
    origen = str(row.get("Origen", "")).strip()
    destino = str(row.get("Destino", "")).strip()
    tramite = str(row.get("Tramite", "")).strip()
    
    # Evitamos procesar filas vacías o con los "nan" por defecto de pandas
    if origen and destino and origen.lower() != 'nan' and destino.lower() != 'nan':
        hay_datos = True
        
        # Dibujamos las cajas (nodos) de los sectores
        grafo.node(origen, origen, shape='box', style='filled', fillcolor='#e1f5fe')
        grafo.node(destino, destino, shape='box', style='filled', fillcolor='#e1f5fe')
        
        # Dibujamos la flecha (conexión) y le ponemos el nombre del trámite arriba
        etiqueta = tramite if tramite and tramite.lower() != 'nan' else ''
        grafo.edge(origen, destino, label=etiqueta)

# Mostramos el gráfico si hay al menos una conexión válida
if hay_datos:
    st.graphviz_chart(grafo)
else:
    st.info("Agregá un 'Origen' y un 'Destino' en la tabla para ver el gráfico aquí.")

st.divider()

# 4. ENVÍO A n8n
if st.button("Enviar Flujo a n8n", type="primary"):
    
    # Limpiamos los datos vacíos antes de enviarlos (opcional pero recomendado)
    df_limpio = df_editado.dropna(subset=["Origen", "Destino"])
    json_data = df_limpio.to_dict(orient="records")
    
    # Acá ponés la URL del webhook de tu n8n
    url_webhook_n8n = "https://tu-n8n.com/webhook/relevamiento"
    
    try:
        if not json_data:
            st.warning("No hay datos válidos para enviar.")
        else:
            respuesta = requests.post(url_webhook_n8n, json=json_data)
            if respuesta.status_code == 200:
                st.success("¡Flujo enviado con éxito!")
            else:
                st.error(f"Error al enviar: {respuesta.status_code}")
    except Exception as e:
        st.warning("Aviso: Reemplazá la URL del webhook de n8n para que el envío real funcione.")
        st.write("Estructura JSON que recibirá n8n:")
        st.json(json_data)
