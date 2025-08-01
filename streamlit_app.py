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

broker = "broker.hivemq.com"
topicos = {
    "tensao": "bess/tensao",
    "corrente": "bess/corrente",
    "potencia": "bess/potencia",
}

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


def publisher_loop():
    while True:
        tensao = round(random.uniform(210, 230), 2)      # V
        corrente = round(random.uniform(10, 50), 2)      # A
        potencia = round(tensao * corrente * 0.9, 2)     # kW (considerando fator potência 0.9)
        
        publish.single(topicos["tensao"], str(tensao), hostname=broker)
        publish.single(topicos["corrente"], str(corrente), hostname=broker)
        publish.single(topicos["potencia"], str(potencia), hostname=broker)

        time.sleep(3)


threading.Thread(target=publisher_loop, daemon=True).start()


