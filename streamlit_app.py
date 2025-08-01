import sqlite3
import random
import time
from datetime import datetime
import pandas as pd
import streamlit as st
import sys

# Nome do banco de dados
DB_NAME = "bess_dados.db"

# --- Função para criar a tabela no banco ---
def criar_banco():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bess_dados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            tensao REAL,
            corrente REAL,
            potencia REAL,
            soc REAL
        )
    """)
    conn.commit()
    conn.close()

# --- Função para inserir dados simulados ---
def simular_dados():
    criar_banco()
    while True:
        timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
        tensao = round(random.uniform(300, 400), 2)      # Volts
        corrente = round(random.uniform(-100, 100), 2)   # Amperes (negativo = descarga)
        potencia = round(tensao * corrente / 1000, 2)    # kW
        soc = round(random.uniform(20, 100), 2)          # %

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bess_dados (timestamp, tensao, corrente, potencia, soc) VALUES (?, ?, ?, ?, ?)",
                       (timestamp, tensao, corrente, potencia, soc))
        conn.commit()
        conn.close()

        print(f"[{timestamp}] V={tensao}V | I={corrente}A | P={potencia}kW | SOC={soc}%")
        time.sleep(2)

# --- Função da interface Streamlit ---
def visualizar_dados():
    st.set_page_config(page_title="Monitoramento BESS", layout="wide")
    st.title("🔋 Monitoramento em Tempo Real - BESS")

    criar_banco()
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM bess_dados ORDER BY timestamp DESC LIMIT 100", conn)
    conn.close()

    df = df.sort_values("timestamp")

    col1, col2, col3, col4 = st.columns(4)
    if not df.empty:
        col1.metric("SOC Atual", f"{df['soc'].iloc[-1]:.2f} %")
        col2.metric("Potência", f"{df['potencia'].iloc[-1]:.2f} kW")
        col3.metric("Tensão", f"{df['tensao'].iloc[-1]:.2f} V")
        col4.metric("Corrente", f"{df['corrente'].iloc[-1]:.2f} A")
    else:
        st.warning("Nenhum dado disponível ainda.")

    st.subheader("📊 Gráficos (últimos dados)")
    st.line_chart(df.set_index("timestamp")[["potencia", "soc"]])

    with st.expander("🔎 Ver todos os dados"):
        st.dataframe(df[::-1], use_container_width=True)

# --- Execução baseada no argumento ---
if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "visualizar"
    
    if modo == "simular":
        simular_dados()
    else:
        visualizar_dados()
