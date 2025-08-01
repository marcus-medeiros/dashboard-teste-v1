# Arquivo: dashboard_realtime.py (Versão Corrigida e Resiliente)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import threading
from datetime import datetime, timedelta

# --- Configurações ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "bess/energia"
DATA_WINDOW_SECONDS = 60

# --- Gerenciamento de Estado do Streamlit ---
if 'timestamps' not in st.session_state:
    st.session_state.timestamps = []
if 'values' not in st.session_state:
    st.session_state.values = []
if 'mqtt_started' not in st.session_state:
    st.session_state.mqtt_started = False

# --- Lógica MQTT ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conexão com MQTT estabelecida com sucesso.")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Falha na conexão com MQTT, código: {rc}")

def on_message(client, userdata, msg):
    try:
        valor = float(msg.payload.decode('utf-8'))
        agora = datetime.now()
        
        # Garante que estamos trabalhando com listas, mesmo que algo tenha corrompido o estado
        if not isinstance(st.session_state.values, list):
             st.session_state.values = []
        if not isinstance(st.session_state.timestamps, list):
             st.session_state.timestamps = []

        st.session_state.timestamps.append(agora)
        st.session_state.values.append(valor)

        limite_tempo = agora - timedelta(seconds=DATA_WINDOW_SECONDS)
        while st.session_state.timestamps and st.session_state.timestamps[0] < limite_tempo:
            st.session_state.timestamps.pop(0)
            st.session_state.values.pop(0)
    except (ValueError, TypeError):
        pass

def start_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# --- Inicia a thread do MQTT ---
if not st.session_state.mqtt_started:
    print("Iniciando a thread do cliente MQTT...")
    mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()
    st.session_state.mqtt_started = True

# --- Interface Gráfica do Streamlit ---
st.set_page_config(page_title="Dashboard BESS em Tempo Real", layout="wide")
st.title("🔋 Dashboard BESS em Tempo Real")
st.markdown(f"Exibindo dados do tópico `{MQTT_TOPIC}` nos últimos {DATA_WINDOW_SECONDS} segundos.")

placeholder = st.empty()

# ***** INÍCIO DA CORREÇÃO PRINCIPAL *****
# Adicionamos uma verificação para garantir que st.session_state.values é uma lista antes de usá-la.
if isinstance(st.session_state.values, list):
    current_values = list(st.session_state.values)
    current_timestamps = list(st.session_state.timestamps)
else:
    # Se a variável foi corrompida, a gente define como lista vazia para não quebrar a aplicação
    # e tenta corrigir o estado para a próxima execução.
    current_values = []
    current_timestamps = []
    st.session_state.values = []
    st.session_state.timestamps = []
    st.error("O estado dos dados foi corrompido e resetado. Verifique o código por atribuições indevidas.")
# ***** FIM DA CORREÇÃO PRINCIPAL *****


with placeholder.container():
    col1, col2 = st.columns(2)
    if current_values:
        last_value = current_values[-1]
        avg_value = sum(current_values) / len(current_values)
        col1.metric("Potência Atual", f"{last_value:.2f} kW")
        col2.metric("Potência Média (na janela)", f"{avg_value:.2f} kW")
    else:
        col1.metric("Potência Atual", "Aguardando...")
        col2.metric("Potência Média", "Aguardando...")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=current_timestamps, y=current_values, mode='lines+markers', name='Potência'))
    fig.update_layout(height=500, xaxis_title='Horário', yaxis_title='Potência (kW)',
                      xaxis=dict(range=[datetime.now() - timedelta(seconds=DATA_WINDOW_SECONDS), datetime.now()]))
    st.plotly_chart(fig, use_container_width=True)

st.rerun(ttl=1)