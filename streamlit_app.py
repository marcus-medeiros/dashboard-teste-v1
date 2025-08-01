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

# Sidebar para seleção de estado e múltiplas cidades
with st.sidebar:
    st.header("Painel de Controle BESS ⚡️")
    opcao_estado = st.selectbox('Selecione o Estado:', ['-', 'PB', 'RN', 'PE'])

    cidades_por_estado = {
        'PB': ['João Pessoa', 'Campina Grande', 'Várzea'],
        'PE': ['Recife', 'Caruaru'],
        'RN': ['Natal', 'Mossoró']
    }

    if opcao_estado != '-':
        opcao_cidades = st.multiselect('Selecione uma ou mais cidades:', cidades_por_estado[opcao_estado])
    else:
        opcao_cidades = []

# Só prossegue se ao menos uma cidade estiver selecionada
if not opcao_cidades:
    st.info("Selecione pelo menos uma cidade para mostrar os gráficos.")
    st.stop()

lock = threading.Lock()

# Estrutura para armazenar dados: {cidade: {parametro: DataFrame}}
dados = {}
parametros = ['tensao', 'corrente', 'potencia']

for cidade in opcao_cidades:
    dados[cidade] = {p: pd.DataFrame(columns=['Hora', 'Valor']) for p in parametros}

# Função para formatar tópico de forma consistente
def formatar_cidade(cidade):
    return cidade.lower().replace(" ", "_")

# Mapeia tópicos MQTT para cidade e parâmetro
topicos_para_cidade_parametro = {}
for cidade in opcao_cidades:
    cidade_fmt = formatar_cidade(cidade)
    for parametro in parametros:
        topico = f"bess/telemetria/{cidade_fmt}/{parametro}"
        topicos_para_cidade_parametro[topico] = (cidade, parametro)

# Callback MQTT
def on_message(client, userdata, msg):
    topico = msg.topic
    try:
        valor = float(msg.payload.decode())
    except:
        return

    agora = datetime.now()

    if topico in topicos_para_cidade_parametro:
        cidade, parametro = topicos_para_cidade_parametro[topico]
        with lock:
            nova_linha = pd.DataFrame({'Hora': [agora], 'Valor': [valor]})
            dados[cidade][parametro] = pd.concat([dados[cidade][parametro], nova_linha], ignore_index=True)
            # Limita a 100 pontos
            if len(dados[cidade][parametro]) > 100:
                dados[cidade][parametro] = dados[cidade][parametro].iloc[-100:]

# Thread para rodar MQTT
def iniciar_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect("test.mosquitto.org", 1883, 60)
    for topico in topicos_para_cidade_parametro.keys():
        client.subscribe(topico)
    client.loop_forever()

threading.Thread(target=iniciar_mqtt, daemon=True).start()

# Função para criar gráfico Altair
def criar_grafico(df, titulo, unidade):
    if df.empty:
        return None
    df_plot = df.tail(50).copy()
    df_plot['Hora'] = pd.to_datetime(df_plot['Hora'])
    chart = alt.Chart(df_plot).mark_line().encode(
        x=alt.X('Hora:T', title='Hora'),
        y=alt.Y('Valor:Q', title=unidade),
        tooltip=[alt.Tooltip('Hora:T', title='Hora'), alt.Tooltip('Valor:Q', title=unidade)]
    ).properties(
        title=titulo,
        width=300,
        height=250
    ).interactive()
    return chart

# Exibe gráficos por cidade
for cidade in opcao_cidades:
    st.subheader(f"📍 Cidade: {cidade}")
    col1, col2, col3 = st.columns(3)

    with lock:
        df_tensao = dados[cidade]['tensao']
        df_corrente = dados[cidade]['corrente']
        df_potencia = dados[cidade]['potencia']

    chart_tensao = criar_grafico(df_tensao, "Tensão", "Volts (V)")
    chart_corrente = criar_grafico(df_corrente, "Corrente", "Ampères (A)")
    chart_potencia = criar_grafico(df_potencia, "Potência", "Kilowatts (kW)")

    if chart_tensao:
        col1.altair_chart(chart_tensao, use_container_width=True)
    else:
        col1.write("Sem dados de tensão ainda.")

    if chart_corrente:
        col2.altair_chart(chart_corrente, use_container_width=True)
    else:
        col2.write("Sem dados de corrente ainda.")

    if chart_potencia:
        col3.altair_chart(chart_potencia, use_container_width=True)
    else:
        col3.write("Sem dados de potência ainda.")

    st.markdown("---")

    # Pequena pausa para não travar o Streamlit (opcional)
    time.sleep(0.5)
