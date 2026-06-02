"""Pré-aquece o cache de traduções para todas as strings dinâmicas que
podem aparecer na UI (tags, gêneros, descrições dos jogos e outras).

Roda só o que está faltando — não retraduz o que já está em cache.
"""
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import i18n
from app import GAMES, app


def coletar_strings():
    """Coleta strings traduzíveis: GAMES + qualquer string de UI extra."""
    strings = set()
    for g in GAMES.values():
        if g.get('description'):
            strings.add(g['description'])
        if g.get('long_description'):
            strings.add(g['long_description'])
        for t in g.get('tags', []):
            strings.add(t)
        for genre in g.get('genres', []):
            strings.add(genre)
        for f in g.get('features', []):
            strings.add(f)
        if g.get('reviews'):
            strings.add(g['reviews'])
        if g.get('req_minimo'):
            strings.add(g['req_minimo'])
        if g.get('req_recomendado'):
            strings.add(g['req_recomendado'])
        for lang in g.get('languages', []):
            strings.add(lang)
    return sorted(strings)


def main():
    i18n._carregar_cache()
    strings = coletar_strings()
    idiomas_destino = [c for c in i18n.IDIOMAS_SUPORTADOS if c != i18n.IDIOMA_PADRAO]
    pendentes = [
        (idioma, texto)
        for idioma in idiomas_destino
        for texto in strings
        if (idioma, texto) not in i18n._CACHE
    ]
    total = len(pendentes)
    if total == 0:
        print("Nada para traduzir — cache já cobre todas as strings.")
        return
    print(f"Strings únicas: {len(strings)}")
    print(f"Idiomas alvo: {idiomas_destino}")
    print(f"Pendentes: {total} traduções")
    inicio = time.time()
    feitos = 0
    falhas = 0
    with app.app_context():
        for idioma, texto in pendentes:
            try:
                i18n.traduzir(texto, idioma, idioma_origem=i18n.IDIOMA_PADRAO)
            except Exception as e:
                falhas += 1
            feitos += 1
            if feitos % 25 == 0:
                elapsed = time.time() - inicio
                print(f"  {feitos}/{total} ({elapsed:.1f}s) — falhas: {falhas}")
    elapsed = time.time() - inicio
    print(f"Concluído em {elapsed:.1f}s. Falhas: {falhas}")


if __name__ == '__main__':
    main()
