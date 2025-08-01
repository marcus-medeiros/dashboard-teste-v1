import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import threading
from datetime import datetime, timedelta
import time

from streamlit_autorefresh import st_autorefresh



# --- 1. CONFIGURAÇÕES ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPICO_WILDCARD = "bess/telemetria/#"
DATA_WINDOW_SECONDS = 120  # Exibir dados dos últimos 2 minutos

# --- 2. GERENCIAMENTO DE ESTADO SEGURO ---
if 'data' not in st.session_state:
    st.session_state.data = {
        'timestamp': [],
        'tensao': [],
        'corrente': [],
        'potencia': []
    }
    st.session_state.last_known = {
        'tensao': 0,
        'corrente': 0,
        'potencia': 0
    }

if 'mqtt_started' not in st.session_state:
    st.session_state.mqtt_started = False

# --- 3. LÓGICA MQTT ---
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Conectado! Código de retorno: {rc}")
    if rc == 0:
        print(f"[MQTT] Inscrito em: {TOPICO_WILDCARD}")
        client.subscribe(TOPICO_WILDCARD)
    else:
        print("[MQTT] Falha na conexão.")

def on_message(client, userdata, msg):
    try:
        parametro = msg.topic.split('/')[-1]
        valor = float(msg.payload.decode('utf-8'))
        agora = datetime.now()
        print(f"[MQTT] Mensagem recebida: {msg.topic} -> {valor}")

        if parametro in st.session_state.data:
            st.session_state.data['timestamp'].append(agora)
            st.session_state.data[parametro].append(valor)
            st.session_state.last_known[parametro] = valor

            limite_tempo = agora - timedelta(seconds=DATA_WINDOW_SECONDS * 1.2)
            while st.session_state.data['timestamp'] and st.session_state.data['timestamp'][0] < limite_tempo:
                st.session_state.data['timestamp'].pop(0)
                for key in ['tensao', 'corrente', 'potencia']:
                    if st.session_state.data[key]:
                        st.session_state.data[key].pop(0)

    except Exception as e:
        print(f"[ERRO MQTT] {e}")

def start_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# --- 4. INICIALIZAÇÃO DA THREAD MQTT ---
if not st.session_state.mqtt_started:
    print("Iniciando a thread do cliente MQTT...")
    mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()
    st.session_state.mqtt_started = True

# --- 5. INTERFACE STREAMLIT ---
st.set_page_config(page_title="BESS - Dashboard Multi-Tópico", page_icon="📊", layout="wide")
st.title("📊 Dashboard BESS - Monitoramento Multi-Parâmetro")

st.sidebar.header("Configurações do Gráfico")
parametro_selecionado = st.sidebar.selectbox(
    "Selecione o parâmetro para exibir no gráfico:",
    ('potencia', 'tensao', 'corrente'),
    format_func=lambda x: f"{x.capitalize()} ({'kW' if x == 'potencia' else 'V' if x == 'tensao' else 'A'})"
)

placeholder = st.empty()

# Auto refresh a cada 1000 ms
st_autorefresh(interval=1000, limit=None, key="auto_refresh")

with placeholder.container():
    st.header("Métricas em Tempo Real")

    col1, col2, col3 = st.columns(3)
    col1.metric(label="Tensão (V)", value=st.session_state.last_known['tensao'])
    col2.metric(label="Corrente (A)", value=st.session_state.last_known['corrente'])
    col3.metric(label="Potência (kW)", value=st.session_state.last_known['potencia'])

    st.write("---")

    df = pd.DataFrame({
        'timestamp': list(st.session_state.data['timestamp']),
        'valor': list(st.session_state.data[parametro_selecionado])
    }).dropna().drop_duplicates(subset='timestamp').sort_values('timestamp')

    st.header(f"Histórico de {parametro_selecionado.capitalize()}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['valor'],
        mode='lines',
        name=parametro_selecionado
    ))
    fig.update_layout(
        height=450,
        xaxis_title='Horário',
        yaxis_title=f"{parametro_selecionado.capitalize()} ({'kW' if parametro_selecionado == 'potencia' else 'V' if parametro_selecionado == 'tensao' else 'A'})"
    )
    st.plotly_chart(fig, use_container_width=True)