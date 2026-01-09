import streamlit as st
import sqlite3
import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Monitor ML", page_icon="📦", layout="wide")

def format_currency(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_db_connection():
    if not os.path.exists('dados.db'): return None
    return sqlite3.connect('dados.db')

st.title("📦 Monitor de Preços - Mercado Livre")

# --- SIDEBAR ---
with st.sidebar:
    if st.button("🔄 Atualizar Dados", type="primary"):
        with st.spinner("Processando..."):
            subprocess.run([sys.executable, "scraper.py"])
            st.rerun()

# --- DISPLAY ---
conn = get_db_connection()
if conn:
    conn.row_factory = sqlite3.Row
    # Tenta pegar a coluna is_demo. Se der erro (banco antigo), assume 0
    try:
        demos = conn.execute("SELECT count(*) as qtd FROM products WHERE is_demo = 1").fetchone()['qtd']
        is_demo_mode = demos > 0
    except:
        is_demo_mode = False
        
    cursor = conn.execute("SELECT * FROM products ORDER BY created_at DESC")
    produtos = cursor.fetchall()
    conn.close()

    if produtos:
        # AVISO DE MODO DEMO
        if is_demo_mode:
            st.warning("⚠️ **Aviso:** O Mercado Livre bloqueou a conexão temporariamente. Exibindo **Dados de Demonstração** para fins de visualização do projeto.")
        else:
            st.success(f"🟢 Conexão Estabelecida! Exibindo {len(produtos)} produtos em tempo real.")

        # Métricas
        col1, col2 = st.columns(2)
        col1.metric("Produtos", len(produtos))
        media = sum(p['current_price'] for p in produtos) / len(produtos)
        col2.metric("Preço Médio", format_currency(media))

        st.divider()
        
        # Grid
        cols = st.columns(4)
        for i, p in enumerate(produtos):
            with cols[i % 4]:
                with st.container(border=True):
                    if p['img_link']: st.image(p['img_link'], use_container_width=True)
                    st.markdown(f"**{p['product'][:40]}...**")
                    st.markdown(f"### {format_currency(p['current_price'])}")
                    st.caption(p['seller'])
                    st.link_button("Ver Oferta", p['source'], use_container_width=True)
    else:
        st.info("Banco vazio. Clique em Atualizar.")
else:
    st.warning("Primeira execução: Clique em Atualizar para criar o banco.")
