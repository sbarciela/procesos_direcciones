import streamlit as st
import pandas as pd
import requests

st.title("Relevamiento de Procesos")

# 1. Creamos la estructura inicial vacía en el session_state
if "datos_proceso" not in st.session_state:
    st.session_state["datos_proceso"] = pd.DataFrame(
        columns=["Tramite", "Origen", "Destino"]
    )

st.write("Cargá los pasos del flujo a continuación:")

# 2. El data_editor permite agregar filas dinámicamente (+ Add row)
df_editado = st.data_editor(
    st.session_state["datos_proceso"], 
    num_rows="dynamic", # ¡Esto es la magia! Permite al usuario agregar filas
    use_container_width=True
)

st.divider()

# 3. El botón para disparar todo a n8n
if st.button("Enviar Flujo a n8n", type="primary"):
    
    # Convertimos la tabla a un diccionario JSON limpio
    json_data = df_editado.to_dict(orient="records")
    
    # Acá ponés la URL del webhook de tu n8n
    url_webhook_n8n = "https://tu-n8n.com/webhook/relevamiento"
    
    try:
        # Enviamos los datos
        respuesta = requests.post(url_webhook_n8n, json=json_data)
        if respuesta.status_code == 200:
            st.success("¡Flujo enviado a n8n con éxito!")
        else:
            st.error(f"Error al enviar: {respuesta.status_code}")
    except Exception as e:
        st.warning("Reemplazá la URL del webhook de n8n para que funcione el envío.")
        st.json(json_data) # Muestra en pantalla el JSON que se enviaría
