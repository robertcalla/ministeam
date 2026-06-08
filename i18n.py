"""Sistema de internacionalização do Ministeam.

- Tradução automática via deep-translator (Google) com cache em arquivo.
- Detecção de idioma com fallback robusto para strings curtas.
- Proteção de termos que não devem ser traduzidos: "Ministeam",
  nomes de jogos (do dict GAMES) e nomes de usuários (resolvidos sob demanda).
- Mapeia chaves do enum do projeto (portuguesBrasil, ingles, alemao, ...)
  para códigos ISO usados pelo Google Translate e bandeiras emoji.
"""

import os
import re
import threading

from deep_translator import GoogleTranslator
from langdetect import detect as _detect, DetectorFactory, LangDetectException

# Resultados determinísticos do langdetect (caso contrário varia entre runs).
DetectorFactory.seed = 0

# ---- MAPAS CÓDIGO ↔ GOOGLE ↔ BANDEIRA ↔ NOME ----
#
# Códigos internos curtos (BCP-47 simplificado, em minúsculas) usados em todos
# os arquivos de dados e na sessão. O Google Translate exige variantes
# específicas (ex.: 'zh-CN' com 'CN' maiúsculo), por isso temos um mapa
# CODIGO_PARA_GOOGLE separado.

CODIGO_PARA_GOOGLE = {
    'pt-br': 'pt',
    'en':    'en',
    'de':    'de',
    'zh-cn': 'zh-CN',
    'pl':    'pl',
    'ko':    'ko',
}

# Mapeia o que o langdetect devolve (ISO ou variantes regionais) para o nosso código.
GOOGLE_PARA_CODIGO = {
    'pt':    'pt-br',
    'pt-BR': 'pt-br',
    'en':    'en',
    'de':    'de',
    'zh':    'zh-cn',
    'zh-CN': 'zh-cn',
    'zh-TW': 'zh-cn',
    'pl':    'pl',
    'ko':    'ko',
}

BANDEIRA = {
    'pt-br': '🇧🇷',
    'en':    '🇺🇸',
    'de':    '🇩🇪',
    'zh-cn': '🇨🇳',
    'pl':    '🇵🇱',
    'ko':    '🇰🇷',
}

NOME = {
    'pt-br': 'Português (Brasil)',
    'en':    'Inglês',
    'de':    'Alemão',
    'zh-cn': 'Chinês Simplificado',
    'pl':    'Polonês',
    'ko':    'Coreano',
}

# Aliases dos nomes antigos para retrocompatibilidade em arquivos legados.
ALIASES_LEGADOS = {
    'portuguesBrasil':    'pt-br',
    'ingles':             'en',
    'alemao':             'de',
    'chinesSimplificado': 'zh-cn',
    'polones':             'pl',
    'coreano':             'ko',
}

IDIOMAS_SUPORTADOS = list(CODIGO_PARA_GOOGLE.keys())
IDIOMA_PADRAO = 'pt-br'


def normalizar_codigo(valor):
    """Aceita o código novo ('pt-br') ou um alias legado ('portuguesBrasil')."""
    if not valor:
        return IDIOMA_PADRAO
    v = str(valor).strip()
    if v in CODIGO_PARA_GOOGLE:
        return v
    if v in ALIASES_LEGADOS:
        return ALIASES_LEGADOS[v]
    # Normaliza case-insensitive (ex.: 'PT-BR', 'Zh-Cn').
    v_lower = v.lower()
    if v_lower in CODIGO_PARA_GOOGLE:
        return v_lower
    return IDIOMA_PADRAO

# Termos que nunca devem ser traduzidos.
TERMOS_PROTEGIDOS_GLOBAIS = {'Ministeam', 'MINISTEAM'}


# ---- CACHE EM ARQUIVO ----

_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CACHE_FILE = os.path.join(_DATA_DIR, 'traducoes_cache.txt')

_CACHE_LOCK = threading.Lock()
_CACHE = None  # dict: (idioma_destino, texto_origem) -> texto_traduzido


def _carregar_cache():
    """Lê o cache do disco. Formato: idioma_destino | texto_origem || texto_traduzido"""
    global _CACHE
    _CACHE = {}
    if not os.path.exists(CACHE_FILE):
        return
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.rstrip('\n')
                if not s or s.startswith('#'):
                    continue
                # Separador inicial: "idioma | resto"
                if ' | ' not in s:
                    continue
                idioma, resto = s.split(' | ', 1)
                # Separador entre origem e tradução: " || "
                if ' || ' not in resto:
                    continue
                origem, traducao = resto.split(' || ', 1)
                _CACHE[(idioma.strip(), _unescape(origem))] = _unescape(traducao)
    except OSError:
        pass


def _persistir_entrada(idioma_destino, origem, traducao):
    """Anexa uma entrada ao arquivo de cache."""
    if not os.path.exists(_DATA_DIR):
        os.makedirs(_DATA_DIR)
    nova_linha = (
        f"{idioma_destino} | {_escape(origem)} || {_escape(traducao)}\n"
    )
    existe = os.path.exists(CACHE_FILE)
    with open(CACHE_FILE, 'a', encoding='utf-8') as f:
        if not existe:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Cache de Traduções\n")
            f.write("# Formato: idioma_destino | texto_origem || texto_traduzido\n")
            f.write("# Quebras de linha e pipes escapados como \\n e \\|\n")
            f.write("# =============================================================================\n")
        f.write(nova_linha)


