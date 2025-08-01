import streamlit as st
import pandas as pd
from pathlib import Path

from datetime import datetime
import time
import threading
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
from datetime import datetime, timedelta  # <== adicionar timedelta



# Definições do broker MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "bess/energia"

# git add .
# git commit -m "Descreva o que foi alterado aqui"
# git push


# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='BESS - Gerenciamento', #Tag da URL
    page_icon=':zap:', # Emoji da URL
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data
def get_gdp_data():
    """Grab GDP data from a CSV file.

    This uses caching to avoid having to read the file every time. If we were
    reading from an HTTP endpoint instead of a file, it's a good idea to set
    a maximum age to the cache with the TTL argument: @st.cache_data(ttl='1d')
    """

    # Instead of a CSV on disk, you could read from an HTTP endpoint here too.
    DATA_FILENAME = Path(__file__).parent/'data/gdp_data.csv'
    raw_gdp_df = pd.read_csv(DATA_FILENAME)

    MIN_YEAR = 1960
    MAX_YEAR = 2000

    # The data above has columns like:
    # - Country Name
    # - Country Code
    # - [Stuff I don't care about]
    # - GDP for 1960
    # - GDP for 1961
    # - GDP for 1962
    # - ...
    # - GDP for 2022
    #
    # ...but I want this instead:
    # - Country Name
    # - Country Code
    # - Year
    # - GDP
    #
    # So let's pivot all those year-columns into two: Year and GDP
    gdp_df = raw_gdp_df.melt(
        ['Country Code'],
        [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
        'Year',
        'GDP',
    )

    # Convert years from string to integers
    gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])

    return gdp_df

gdp_df = get_gdp_data()

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
#st.image("Logo-Baterias-Moura.png", width=200)
'''
# :zap: BESS - Battery Energy Storage System

Este projeto poderá servir como base para pesquisas, desenvolvimento de projetos de 
engenharia elétrica/energia, e implementação prática de soluções baseadas em 
armazenamento energético.
'''

# Add some spacing
''
''

opcao_estado = st.selectbox(
    'Selecione o BESS:',
    ['-', 'PB', 'RN', 'PE']
)

if opcao_estado == 'PB':
    opcao_cidade = st.selectbox(
        'Selecione a cidade:',
        ['-', 'João Pessoa', 'Campina Grande', 'Várzea']
    )

elif opcao_estado == 'PE':
    opcao_cidade = st.selectbox(
        'Selecione a cidade:',
        ['-', 'Recife', 'Caruaru']
    )

elif opcao_estado == 'RN':
    opcao_cidade = st.selectbox(
        'Selecione a cidade:',
        ['-', 'Natal', 'Mossoró']
    )

# Exemplo extra (opcional): se quiser mostrar a escolha
if opcao_estado != '-' and opcao_cidade != '-':
    st.write(f'Você selecionou: {opcao_cidade} - {opcao_estado}')
    grafico = True
else: grafico = False

''
''
''

st.write("Timestamps:", st.session_state.timestamps)
st.write("Values:", st.session_state.values)

if (grafico):
    # Inicia estrutura de dados
    if "timestamps" not in st.session_state:
        st.session_state.timestamps = []
    if "values" not in st.session_state:
        st.session_state.values = []

    # Funções MQTT
    def on_connect(client, userdata, flags, rc):
        client.subscribe(MQTT_TOPIC)

    def on_message(client, userdata, msg):
        try:
            valor = float(msg.payload.decode())
            agora = datetime.now()
            st.session_state.timestamps.append(agora)
            st.session_state.values.append(valor)

            # Mantém apenas os últimos 60 segundos
            limite = agora - timedelta(seconds=60)
            while st.session_state.timestamps and st.session_state.timestamps[0] < limite:
                st.session_state.timestamps.pop(0)
                st.session_state.values.pop(0)
        except:
            pass

    def start_mqtt():
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()

    # Inicia o cliente MQTT em uma thread
    if "mqtt_thread" not in st.session_state:
        mqtt_thread = threading.Thread(target=start_mqtt)
        mqtt_thread.daemon = True
        mqtt_thread.start()
        st.session_state.mqtt_thread = mqtt_thread

    # Interface
    st.title("Gráfico MQTT em tempo real (últimos 60s)")

    # Cria o gráfico Plotly
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=st.session_state.timestamps,
        y=st.session_state.values,
        mode="lines+markers",
        line=dict(color="blue")
    ))
    fig.update_layout(
        xaxis_title="Tempo",
        yaxis_title="Valor",
        xaxis=dict(range=[datetime.now() - timedelta(seconds=60), datetime.now()]),
        yaxis=dict(autorange=True),
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)


