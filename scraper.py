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

# Tente importar o stealth. Se não tiver, avisa, mas tenta rodar sem.
try:
    from selenium_stealth import stealth
except ImportError:
    print("AVISO: 'selenium-stealth' não instalado. Adicione ao requirements.txt para evitar bloqueios.")
    stealth = None

# Configuração para logs no Streamlit
sys.stdout.reconfigure(encoding='utf-8')

# --- FUNÇÃO DE ORGANIZAÇÃO (Mais robusta) ---
def organize(item):
    try:
        # Tenta pegar título e link (suporta layout Novo e Antigo)
        title_tag = item.select_one(".poly-component__title, .ui-search-item__title, a.ui-search-link")
        if not title_tag:
            # Fallback: tenta achar qualquer link dentro do card
            title_tag = item.select_one("a")
        
        if not title_tag: return None

        title = title_tag.get_text(strip=True) or title_tag.get("title")
        source = title_tag.get("href")

        # Vendedor
        seller_tag = item.select_one(".poly-component__seller, .ui-search-official-store-label")
        seller = seller_tag.text.strip() if seller_tag else 'Não informado'
        
        # Preços (Lógica unificada)
        # O seletor .andes-money-amount__fraction costuma ser universal no ML
        price_tag = item.select_one(".andes-money-amount__fraction")
        
        # Se não tiver preço (ex: anúncio de catálogo), ignoramos
        if not price_tag:
            return None

        # Monta o preço atual
        current_integer = price_tag.text.strip()
        cents_el = item.select_one(".andes-money-amount__cents")
        current_cents = cents_el.text.strip() if cents_el else '00'
        new_price_str = f"{current_integer},{current_cents}"

        # Preço antigo (Se houver riscado)
        # Procuramos um container de preço anterior
        old_price_str = "0,00"
        # Lógica simplificada: se houver dois preços, o primeiro costuma ser o antigo
        prices = item.select(".andes-money-amount__fraction")
        if len(prices) > 1:
            old_integer = prices[0].text.strip()
            # Tenta achar centavos próximos
            old_price_str = f"{old_integer},00" 

        # Imagem (Lazy load e src normal)
        image_tag = item.select_one("img")
        image = ""
        if image_tag:
            image = image_tag.get("data-src") or image_tag.get("src")

    except Exception as e: 
        # print(f"Erro leve ao organizar item: {e}")
        return None 
    else:
         return {
            "product": title,
            "seller": seller,
            "old_price": old_price_str,
            "current_price": new_price_str,
            "source": source,
            "img_link": image
        }

# --- CONEXÃO SQLITE ---
def connectDb():
    try:
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
    except Exception as e: 
        raise e
    else:
        print("Conectado ao SQLite com sucesso")
        return conn, cursor

# --- INÍCIO DO PROCESSO ---

load_dotenv()
# URL padrão para testes caso a ENV falhe
url = os.environ.get("URL", "https://www.mercadolivre.com.br/ofertas#nav-header") 

print("--- INICIANDO SCRAPER (HEADLESS NEW) ---")

# 1. CONFIGURAÇÃO DO CHROME (Ajuste Crítico)
chrome_options = Options()

# O SEGREDO: Use --headless=new em vez de --headless
chrome_options.add_argument("--headless=new") 

# Configurações para rodar no Linux/Streamlit Cloud
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080") # Janela grande evita layout mobile
chrome_options.add_argument("--ignore-certificate-errors")

# User-Agent Fixo (Finge ser Windows 10)
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

service = Service() 
driver = webdriver.Chrome(service=service, options=chrome_options)

# 2. CAMUFLAGEM (Stealth)
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
    time.sleep(3) # Tempo inicial de carga

    # Verifica título para saber se foi bloqueado
    print(f"Título da página: {driver.title}")

    # Scrolls para carregar imagens (Lazy Load)
    driver.execute_script("window.scrollTo(0, 1000);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # Pegando HTML Total
    html_base = driver.page_source

finally:
    driver.quit()

# 3. Processando com BeautifulSoup
soup = BeautifulSoup(html_base, "lxml")

# --- ESTRATÉGIA DE SELETORES MÚLTIPLOS ---
# Tenta layout novo (Poly), depois lista (Search), depois genérico (Andes)
items = soup.select("div.poly-card")
if not items:
    items = soup.select("li.ui-search-layout__item")
if not items:
    items = soup.select("div.andes-card")

print(f"Itens encontrados no HTML: {len(items)}")

produtos = [organize(item) for item in items if organize(item) is not None]

if len(produtos) == 0:
    print("⚠️ Nenhum produto estruturado foi extraído. O HTML pode ter mudado ou houve bloqueio.")
else:
    # Salvando itens num DF
    dataFrame_full = pd.DataFrame(produtos)

    # Limpeza de dados
    # Converter strings "1.200,50" para float
    for col in ["old_price", "current_price"]:
        dataFrame_full[col] = (
            dataFrame_full[col]
            .astype(str) # Garante que é string antes de replace
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        # Converte para float, transformando erros em NaN e depois em 0
        dataFrame_full[col] = pd.to_numeric(dataFrame_full[col], errors='coerce').fillna(0.0)

    # Preparando dados para SQLite
    rows = list(
        dataFrame_full[["product", "old_price", "current_price", "seller", "source", "img_link"]]
        .itertuples(index=False, name=None)
    )

    # Query SQLite (Upsert)
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
        print(f"✅ SUCESSO: {cursor.rowcount} produtos processados/atualizados.")
    except Exception as e: 
        print(f"❌ Erro ao salvar no banco: {e}")
    finally:
        cursor.close()
        conn.close()

print("Fim do scraping.")

