from flask import Flask, render_template
import mysql.connector
import subprocess

app = Flask(__name__)

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Tomato@mysql08",
        database="banco_dayve"
    )

@app.route("/")
def produtos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT product, old_price, current_price, seller, source, img_link, created_at
        FROM products
        ORDER BY created_at DESC
    """)
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("produtos.html", produtos=rows)
def br_currency(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def br_datetime(value):
    if not value:
        return ""
    return value.strftime("%d/%m/%Y %H:%M")

app.jinja_env.filters["br_datetime"] = br_datetime
app.jinja_env.filters["br_currency"] = br_currency

@app.route("/run-scraper")
def run_scraper():
    subprocess.run(["python", "scraper.py"])
    return "Scraper executado"

if __name__ == "__main__":
    app.run(debug=True)
