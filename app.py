import streamlit as st
import sqlite3
import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Produtos Scraping", layout="wide")

# Funções de formatação
def format_currency(value):
    if value is None: return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date(value):
    if not value: return ""
    # Se vier como string do SQLite, tenta converter ou exibir direto
    return str(value)

# Conexão SQLite
def get_db_connection():
    return sqlite3.connect('dados.db')

st.title("🛒 Produtos Coletados (SQLite)")

# Botão de execução
if st.button("🔄 Rodar Scraper Novamente"):
    with st.spinner("Rodando o robô... aguarde."):
        try:
            # sys.executable garante que usa o python correto
            result = subprocess.run(
                [sys.executable, "scraper.py"], 
                capture_output=True, 
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                st.success("Atualizado com sucesso!")
                st.rerun()
            else:
                st.error("Erro no scraper:")
                st.code(result.stderr) # Mostra o erro real
                st.text("Logs de saída:")
                st.code(result.stdout)
        except Exception as e:
            st.error(f"Erro crítico: {e}")

# Exibir dados
if os.path.exists('dados.db'):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Retorna dicionário para facilitar
        cursor.row_factory = sqlite3.Row 
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
        produtos = cursor.fetchall()
        conn.close()

        if not produtos:
            st.info("Banco vazio. Clique no botão acima para coletar.")
        else:
            st.metric("Total de Produtos", len(produtos))
            
            cols = st.columns(4)
            for index, p in enumerate(produtos):
                with cols[index % 4]:
                    with st.container(border=True):
                        if p['img_link']:
                            st.image(p['img_link'], use_container_width=True)
                        
                        st.markdown(f"**{p['product']}**")
                        st.caption(f"{p['seller']}")
                        
                        st.markdown(f"De: ~~{format_currency(p['old_price'])}~~")
                        st.markdown(f"**Por: {format_currency(p['current_price'])}**")
                        
                        st.link_button("Acessar", p['source'], use_container_width=True)
                        st.caption(f"Atualizado em: {p['created_at']}")
    except Exception as e:
        st.error(f"Erro ao ler banco: {e}")
else:
    st.warning("Arquivo de banco de dados não encontrado. Rode o scraper pela primeira vez.")
