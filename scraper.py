import time
import os
import sqlite3  # Trocamos mysql.connector por sqlite3
from selenium import webdriver
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import sys

# Configuração para logs no Streamlit
sys.stdout.reconfigure(encoding='utf-8')

# Declarando funções que vão ser usadas no scraping
def organize(item):
    try:
        title = item.select_one(".poly-component__title").text
        source = item.select_one(".poly-component__title")["href"]
        seller = item.select_one(".poly-component__seller").text if item.select_one(".poly-component__seller") else 'Não informado'
        
        # oldPrice
        old_element = item.select_one(".andes-money-amount__fraction")
        if old_element:
            old_integer = old_element.text.strip()
            cents_el = item.select_one(".andes-money-amount__cents")
            old_cents = cents_el.text.strip() if cents_el else '00'
            old_price_str = f"{old_integer},{old_cents}"
        else:
            old_price_str = "0,00" # Valor padrão caso não tenha preço antigo
        
        # currentPrice
        new_element = item.select_one(".poly-price__current")
        if new_element:
            new_integer = new_element.select_one(".andes-money-amount__fraction").text.strip()
            cents_el = new_element.select_one(".andes-money-amount__cents")
            new_cents = cents_el.text.strip() if cents_el else '00'
            new_price_str = f"{new_integer},{new_cents}"
        else:
            return None # Se não tem preço atual, ignora o item
        
        image_tag = item.select_one(".poly-component__picture")
        image = image_tag["src"] if image_tag else ""

    except Exception as e: 
        print(f"Erro ao organizar item: {e}")
        return None # Retorna None para filtrar depois
    else:
         return {
            "product": title,
            "seller": "Vendido por: " + seller,
            "old_price": old_price_str,
            "current_price": new_price_str,
            "source": source,
            "img_link": image
        }

def connectDb():
    try:
        # SQLite conecta a um arquivo local (.db)
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
        
    except Exception as e: 
        raise e
    else:
        print("Conectado ao SQLite com sucesso")
        return conn, cursor

# --- INÍCIO DO PROCESSO ---

load_dotenv()
url = os.environ.get("URL", "https://www.mercadolivre.com.br/ofertas#nav-header") 

# Configurações do Chrome para rodar no Streamlit Cloud (Headless)
chrome_options = Options()
chrome_options.add_argument("--headless") # Obrigatório na nuvem
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
service = Service() 

print("Iniciando WebDriver...")
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Acessando {url}...")
    driver.get(url)
    time.sleep(3)

    # Scrolls
    driver.execute_script("window.scrollTo({ top: document.body.scrollHeight / 2, behavior: 'smooth' });")
    time.sleep(2)
    driver.execute_script("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });")
    time.sleep(2)

    # Pegando HTML
    # OBS: O seletor 'items-with-smart-groups' pode não existir dependendo da busca.
    # Tente pegar o body inteiro se falhar.
    try:
        element = driver.find_element(By.CLASS_NAME, 'items-with-smart-groups')
        html_base = element.get_attribute('outerHTML')
    except:
        print("Container específico não encontrado, pegando HTML total.")
        html_base = driver.page_source

finally:
    driver.quit()

# 2. Processando com BeautifulSoup
soup = BeautifulSoup(html_base, "lxml")

# Seletores do ML mudam com frequência, mantive o seu
items = soup.select(".andes-card.poly-card")

# Filtra itens None (que deram erro na função organize)
produtos = [organize(item) for item in items if organize(item) is not None]

if len(produtos) == 0:
    print("Nenhum produto encontrado. Verifique os seletores CSS.")
else:
    # Salvando itens num DF
    dataFrame_full = pd.DataFrame(produtos)

    # Limpeza de dados (Pandas)
    dataFrame_full["old_price"] = (
        dataFrame_full["old_price"]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    dataFrame_full["current_price"] = (
        dataFrame_full["current_price"]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    # Preparando dados para SQLite
    # Importante: A ordem das colunas no DF deve bater com a Query abaixo
    rows = list(
        dataFrame_full[["product", "old_price", "current_price", "seller", "source", "img_link"]]
        .itertuples(index=False, name=None)
    )

    # Query SQLite (Upsert)
    # ? é o placeholder do SQLite (no MySQL era %s)
    sql = """
    INSERT INTO products (product, old_price, current_price, seller, source, img_link)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(product, source) DO UPDATE SET
        current_price = excluded.current_price,
        created_at = CURRENT_TIMESTAMP
    """

    conn, cursor = connectDb()

    try:
        cursor.executemany(sql, rows)
        conn.commit()
        print(f"{cursor.rowcount} registros processados.")
    except Exception as e: 
        print(f"Erro ao salvar no banco: {e}")
    finally:
        cursor.close()
        conn.close()

print("Fim do scraping.")
