import streamlit as st
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
import threading
import queue
import time
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPICO_WILDCARD = "bess/telemetria/#"
DATA_WINDOW_SECONDS = 60

# ✅ Fila para comunicação entre thread MQTT e Streamlit
mqtt_queue = queue.Queue()

# ✅ Inicialização segura do session_state
if "data" not in st.session_state:
    st.session_state.data = {
        "timestamp": [],
        "tensao": [],
        "corrente": [],
        "potencia": [],
    }

# 🔧 Função chamada quando recebe mensagem MQTT
def on_message(client, userdata, msg):
    parametro = msg.topic.split("/")[-1]
    try:
        valor = float(msg.payload.decode("utf-8"))
        mqtt_queue.put((parametro, valor, datetime.now()))
    except Exception as e:
        print(f"[ERRO on_message] {e}")

def on_connect(client, userdata, flags, rc):
    print("[MQTT] Conectado:", rc)
    client.subscribe(TOPICO_WILDCARD)

def mqtt_thread():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# ✅ Inicia thread MQTT apenas uma vez
if "mqtt_thread_started" not in st.session_state:
    threading.Thread(target=mqtt_thread, daemon=True).start()
    st.session_state.mqtt_thread_started = True

# ✅ Consome dados da fila e atualiza session_state
while not mqtt_queue.empty():
    parametro, valor, agora = mqtt_queue.get()
    if parametro in st.session_state.data:
        st.session_state.data["timestamp"].append(agora)
        st.session_state.data[parametro].append(valor)

# 🔧 Remove dados antigos para manter a janela
agora = datetime.now()
limite = agora - timedelta(seconds=DATA_WINDOW_SECONDS)
while st.session_state.data["timestamp"] and st.session_state.data["timestamp"][0] < limite:
    st.session_state.data["timestamp"].pop(0)
    for key in ["tensao", "corrente", "potencia"]:
        if st.session_state.data[key]:
            st.session_state.data[key].pop(0)

# ✅ Gráfico
st.title("Painel BESS - Telemetria em tempo real")
fig = go.Figure()
for key, color in zip(["tensao", "corrente", "potencia"], ["red", "blue", "green"]):
    fig.add_trace(go.Scatter(
        x=st.session_state.data["timestamp"],
        y=st.session_state.data[key],
        mode="lines",
        name=key,
        line=dict(color=color)
    ))

fig.update_layout(xaxis_title="Tempo", yaxis_title="Valor", template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)
st_autorefresh(interval=3000, key="telemetria_refresh")
