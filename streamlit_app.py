import streamlit as st
import pandas as pd
import threading
from datetime import datetime
import time
import paho.mqtt.client as mqtt
import altair as alt

# --- Configuração da Página ---
st.set_page_config(
    page_title='BESS - Gerenciamento',
    page_icon=':zap:',
    layout="wide"
)

# --- Título ---
st.title(":zap: BESS - Battery Energy Storage System")

# --- SIDEBAR: SELEÇÃO DE CIDADES ---
with st.sidebar:
    st.header("Painel de Controle BESS ⚡️")

    cidades_disponiveis = [
        'João Pessoa', 'Campina Grande', 'Várzea',  # PB
        'Recife', 'Caruaru',                         # PE
        'Natal', 'Mossoró'                           # RN
    ]

    cidades_selecionadas = st.multiselect(
        'Selecione até 2 cidades para monitorar:',
        options=cidades_disponiveis,
        default=[],
        max_selections=2,
        key='cidades_multiselect'
    )

# --- LÓGICA PRINCIPAL ---
if cidades_selecionadas:
    # Estrutura de dados aninhada para armazenar dados de múltiplas cidades
    if 'dados' not in st.session_state or st.session_state.get('cidades_monitoradas') != cidades_selecionadas:
        st.session_state.dados = {
            cidade.lower().replace(" ", "_"): {
                'tensao': pd.DataFrame(columns=['Hora', 'Valor']),
                'corrente': pd.DataFrame(columns=['Hora', 'Valor']),
                'potencia': pd.DataFrame(columns=['Hora', 'Valor'])
            } for cidade in cidades_selecionadas
        }
        st.session_state.cidades_monitoradas = cidades_selecionadas

    # Gera a lista completa de tópicos MQTT para todas as cidades selecionadas
    topicos_a_subscrever = []
    for cidade in cidades_selecionadas:
        cidade_formatada = cidade.lower().replace(" ", "_")
        for parametro in ['tensao', 'corrente', 'potencia']:
            topicos_a_subscrever.append(f"bess/telemetria/{cidade_formatada}/{parametro}")

    lock = threading.Lock()

    # Callback do MQTT
    def on_message(client, userdata, msg):
        topico = msg.topic
        try:
            partes_topico = topico.split('/')
            cidade_topico, parametro_topico = partes_topico[2], partes_topico[3]
            valor = float(msg.payload.decode())
        except (IndexError, ValueError):
            return

        agora = datetime.now()
        if cidade_topico in st.session_state.dados:
            with lock:
                df_alvo = st.session_state.dados[cidade_topico][parametro_topico]
                nova_linha = pd.DataFrame({'Hora': [agora], 'Valor': [valor]})
                df_atualizado = pd.concat([df_alvo, nova_linha], ignore_index=True)
                st.session_state.dados[cidade_topico][parametro_topico] = df_atualizado.tail(100)

    # Função para rodar o cliente MQTT em uma thread separada
    def iniciar_mqtt():
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        client.on_message = on_message
        client.connect("test.mosquitto.org", 1883, 60)
        for t in topicos_a_subscrever:
            client.subscribe(t)
        client.loop_forever()

    # Inicia a thread MQTT
    if 'mqtt_thread_started' not in st.session_state or st.session_state.get('cidades_monitoradas') != cidades_selecionadas:
        thread = threading.Thread(target=iniciar_mqtt, daemon=True)
        thread.start()
        st.session_state.mqtt_thread_started = True

    # --- GERAÇÃO DOS GRÁFICOS ---
    
    st.header("Comparativos em Tempo Real")
    
    # Placeholders para os gráficos combinados
    placeholders = {
        'tensao': st.empty(),
        'corrente': st.empty(),
        'potencia': st.empty()
    }

    # Dicionário para mapear nomes de parâmetros para títulos e unidades
    info_parametros = {
        'tensao': ('Tensão', 'Tensão (V)'),
        'corrente': ('Corrente', 'Corrente (A)'),
        'potencia': ('Potência', 'Potência (kW)')
    }

    # Loop de atualização contínua dos gráficos
    while True:
        with lock:
            # Itera sobre cada parâmetro para criar um gráfico comparativo
            for parametro, area in placeholders.items():
                lista_dfs = []
                # Coleta os dataframes do parâmetro atual de todas as cidades selecionadas
                for cidade_nome_amigavel in cidades_selecionadas:
                    cidade_formatada = cidade_nome_amigavel.lower().replace(" ", "_")
                    df_parametro = st.session_state.dados[cidade_formatada][parametro]
                    
                    if not df_parametro.empty:
                        df_temp = df_parametro.copy()
                        df_temp['Cidade'] = cidade_nome_amigavel  # Adiciona coluna para a legenda
                        lista_dfs.append(df_temp)

                # Se houver dados, cria e exibe o gráfico combinado
                if lista_dfs:
                    df_plot = pd.concat(lista_dfs, ignore_index=True)
                    df_plot['Hora'] = pd.to_datetime(df_plot['Hora'])

                    titulo_amigavel, unidade = info_parametros[parametro]

                    chart = alt.Chart(df_plot).mark_line().encode(
                        x=alt.X('Hora:T', title='Hora'),
                        y=alt.Y('Valor:Q', title=unidade, scale=alt.Scale(zero=False)),
                        color=alt.Color('Cidade:N', title='Cidade'),  # Usa a coluna 'Cidade' para criar linhas coloridas
                        tooltip=[
                            alt.Tooltip('Cidade:N', title='Cidade'),
                            alt.Tooltip('Hora:T', format='%H:%M:%S', title='Hora'),
                            alt.Tooltip('Valor:Q', format='.2f', title=unidade)
                        ],
                    ).properties(
                        title=f"Comparativo de {titulo_amigavel}"
                    ).interactive()
                    
                    area.altair_chart(chart, use_container_width=True)
        
        time.sleep(1)
else:
    st.info("⬅️ Por favor, selecione uma ou mais cidades no painel à esquerda para iniciar o monitoramento.")
