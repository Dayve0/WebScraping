import streamlit as st
import sqlite3
import subprocess
import pandas as pd
import os
import sys

# Configuração da página
st.set_page_config(page_title="Monitor ML", layout="wide")

# No início do scraper.py
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Truque para não ser detectado como robô facilmente:
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    service = Service()
    return webdriver.Chrome(service=service, options=chrome_options)

# --- NOVO: Função para garantir que o banco existe ---
def init_db_if_not_exists():
    if not os.path.exists('dados.db'):
        conn = sqlite3.connect('dados.db')
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            old_price REAL,
            current_price REAL,
            seller TEXT,
            source TEXT,
            img_link TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(product, source)
        )
        """)
        conn.commit()
        conn.close()

# Executa a criação do banco ao abrir o app
init_db_if_not_exists()

# Função de conexão para leitura
def get_connection():
    return sqlite3.connect('dados.db')

st.title("🛒 Monitor de Preços - SQLite")

# Botão para rodar o Scraper
if st.button("🔄 Atualizar Dados"):
    with st.spinner('Rodando scraper... Isso pode levar alguns segundos.'):
        try:
            # Usa sys.executable para garantir que o Pandas seja encontrado
            result = subprocess.run([sys.executable, "scraper.py"], capture_output=True, text=True)
            
            # Exibe logs técnicos apenas se houver erro ou para debug
            if result.returncode == 0:
                st.success("Scraper finalizado com sucesso!")
                st.rerun() # Recarrega a página sozinho
            else:
                st.error("Ocorreu um erro ao rodar o script.")
                with st.expander("Ver detalhes do erro"):
                    st.code(result.stderr)
                    st.code(result.stdout)
        except Exception as e:
            st.error(f"Erro crítico ao tentar executar: {e}")

# Exibição dos dados
try:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products ORDER BY created_at DESC", conn)
    conn.close()

    if not df.empty:
        st.metric("Total de Produtos Rastreados", len(df))
        
        cols = st.columns(4)
        for index, row in df.iterrows():
            with cols[index % 4]:
                with st.container(border=True):
                    # Tratamento para imagem quebrada
                    try:
                        st.image(row['img_link'], use_container_width=True)
                    except:
                        st.text("Sem imagem")
                        
                    st.markdown(f"**{row['product'][:50]}...**")
                    
                    preco = f"R$ {row['current_price']:,.2f}"
                    st.markdown(f"### {preco}")
                    
                    st.link_button("Ver no Site", row['source'])
    else:
        st.info("O banco de dados foi criado, mas está vazio. Clique em 'Atualizar Dados' para buscar produtos.")

except Exception as e:
    st.error(f"Erro ao ler banco de dados: {e}")
