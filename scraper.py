import time
import os
import sqlite3
import sys
import requests
from bs4 import BeautifulSoup

# Configuração de Encoding para logs
sys.stdout.reconfigure(encoding='utf-8')

def setup_db():
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
    return conn

def clean_price(price_str):
    # O site usa libras (£), vamos limpar
    if not price_str: return 0.0
    try:
        clean = price_str.replace("£", "").replace("Â", "").strip()
        return float(clean)
    except:
        return 0.0

def run_scraper():
    print("--- INICIANDO SCRAPER (BOOKS DEMO) ---")
    
    # URL de teste oficial para scrapers (Categoria Travel)
    url = "http://books.toscrape.com/catalogue/category/books/travel_2/index.html"
    print(f"Alvo: {url}")

    try:
        # Usamos requests direto pois o site é estático (mais rápido e leve que Selenium)
        response = requests.get(url)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"Erro ao acessar site: Status {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "lxml")
        items = soup.select("article.product_pod")
        
        print(f"Livros encontrados: {len(items)}")

        produtos_processados = []

        for item in items:
            try:
                # Título e Link
                h3 = item.select_one("h3 a")
                title = h3['title']
                link_rel = h3['href']
                # Ajusta o link relativo para absoluto
                link = f"http://books.toscrape.com/catalogue/category/books/travel_2/{link_rel}"
                
                # Preço
                price_tag = item.select_one(".price_color")
                price_val = clean_price(price_tag.text)
                
                # Imagem
                img_tag = item.select_one("img.thumbnail")
                img_rel = img_tag['src']
                # Ajusta link da imagem
                img_link = f"http://books.toscrape.com/catalogue/category/books/travel_2/{img_rel}"
                img_link = img_link.replace("../../../../", "http://books.toscrape.com/")

                # Estoque/Vendedor
                stock = item.select_one(".instock.availability").text.strip()

                # Adiciona na lista (simulando preço antigo sendo 10% maior só para visual)
                produtos_processados.append((
                    title, 
                    stock,        # Usamos estoque no lugar de vendedor
                    price_val * 1.1, # Preço "antigo" fictício
                    price_val,    # Preço atual
                    link, 
                    img_link
                ))
                
            except Exception as e:
                print(f"Erro ao processar item: {e}")
                continue

        if produtos_processados:
            conn = setup_db()
            cursor = conn.cursor()
            
            sql = """
            INSERT INTO products (product, seller, old_price, current_price, source, img_link)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(product, source) DO UPDATE SET
                current_price = excluded.current_price,
                created_at = CURRENT_TIMESTAMP
            """
            cursor.executemany(sql, produtos_processados)
            conn.commit()
            conn.close()
            print(f"SUCESSO! {len(produtos_processados)} livros salvos no banco.")
        else:
            print("Nenhum dado extraído.")

    except Exception as e:
        print(f"Erro crítico: {e}")

if __name__ == "__main__":
    run_scraper()