def _escape(s):
    return (s.replace('\\', '\\\\')
             .replace('\n', '\\n')
             .replace('\r', '')
             .replace('|', '\\|'))


def _unescape(s):
    # Ordem importa para não desescapar pipe escapado como \|
    out = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == 'n':
                out.append('\n'); i += 2; continue
            if nxt == '|':
                out.append('|'); i += 2; continue
            if nxt == '\\':
                out.append('\\'); i += 2; continue
        out.append(s[i]); i += 1
    return ''.join(out)


# ---- PROTEÇÃO DE TERMOS ----

_TOKEN_PATTERN = re.compile(r'__MTSTKN_(\d+)__')


def _termos_protegidos_runtime():
    """Coleta nomes que não devem ser traduzidos: GAMES + usuários + publishers.

    Importação tardia para evitar import circular com app.py.
    """
    termos = set(TERMOS_PROTEGIDOS_GLOBAIS)
    try:
        from app import GAMES, ler_usuarios
        for g in GAMES.values():
            if g.get('name'):
                termos.add(g['name'])
            if g.get('publisher'):
                termos.add(g['publisher'])
            if g.get('developer'):
                termos.add(g['developer'])
        for u in ler_usuarios():
            if u.get('nome'):
                termos.add(u['nome'])
            if u.get('username'):
                termos.add(u['username'])
    except Exception:
        pass
    # Ordena por comprimento desc para evitar matches parciais.
    return sorted(termos, key=len, reverse=True)


def _proteger(texto):
    """Substitui termos protegidos por tokens. Retorna (texto_protegido, mapa)."""
    mapa = {}
    if not texto:
        return texto, mapa
    for i, termo in enumerate(_termos_protegidos_runtime()):
        if termo and termo in texto:
            token = f"__MTSTKN_{i}__"
            mapa[token] = termo
            texto = texto.replace(termo, token)
    return texto, mapa


def _desproteger(texto, mapa):
    if not mapa:
        return texto
    # Google às vezes adiciona espaços ou muda case do token; ignora variantes.
    def restaurar(match):
        token = match.group(0)
        # tenta exato primeiro, depois fuzzy via número
        if token in mapa:
            return mapa[token]
        num = match.group(1)
        for k, v in mapa.items():
            if k.endswith(f"_{num}__"):
                return v
        return token
    return _TOKEN_PATTERN.sub(restaurar, texto)


# ---- DETECÇÃO DE IDIOMA ----

def detectar_idioma(texto):
    """Retorna o código interno (ex.: 'en') ou IDIOMA_PADRAO se não detectar."""
    if not texto or not texto.strip():
        return IDIOMA_PADRAO
    try:
        iso = _detect(texto)
    except LangDetectException:
        return IDIOMA_PADRAO
    if iso in GOOGLE_PARA_CODIGO:
        return GOOGLE_PARA_CODIGO[iso]
    # Reduz variante regional (ex.: 'pt-BR' -> 'pt')
    base = iso.split('-')[0]
    return GOOGLE_PARA_CODIGO.get(base, IDIOMA_PADRAO)


# ---- TRADUÇÃO COM CACHE ----

def traduzir(texto, idioma_destino, idioma_origem=None):
    """Traduz `texto` para `idioma_destino` (código interno, ex.: 'en').

    Aceita também aliases legados ('portuguesBrasil', ...) e normaliza.
    Se origem == destino ou o texto for vazio, devolve o original.
    Termos protegidos (Ministeam, nomes de jogos/usuários) são preservados.
    """
    if not texto or not texto.strip():
        return texto
    idioma_destino = normalizar_codigo(idioma_destino)
    idioma_origem  = normalizar_codigo(idioma_origem) if idioma_origem else None
    if idioma_destino == idioma_origem:
        return texto
    if idioma_destino not in CODIGO_PARA_GOOGLE:
        return texto

    global _CACHE
    if _CACHE is None:
        with _CACHE_LOCK:
            if _CACHE is None:
                _carregar_cache()

    chave = (idioma_destino, texto)
    if chave in _CACHE:
        return _CACHE[chave]

    iso_destino = CODIGO_PARA_GOOGLE[idioma_destino]
    iso_origem  = CODIGO_PARA_GOOGLE.get(idioma_origem, 'auto')

    texto_protegido, mapa = _proteger(texto)
    try:
        traduzido = GoogleTranslator(source=iso_origem, target=iso_destino).translate(texto_protegido)
        if not traduzido:
            traduzido = texto
        else:
            traduzido = _desproteger(traduzido, mapa)
    except Exception:
        # Sem internet ou erro de API: devolve o original e NÃO cacheia.
        return texto

    with _CACHE_LOCK:
        _CACHE[chave] = traduzido
        _persistir_entrada(idioma_destino, texto, traduzido)
    return traduzido


def bandeira(idioma):
    """Retorna a bandeira emoji do idioma."""
    return BANDEIRA.get(normalizar_codigo(idioma), '🌐')


def nome_idioma(idioma):
    return NOME.get(normalizar_codigo(idioma), idioma)
