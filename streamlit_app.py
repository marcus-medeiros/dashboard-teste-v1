import streamlit as st
import pandas as pd
import threading
from datetime import datetime
import time
import paho.mqtt.client as mqtt
import altair as alt
import random
import socket

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
    
    st.markdown("---")
    usar_simulador = st.toggle("Simular Dados (para teste)", value=True)
    st.caption("Ative esta opção para ver os gráficos funcionando se não houver dados reais no MQTT.")

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
        if 'mqtt_connection_error' in st.session_state:
            del st.session_state['mqtt_connection_error']


    topicos_a_subscrever = []
    if not usar_simulador:
        for cidade in cidades_selecionadas:
            cidade_formatada = cidade.lower().replace(" ", "_")
            for parametro in ['tensao', 'corrente', 'potencia']:
                topicos_a_subscrever.append(f"bess/telemetria/{cidade_formatada}/{parametro}")

    lock = threading.Lock()

    # Callback do MQTT (Tornado mais robusto)
    def on_message(client, userdata, msg):
        topico = msg.topic
        try:
            partes_topico = topico.split('/')
            cidade_topico, parametro_topico = partes_topico[2], partes_topico[3]
            valor = float(msg.payload.decode())
        except (IndexError, ValueError):
            return

        agora = datetime.now()
        with lock:
            # FIX: Verifica se a estrutura de dados ainda existe antes de escrever nela
            if 'dados' in st.session_state and cidade_topico in st.session_state.dados:
                df_alvo = st.session_state.dados[cidade_topico][parametro_topico]
                nova_linha = pd.DataFrame({'Hora': [agora], 'Valor': [valor]})
                df_atualizado = pd.concat([df_alvo, nova_linha], ignore_index=True)
                st.session_state.dados[cidade_topico][parametro_topico] = df_atualizado.tail(100)

    # Função para rodar o cliente MQTT (com tratamento de erro e API atualizada)
    def iniciar_mqtt():
        try:
            # FIX: Atualizado para a API recomendada para evitar DeprecationWarning
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            client.on_message = on_message
            client.connect("test.mosquitto.org", 1883, 60)
            
            if 'mqtt_connection_error' in st.session_state:
                del st.session_state['mqtt_connection_error']

            for t in topicos_a_subscrever:
                client.subscribe(t)
            client.loop_forever()
        except (socket.gaierror, OSError) as e:
            st.session_state.mqtt_connection_error = f"Erro de Conexão MQTT: {e}. Verifique sua conexão de rede ou firewall."
        except Exception as e:
            st.session_state.mqtt_connection_error = f"Ocorreu um erro inesperado no MQTT: {e}"


    # Função para simular a chegada de dados (Refatorada para ser mais segura)
    def iniciar_simulador(cidades_a_simular, lock_obj):
        while True:
            with lock_obj:
                # FIX: Verifica se 'dados' existe no session_state antes de usá-lo
                if 'dados' in st.session_state:
                    for cidade_nome_amigavel in cidades_a_simular:
                        cidade_formatada = cidade_nome_amigavel.lower().replace(" ", "_")
                        # FIX: Verifica se a chave da cidade específica ainda existe
                        if cidade_formatada in st.session_state.dados:
                            agora = datetime.now()
                            dados_cidade = st.session_state.dados[cidade_formatada]
                            
                            dados_cidade['tensao'] = pd.concat([
                                dados_cidade['tensao'],
                                pd.DataFrame({'Hora': [agora], 'Valor': [220 + random.uniform(-5, 5)]})
                            ], ignore_index=True).tail(100)

                            dados_cidade['corrente'] = pd.concat([
                                dados_cidade['corrente'],
                                pd.DataFrame({'Hora': [agora], 'Valor': [10 + random.uniform(-2, 2)]})
                            ], ignore_index=True).tail(100)

                            dados_cidade['potencia'] = pd.concat([
                                dados_cidade['potencia'],
                                pd.DataFrame({'Hora': [agora], 'Valor': [2.5 + random.uniform(-0.5, 0.5)]})
                            ], ignore_index=True).tail(100)
            time.sleep(2)

    # Inicia a thread (MQTT ou Simulador) apenas uma vez por seleção
    session_key = f"thread_started_{'sim' if usar_simulador else 'mqtt'}_{'_'.join(sorted(cidades_selecionadas))}"
    if session_key not in st.session_state:
        for key in list(st.session_state.keys()):
            if key.startswith('thread_started_'):
                del st.session_state[key]

        if usar_simulador:
            # FIX: Passa a lista de cidades como argumento para a thread
            thread = threading.Thread(target=iniciar_simulador, args=(cidades_selecionadas.copy(), lock), daemon=True)
        else:
            thread = threading.Thread(target=iniciar_mqtt, daemon=True)
        
        thread.start()
        st.session_state[session_key] = True

    # --- GERAÇÃO DOS GRÁFICOS ---
    st.header("Comparativos em Tempo Real")
    
    if 'mqtt_connection_error' in st.session_state:
        st.error(st.session_state.mqtt_connection_error)

    placeholders = {'tensao': st.empty(), 'corrente': st.empty(), 'potencia': st.empty()}
    info_parametros = {
        'tensao': ('Tensão', 'Tensão (V)'),
        'corrente': ('Corrente', 'Corrente (A)'),
        'potencia': ('Potência', 'Potência (kW)')
    }

    with lock:
        for parametro, area in placeholders.items():
            lista_dfs = []
            for cidade_nome_amigavel in cidades_selecionadas:
                cidade_formatada = cidade_nome_amigavel.lower().replace(" ", "_")
                if cidade_formatada in st.session_state.dados:
                    df_parametro = st.session_state.dados[cidade_formatada][parametro]
                    if not df_parametro.empty:
                        df_temp = df_parametro.copy()
                        df_temp['Cidade'] = cidade_nome_amigavel
                        lista_dfs.append(df_temp)

            if lista_dfs:
                df_plot = pd.concat(lista_dfs, ignore_index=True)
                df_plot['Hora'] = pd.to_datetime(df_plot['Hora'])
                titulo_amigavel, unidade = info_parametros[parametro]
                chart = alt.Chart(df_plot).mark_line().encode(
                    x=alt.X('Hora:T', title='Hora'),
                    y=alt.Y('Valor:Q', title=unidade, scale=alt.Scale(zero=False)),
                    color=alt.Color('Cidade:N', title='Cidade'),
                    tooltip=[
                        alt.Tooltip('Cidade:N', title='Cidade'),
                        alt.Tooltip('Hora:T', format='%H:%M:%S', title='Hora'),
                        alt.Tooltip('Valor:Q', format='.2f', title=unidade)
                    ],
                ).properties(title=f"Comparativo de {titulo_amigavel}").interactive()
                area.altair_chart(chart, use_container_width=True)

    time.sleep(1)
    st.rerun()

else:
    st.info("⬅️ Por favor, selecione uma ou mais cidades no painel à esquerda para iniciar o monitoramento.")
