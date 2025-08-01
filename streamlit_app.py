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


# --- BARRA LATERAL (SIDEBAR) ---
# Usamos o 'with st.sidebar:' para agrupar todos os elementos que irão para a lateral.
with st.sidebar:
    st.header("Painel de Controle BESS ⚡️")

    st.header("Localização")

    # Seletor de estado (BESS)
    opcao_estado = st.selectbox(
        'Selecione o Estado:',
        ['-', 'PB', 'RN', 'PE'],
        key="select_estado" # Adicionar uma key é uma boa prática
    )
    
    # Lógica para o seletor de cidade dependente do estado
    opcao_cidade = '-' # Valor padrão
    if opcao_estado == 'PB':
        opcao_cidade = st.selectbox(
            'Selecione a cidade:',
            ['-', 'João Pessoa', 'Campina Grande', 'Várzea'],
            key="select_cidade_pb"
        )
    elif opcao_estado == 'PE':
        opcao_cidade = st.selectbox(
            'Selecione a cidade:',
            ['-', 'Recife', 'Caruaru'],
            key="select_cidade_pe"
        )
    elif opcao_estado == 'RN':
        opcao_cidade = st.selectbox(
            'Selecione a cidade:',
            ['-', 'Natal', 'Mossoró'],
            key="select_cidade_rn"
        )

    # Seletor de parâmetro para o gráfico
    st.markdown("---")
    parametro_selecionado = st.selectbox(
        "Selecione o parâmetro do gráfico:",
        ('potencia', 'tensao', 'corrente'),
        # A função format_func deixa a exibição mais amigável
        format_func=lambda x: f"{x.capitalize()} ({'kW' if x == 'potencia' else 'V' if x == 'tensao' else 'A'})"
    )
    st.markdown("---") # Adiciona um separador visual

# Exemplo extra (opcional): se quiser mostrar a escolha
if opcao_estado != '-' and opcao_cidade != '-':
    st.write(f'Você selecionou: {opcao_cidade} - {opcao_estado}')
    grafico = True
else: grafico = False

''
''
''
if (grafico):
    # Dicionário para armazenar os dados de cada parâmetro
    dados = {
        'tensao': pd.DataFrame(columns=['Hora', 'Valor']),
        'corrente': pd.DataFrame(columns=['Hora', 'Valor']),
        'potencia': pd.DataFrame(columns=['Hora', 'Valor'])
    }

    # Mapeia tópico para o nome do parâmetro
    topicos = {
        "bess/telemetria/tensao": "tensao",
        "bess/telemetria/corrente": "corrente",
        "bess/telemetria/potencia": "potencia"
    }

    lock = threading.Lock()



 # Callback quando uma mensagem é recebida
    def on_message(client, userdata, msg):
        topico = msg.topic
        valor = float(msg.payload.decode())
        agora = datetime.now()

        if topico in topicos:
            parametro = topicos[topico]
            with lock:
                nova_linha = pd.DataFrame({'Hora': [agora], 'Valor': [valor]})
                dados[parametro] = pd.concat([dados[parametro], nova_linha], ignore_index=True)

                # Limita a 100 dados
                if len(dados[parametro]) > 100:
                    dados[parametro] = dados[parametro].iloc[-100:]

    # Inicia o cliente MQTT em uma thread
    def iniciar_mqtt():
        client = mqtt.Client()
        client.on_message = on_message
        client.connect("broker.hivemq.com", 1883, 60)

        for t in topicos:
            client.subscribe(t)

        client.loop_forever()

    threading.Thread(target=iniciar_mqtt, daemon=True).start()

    # Espaço para o gráfico
    grafico_area = st.empty()

    # Loop de atualização
    while True:
        with lock:
            df_atual = dados[parametro_selecionado]
            if not df_atual.empty:
                df_plot = df_atual.tail(50).set_index('Hora')
                grafico_area.line_chart(df_plot)
        time.sleep(1)


