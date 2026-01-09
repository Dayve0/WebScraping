import streamlit as st
import sqlite3
import subprocess
import pandas as pd
import os

# Configuração da página
st.set_page_config(page_title="Monitor ML", layout="wide")

# Função para conectar no SQLite
def get_connection():
    return sqlite3.connect('dados.db')

st.title("🛒 Monitor de Preços - SQLite")

# Botão para rodar o Scraper
if st.button("🔄 Atualizar Dados"):
    with st.spinner('Rodando scraper...'):
        try:
            # Chama o scraper.py
            result = subprocess.run(["python", "scraper.py"], capture_output=True, text=True)
            # Mostra logs para debug
            st.text(result.stdout)
            if result.returncode == 0:
                st.success("Dados atualizados!")
            else:
                st.error("Erro no script.")
                st.code(result.stderr)
        except Exception as e:
            st.error(f"Erro ao executar: {e}")

# Exibição dos dados
if os.path.exists('dados.db'):
    try:
        conn = get_connection()
        # Lendo direto com Pandas (mais fácil)
        df = pd.read_sql_query("SELECT * FROM products ORDER BY created_at DESC", conn)
        conn.close()

        if not df.empty:
            st.metric("Total de Produtos", len(df))
            
            # Grid de Produtos
            cols = st.columns(4)
            for index, row in df.iterrows():
                with cols[index % 4]:
                    with st.container(border=True):
                        st.image(row['img_link'], use_container_width=True)
                        st.markdown(f"**{row['product'][:40]}...**")
                        
                        # Formatação de preço
                        preco = f"R$ {row['current_price']:,.2f}"
                        st.markdown(f"### {preco}")
                        
                        st.link_button("Ver no Site", row['source'])
        else:
            st.info("Banco de dados vazio. Clique em 'Atualizar Dados'.")
            
    except Exception as e:
        st.error(f"Erro ao ler banco: {e}")
else:
    st.warning("Arquivo 'dados.db' ainda não existe. Rode o scraper pela primeira vez.")
