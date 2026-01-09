import time
import os
import sqlite3
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Configurações do Chrome (Headless para rodar na nuvem)
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Obrigatório para servidores
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Tenta usar o driver instalado localmente ou pelo sistema
    service = Service()
    return webdriver.Chrome(service=service, options=chrome_options)

def organize(item):
    try:
        title = item.select_one(".poly-component__title").text
        source = item.select_one(".poly-component__title")["href"]
        seller = item.select_one(".poly-component__seller").text if item.select_one(".poly-component__seller") else 'Não informado'
        
        # Preço antigo
        old_price_element = item.select_one(".andes-money-amount__fraction")
        old_price_str = old_price_element.text.strip() if old_price_element else "0"
        
        # Preço atual
        new_element = item.select_one(".poly-price__current")
        new_price_str = new_element.select_one(".andes-money-amount__fraction").text.strip()
        
        image = item.select_one(".poly-component__picture")["src"]
        
    except Exception as e: 
        print(f"Erro ao processar item: {e}")
        return None
    else:
         return {
            "product": title,
            "seller": seller,
            "old_price": old_price_str.replace('.', '').replace(',', '.'), # Limpeza básica
            "current_price": new_price_str.replace('.', '').replace(',', '.'),
            "source": source,
            "img_link": image
        }

def setup_db():
    conn = sqlite3.connect('dados.db')
    cursor = conn.cursor()
    
    # Cria a tabela se não existir (Sintaxe SQLite)
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

# --- Início do Script Principal ---

URL = "https://lista.mercadolivre.com.br/monitor-gamer" # Defina sua URL padrão aqui

print("Iniciando scraping...")
driver = get_driver()
driver.get(URL)
time.sleep(3)

# Scroll para carregar itens
driver.execute_script("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });")
time.sleep(2)

# Pegando HTML
html_base = driver.page_source
driver.quit()

# Processando com BeautifulSoup
soup = BeautifulSoup(html_base, "lxml")
items = soup.select(".andes-card.poly-card") # Seletor pode variar, mantive o padrão genérico
produtos = [organize(item) for item in items if organize(item) is not None]

# Salvando no Banco
if produtos:
    conn = setup_db()
    cursor = conn.cursor()
    
    # Query SQLite para Inserir ou Atualizar (Upsert)
    sql = """
    INSERT INTO products (product, old_price, current_price, seller, source, img_link)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(product, source) DO UPDATE SET
        current_price = excluded.current_price,
        created_at = CURRENT_TIMESTAMP
    """
    
    # Convertendo lista de dicts para lista de tuplas
    rows = [
        (p['product'], p['old_price'], p['current_price'], p['seller'], p['source'], p['img_link']) 
        for p in produtos
    ]
    
    cursor.executemany(sql, rows)
    conn.commit()
    conn.close()
    print(f"{len(produtos)} produtos processados e salvos no SQLite.")
else:
    print("Nenhum produto encontrado.")
