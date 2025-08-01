# Arquivo: app_completo.py
# Descrição: Um único aplicativo Streamlit que:
# 1. Inicia uma thread para SIMULAR e PUBLICAR dados MQTT.
# 2. Inicia uma thread para ASSINAR e RECEBER dados MQTT.
# 3. Exibe os dados recebidos em um gráfico em tempo real.

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import threading
import time
import random
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÕES GERAIS ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "bess/energia/simultaneo" # Tópico único para este app
DATA_WINDOW_SECONDS = 60 # Janela de tempo do gráfico em segundos

# --- 2. GERENCIAMENTO DE ESTADO ---
# Inicializa as variáveis na memória da sessão do Streamlit
if 'timestamps' not in st.session_state:
    st.session_state.timestamps = []
if 'values' not in st.session_state:
    st.session_state.values = []
# Flags para garantir que as threads iniciem apenas uma vez
if 'subscriber_started' not in st.session_state:
    st.session_state.subscriber_started = False
if 'publisher_started' not in st.session_state:
    st.session_state.publisher_started = False

# --- 3. LÓGICA DO PUBLICADOR (SIMULADOR) ---
def run_publisher_thread():
    """Gera e publica dados em uma loop infinito. Roda em sua própria thread."""
    print("Thread do Publicador iniciada.")
    while True:
        try:
            # Gera um valor de potência simulado
            potencia_simulada = round(50 + random.uniform(-25, 25), 2)
            
            # Publica o valor no tópico MQTT
            publish.single(
                topic=MQTT_TOPIC,
                payload=str(potencia_simulada),
                hostname=MQTT_BROKER,
                port=MQTT_PORT
            )
            print(f"[Publicador] Enviado: {potencia_simulada} kW")
            # Pausa por 2 segundos antes de enviar o próximo valor
            time.sleep(2)
        except Exception as e:
            print(f"[Publicador] Erro: {e}")
            time.sleep(5) # Aguarda antes de tentar novamente

# --- 4. LÓGICA DO ASSINANTE (RECEPTOR) ---
def on_connect_subscriber(client, userdata, flags, rc):
    """Callback de conexão para o assinante."""
    if rc == 0:
        print("Thread do Assinante conectada ao MQTT.")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[Assinante] Falha na conexão, código: {rc}")

def on_message_subscriber(client, userdata, msg):
    """Callback que processa as mensagens recebidas."""
    try:
        valor = float(msg.payload.decode('utf-8'))
        agora = datetime.now()
        
        # Adiciona os novos dados às listas no estado da sessão
        st.session_state.timestamps.append(agora)
        st.session_state.values.append(valor)
        
        # Mantém a janela de dados com o tamanho definido
        limite_tempo = agora - timedelta(seconds=DATA_WINDOW_SECONDS)
        while st.session_state.timestamps and st.session_state.timestamps[0] < limite_tempo:
            st.session_state.timestamps.pop(0)
            st.session_state.values.pop(0)
            
    except (ValueError, TypeError):
        pass # Ignora mensagens mal formatadas

def run_subscriber_thread():
    """Configura e inicia o loop do cliente MQTT assinante."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect_subscriber
    client.on_message = on_message_subscriber
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# --- 5. INICIALIZAÇÃO DAS THREADS ---
# Garante que as threads de fundo iniciem apenas uma vez por sessão
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

# Placeholder para o conteúdo dinâmico
placeholder = st.empty()

# Loop principal da interface que se auto-atualiza
while True:
    with placeholder.container():
        # Copia os dados do estado para evitar problemas de concorrência durante a renderização
        current_timestamps = list(st.session_state.timestamps)
        current_values = list(st.session_state.values)

        # Exibe as métricas
        col1, col2 = st.columns(2)
        if current_values:
            col1.metric("Leitura Atual", f"{current_values[-1]:.2f} kW")
            col2.metric("Leitura Média (na janela)", f"{(sum(current_values)/len(current_values)):.2f} kW")
        else:
            col1.metric("Leitura Atual", "Aguardando...")
            col2.metric("Leitura Média", "Aguardando...")

        # Exibe o gráfico
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=current_timestamps, y=current_values, mode='lines', name='Potência'))
        fig.update_layout(
            height=400,
            xaxis_title='Horário',
            yaxis_title='Potência (kW)',
            xaxis=dict(range=[datetime.now() - timedelta(seconds=DATA_WINDOW_SECONDS), datetime.now()])
        )
        st.plotly_chart(fig, use_container_width=True)

    # Pausa de 1 segundo para dar tempo para a UI renderizar e não sobrecarregar o sistema
    time.sleep(1)