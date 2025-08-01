# Arquivo: dashboard_app.py
# Descrição: Dashboard para visualizar os dados de energia do BESS a partir de um banco de dados SQLite.

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Configurações ---
DB_FILE = "dados_energia.db"

# Configuração da página do Streamlit
st.set_page_config(
    page_title='Dashboard BESS',
    page_icon='🔋',
    layout='wide'
)

def fetch_data(minutes_ago=10):
    """Busca dados do banco de dados dos últimos X minutos."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            time_filter = (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()
            query = f"SELECT timestamp, valor FROM energia WHERE timestamp >= '{time_filter}' ORDER BY timestamp ASC"
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
    except Exception as e:
        st.error(f"Não foi possível ler o banco de dados. O coletor está rodando? Erro: {e}")
        return pd.DataFrame({'timestamp': [], 'valor': []})

# --- Layout do Dashboard ---
st.title("🔋 Dashboard de Monitoramento BESS")
st.markdown(f"Exibindo dados em tempo real. Atualizado pela última vez em: `{datetime.now().strftime('%H:%M:%S')}`")

minutes = st.sidebar.slider("Ver dados dos últimos (minutos):", 1, 120, 10)

df = fetch_data(minutes_ago=minutes)

if df.empty:
    st.warning("Aguardando dados... Verifique se o simulador e o coletor estão em execução.")
else:
    # --- Métricas Principais ---
    st.subheader("Métricas Atuais")
    last_power = df['valor'].iloc[-1]
    avg_power = df['valor'].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Potência Atual", f"{last_power:.2f} kW")
    col2.metric("Potência Média (período)", f"{avg_power:.2f} kW")

    # Determina o status com base no valor da potência
    if last_power < -5:
        status_text = "Carregando"
        status_emoji = "🔌"
    elif last_power > 5:
        status_text = "Descarregando"
        status_emoji = "⚡"
    else:
        status_text = "Ocioso"
        status_emoji = " standby" # Emoji de espera, ou pode usar 💤
    col3.metric("Status Atual", f"{status_text} {status_emoji}")

    st.write("---")

    # --- Gráfico Principal ---
    st.subheader(f"Histórico de Potência ({minutes} min)")
    fig = go.Figure()
    
    # Adiciona linha de potência
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['valor'],
        mode='lines',
        name='Potência',
        line=dict(color='deepskyblue', width=3),
        fill='tozeroy' # Preenche a área abaixo da linha
    ))

    fig.update_layout(
        xaxis_title='Horário',
        yaxis_title='Potência (kW)',
        hovermode='x unified',
        height=500,
        yaxis_zeroline=True, 
        yaxis_zerolinewidth=2, 
        yaxis_zerolinecolor='rgba(255,0,0,0.5)' # Linha vermelha no zero para ver carga/descarga
    )
    st.plotly_chart(fig, use_container_width=True)

# Força o Streamlit a recarregar a página a cada 10 segundos para buscar novos dados
st.rerun(ttl=10)