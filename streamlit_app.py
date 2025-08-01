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

    # Lista de todas as cidades disponíveis para seleção
    cidades_disponiveis = [
        'João Pessoa', 'Campina Grande', 'Várzea',  # PB
        'Recife', 'Caruaru',                         # PE
        'Natal', 'Mossoró'                           # RN
    ]

    # Modificado para multiselect, permitindo escolher até 2 cidades
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
    # Formato: { 'cidade_1': {'tensao': df, 'corrente': df}, 'cidade_2': ... }
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

    # Lock para garantir a segurança do acesso concorrente aos dados
    lock = threading.Lock()

    # Callback do MQTT: agora inteligente para rotear os dados para a cidade correta
    def on_message(client, userdata, msg):
        topico = msg.topic
        try:
            # Extrai cidade e parâmetro do tópico: "bess/telemetria/joao_pessoa/tensao"
            partes_topico = topico.split('/')
            cidade_topico = partes_topico[2]
            parametro_topico = partes_topico[3]
            valor = float(msg.payload.decode())
        except (IndexError, ValueError):
            # Ignora mensagens mal formatadas ou com payload inválido
            return

        agora = datetime.now()

        # Verifica se a mensagem é de uma cidade monitorada
        if cidade_topico in st.session_state.dados:
            with lock:
                df_alvo = st.session_state.dados[cidade_topico][parametro_topico]
                nova_linha = pd.DataFrame({'Hora': [agora], 'Valor': [valor]})
                
                # Adiciona nova linha e mantém o DataFrame com no máximo 100 pontos
                df_atualizado = pd.concat([df_alvo, nova_linha], ignore_index=True)
                st.session_state.dados[cidade_topico][parametro_topico] = df_atualizado.tail(100)

    # Função para rodar o cliente MQTT em uma thread separada
    def iniciar_mqtt():
        # Especifica a versão da API de callback para compatibilidade com paho-mqtt > 2.0
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        client.on_message = on_message
        client.connect("test.mosquitto.org", 1883, 60)
        for t in topicos_a_subscrever:
            client.subscribe(t)
        client.loop_forever()

    # Inicia a thread MQTT apenas uma vez usando o st.session_state
    if 'mqtt_thread_started' not in st.session_state or st.session_state.get('cidades_monitoradas') != cidades_selecionadas:
        # Se a seleção de cidades mudar, uma nova thread será necessária (simplificação)
        # Em um app real, seria melhor gerenciar a mesma thread, alterando as subscrições.
        thread = threading.Thread(target=iniciar_mqtt, daemon=True)
        thread.start()
        st.session_state.mqtt_thread_started = True

    # --- GERAÇÃO DOS GRÁFICOS ---
    
    # Cria colunas principais, uma para cada cidade selecionada
    cols_cidades = st.columns(len(cidades_selecionadas))

    # Dicionário para armazenar os placeholders dos gráficos
    placeholders = {}

    for i, cidade in enumerate(cidades_selecionadas):
        cidade_formatada = cidade.lower().replace(" ", "_")
        with cols_cidades[i]:
            st.subheader(f"Telemetria de {cidade}")
            placeholders[cidade_formatada] = {
                'tensao': st.empty(),
                'corrente': st.empty(),
                'potencia': st.empty()
            }

    # Loop de atualização contínua dos gráficos
    while True:
        with lock:
            for cidade_formatada, graficos_cidade in placeholders.items():
                for parametro, area in graficos_cidade.items():
                    df = st.session_state.dados[cidade_formatada][parametro]
                    if not df.empty:
                        # Mapeia o nome do parâmetro para o título e unidade
                        info_parametro = {
                            'tensao': ('Tensão', 'Volts (V)'),
                            'corrente': ('Corrente', 'Ampères (A)'),
                            'potencia': ('Potência', 'Kilowatts (kW)')
                        }
                        titulo, unidade = info_parametro[parametro]
                        
                        df_plot = df.copy()
                        df_plot['Hora'] = pd.to_datetime(df_plot['Hora'])

                        chart = alt.Chart(df_plot).mark_line().encode(
                            x=alt.X('Hora:T', title='Hora'),
                            y=alt.Y('Valor:Q', title=unidade, scale=alt.Scale(zero=False)),
                            tooltip=[
                                alt.Tooltip('Hora:T', format='%H:%M:%S', title='Hora'),
                                alt.Tooltip('Valor:Q', format='.2f', title=unidade)
                            ],
                        ).properties(
                            title=titulo
                        ).interactive()
                        
                        area.altair_chart(chart, use_container_width=True)
        time.sleep(1)
else:
    st.info("⬅️ Por favor, selecione uma ou duas cidades no painel à esquerda para iniciar o monitoramento.")

