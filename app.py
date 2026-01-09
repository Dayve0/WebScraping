import streamlit as st
import mysql.connector
import subprocess
import sys
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração da página (deve ser o primeiro comando Streamlit)
st.set_page_config(page_title="Produtos Scraping", layout="wide")

# Funções auxiliares de formatação (substituindo os filtros do Jinja2)
def format_currency(value):
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date(value):
    if not value:
        return ""
    return value.strftime("%d/%m/%Y %H:%M")

# Função de conexão com o banco
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Tomato@mysql08", # Idealmente, use os.getenv("DB_PASSWORD")
        database="banco_dayve"
    )

# Título da Aplicação
st.title("🛒 Produtos Coletados")

# Botão para rodar o Scraper
if st.button("🔄 Rodar Scraper Novamente"):
    with st.spinner("Rodando o robô de captura... aguarde."):
        try:
            # Usa sys.executable para garantir que rode no mesmo ambiente virtual
            result = subprocess.run(
                [sys.executable, "scraper.py"], 
                capture_output=True, 
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                st.success("Scraper executado com sucesso!")
                st.rerun() # Recarrega a página para mostrar os dados novos
            else:
                st.error("Erro ao rodar o scraper.")
                st.code(result.stderr) # Mostra o erro na tela para debug
        except Exception as e:
            st.error(f"Erro ao tentar executar o script: {e}")

# Exibição dos Produtos
try:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT product, old_price, current_price, seller, source, img_link, created_at
        FROM products
        ORDER BY created_at DESC
    """)
    produtos = cursor.fetchall()
    
    conn.close()

    if not produtos:
        st.info("Nenhum produto encontrado no banco de dados.")
    else:
        # Cria um grid com 4 colunas (igual ao seu HTML grid-cols-4)
        cols = st.columns(4)
        
        for index, p in enumerate(produtos):
            # O operador % 4 garante que distribua entre as 4 colunas ciclicamente
            with cols[index % 4]:
                # st.container(border=True) cria o efeito de "Card"
                with st.container(border=True):
                    # Imagem
                    if p['img_link']:
                        st.image(p['img_link'], use_container_width=True)
                    
                    # Título e Vendedor
                    st.markdown(f"**{p['product']}**")
                    st.caption(f"{p['seller']}")
                    
                    # Preços
                    st.markdown(f"De: ~~{format_currency(p['old_price'])}~~")
                    st.markdown(f"**Por: {format_currency(p['current_price'])}**")
                    
                    # Link
                    st.link_button("Acessar Oferta", p['source'], use_container_width=True)
                    
                    # Data
                    st.text(f"Coletado: {format_date(p['created_at'])}")

except mysql.connector.Error as err:
    st.error(f"Erro de conexão com o banco de dados: {err}")
