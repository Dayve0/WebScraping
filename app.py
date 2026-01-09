import streamlit as st
import mysql.connector
import pandas as pd
import subprocess
import os

# Configuração da página
st.set_page_config(page_title="Monitor de Preços", layout="wide")

# Função para conectar no banco
# OBS: No Streamlit Cloud, 'localhost' NÃO funciona porque o banco não está lá.
# Você precisará de um banco na nuvem ou mudar para SQLite.
def get_connection():
    # Tenta pegar as credenciais dos "Secrets" do Streamlit ou usa o padrão (para teste local)
    return mysql.connector.connect(
        host=st.secrets.get("DB_HOST", "localhost"),
        user=st.secrets.get("DB_USER", "root"),
        password=st.secrets.get("DB_PASS", "Tomato@mysql08"),
        database=st.secrets.get("DB_NAME", "banco_dayve")
    )

st.title("🛒 Produtos Monitorados")

# Botão para rodar o Scraper
if st.button("🔄 Rodar Scraper Agora"):
    with st.spinner('Buscando dados no Mercado Livre...'):
        try:
            # Roda o script e captura a saída
            result = subprocess.run(["python", "scraper.py"], capture_output=True, text=True)
            if result.returncode == 0:
                st.success("Scraper executado com sucesso!")
            else:
                st.error(f"Erro ao rodar scraper: {result.stderr}")
        except Exception as e:
            st.error(f"Erro: {e}")

# Exibição dos produtos
try:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT product, old_price, current_price, seller, source, img_link, created_at
        FROM products
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    if rows:
        # Cria um grid de cards (substituindo seu HTML/Tailwind)
        cols = st.columns(4) # 4 colunas como no seu HTML
        
        for i, produto in enumerate(rows):
            with cols[i % 4]: # Distribui entre as colunas
                with st.container(border=True):
                    st.image(produto['img_link'], use_container_width=True)
                    st.markdown(f"**{produto['product'][:50]}...**")
                    st.caption(produto['seller'])
                    
                    st.markdown(f"De: ~~R$ {produto['old_price']}~~")
                    st.markdown(f"**Por: R$ {produto['current_price']}**")
                    
                    st.link_button("Acessar", produto['source'])
                    st.caption(f"Coletado em: {produto['created_at']}")
    else:
        st.warning("Nenhum produto encontrado no banco de dados.")

except Exception as e:
    st.error(f"Erro de conexão com o banco: {e}")
