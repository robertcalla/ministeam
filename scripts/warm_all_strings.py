"""Pré-aquece o cache de traduções para TODAS as strings traduzíveis do projeto:

- Strings literais `{{ "..."|t }}` em templates Jinja
- Strings de `flash(...)` em app.py (incluindo f-strings sem variáveis)
- Strings de GAMES (tags, gêneros, descrições, features, requisitos)

Roda só o que está faltando — não retraduz o que já está em cache.
"""
import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n
from app import GAMES, app


TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
APP_FILE      = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')


# Captura {{ "..."|t }} e {{ '...'|t }} (com qualquer whitespace)
T_FILTER = re.compile(r'\{\{\s*([\'"])(.+?)\1\s*\|\s*t\b')

# Captura flash("...", "...") e flash('...', '...')
FLASH = re.compile(r'flash\s*\(\s*([\'"])(.+?)\1\s*,')


def coletar_strings_templates():
    strings = set()
    for nome in os.listdir(TEMPLATES_DIR):
        if not nome.endswith('.html'):
            continue
        caminho = os.path.join(TEMPLATES_DIR, nome)
        with open(caminho, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        for m in T_FILTER.finditer(conteudo):
            texto = m.group(2)
            if texto and not texto.startswith('{') and '{{' not in texto and '{%' not in texto:
                # Ignora interpolação Jinja dentro de strings
                strings.add(texto)
    return strings


def coletar_strings_flash():
    strings = set()
    with open(APP_FILE, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    for m in FLASH.finditer(conteudo):
        texto = m.group(2)
        # Pula strings que dependem de interpolação (f-strings têm {})
        if '{' not in texto and texto:
            strings.add(texto)
    return strings


def coletar_strings_games():
    strings = set()
    for g in GAMES.values():
        for k in ('description', 'long_description', 'reviews', 'req_minimo', 'req_recomendado'):
            v = g.get(k)
            if v:
                strings.add(v)
        for lista_k in ('tags', 'genres', 'features', 'languages'):
            for v in g.get(lista_k, []):
                if v:
                    strings.add(v)
    return strings


def main():
    i18n._carregar_cache()
    templates = coletar_strings_templates()
    flash_msgs = coletar_strings_flash()
    games = coletar_strings_games()
    todas = templates | flash_msgs | games
    print(f"Strings de templates: {len(templates)}")
    print(f"Strings de flash:     {len(flash_msgs)}")
    print(f"Strings de GAMES:     {len(games)}")
    print(f"Total únicas:         {len(todas)}")

    idiomas_destino = [c for c in i18n.IDIOMAS_SUPORTADOS if c != i18n.IDIOMA_PADRAO]
    pendentes = [
        (idioma, texto)
        for idioma in idiomas_destino
        for texto in todas
        if (idioma, texto) not in i18n._CACHE
    ]
    print(f"Idiomas alvo: {idiomas_destino}")
    print(f"Pendentes: {len(pendentes)}")

    if not pendentes:
        print("Nada para traduzir.")
        return

    inicio = time.time()
    feitos, falhas = 0, 0
    with app.app_context():
        for idioma, texto in pendentes:
            try:
                i18n.traduzir(texto, idioma, idioma_origem=i18n.IDIOMA_PADRAO)
            except Exception:
                falhas += 1
            feitos += 1
            if feitos % 25 == 0:
                print(f"  {feitos}/{len(pendentes)} ({time.time()-inicio:.1f}s) — falhas: {falhas}")
    print(f"Concluído em {time.time()-inicio:.1f}s. Falhas: {falhas}")


if __name__ == '__main__':
    main()
