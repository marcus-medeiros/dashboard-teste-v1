# Arquivo: app_completo.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import threading
import time
import random
from datetime import datetime, timedelta
import queue
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÕES GERAIS ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "bess/energia/simultaneo"
DATA_WINDOW_SECONDS = 60

# Fila para comunicação entre threads
data_queue = queue.Queue()

# --- 2. GERENCIAMENTO DE ESTADO ---
if 'timestamps' not in st.session_state:
    st.session_state.timestamps = []
if 'values' not in st.session_state:
    st.session_state.values = []
if 'subscriber_started' not in st.session_state:
    st.session_state.subscriber_started = False
if 'publisher_started' not in st.session_state:
    st.session_state.publisher_started = False

# --- 3. LÓGICA DO PUBLICADOR (SIMULADOR) ---
def run_publisher_thread():
    print("Thread do Publicador iniciada.")
    while True:
        try:
            potencia_simulada = round(50 + random.uniform(-25, 25), 2)
            publish.single(
                topic=MQTT_TOPIC,
                payload=str(potencia_simulada),
                hostname=MQTT_BROKER,
                port=MQTT_PORT
            )
            print(f"[Publicador] Enviado: {potencia_simulada} kW")
            time.sleep(2)
        except Exception as e:
            print(f"[Publicador] Erro: {e}")
            time.sleep(5)

# --- 4. LÓGICA DO ASSINANTE (RECEPTOR) ---
def on_connect_subscriber(client, userdata, flags, rc):
    if rc == 0:
        print("Thread do Assinante conectada ao MQTT.")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[Assinante] Falha na conexão, código: {rc}")

def on_message_subscriber(client, userdata, msg):
    try:
        valor = float(msg.payload.decode('utf-8'))
        agora = datetime.now()
        data_queue.put((agora, valor))  # Envia os dados para o thread principal
    except (ValueError, TypeError):
        pass

def run_subscriber_thread():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect_subscriber
    client.on_message = on_message_subscriber
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# --- 5. INICIALIZAÇÃO DAS THREADS ---
if not st.session_state.publisher_started:
    publisher_thread = threading.Thread(target=run_publisher_thread, daemon=True)
    publisher_thread.start()
    st.session_state.publisher_started = True

if not st.session_state.subscriber_started:
    subscriber_thread = threading.Thread(target=run_subscriber_thread, daemon=True)
    subscriber_thread.start()
    st.session_state.subscriber_started = True

# --- 6. INTERFACE GRÁFICA (STREAMLIT) ---
st.set_page_config(page_title="Dashboard Tudo-em-Um", layout="wide")
st.title("⚡️ Dashboard MQTT Tudo-em-Um")
st.markdown(f"Este app simula, envia, recebe e exibe dados do tópico `{MQTT_TOPIC}`.")

# Atualização automática a cada 1000ms
st_autorefresh(interval=1000, limit=None, key="auto_refresh")

# Processa novos dados recebidos via fila
while not data_queue.empty():
    timestamp, valor = data_queue.get()
    st.session_state.timestamps.append(timestamp)
    st.session_state.values.append(valor)

# Remove dados antigos fora da janela
limite_tempo = datetime.now() - timedelta(seconds=DATA_WINDOW_SECONDS)
while st.session_state.timestamps and st.session_state.timestamps[0] < limite_tempo:
    st.session_state.timestamps.pop(0)
    st.session_state.values.pop(0)

# Copia os dados atuais
current_timestamps = list(st.session_state.timestamps)
current_values = list(st.session_state.values)

# Interface dinâmica
col1, col2 = st.columns(2)
if current_values:
    col1.metric("Leitura Atual", f"{current_values[-1]:.2f} kW")
    col2.metric("Leitura Média (na janela)", f"{(sum(current_values)/len(current_values)):.2f} kW")
else:
    col1.metric("Leitura Atual", "Aguardando...")
    col2.metric("Leitura Média", "Aguardando...")

# Gráfico
fig = go.Figure()
fig.add_trace(go.Scatter(x=current_timestamps, y=current_values, mode='lines', name='Potência'))
fig.update_layout(
    height=400,
    xaxis_title='Horário',
    yaxis_title='Potência (kW)',
    xaxis=dict(range=[datetime.now() - timedelta(seconds=DATA_WINDOW_SECONDS), datetime.now()])
)
st.plotly_chart(fig, use_container_width=True)
