import time
import os
import sqlite3
import sys
from selenium import webdriver
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd

# Garante encoding correto no terminal
sys.stdout.reconfigure(encoding='utf-8')

def organize(item):
    try:
        title = item.select_one(".poly-component__title").text
        source = item.select_one(".poly-component__title")["href"]
        seller = item.select_one(".poly-component__seller").text if item.select_one(".poly-component__seller") else 'Não informado'
        
        # oldPrice
        old_integer = item.select_one(".andes-money-amount__fraction").text.strip()
        old_cents = item.select_one(".andes-money-amount__cents").text.strip() if item.select_one(".andes-money-amount__cents") else '00'
        old_price_str = str(old_integer + "," + old_cents)
        
        new_element = item.select_one(".poly-price__current")
        
        # currentPrice
        new_integer = new_element.select_one(".andes-money-amount__fraction").text.strip()
        new_cents = new_element.select_one(".andes-money-amount__cents").text.strip() if new_element.select_one(".andes-money-amount__cents") else '00'
        new_price_str = str(new_integer + "," + new_cents)
        
        image = item.select_one(".poly-component__picture")["src"]
    except Exception as e: 
        print("Erro ao extrair item")
        return None
    else:
         return {
            "product": title,
            "seller": "Vendido por: " + seller,
            "old_price": old_price_str,
            "current_price": new_price_str,
            "source": source,
            "img_link": image
        }

def setup_db():
    # Conecta ou cria o arquivo dados.db
    conn = sqlite3.connect('dados.db')
    cursor = conn.cursor()
    
    # Cria tabela compatível com SQLite
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
    return conn

# --- INÍCIO DO PROCESSO ---

load_dotenv()
url = os.environ.get("URL", "https://lista.mercadolivre.com.br/monitor-gamer") 

print("Iniciando driver...")

service = Service() 
chrome_options = Options()
# Configurações obrigatórias para rodar em servidor (Headless)
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
# User agent para não ser bloqueado
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Acessando {url}...")
    driver.get(url)
    time.sleep(3)
    
    driver.execute_script("window.scrollTo({ top: document.body.scrollHeight / 2, behavior: 'smooth' });")
    time.sleep(2)
    driver.execute_script("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });")
    time.sleep(2)

    # Pega o HTML total
    html_base = driver.page_source
finally:
    driver.quit()

print("Processando HTML...")
soup = BeautifulSoup(html_base, "lxml")

# Seletor genérico que costuma funcionar (pode variar)
items = soup.select(".andes-card.poly-card")
produtos = [organize(item) for item in items if organize(item) is not None]

if not produtos:
    print("Nenhum produto encontrado. Verifique os seletores CSS.")
else:
    # Tratamento de dados com Pandas
    df = pd.DataFrame(produtos)
    
    df["old_price"] = (
        df["old_price"]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    df["current_price"] = (
        df["current_price"]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    # Prepara para salvar no SQLite
    conn = setup_db()
    cursor = conn.cursor()
    
    # Query específica do SQLite para Upsert (Atualizar se existir)
    sql = """
    INSERT INTO products (product, seller, old_price, current_price, source, img_link)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(product, source) DO UPDATE SET
        current_price = excluded.current_price,
        created_at = CURRENT_TIMESTAMP
    """
    
    # Ordem correta das colunas conforme a query acima
    rows = [
        (p['product'], p['seller'], row.old_price, row.current_price, p['source'], p['img_link'])
        for p, row in zip(produtos, df.itertuples())
    ]
    
    try:
        cursor.executemany(sql, rows)
        conn.commit()
        print(f"Sucesso! {len(rows)} produtos processados.")
    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")
    finally:
        conn.close()

print("Fim do scraping.")
