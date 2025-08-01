import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURAÇÕES GLOBAIS ---
CSV_ARQUIVO = "bess_dados.csv"
INTERVALO = 2  # segundos
# Adicionamos a capacidade da bateria, essencial para o cálculo do SOC
CAPACIDADE_BATERIA_kWh = 200.0  # Exemplo: Bateria com capacidade de 200 kWh

# --- FUNÇÕES ---

# Inicializa o CSV (sem alterações, está correto)
def inicializar_csv():
    if not os.path.exists(CSV_ARQUIVO):
        df = pd.DataFrame(columns=["timestamp", "tensao", "corrente", "potencia", "soc"])
        df.to_csv(CSV_ARQUIVO, index=False)

# Simula e salva novo dado com a lógica do SOC corrigida
def gerar_e_salvar_dado(soc_atual):
    # Geração dos dados brutos
    timestamp = datetime.now()
    tensao = round(random.uniform(320, 410), 2)
    corrente = round(random.uniform(-120, 120), 2) # Negativo=carregando, Positivo=descarregando
    potencia = round(tensao * corrente / 1000, 2)  # Em kW

    # --- LÓGICA DO SOC CORRIGIDA ---
    # 1. Calcula a energia em kWh durante o intervalo
    energia_kWh = potencia * (INTERVALO / 3600)
    # 2. Calcula a variação percentual do SOC
    delta_soc_percent = (energia_kWh / CAPACIDADE_BATERIA_kWh) * 100
    # 3. Aplica a variação (inversa à potência: se potência > 0, SOC diminui)
    soc_novo = max(0, min(100, soc_atual - delta_soc_percent))

    novo_dado = {
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "tensao": tensao,
        "corrente": corrente,
        "potencia": potencia,
        "soc": round(soc_novo, 2)
    }

    # Salva o novo dado no CSV sem precisar reler o arquivo
    df_novo_dado = pd.DataFrame([novo_dado])
    df_novo_dado.to_csv(CSV_ARQUIVO, mode='a', header=False, index=False)
    
    return soc_novo, novo_dado


# --- INTERFACE STREAMLIT ---
st.set_page_config("Simulador BESS Otimizado", layout="wide")
st.title("🔋 Dashboard com Simulador BESS Otimizado")

# Inicializa o CSV apenas uma vez
inicializar_csv()

# --- LÓGICA DE PERFORMANCE CORRIGIDA ---
# Carrega o DataFrame para a memória (session_state) apenas uma vez
if 'df_dados' not in st.session_state:
    st.session_state.df_dados = pd.read_csv(CSV_ARQUIVO)
    st.session_state.df_dados['timestamp'] = pd.to_datetime(st.session_state.df_dados['timestamp'])
    
    # Define o SOC inicial com base no último registro ou um valor aleatório
    if not st.session_state.df_dados.empty:
        st.session_state.soc = st.session_state.df_dados['soc'].iloc[-1]
    else:
        st.session_state.soc = random.uniform(40, 80)

# Botão para gerar um novo dado
if st.button("Simular e Adicionar Novo Dado"):
    soc_atualizado, novo_dado_dict = gerar_e_salvar_dado(st.session_state.soc)
    st.session_state.soc = soc_atualizado
    
    # Adiciona o novo dado ao DataFrame em memória, sem reler o CSV
    df_novo = pd.DataFrame([novo_dado_dict])
    df_novo['timestamp'] = pd.to_datetime(df_novo['timestamp'])
    st.session_state.df_dados = pd.concat([st.session_state.df_dados, df_novo], ignore_index=True)
    
    st.success("Novo dado simulado e adicionado com sucesso!")

# Exibe as métricas e gráficos usando o DataFrame da memória
df_display = st.session_state.df_dados

st.subheader("Métricas Atuais")
col1, col2, col3, col4 = st.columns(4)
if not df_display.empty:
    ultimo_dado = df_display.iloc[-1]
    col1.metric("SOC Atual", f"{ultimo_dado['soc']:.2f} %")
    col2.metric("Potência", f"{ultimo_dado['potencia']:.2f} kW")
    col3.metric("Tensão", f"{ultimo_dado['tensao']:.2f} V")
    col4.metric("Corrente", f"{ultimo_dado['corrente']:.2f} A")

# --- SUGESTÃO DE MELHORIA: GRÁFICO COM DOIS EIXOS USANDO PLOTLY ---
st.subheader("Histórico de Potência e Estado de Carga (SOC)")
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Adiciona o gráfico de Potência (eixo Y primário)
fig.add_trace(
    go.Scatter(x=df_display['timestamp'], y=df_display['potencia'], name="Potência (kW)"),
    secondary_y=False,
)

# Adiciona o gráfico de SOC (eixo Y secundário)
fig.add_trace(
    go.Scatter(x=df_display['timestamp'], y=df_display['soc'], name="SOC (%)"),
    secondary_y=True,
)

# Configura títulos e eixos
fig.update_layout(title_text="Potência vs. SOC")
fig.update_xaxes(title_text="Tempo")
fig.update_yaxes(title_text="<b>Potência (kW)</b>", secondary_y=False)
fig.update_yaxes(title_text="<b>SOC (%)</b>", secondary_y=True, range=[0, 100])

st.plotly_chart(fig, use_container_width=True)


with st.expander("Ver tabela completa de dados"):
    st.dataframe(df_display.sort_values(by="timestamp", ascending=False), use_container_width=True)