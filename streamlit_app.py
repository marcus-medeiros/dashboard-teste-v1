# Arquivo: dashboard_app.py
# Descrição: Recebe dados de múltiplos tópicos MQTT (tensão, corrente, potência)
#            e exibe em um dashboard interativo com seleção de gráfico.

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import threading
from datetime import datetime, timedelta
import time

# --- 1. CONFIGURAÇÕES ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
# Tópico base para se inscrever usando um wildcard (#)
# O wildcard '#' inscreve o cliente em TODOS os tópicos que começam com 'bess/telemetria/'
TOPICO_WILDCARD = "bess/telemetria/#"
DATA_WINDOW_SECONDS = 120 # Exibir dados dos últimos 2 minutos

# --- 2. GERENCIAMENTO DE ESTADO SEGURO ---
# Usamos o st.session_state para armazenar os dados de forma persistente na sessão do usuário
if 'data' not in st.session_state:
    # Estrutura para armazenar séries temporais para cada parâmetro
    st.session_state.data = {
        'timestamp': [],
        'tensao': [],
        'corrente': [],
        'potencia': []
    }
    # Estrutura para armazenar apenas o último valor conhecido de cada métrica
    st.session_state.last_known = {
        'tensao': 0,
        'corrente': 0,
        'potencia': 0
    }
if 'mqtt_started' not in st.session_state:
    st.session_state.mqtt_started = False

# --- 3. LÓGICA MQTT PARA MÚLTIPLOS TÓPICOS ---
def on_connect(client, userdata, flags, rc):
    """Callback de conexão."""
    if rc == 0:
        print("Conexão com MQTT estabelecida.")
        # Se inscreve no tópico com wildcard para receber todas as métricas
        client.subscribe(TOPICO_WILDCARD)
        print(f"Inscrito em: {TOPICO_WILDCARD}")
    else:
        print(f"Falha na conexão com MQTT, código: {rc}")

def on_message(client, userdata, msg):
    """Callback que processa as mensagens recebidas de múltiplos tópicos."""
    try:
        # Extrai o nome do parâmetro do tópico (ex: 'tensao', 'corrente')
        parametro = msg.topic.split('/')[-1]
        valor = float(msg.payload.decode('utf-8'))
        agora = datetime.now()

        # Verifica se o parâmetro é um dos que queremos armazenar
        if parametro in st.session_state.data:
            # Armazena o dado na sua respectiva lista de série temporal
            st.session_state.data['timestamp'].append(agora)
            st.session_state.data[parametro].append(valor)
            
            # Atualiza o último valor conhecido para as métricas
            st.session_state.last_known[parametro] = valor

            # Limpa dados antigos para não sobrecarregar a memória
            limite_tempo = agora - timedelta(seconds=DATA_WINDOW_SECONDS * 1.2) # Buffer de 20%
            # Esta limpeza é simplificada, uma limpeza mais complexa seria necessária para manter
            # a integridade perfeita entre as listas, mas para visualização é suficiente.
            while st.session_state.data['timestamp'] and st.session_state.data['timestamp'][0] < limite_tempo:
                st.session_state.data['timestamp'].pop(0)
                # Remove o valor correspondente de todas as listas para manter o alinhamento
                for key in ['tensao', 'corrente', 'potencia']:
                    if st.session_state.data[key]:
                        st.session_state.data[key].pop(0)

    except (ValueError, TypeError, IndexError):
        pass # Ignora mensagens mal formatadas ou erros de processamento

def start_mqtt_client():
    """Inicia o cliente MQTT em uma thread separada."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# --- 4. INICIALIZAÇÃO DA THREAD ---
if not st.session_state.mqtt_started:
    print("Iniciando a thread do cliente MQTT...")
    mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()
    st.session_state.mqtt_started = True

# --- 5. INTERFACE GRÁFICA DO STREAMLIT ---
st.set_page_config(page_title="BESS - Dashboard Multi-Tópico", page_icon="📊", layout="wide")
st.title("📊 Dashboard BESS - Monitoramento Multi-Parâmetro")

# Seletor para o usuário escolher o gráfico
st.sidebar.header("Configurações do Gráfico")
parametro_selecionado = st.sidebar.selectbox(
    "Selecione o parâmetro para exibir no gráfico:",
    ('potencia', 'tensao', 'corrente'),
    # Formata as opções para ficarem mais amigáveis (ex: "Potência (kW)")
    format_func=lambda x: f"{x.capitalize()} ({'kW' if x == 'potencia' else 'V' if x == 'tensao' else 'A'})"
)

# Placeholder para o conteúdo dinâmico
placeholder = st.empty()

# Loop principal da interface para atualização contínua
while True:
    # Todo o conteúdo que se atualiza deve estar dentro do "with placeholder.container()"
    with placeholder.container():
        st.header("Métricas em Tempo Real")
        
        # Exibe as métricas com os últimos valores conhecidos
        col1, col2, col3 = st.columns(3)
        # Adicionando chaves únicas para cada métrica
        col1.metric("Tensão", f"{st.session_state.last_known['tensao']:.2f} V", key="metric_tensao")
        col2.metric("Corrente", f"{st.session_state.last_known['corrente']:.2f} A", key="metric_corrente")
        col3.metric("Potência", f"{st.session_state.last_known['potencia']:.2f} kW", key="metric_potencia")
        
        st.write("---")
        
        # Prepara os dados para o gráfico selecionado
        df = pd.DataFrame({
            'timestamp': list(st.session_state.data['timestamp']),
            'valor': list(st.session_state.data[parametro_selecionado])
        }).dropna().drop_duplicates(subset='timestamp').sort_values('timestamp')

        # Cria o gráfico
        st.header(f"Histórico de {parametro_selecionado.capitalize()}", key="grafico_header") # Chave opcional, mas boa prática
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
        
        # A CORREÇÃO PRINCIPAL ESTÁ AQUI: ADICIONANDO A 'KEY'
        st.plotly_chart(fig, use_container_width=True, key="grafico_principal")

    # Pausa para controlar a taxa de atualização
    time.sleep(1)
