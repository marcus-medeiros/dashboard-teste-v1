import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime, timedelta
import time

CSV_ARQUIVO = "bess_dados.csv"
INTERVALO = 2  # segundos

# Inicializa CSV
def inicializar_csv():
    if not os.path.exists(CSV_ARQUIVO):
        df = pd.DataFrame(columns=["timestamp", "tensao", "corrente", "potencia", "soc"])
        df.to_csv(CSV_ARQUIVO, index=False)

# Simula e salva novo dado
def gerar_dado(soc_atual):
    timestamp = datetime.now()
    tensao = round(random.uniform(320, 410), 2)
    corrente = round(random.uniform(-120, 120), 2)
    potencia = round(tensao * corrente / 1000, 2)
    delta_soc = -potencia * INTERVALO / 3600
    soc_atual = max(0, min(100, soc_atual + delta_soc))

    novo_dado = {
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "tensao": tensao,
        "corrente": corrente,
        "potencia": potencia,
        "soc": round(soc_atual, 2)
    }

    df = pd.DataFrame([novo_dado])
    df.to_csv(CSV_ARQUIVO, mode='a', index=False, header=False)
    return soc_atual

# Interface
st.set_page_config("Simulador BESS", layout="wide")
st.title("🔋 Dashboard com Simulador BESS Integrado")

inicializar_csv()

if "soc" not in st.session_state:
    st.session_state.soc = random.uniform(40, 80)

# Botão para ativar simulação contínua
if st.button("Simular novo dado"):
    st.session_state.soc = gerar_dado(st.session_state.soc)
    st.success("Novo dado simulado!")

# Carrega e exibe os dados
df = pd.read_csv(CSV_ARQUIVO)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values("timestamp")

col1, col2, col3, col4 = st.columns(4)
if not df.empty:
    col1.metric("SOC Atual", f"{df['soc'].iloc[-1]:.2f} %")
    col2.metric("Potência", f"{df['potencia'].iloc[-1]:.2f} kW")
    col3.metric("Tensão", f"{df['tensao'].iloc[-1]:.2f} V")
    col4.metric("Co
