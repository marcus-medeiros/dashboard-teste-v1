# Arquivo: dashboard_realtime.py
# Descrição: Recebe dados via MQTT e os exibe em um gráfico de tempo real no Streamlit.

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
DATA_WINDOW_SECONDS = 60 # Janela de tempo dos dados a serem exibidos (60 segundos)

# --- Gerenciamento de Estado do Streamlit ---
# Usamos o st.session_state para manter os dados entre as atualizações da página
if 'timestamps' not in st.session_state:
    st.session_state.timestamps = []
if 'values' not in st.session_state:
    st.session_state.values = []
if 'mqtt_started' not in st.session_state:
    st.session_state.mqtt_started = False

# --- Lógica MQTT (executará em uma thread separada) ---

def on_connect(client, userdata, flags, rc):
    """Callback de conexão."""
    if rc == 0:
        print("Conexão com MQTT estabelecida com sucesso.")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Falha na conexão com MQTT, código: {rc}")

def on_message(client, userdata, msg):
    """Callback de recebimento de mensagens."""
    try:
        valor = float(msg.payload.decode('utf-8'))
        agora = datetime.now()

        st.session_state.timestamps.append(agora)
        st.session_state.values.append(valor)

        # Lógica para manter apenas os dados da janela de tempo definida (sliding window)
        limite_tempo = agora - timedelta(seconds=DATA_WINDOW_SECONDS)
        while st.session_state.timestamps and st.session_state.timestamps[0] < limite_tempo:
            st.session_state.timestamps.pop(0)
            st.session_state.values.pop(0)

    except ValueError:
        # Ignora mensagens que não podem ser convertidas para float
        pass

def start_mqtt_client():
    """Inicia o cliente MQTT em uma thread separada para não bloquear o Streamlit."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# --- Inicia a thread do MQTT apenas uma vez por sessão ---
if not st.session_state.mqtt_started:
    print("Iniciando a thread do cliente MQTT...")
    mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()
    st.session_state.mqtt_started = True

# --- Interface Gráfica do Streamlit ---
st.set_page_config(page_title="Dashboard BESS em Tempo Real", layout="wide")
st.title("🔋 Dashboard BESS em Tempo Real")
st.markdown(f"Exibindo dados do tópico `{MQTT_TOPIC}` nos últimos {DATA_WINDOW_SECONDS} segundos.")

# Placeholder para o gráfico, para que possamos atualizá-lo
placeholder = st.empty()

# Cria cópias dos dados para evitar problemas de concorrência com a thread
current_timestamps = list(st.session_state.timestamps)
current_values = list(st.session_state.values)

with placeholder.container():
    # --- Métricas ---
    col1, col2 = st.columns(2)
    if current_values:
        last_value = current_values[-1]
        avg_value = sum(current_values) / len(current_values)
        col1.metric("Potência Atual", f"{last_value:.2f} kW")
        col2.metric("Potência Média (na janela)", f"{avg_value:.2f} kW")
    else:
        col1.metric("Potência Atual", "Aguardando...")
        col2.metric("Potência Média", "Aguardando...")

    # --- Gráfico ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=current_timestamps,
        y=current_values,
        mode='lines+markers',
        name='Potência',
        line=dict(color='deepskyblue', width=3)
    ))
    fig.update_layout(
        height=500,
        xaxis_title='Horário',
        yaxis_title='Potência (kW)',
        # Define o range do eixo X para ser exatamente a janela de tempo
        xaxis=dict(range=[datetime.now() - timedelta(seconds=DATA_WINDOW_SECONDS), datetime.now()])
    )
    st.plotly_chart(fig, use_container_width=True)

# Força a re-execução do script a cada 1 segundo para atualizar a UI
st.rerun(ttl=1)