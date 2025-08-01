import streamlit as st
import threading
import queue
import time
import paho.mqtt.client as mqtt
from streamlit_autorefresh import st_autorefresh

# Fila para comunicação thread-safe
mqtt_data_queue = queue.Queue()

# Inicializa session_state.data se ainda não existir
if "data" not in st.session_state:
    st.session_state.data = {
        "tensao": None,
        "corrente": None,
        "potencia": None
    }

# Callback MQTT
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    mqtt_data_queue.put((topic, payload))

# Thread MQTT
def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect("test.mosquitto.org", 1883, 60)  # ajuste seu broker
    client.subscribe("bess/telemetria/#")
    client.loop_forever()

# Inicia a thread MQTT uma única vez
if "mqtt_thread_started" not in st.session_state:
    threading.Thread(target=mqtt_thread, daemon=True).start()
    st.session_state.mqtt_thread_started = True

# Atualiza dados a partir da fila
while not mqtt_data_queue.empty():
    topic, payload = mqtt_data_queue.get()
    if "potencia" in topic:
        st.session_state.data["potencia"] = float(payload)
    elif "tensao" in topic:
        st.session_state.data["tensao"] = float(payload)
    elif "corrente" in topic:
        st.session_state.data["corrente"] = float(payload)

# Exibição no app
st.title("Dashboard Telemetria MQTT (sem rerun)")

st.write(f"Tensão: {st.session_state.data['tensao']}")
st.write(f"Corrente: {st.session_state.data['corrente']}")
st.write(f"Potência: {st.session_state.data['potencia']}")

# Atualiza a página a cada 2 segundos automaticamente, sem rerun manual
st_autorefresh(interval=2000, limit=None, key="refresh")
