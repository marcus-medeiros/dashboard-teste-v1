import streamlit as st
import pandas as pd
import threading
from datetime import datetime
import time
import paho.mqtt.client as mqtt
import altair as alt

# Configuração da página
st.set_page_config(
    page_title='BESS - Gerenciamento',
    page_icon=':zap:',
    layout="wide"
)

# Título da página
st.title(":zap: BESS - Battery Energy Storage System")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Painel de Controle BESS ⚡️")

    opcao_estado = st.selectbox('Selecione o Estado:', ['-', 'PB', 'RN', 'PE'])

    opcao_cidade = '-'
    if opcao_estado == 'PB':
        opcao_cidade = st.selectbox('Selecione a cidade:', ['-', 'João Pessoa', 'Campina Grande', 'Várzea'])
    elif opcao_estado == 'PE':
        opcao_cidade = st.selectbox('Selecione a cidade:', ['-', 'Recife', 'Caruaru'])
    elif opcao_estado == 'RN':
        opcao_cidade = st.selectbox('Selecione a cidade:', ['-', 'Natal', 'Mossoró', 'Caicó'])

if opcao_estado != '-' and opcao_cidade != '-':
    st.write(f'Você selecionou: {opcao_cidade} - {opcao_estado}')
    grafico = True
else:
    grafico = False

# --- GERAÇÃO DOS GRÁFICOS ---
if grafico:
    # Estrutura de dados
    dados = {
        'tensao': pd.DataFrame(columns=['Hora', 'Valor']),
        'corrente': pd.DataFrame(columns=['Hora', 'Valor']),
        'potencia': pd.DataFrame(columns=['Hora', 'Valor'])
    }

    # Mapeia tópicos para nomes
    cidade_formatada = opcao_cidade.lower().replace(" ", "_")  # ex: "João Pessoa" → "joão_pessoa"
    topicos = {
        f"bess/telemetria/{cidade_formatada}/tensao": "tensao",
        f"bess/telemetria/{cidade_formatada}/corrente": "corrente",
        f"bess/telemetria/{cidade_formatada}/potencia": "potencia"
    }

    lock = threading.Lock()

    # Callback do MQTT
    def on_message(client, userdata, msg):
        topico = msg.topic
        try:
            valor = float(msg.payload.decode())
        except:
            return
        agora = datetime.now()

        if topico in topicos:
            parametro = topicos[topico]
            with lock:
                nova_linha = pd.DataFrame({'Hora': [agora], 'Valor': [valor]})
                dados[parametro] = pd.concat([dados[parametro], nova_linha], ignore_index=True)

                if len(dados[parametro]) > 100:
                    dados[parametro] = dados[parametro].iloc[-100:]

    # Thread MQTT
    def iniciar_mqtt():
        client = mqtt.Client()
        client.on_message = on_message
        client.connect("test.mosquitto.org", 1883, 60)

        for t in topicos:
            client.subscribe(t)

        client.loop_forever()

    threading.Thread(target=iniciar_mqtt, daemon=True).start()

    # Cria colunas para os gráficos
    col1, col2, col3 = st.columns(3)
    grafico_tensao = col1.empty()
    grafico_corrente = col2.empty()
    grafico_potencia = col3.empty()

    # Loop de atualização dos gráficos
    while True:
        with lock:
            for parametro, area, titulo, unidade in zip(
                ['tensao', 'corrente', 'potencia'],
                [grafico_tensao, grafico_corrente, grafico_potencia],
                ['Tensão', 'Corrente', 'Potência'],
                ['Volts (V)', 'Ampères (A)', 'Kilowatts (kW)']
            ):
                df = dados[parametro]
                if not df.empty:
                    df_plot = df.tail(50).copy()
                    df_plot['Hora'] = pd.to_datetime(df_plot['Hora'])
                    chart = alt.Chart(df_plot).mark_line().encode(
                        x=alt.X('Hora:T', title='Hora'),
                        y=alt.Y('Valor:Q', title=unidade),
                        tooltip=[alt.Tooltip('Hora:T', title='Hora'), alt.Tooltip('Valor:Q', title=unidade)],
                    ).properties(
                        title=titulo,
                        width=300,
                        height=250
                    ).interactive()
                    area.altair_chart(chart, use_container_width=True)
        time.sleep(1)
