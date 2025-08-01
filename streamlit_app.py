import streamlit as st
import pandas as pd
import math
from pathlib import Path
import numpy as np

from datetime import datetime
import time
import threading
import paho.mqtt.client as mqtt

import paho.mqtt.publish as publish
import random


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
if (grafico):
    # Dados globais
    df = pd.DataFrame(columns=['Hora', 'Valor'])

    # Lock para garantir acesso sincronizado aos dados
    lock = threading.Lock()

    # Função chamada ao receber mensagem
    def on_message(client, userdata, msg):
        global df
        valor = float(msg.payload.decode())

        with lock:
            nova_linha = pd.DataFrame({
                'Hora': [datetime.now()],
                'Valor': [valor]
            })
            df = pd.concat([df, nova_linha], ignore_index=True)

    # Configura o cliente MQTT
    def iniciar_mqtt():
        client = mqtt.Client()
        client.on_message = on_message

        # Conecte ao broker (altere se necessário)
        client.connect("broker.hivemq.com", 1883, 60)

        # Tópico que deseja assinar (ex: "bess/energia")
        client.subscribe("bess/energia")

        client.loop_forever()

    # Inicia o MQTT em uma thread separada
    threading.Thread(target=iniciar_mqtt, daemon=True).start()

    # Espaço do gráfico
    grafico = st.empty()

    # Loop do Streamlit para atualizar gráfico
    while True:
        with lock:
            if not df.empty:
                df_filtrado = df.tail(50).set_index('Hora')  # Limita a 50 pontos mais recentes
                grafico.line_chart(df_filtrado)

        time.sleep(1)



