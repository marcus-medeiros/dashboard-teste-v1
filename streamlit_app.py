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
        client.connect("test.mosquitto.org", 1883, 60)

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


