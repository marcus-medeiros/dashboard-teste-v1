import pandas as pd
import random
from datetime import datetime, timedelta
import streamlit as st
import os

# Nome do arquivo CSV
CSV_ARQUIVO = "bess_dados.csv"

# --- 1. Função para gerar dados simulados ---
def gerar_dados_simulados(qtd=1000):
    timestamps = []
    tensoes = []
    correntes = []
    potencias = []
    socs = []

    tempo_inicial = datetime.now()
    soc_atual = random.uniform(40, 80)

    for i in range(qtd):
        ts = tempo_inicial + timedelta(seconds=i * 2)

        tensao = round(random.uniform(320, 410), 2)     # Volts
        corrente = round(random.uniform(-120, 120), 2)  # Amperes
        potencia = round(tensao * corrente / 1000, 2)   # kW

        # Atualiza o SOC de forma incremental
        delta_soc = -potencia * 2 / 3600  # kW * s -> kWh -> % aproximado
        soc_atual += delta_soc
        soc_atual = max(0, min(100, soc_atual))         # Limita entre 0% e 100%

        timestamps.append(ts)
        tensoes.append(tensao)
        correntes.append(corrente)
        potencias.append(potencia)
        socs.append(round(soc_atual, 2))

    df = pd.DataFrame({
        "timestamp": timestamps,
        "tensao": tensoes,
        "corrente": correntes,
        "potencia": potencias,
        "soc": socs
    })

    df.to_csv(CSV_ARQUIVO, index=False)
    print(f"✅ {qtd} dados simulados salvos em '{CSV_ARQUIVO}'.")

# --- 2. Streamlit App para visualização ---
def app_streamlit():
    st.set_page_config(page_title="Dashboard BESS Simulado", layout="wide")
    st.title("🔋 Dashboard BESS - Simulação")

    if not os.path.exists(CSV_ARQUIVO):
        st.warning("Arquivo de dados não encontrado. Gerando dados simulados...")
        gerar_dados_simulados()

    df = pd.read_csv(CSV_ARQUIVO)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values("timestamp")

    st.markdown("Visualização dos dados simulados de um sistema de armazenamento de energia (BESS).")

    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("SOC Atual", f"{df['soc'].iloc[-1]:.2f} %")
    col2.metric("Potência", f"{df['potencia'].iloc[-1]:.2f} kW")
    col3.metric("Tensão", f"{df['tensao'].iloc[-1]:.2f} V")
    col4.metric("Corrente", f"{df['corrente'].iloc[-1]:.2f} A")

    # Gráficos
    st.subheader("📈 Gráfico: Potência e SOC ao longo do tempo")
    st.line_chart(df.set_index("timestamp")[["potencia", "soc"]])

    with st.expander("🔎 Ver tabela completa"):
        st.dataframe(df[::-1], use_container_width=True)

# --- 3. Execução principal ---
if __name__ == "__main__":
    # Executa como app Streamlit
    app_streamlit()
