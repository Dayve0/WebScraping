import time
import os
import sqlite3
import sys
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Tente importar o stealth
try:
    from selenium_stealth import stealth
except ImportError:
    print("AVISO: 'selenium-stealth' não instalado.")
    stealth = None

sys.stdout.reconfigure(encoding='utf-8')

# --- FUNÇÃO DE ORGANIZAÇÃO (Com Limpeza de URL) ---
def organize(item):
    try:
        # Tenta pegar título e link
        title_tag = item.select_one(".poly-component__title, .ui-search-item__title, a.ui-search-link")
        if not title_tag:
            title_tag = item.select_one("a")
        
        if not title_tag: return None

        title = title_tag.get_text(strip=True) or title_tag.get("title")
        raw_source = title_tag.get("href")

        # --- CORREÇÃO 1: LIMPEZA DE URL ---
        # Remove parâmetros de rastreamento (?tracking_id=...) e âncoras (#position=...)
        if raw_source:
            source = raw_source.split('?')[0].split('#')[0]
        else:
            return None

        # Vendedor
        seller_tag = item.select_one(".poly-component__seller, .ui-search-official-store-label")
        seller = seller_tag.text.strip() if seller_tag else 'Não informado'
        
        # Preços
        prices = item.select(".andes-money-amount__fraction")
        cents = item.select(".andes-money-amount__cents")
        if not prices: return None
        
        old_integer = prices[0].text.strip()
        old_cents = cents[0].text.strip() if cents[0] else '00'
        old_price_str = f"{old_integer},{old_cents}"

        current_integer = prices[1].text.strip()
        current_cents = cents[1].text.strip() if cents[1] else '00'
        new_price_str = f"{current_integer},{current_cents}"
        
        image_tag = item.select_one("img")
        image = ""
        if image_tag:
            image = image_tag.get("data-src") or image_tag.get("src")

    except Exception as e: 
        return None 
    else:
         return {
            "product": title,
            "seller": seller,
            "old_price": old_price_str,
            "current_price": new_price_str,
            "source": source, # URL Limpa
            "img_link": image
        }

# --- CONEXÃO SQLITE ---
def connectDb():
    try:
        conn = sqlite3.connect('dados.db')
        cursor = conn.cursor()

        # A constraint UNIQUE impede duplicatas no nível do Banco
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
        return conn, cursor

# --- INÍCIO DO PROCESSO ---

load_dotenv()
url = os.environ.get("URL", "https://www.mercadolivre.com.br/ofertas#nav-header") 

print("--- INICIANDO SCRAPER ---")

chrome_options = Options()
chrome_options.add_argument("--headless=new") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--ignore-certificate-errors")

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

service = Service() 
driver = webdriver.Chrome(service=service, options=chrome_options)

if stealth:
    stealth(driver,
        languages=["pt-BR", "pt"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

try:
    print(f"Acessando {url}...")
    driver.get(url)
    time.sleep(3)

    driver.execute_script("window.scrollTo(0, 1000);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    html_base = driver.page_source

finally:
    driver.quit()

soup = BeautifulSoup(html_base, "lxml")

items = soup.select("div.poly-card")
if not items:
    items = soup.select("li.ui-search-layout__item")
if not items:
    items = soup.select("div.andes-card")

print(f"Itens encontrados no HTML: {len(items)}")

produtos = [organize(item) for item in items if organize(item) is not None]

if len(produtos) == 0:
    print("⚠️ Nenhum produto extraído.")
else:
    dataFrame_full = pd.DataFrame(produtos)

    # --- CORREÇÃO 2: REMOVER DUPLICATAS DO DATAFRAME ATUAL ---
    # Se na mesma página tiver o mesmo produto 2 vezes, removemos antes de salvar
    dataFrame_full.drop_duplicates(subset=['source'], inplace=True)

    for col in ["old_price", "current_price"]:
        dataFrame_full[col] = (
            dataFrame_full[col]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        dataFrame_full[col] = pd.to_numeric(dataFrame_full[col], errors='coerce').fillna(0.0)

    rows = list(
        dataFrame_full[["product", "old_price", "current_price", "seller", "source", "img_link"]]
        .itertuples(index=False, name=None)
    )

    # O SQL abaixo atualiza o preço se o produto (link limpo) já existir
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
        print(f"✅ SUCESSO: {cursor.rowcount} produtos processados.")
    except Exception as e: 
        print(f"❌ Erro ao salvar no banco: {e}")
    finally:
        cursor.close()
        conn.close()

print("Fim do scraping.")
