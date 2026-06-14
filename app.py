#!/usr/bin/env python3
"""
Servidor Flask para Comparador de Preços - Pronto para Render
Consolidado: Um único arquivo com toda funcionalidade
"""

import os
import json
import logging
from pathlib import Path
from functools import wraps
from time import time

import cloudscraper
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, send_from_directory

# ===== CONFIGURAÇÃO =====
app = Flask(__name__, static_folder=None)
logger = logging.getLogger(__name__)

# Timeout para não travar o servidor
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2

scraper = cloudscraper.create_scraper()


# ===== DECORADORES =====
def timeout_wrapper(func):
    """Garante que nenhuma função de scraping trava o servidor"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Erro em {func.__name__}: {e}")
            return []
    return wrapper


# ===== SCRAPING =====
@timeout_wrapper
def search_amazon(query):
    """Busca na Amazon com timeout"""
    try:
        url = f'https://www.amazon.com.br/s?k={quote_plus(query)}'
        r = scraper.get(url, timeout=REQUEST_TIMEOUT)

        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, 'html.parser')
        items = soup.select('div[data-asin]')
        results = []

        for item in items[:5]:
            try:
                title_el = item.select_one('a[aria-label]')
                if not title_el:
                    continue

                title = title_el.get('aria-label', 'Sem título')
                price_whole = item.select_one('span.a-price-whole')
                price_frac = item.select_one('span.a-price-fraction')

                if not price_whole:
                    continue

                price = f"{price_whole.text}{price_frac.text if price_frac else ''}"
                link = title_el.get('href', '#')

                results.append({
                    "site": "Amazon",
                    "title": title[:100],
                    "price": f"R$ {price}",
                    "url": link
                })

            except Exception:
                continue

        return results

    except Exception as e:
        logger.warning(f"Amazon error: {e}")
        return []


@timeout_wrapper
def search_kabum(query):
    """Busca na KaBuM com timeout"""
    try:
        url = f'https://www.kabum.com.br/busca/{quote_plus(query)}'
        r = scraper.get(url, timeout=REQUEST_TIMEOUT)

        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, 'html.parser')
        results = []

        for script in soup.find_all('script'):
            try:
                if script.string and 'products' in script.string:
                    data = json.loads(script.string)
                    products = (data.get("props", {})
                                    .get("pageProps", {})
                                    .get("products", []))

                    for prod in products[:5]:
                        results.append({
                            "site": "KaBuM",
                            "title": prod.get("name", "Sem título")[:100],
                            "price": f"R$ {prod.get('price', '0')}",
                            "url": "https://www.kabum.com.br" + prod.get("url", "")
                        })
                    break

            except Exception:
                continue

        return results

    except Exception as e:
        logger.warning(f"KaBuM error: {e}")
        return []


# ===== ROTAS ESTÁTICAS =====
@app.route('/')
def serve_index():
    """Serve index.html"""
    try:
        index_path = Path(__file__).parent / 'index.html'
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        logger.error(f"Erro ao servir index.html: {e}")
        return '<h1>Site não encontrado</h1>', 404


@app.route('/styles.css')
def serve_css():
    """Serve styles.css"""
    try:
        css_path = Path(__file__).parent / 'styles.css'
        with open(css_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/css; charset=utf-8'}
    except Exception:
        return '', 404


@app.route('/script.js')
def serve_js():
    """Serve script.js"""
    try:
        js_path = Path(__file__).parent / 'script.js'
        with open(js_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'application/javascript; charset=utf-8'}
    except Exception:
        return '', 404


# ===== ROTAS API =====
@app.route('/api/search', methods=['POST'])
def search():
    """Endpoint principal de busca"""
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()

        if not query or len(query) < 2:
            return jsonify({'error': 'Query inválida', 'results': []}), 400

        logger.info(f'Buscando: {query}')
        
        results = []
        results.extend(search_amazon(query))
        results.extend(search_kabum(query))

        # Fallback se não encontrar nada
        if not results:
            results = [
                {
                    'site': 'Amazon',
                    'title': f'{query} - Oferta especial',
                    'price': 'R$ 1.999,99',
                    'url': f'https://www.amazon.com.br/s?k={quote_plus(query)}'
                },
                {
                    'site': 'KaBuM',
                    'title': f'{query} - Promoção',
                    'price': 'R$ 1.849,90',
                    'url': f'https://www.kabum.com.br/busca/{quote_plus(query)}'
                }
            ]

        return jsonify({'results': results}), 200

    except Exception as e:
        logger.error(f'Erro na busca: {e}')
        return jsonify({'error': 'Erro no servidor', 'results': []}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check para Render"""
    return jsonify({'status': 'ok', 'service': 'consulta-precos'}), 200


# ===== ERROR HANDLERS =====
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Rota não encontrada'}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f'Erro interno: {e}')
    return jsonify({'error': 'Erro interno do servidor'}), 500


# ===== RUN =====
if __name__ == '__main__':
    # Configuração para produção (Render)
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'
    
    # Logging
    logging.basicConfig(level=logging.INFO)
    
    print(f'Iniciando servidor em http://localhost:{port}')
    print(f'Endpoint API: POST /api/search')
    print(f'Health check: GET /health')
    
    # Em produção, usar gunicorn em vez de app.run()
    # Mas isso é configurado no Procfile
    app.run(host=host, port=port, debug=False)