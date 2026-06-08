from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from jinja2 import pass_context
from datetime import datetime
import os
import json
import random
import re

import i18n

app = Flask(__name__)
app.secret_key = 'chave_secreta_super_segura'


# ---- INTERNACIONALIZAÇÃO ----

def _idioma_usuario():
    """Idioma atual de quem está vendo a tela.

    Prioridade:
      1) sessão (usuário logado escolheu)
      2) configuração da máquina (maquina.txt) — usada antes do login também
      3) padrão (pt-br)

    Lê fresco a cada chamada porque `g` em alguns contextos (test/repl) é
    compartilhado entre requests, e cachear ali manteria um valor antigo
    quando o usuário trocou de idioma. A lookup é barata: dict + uma leitura
    de arquivo curta no caminho do "não logado".
    """
    profile = session.get('user_profile') or {}
    idioma = profile.get('linguagem')
    if idioma:
        return idioma
    try:
        return ler_linguagem_maquina() or i18n.IDIOMA_PADRAO
    except Exception:
        return i18n.IDIOMA_PADRAO


@app.template_filter('t')
@pass_context
def _filter_t(ctx, texto):
    """Filtro Jinja: traduz `texto` (PT-BR) para o idioma do usuário atual.

    `@pass_context` é essencial: sem ele, o Jinja faz constant folding em
    expressões como `{{ "literal"|t }}` no momento da compilação do
    template, congelando a tradução no idioma da primeira renderização.
    """
    if texto is None:
        return texto
    destino = _idioma_usuario()
    if destino == i18n.IDIOMA_PADRAO:
        return texto
    return i18n.traduzir(str(texto), destino, idioma_origem=i18n.IDIOMA_PADRAO)


@app.template_filter('traduzir_aval')
@pass_context
def _filter_traduzir_aval(ctx, texto, idioma_origem):
    """Filtro Jinja: traduz uma avaliação do `idioma_origem` para o idioma do usuário."""
    if texto is None:
        return texto
    destino = _idioma_usuario()
    if destino == idioma_origem:
        return texto
    return i18n.traduzir(str(texto), destino, idioma_origem=idioma_origem)


@app.template_filter('bandeira')
@pass_context
def _filter_bandeira(ctx, idioma_enum):
    return i18n.bandeira(idioma_enum)


@app.after_request
def _impedir_cache_html(response):
    """Impede o navegador de servir uma versão antiga de HTML após troca de idioma.

    Sem isso, ao mudar de idioma e voltar via histórico, o browser pode
    exibir uma renderização antiga ou misturar partes em outro idioma.
    Só afeta text/html — assets estáticos seguem cacheáveis.
    """
    ctype = response.content_type or ''
    if ctype.startswith('text/html'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


@app.context_processor
def _injetar_i18n():
    return {
        'lang_user':         _idioma_usuario(),
        'idiomas_suportados': i18n.IDIOMAS_SUPORTADOS,
        'nome_idioma':       i18n.nome_idioma,
        'bandeira_idioma':   i18n.bandeira,
    }

# ---- CATÁLOGO DE JOGOS (DADOS FIXOS) ----
# As informações abaixo são fictícias e podem ser editadas manualmente.
GAMES = {
    '1': {
        'id': '1', 'name': 'Aventura Épica', 'price': 150.00, 'age_rating': 10,
        'description': 'Explore masmorras e derrote monstros com amigos nesta jornada incrível.',
        'developer': 'Mythic Forge Studios',
        'publisher': 'MINIntendo',
        'release_date': '15 de março de 2024',
        'genres': ['RPG', 'Ação', 'Aventura', 'Cooperativo'],
        'tags': ['Mundo Aberto', 'Fantasia', 'Multijogador', 'Masmorras', 'História Rica'],
        'features': ['Um jogador', 'Cooperativo online', 'Conquistas Steam', 'Nuvem Steam', 'Suporte a controle'],
        'long_description': (
            'Aventura Épica leva você a um vasto mundo de fantasia repleto de masmorras sombrias, '
            'chefes colossais e tesouros lendários. Forme um grupo com até quatro amigos, personalize '
            'seu herói com centenas de habilidades e enfrente uma campanha épica de mais de 60 horas. '
            'Cada masmorra é gerada com desafios únicos, garantindo que nenhuma jornada seja igual.'
        ),
        'reviews': 'Muito positivas', 'review_count': 12480,
        'languages': ['Português', 'Inglês', 'Espanhol', 'Francês', 'Alemão'],
        'req_minimo': 'SO: Windows 10 64-bit · CPU: Intel i5-4460 · RAM: 8 GB · GPU: GTX 760 · 40 GB',
        'req_recomendado': 'SO: Windows 11 64-bit · CPU: Intel i7-9700 · RAM: 16 GB · GPU: RTX 2060 · 40 GB SSD',
    },
    '2': {
        'id': '2', 'name': 'Sobrevivência Sombria', 'price': 90.00, 'age_rating': 18,
        'description': 'Jogo de terror com zumbis. Sobreviva a noites aterrorizantes com recursos escassos.',
        'developer': 'Nightfall Interactive',
        'publisher': 'MINIcraft',
        'release_date': '31 de outubro de 2023',
        'genres': ['Terror', 'Sobrevivência', 'Ação', 'Mundo Aberto'],
        'tags': ['Zumbis', 'Survival Horror', 'Crafting', 'Atmosférico', 'Difícil', 'Multijogador'],
        'features': ['Um jogador', 'Cooperativo online', 'Conquistas Steam', 'Nuvem Steam'],
        'long_description': (
            'Sobrevivência Sombria coloca você em uma cidade devastada por uma praga implacável. '
            'Gerencie recursos escassos, fabrique armas improvisadas e fortifique seu esconderijo '
            'antes que a noite chegue. Cada decisão importa: o som de um tiro pode atrair hordas '
            'inteiras. Sozinho ou com amigos, até onde você irá para ver o amanhecer?'
        ),
        'reviews': 'Extremamente positivas', 'review_count': 28930,
        'languages': ['Português', 'Inglês', 'Espanhol', 'Russo', 'Japonês'],
        'req_minimo': 'SO: Windows 10 64-bit · CPU: Ryzen 3 1200 · RAM: 8 GB · GPU: GTX 1050 Ti · 50 GB',
        'req_recomendado': 'SO: Windows 11 64-bit · CPU: Ryzen 5 5600 · RAM: 16 GB · GPU: RTX 3060 · 50 GB SSD',
    },
    '3': {
        'id': '3', 'name': 'Corrida Divertida', 'price': 45.00, 'age_rating': 0,
        'description': 'Corridas para toda a família. Karts coloridos e pistas malucas!',
        'developer': 'Sunny Lab',
        'publisher': 'MINIntendo',
        'release_date': '5 de junho de 2022',
        'genres': ['Corrida', 'Casual', 'Família', 'Arcade'],
        'tags': ['Karts', 'Festa', 'Colorido', 'Multijogador Local', 'Fácil de Aprender'],
        'features': ['Um jogador', 'Multijogador local', 'Tela dividida', 'Conquistas Steam', 'Suporte total a controle'],
        'long_description': (
            'Corrida Divertida é o party game definitivo para toda a família! Escolha entre dezenas '
            'de personagens carismáticos, dispute pistas malucas cheias de atalhos secretos e use '
            'power-ups hilários para virar a corrida no último segundo. Jogue em tela dividida com '
            'até quatro pessoas no mesmo sofá.'
        ),
        'reviews': 'Positivas', 'review_count': 5310,
        'languages': ['Português', 'Inglês', 'Espanhol', 'Italiano'],
        'req_minimo': 'SO: Windows 10 64-bit · CPU: Intel i3-6100 · RAM: 4 GB · GPU: GTX 650 · 15 GB',
        'req_recomendado': 'SO: Windows 10 64-bit · CPU: Intel i5-7400 · RAM: 8 GB · GPU: GTX 1050 · 15 GB SSD',
    },
    '4': {
        'id': '4', 'name': 'Lombriguinha', 'price': 120.00, 'age_rating': 16,
        'description': 'Jogo de combate de guerra com os amigos. Que vença a lombriguinha melhor!',
        'developer': 'Worm Wars Studio',
        'publisher': 'MINIteam67',
        'release_date': '10 de janeiro de 2025',
        'genres': ['Ação', 'Estratégia', 'Multijogador', 'Tático'],
        'tags': ['Combate', 'Guerra', 'Multijogador', 'Estratégico', 'Competitivo', 'Engraçado'],
        'features': ['Multijogador online', 'Cooperativo online', 'Conquistas Steam', 'Nuvem Steam', 'Suporte a controle'],
        'long_description': (
            'Lombriguinha é um jogo de combate de guerra hilário e estratégico onde você comanda '
            'um exército de lombrigas armadas até os dentes. Enfrente seus amigos em batalhas '
            'táticas por turnos em cenários destrutíveis, use um arsenal absurdo de armas '
            'criativas e prove que a sua lombriguinha é a melhor do campo de batalha!'
        ),
        'reviews': 'Muito positivas', 'review_count': 3210,
        'languages': ['Português', 'Inglês', 'Espanhol', 'Francês'],
        'req_minimo': 'SO: Windows 10 64-bit · CPU: Intel i3-7100 · RAM: 4 GB · GPU: GTX 750 · 10 GB',
        'req_recomendado': 'SO: Windows 11 64-bit · CPU: Intel i5-9400 · RAM: 8 GB · GPU: GTX 1060 · 10 GB SSD',
    }
}

# ==============================================================================
# BANCO DE DADOS EM ARQUIVO DE TEXTO
# ==============================================================================
DATA_DIR        = os.path.join(os.path.dirname(__file__), 'data')
USUARIOS_FILE   = os.path.join(DATA_DIR, 'usuarios.txt')
MAQUINA_FILE    = os.path.join(DATA_DIR, 'maquina.txt')
AMIZADES_FILE   = os.path.join(DATA_DIR, 'amizades.txt')
BIBLIOTECA_FILE = os.path.join(DATA_DIR, 'biblioteca.txt')
FAMILIAS_FILE   = os.path.join(DATA_DIR, 'familias.txt')
CARTEIRAS_FILE  = os.path.join(DATA_DIR, 'carteiras.txt')
SESSOES_FILE    = os.path.join(DATA_DIR, 'sessoes.txt')
DESEJOS_FILE     = os.path.join(DATA_DIR, 'desejos.txt')
PROMOCOES_FILE   = os.path.join(DATA_DIR, 'promocoes.txt')
HISTORICO_PROMOCOES_FILE = os.path.join(DATA_DIR, 'historico_promocoes.txt')
COMENTARIOS_FILE = os.path.join(DATA_DIR, 'comentarios.txt')
AVALIACOES_FILE  = os.path.join(DATA_DIR, 'avaliacoes.txt')

CARTEIRA_INICIAL = 100.00
LIMITE_TROCAS_USERNAME = 3


def _garantir_arquivos():
    """Cria a pasta de dados e os arquivos base se não existirem."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if not os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Banco de Dados de Usuários\n")
            f.write("# Formato: id | usuario | senha | data_nascimento | nome_exibicao | notas | trocas\n")
            f.write("# Exemplo: 1 | joao123 | senha456 | 1990-05-15 | João Silva | Jogador casual | 0\n")
            f.write("# Dica: data_nascimento como 'none' significa que o usuário não a cadastrou.\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(MAQUINA_FILE):
        with open(MAQUINA_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Configurações e Contas desta Máquina\n")
            f.write("# - Linhas de config: chave | valor   (ex: linguagem | pt-br)\n")
            f.write("# - Linhas de conta:  apenas o ID do usuário que já fez login aqui\n")
            f.write("# Idiomas: pt-br | en | de | zh-cn | pl | ko\n")
            f.write("# =============================================================================\n")
            f.write(f"linguagem | {i18n.IDIOMA_PADRAO}\n")

    if not os.path.exists(AMIZADES_FILE):
        with open(AMIZADES_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Banco de Dados de Amizades\n")
            f.write("# Formato: id_menor | id_maior  (IDs ordenados para evitar duplicatas)\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(BIBLIOTECA_FILE):
        with open(BIBLIOTECA_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Banco de Dados de Bibliotecas de Usuários\n")
            f.write("# Formato: user_id | game_id1,game_id2,...\n")
            f.write("# Exemplo: 1 | 1,3  (usuário 1 possui os jogos 1 e 3)\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(FAMILIAS_FILE):
        with open(FAMILIAS_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Banco de Dados de Famílias\n")
            f.write("# Cada linha é um objeto JSON representando uma família.\n")
            f.write("# Campos: id, name, created_at, founder, founder_id, members,\n")
            f.write("#         member_ids, library_pool, licenses\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(CARTEIRAS_FILE):
        with open(CARTEIRAS_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Banco de Dados de Carteiras dos Usuários\n")
            f.write("# Formato: user_id | saldo\n")
            f.write("# Exemplo: 1 | 100.00\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(SESSOES_FILE):
        with open(SESSOES_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Sessões de Jogo Ativas (Compartilhamento Familiar)\n")
            f.write("# Cada linha = um usuário jogando agora um título do pool da família.\n")
            f.write("# Formato: user_id | family_id | game_id | modo  (modo: online|offline)\n")
            f.write("# Usado para contar 'Em uso por parentes' de forma persistente entre contas.\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(DESEJOS_FILE):
        with open(DESEJOS_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Listas de Desejos dos Usuários\n")
            f.write("# Formato: user_id | game_id1,game_id2,...\n")
            f.write("# Exemplo: 1 | 2,3  (usuário 1 deseja os jogos 2 e 3)\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(PROMOCOES_FILE):
        with open(PROMOCOES_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Promoções da Loja (Simulação Manual via /admin)\n")
            f.write("# Linha de config:   config | <modo: nenhum|evento|unico> | <nome> | <data_fim>\n")
            f.write("# Desconto por jogo: <game_id> | <percentual 0-100>\n")
            f.write("# =============================================================================\n")
            f.write("config | nenhum | Promoção de Evento | none\n")

    if not os.path.exists(HISTORICO_PROMOCOES_FILE):
        with open(HISTORICO_PROMOCOES_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Histórico de Promoções\n")
            f.write("# Cada linha é um objeto JSON com uma promoção criada via /admin.\n")
            f.write("# Campos: id, criado_em, data_inicio, data_fim, modo, nome, descontos\n")
            f.write("# - modo: evento | unico\n")
            f.write("# - datas: AAAA-MM-DD\n")
            f.write("# - descontos: {game_id: percentual_inteiro_0_100}\n")
            f.write("# A promoção ATIVA é aquela cuja data atual está entre data_inicio e data_fim.\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(COMENTARIOS_FILE):
        with open(COMENTARIOS_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Comentários nos Perfis dos Usuários\n")
            f.write("# Formato: perfil_id | autor_id | data | texto\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Avaliações de Jogos\n")
            f.write("# Formato: game_id | autor_id | recomenda | data | linguagem | votos_uteis | voted_users | comentario\n")
            f.write("# - recomenda: sim | nao\n")
            f.write("# - data: dd/mm/aaaa\n")
            f.write("# - linguagem: pt-br | en | de | zh-cn | pl | ko\n")
            f.write("# - voted_users: 'none' ou 'id1:sim,id2:nao,...'\n")
            f.write("# - comentario: texto livre (pipes viram /, quebras de linha viram espaço)\n")
            f.write("# =============================================================================\n")
            f.write("1 | 1 | sim | 20/05/2026 | pt-br | 12 | none | Jogo excelente! Muito divertido para jogar em grupo.\n")
            f.write("1 | 2 | sim | 19/05/2026 | en | 5 | none | Amazing gameplay and graphics. Highly recommended to play with friends!\n")
            f.write("1 | 3 | nao | 18/05/2026 | de | 2 | none | Das Spiel hat zu viele Bugs. Ich kann es im Moment nicht empfehlen.\n")
            f.write("1 | 4 | sim | 21/05/2026 | pt-br | 8 | none | A lógica por trás dos puzzles deste jogo é fantástica.\n")
            f.write("2 | 5 | sim | 15/05/2026 | en | 14 | none | Great horror atmosphere! Found a few system bugs though.\n")


# ---- FUNÇÕES DE USUÁRIOS ----

def ler_usuarios():
    _garantir_arquivos()
    usuarios = []
    try:
        with open(USUARIOS_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith('#'):
                    continue
                partes = [p.strip() for p in linha.split('|')]
                if len(partes) >= 5:
                    usuarios.append({
                        'id':       partes[0],
                        'username': partes[1],
                        'senha':    partes[2],
                        'dob':      partes[3] if partes[3] != 'none' else None,
                        'nome':     partes[4],
                        'notas':    partes[5] if len(partes) > 5 else '',
                        'trocas_username': int(partes[6]) if len(partes) > 6 and partes[6].strip().isdigit() else 0
                    })
    except FileNotFoundError:
        pass
    return usuarios


def salvar_usuario(usuario):
    _garantir_arquivos()
    with open(USUARIOS_FILE, 'a', encoding='utf-8') as f:
        dob_val    = usuario['dob'] if usuario['dob'] else 'none'
        notas_val  = usuario.get('notas', '').replace('|', '-')
        trocas_val = usuario.get('trocas_username', 0)
        f.write(f"{usuario['id']} | {usuario['username']} | {usuario['senha']} | {dob_val} | {usuario['nome']} | {notas_val} | {trocas_val}\n")


def buscar_por_username(username):
    for u in ler_usuarios():
        if u['username'].lower() == username.lower():
            return u
    return None


def atualizar_usuario_db(uid, nome=None, notas=None, dob=None, username=None, trocas=None):
    """Atualiza nome, notas, data de nascimento, @usuário e/ou contador de trocas no arquivo."""
    _garantir_arquivos()
    uid = str(uid)
    linhas_novas = []
    with open(USUARIOS_FILE, 'r', encoding='utf-8') as f:
        for linha in f:
            s = linha.strip()
            if not s or s.startswith('#'):
                linhas_novas.append(linha)
                continue
            partes = [p.strip() for p in s.split('|')]
            if len(partes) >= 5 and partes[0] == uid:
                user_atual   = partes[1]
                dob_atual    = partes[3]
                nome_atual   = partes[4]
                notas_atual  = partes[5] if len(partes) > 5 else ''
                trocas_atual = partes[6] if len(partes) > 6 and partes[6].strip().isdigit() else '0'
                novo_user   = (username if username is not None else user_atual).replace('|', '-')
                novo_dob    = (dob if dob else dob_atual) or 'none'
                novo_nome   = (nome if nome is not None else nome_atual).replace('|', '-')
                novo_notas  = (notas if notas is not None else notas_atual).replace('|', '-')
                novo_trocas = str(trocas) if trocas is not None else trocas_atual
                linhas_novas.append(
                    f"{partes[0]} | {novo_user} | {partes[2]} | {novo_dob} | {novo_nome} | {novo_notas} | {novo_trocas}\n"
                )
            else:
                linhas_novas.append(linha)
    with open(USUARIOS_FILE, 'w', encoding='utf-8') as f:
        f.writelines(linhas_novas)


def buscar_por_id(uid):
    for u in ler_usuarios():
        if u['id'] == str(uid):
            return u
    return None


def proximo_id():
    usuarios = ler_usuarios()
    return str(max((int(u['id']) for u in usuarios), default=0) + 1)


# ---- FUNÇÕES DE MÁQUINA ----

def ler_ids_maquina():
    _garantir_arquivos()
    ids = []
    try:
        with open(MAQUINA_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith('#'):
                    continue
                # Linhas de config têm '|'; linhas de conta são apenas o ID.
                if '|' in linha:
                    continue
                ids.append(linha)
    except FileNotFoundError:
        pass
    return ids


def registrar_maquina(uid):
    if str(uid) not in ler_ids_maquina():
        _garantir_arquivos()
        with open(MAQUINA_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{uid}\n")


def ler_linguagem_maquina():
    """Retorna o idioma padrão configurado para esta máquina."""
    _garantir_arquivos()
    try:
        with open(MAQUINA_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#') or '|' not in s:
                    continue
                chave, _, valor = s.partition('|')
                if chave.strip() == 'linguagem':
                    valor = valor.strip()
                    if valor in i18n.IDIOMAS_SUPORTADOS:
                        return valor
    except FileNotFoundError:
        pass
    return i18n.IDIOMA_PADRAO


def salvar_linguagem_maquina(linguagem):
    """Persiste o idioma desta máquina, criando ou atualizando a linha de config."""
    if linguagem not in i18n.IDIOMAS_SUPORTADOS:
        return
    _garantir_arquivos()
    linhas_novas = []
    encontrou = False
    with open(MAQUINA_FILE, 'r', encoding='utf-8') as f:
        for linha in f:
            s = linha.strip()
            if not s or s.startswith('#') or '|' not in s:
                linhas_novas.append(linha)
                continue
            chave, _, _ = s.partition('|')
            if chave.strip() == 'linguagem':
                linhas_novas.append(f"linguagem | {linguagem}\n")
                encontrou = True
            else:
                linhas_novas.append(linha)
    if not encontrou:
        # Insere a linha de config logo após o cabeçalho (antes da primeira linha de ID).
        linhas_final = []
        inserido = False
        for linha in linhas_novas:
            s = linha.strip()
            if not inserido and s and not s.startswith('#') and '|' not in s:
                linhas_final.append(f"linguagem | {linguagem}\n")
                inserido = True
            linhas_final.append(linha)
        if not inserido:
            linhas_final.append(f"linguagem | {linguagem}\n")
        linhas_novas = linhas_final
    with open(MAQUINA_FILE, 'w', encoding='utf-8') as f:
        f.writelines(linhas_novas)


def remover_maquina(uid):
    """Remove o usuário da lista de contas desta máquina (usado ao finalizar sessão)."""
    if uid is None:
        return
    uid = str(uid)
    ids = [i for i in ler_ids_maquina() if i != uid]
    _garantir_arquivos()
    with open(MAQUINA_FILE, 'w', encoding='utf-8') as f:
        f.write("# =============================================================================\n")
        f.write("# MINISTEAM - Contas desta Máquina\n")
        f.write("# Cada linha contém o ID de um usuário que já fez login neste computador.\n")
        f.write("# =============================================================================\n")
        for i in ids:
            f.write(f"{i}\n")


# ---- FUNÇÕES DE AMIZADES ----

def ler_amizades():
    _garantir_arquivos()
    pares = []
    try:
        with open(AMIZADES_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith('#'):
                    continue
                partes = [p.strip() for p in linha.split('|')]
                if len(partes) == 2:
                    pares.append((partes[0], partes[1]))
    except FileNotFoundError:
        pass
    return pares


def _reescrever_amizades(pares):
    _garantir_arquivos()
    with open(AMIZADES_FILE, 'w', encoding='utf-8') as f:
        f.write("# =============================================================================\n")
        f.write("# MINISTEAM - Banco de Dados de Amizades\n")
        f.write("# Formato: id_menor | id_maior  (IDs ordenados para evitar duplicatas)\n")
        f.write("# =============================================================================\n")
        for a, b in pares:
            f.write(f"{a} | {b}\n")


def sao_amigos(uid1, uid2):
    uid1, uid2 = str(uid1), str(uid2)
    for a, b in ler_amizades():
        if {a, b} == {uid1, uid2}:
            return True
    return False


def adicionar_amizade(uid1, uid2):
    if sao_amigos(uid1, uid2):
        return
    a, b = sorted([str(uid1), str(uid2)], key=lambda x: int(x))
    _garantir_arquivos()
    with open(AMIZADES_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{a} | {b}\n")


def remover_amizade(uid1, uid2):
    uid1, uid2 = str(uid1), str(uid2)
    pares = [(a, b) for a, b in ler_amizades() if {a, b} != {uid1, uid2}]
    _reescrever_amizades(pares)


def get_amigos_usuario(uid):
    uid = str(uid)
    amigos = []
    for a, b in ler_amizades():
        friend_id = b if a == uid else (a if b == uid else None)
        if friend_id:
            u = buscar_por_id(friend_id)
            if u:
                amigos.append(u)
    return amigos


def get_amigos_dict(uid):
    return {u['id']: u['nome'] for u in get_amigos_usuario(uid)}


# ---- FUNÇÕES DE BIBLIOTECA ----

def ler_biblioteca_usuario(uid):
    """Retorna lista de IDs de jogos que o usuário possui."""
    _garantir_arquivos()
    uid = str(uid)
    try:
        with open(BIBLIOTECA_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#'):
                    continue
                partes = [p.strip() for p in s.split('|', 1)]
                if partes[0] == uid:
                    if len(partes) >= 2 and partes[1].strip():
                        return [g for g in partes[1].strip().split(',') if g.strip()]
                    return []
    except FileNotFoundError:
        pass
    return []


def salvar_biblioteca_usuario(uid, game_ids):
    """Salva/atualiza a lista de jogos do usuário no arquivo de banco de dados."""
    _garantir_arquivos()
    uid = str(uid)
    game_ids = list(dict.fromkeys(str(g) for g in game_ids if g))  # deduplica mantendo ordem
    linhas_novas = []
    encontrou = False
    try:
        with open(BIBLIOTECA_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#'):
                    linhas_novas.append(linha)
                    continue
                partes = [p.strip() for p in s.split('|', 1)]
                if partes[0] == uid:
                    linhas_novas.append(f"{uid} | {','.join(game_ids)}\n")
                    encontrou = True
                else:
                    linhas_novas.append(linha)
    except FileNotFoundError:
        linhas_novas = [
            "# =============================================================================\n",
            "# MINISTEAM - Banco de Dados de Bibliotecas de Usuários\n",
            "# Formato: user_id | game_id1,game_id2,...\n",
            "# =============================================================================\n"
        ]
    if not encontrou:
        linhas_novas.append(f"{uid} | {','.join(game_ids)}\n")
    with open(BIBLIOTECA_FILE, 'w', encoding='utf-8') as f:
        f.writelines(linhas_novas)


# ---- FUNÇÕES DE CARTEIRA ----

def ler_carteira_usuario(uid):
    """Retorna o saldo persistido do usuário (float). Default: CARTEIRA_INICIAL."""
    _garantir_arquivos()
    uid = str(uid)
    try:
        with open(CARTEIRAS_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#'):
                    continue
                partes = [p.strip() for p in s.split('|', 1)]
                if partes[0] == uid and len(partes) >= 2:
                    try:
                        return float(partes[1])
                    except ValueError:
                        return CARTEIRA_INICIAL
    except FileNotFoundError:
        pass
    return CARTEIRA_INICIAL


def salvar_carteira_usuario(uid, saldo):
    """Salva/atualiza o saldo da carteira do usuário no banco de dados."""
    _garantir_arquivos()
    uid = str(uid)
    try:
        saldo = float(saldo)
    except (TypeError, ValueError):
        saldo = CARTEIRA_INICIAL
    linhas_novas = []
    encontrou = False
    try:
        with open(CARTEIRAS_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#'):
                    linhas_novas.append(linha)
                    continue
                partes = [p.strip() for p in s.split('|', 1)]
                if partes[0] == uid:
                    linhas_novas.append(f"{uid} | {saldo:.2f}\n")
                    encontrou = True
                else:
                    linhas_novas.append(linha)
    except FileNotFoundError:
        linhas_novas = [
            "# =============================================================================\n",
            "# MINISTEAM - Banco de Dados de Carteiras dos Usuários\n",
            "# Formato: user_id | saldo\n",
            "# =============================================================================\n"
        ]
    if not encontrou:
        linhas_novas.append(f"{uid} | {saldo:.2f}\n")
    with open(CARTEIRAS_FILE, 'w', encoding='utf-8') as f:
        f.writelines(linhas_novas)


# ---- FUNÇÕES DE LISTA DE DESEJOS (WISHLIST) ----

def ler_desejos_usuario(uid):
    """Retorna lista de IDs de jogos na lista de desejos do usuário."""
    _garantir_arquivos()
    uid = str(uid)
    try:
        with open(DESEJOS_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#'):
                    continue
                partes = [p.strip() for p in s.split('|', 1)]
                if partes[0] == uid:
                    if len(partes) >= 2 and partes[1].strip():
                        return [g for g in partes[1].strip().split(',') if g.strip()]
                    return []
    except FileNotFoundError:
        pass
    return []


def salvar_desejos_usuario(uid, game_ids):
    """Salva/atualiza a lista de desejos do usuário no banco de dados."""
    _garantir_arquivos()
    uid = str(uid)
    game_ids = list(dict.fromkeys(str(g) for g in game_ids if g))
    linhas_novas = []
    encontrou = False
    try:
        with open(DESEJOS_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#'):
                    linhas_novas.append(linha)
                    continue
                partes = [p.strip() for p in s.split('|', 1)]
                if partes[0] == uid:
                    linhas_novas.append(f"{uid} | {','.join(game_ids)}\n")
                    encontrou = True
                else:
                    linhas_novas.append(linha)
    except FileNotFoundError:
        linhas_novas = [
            "# =============================================================================\n",
            "# MINISTEAM - Listas de Desejos dos Usuários\n",
            "# Formato: user_id | game_id1,game_id2,...\n",
            "# =============================================================================\n"
        ]
    if not encontrou:
        linhas_novas.append(f"{uid} | {','.join(game_ids)}\n")
    with open(DESEJOS_FILE, 'w', encoding='utf-8') as f:
        f.writelines(linhas_novas)


# ---- FUNÇÕES DE PROMOÇÃO ----

def _data_str_hoje():
    """Data de hoje em formato AAAA-MM-DD (usada como referência de 'agora')."""
    return datetime.now().strftime("%Y-%m-%d")


def _validar_data_iso(s):
    """Retorna True se `s` está em formato AAAA-MM-DD e parsa como data válida."""
    if not s or not isinstance(s, str):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def ler_historico_promocoes():
    """Retorna lista de todas as promoções já criadas, em ordem cronológica de criação."""
    _garantir_arquivos()
    promocoes = []
    try:
        with open(HISTORICO_PROMOCOES_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#'):
                    continue
                try:
                    promo = json.loads(s)
                    # Normalizações defensivas: campos opcionais com defaults seguros
                    promo.setdefault('id', f"promo_{len(promocoes)}")
                    promo.setdefault('modo', 'evento')
                    promo.setdefault('nome', 'Promoção')
                    promo.setdefault('descontos', {})
                    promo.setdefault('data_inicio', None)
                    promo.setdefault('data_fim', None)
                    promo.setdefault('criado_em', '')
                    promocoes.append(promo)
                except (json.JSONDecodeError, ValueError):
                    continue
    except FileNotFoundError:
        pass
    return promocoes


def _escrever_historico(promocoes):
    """Reescreve o arquivo de histórico preservando o cabeçalho."""
    _garantir_arquivos()
    cabecalho = []
    try:
        with open(HISTORICO_PROMOCOES_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                if linha.startswith('#'):
                    cabecalho.append(linha)
                else:
                    break
    except FileNotFoundError:
        pass
    with open(HISTORICO_PROMOCOES_FILE, 'w', encoding='utf-8') as f:
        f.writelines(cabecalho)
        for p in promocoes:
            f.write(json.dumps(p, ensure_ascii=False, sort_keys=True) + '\n')


def criar_promocao(nome, modo, data_inicio, data_fim, descontos):
    """Adiciona uma nova promoção ao histórico. Retorna (ok, mensagem).

    `descontos` é dict {game_id: percentual_inteiro_1_a_100}.
    Datas em formato AAAA-MM-DD. Modo: 'evento' ou 'unico'.
    """
    if modo not in ('evento', 'unico'):
        return False, "Modo inválido (use evento ou unico)."
    if not _validar_data_iso(data_inicio):
        return False, "Data de início obrigatória no formato AAAA-MM-DD."
    if not _validar_data_iso(data_fim):
        return False, "Data de fim obrigatória no formato AAAA-MM-DD."
    if data_fim < data_inicio:
        return False, "Data de fim não pode ser anterior à data de início."
    descontos_limpos = {}
    for gid, pct in (descontos or {}).items():
        try:
            pct_i = int(pct)
        except (TypeError, ValueError):
            continue
        if str(gid) in GAMES and 0 < pct_i <= 100:
            descontos_limpos[str(gid)] = pct_i
    if not descontos_limpos:
        return False, "Selecione ao menos um jogo com desconto > 0."
    promo = {
        'id':          f"promo_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        'criado_em':   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'data_inicio': data_inicio,
        'data_fim':    data_fim,
        'modo':        modo,
        'nome':        (nome or 'Promoção').replace('|', '-')[:80],
        'descontos':   descontos_limpos,
    }
    promocoes = ler_historico_promocoes()
    promocoes.append(promo)
    _escrever_historico(promocoes)
    return True, promo


def remover_promocao(promo_id):
    """Remove uma promoção inteira do histórico. Retorna (ok, mensagem)."""
    promocoes = ler_historico_promocoes()
    novas = [p for p in promocoes if p.get('id') != promo_id]
    if len(novas) == len(promocoes):
        return False, "Promoção não encontrada."
    _escrever_historico(novas)
    return True, "Promoção removida do histórico."


def remover_desconto_de_promocao(promo_id, game_id):
    """Remove o desconto de um jogo específico de uma promoção. Se ficar sem
    nenhum desconto, remove a promoção inteira. Retorna (ok, mensagem)."""
    game_id  = str(game_id)
    promocoes = ler_historico_promocoes()
    alvo = next((p for p in promocoes if p.get('id') == promo_id), None)
    if not alvo:
        return False, "Promoção não encontrada."
    if game_id not in alvo.get('descontos', {}):
        return False, "Esse jogo não estava na promoção."
    del alvo['descontos'][game_id]
    if not alvo['descontos']:
        promocoes = [p for p in promocoes if p.get('id') != promo_id]
        _escrever_historico(promocoes)
        return True, "Último desconto removido; promoção encerrada."
    _escrever_historico(promocoes)
    return True, "Desconto do jogo removido da promoção."


def remover_publisher_de_promocao(promo_id, publisher):
    """Remove todos os jogos de um publisher de uma promoção. Retorna (ok, mensagem)."""
    promocoes = ler_historico_promocoes()
    alvo = next((p for p in promocoes if p.get('id') == promo_id), None)
    if not alvo:
        return False, "Promoção não encontrada."
    ids_publisher = [gid for gid, g in GAMES.items() if g.get('publisher') == publisher]
    removidos = [gid for gid in ids_publisher if gid in alvo.get('descontos', {})]
    if not removidos:
        return False, "Esse publisher não estava na promoção."
    for gid in removidos:
        del alvo['descontos'][gid]
    if not alvo['descontos']:
        promocoes = [p for p in promocoes if p.get('id') != promo_id]
        _escrever_historico(promocoes)
        return True, f"Todos os jogos da {publisher} removidos; promoção encerrada."
    _escrever_historico(promocoes)
    return True, f"Jogos da {publisher} removidos da promoção."


def _promocao_ativa_em(data_ref, promocoes):
    """Retorna a promoção ativa em `data_ref` (AAAA-MM-DD).

    Se houver mais de uma cobrindo a data, escolhe a criada mais recentemente.
    """
    candidatas = []
    for p in promocoes:
        ini, fim = p.get('data_inicio'), p.get('data_fim')
        if ini and fim and ini <= data_ref <= fim and p.get('descontos'):
            candidatas.append(p)
    if not candidatas:
        return None
    candidatas.sort(key=lambda p: p.get('criado_em', ''), reverse=True)
    return candidatas[0]


def ler_promocao():
    """Retorna a promoção ATIVA agora no formato esperado pelo resto do app.

    Estrutura: {modo, ativo, nome, data_fim, data_inicio, id, descontos{gid: pct}}.
    Se não há promoção ativa, devolve um placeholder inativo.
    """
    promocoes = ler_historico_promocoes()
    ativa = _promocao_ativa_em(_data_str_hoje(), promocoes)
    if not ativa:
        return {
            'modo': 'nenhum', 'nome': 'Promoção', 'data_fim': None,
            'data_inicio': None, 'id': None, 'descontos': {}, 'ativo': False
        }
    return {
        'modo':        ativa.get('modo', 'evento'),
        'nome':        ativa.get('nome', 'Promoção'),
        'data_inicio': ativa.get('data_inicio'),
        'data_fim':    ativa.get('data_fim'),
        'id':          ativa.get('id'),
        'descontos':   {gid: int(pct) for gid, pct in ativa.get('descontos', {}).items()},
        'ativo':       True,
    }


def calcular_preco(gid):
    """Retorna {original, final, pct, on_sale} para um jogo, aplicando a promoção ativa."""
    gid  = str(gid)
    game = GAMES.get(gid)
    if not game:
        return {'original': 0.0, 'final': 0.0, 'pct': 0, 'on_sale': False}
    promo    = ler_promocao()
    original = game['price']
    pct      = promo['descontos'].get(gid, 0) if promo['ativo'] else 0
    final    = round(original * (1 - pct / 100), 2)
    return {'original': original, 'final': final, 'pct': pct, 'on_sale': pct > 0}


def agrupar_jogos_por_publisher():
    """Retorna dict {publisher: [(game_id, game_dict), ...]} ordenado por publisher."""
    grupos = {}
    for gid in sorted(GAMES.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        game = GAMES[gid]
        pub  = game.get('publisher') or 'Outros'
        grupos.setdefault(pub, []).append((gid, game))
    return dict(sorted(grupos.items()))


# ---- FUNÇÕES DE COMENTÁRIOS DE PERFIL ----

def ler_comentarios_perfil(perfil_id):
    """Retorna os comentários feitos no perfil (mais recentes primeiro)."""
    _garantir_arquivos()
    perfil_id = str(perfil_id)
    comentarios = []
    try:
        with open(COMENTARIOS_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.rstrip('\n')
                if not s.strip() or s.startswith('#'):
                    continue
                partes = s.split('|', 3)
                if len(partes) == 4 and partes[0].strip() == perfil_id:
                    autor_id = partes[1].strip()
                    autor    = buscar_por_id(autor_id)
                    comentarios.append({
                        'autor_id':   autor_id,
                        'autor_nome': autor['nome'] if autor else 'Usuário',
                        'data':       partes[2].strip(),
                        'texto':      partes[3].strip()
                    })
    except FileNotFoundError:
        pass
    return list(reversed(comentarios))


def adicionar_comentario(perfil_id, autor_id, texto):
    """Registra um novo comentário no perfil informado."""
    _garantir_arquivos()
    texto = ' '.join(texto.split()).replace('|', '/')[:300]
    if not texto:
        return
    data = datetime.now().strftime("%d/%m/%Y %H:%M")
    with open(COMENTARIOS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{perfil_id} | {autor_id} | {data} | {texto}\n")


# ---- FUNÇÕES DE AVALIAÇÕES DE JOGOS ----

def _serializar_votos(voted_users):
    """Converte {'1': 'sim', '2': 'nao'} → '1:sim,2:nao'. Vazio vira 'none'."""
    if not voted_users:
        return 'none'
    return ','.join(f"{uid}:{voto}" for uid, voto in voted_users.items())


def _desserializar_votos(texto):
    """Converte '1:sim,2:nao' → {'1': 'sim', '2': 'nao'}. 'none' vira {}."""
    if not texto or texto == 'none':
        return {}
    votos = {}
    for par in texto.split(','):
        if ':' in par:
            uid, voto = par.split(':', 1)
            uid, voto = uid.strip(), voto.strip()
            if uid and voto in ('sim', 'nao'):
                votos[uid] = voto
    return votos


def _ler_todas_avaliacoes():
    """Lê o arquivo bruto e retorna uma lista de dicts (com autor_id, sem nome resolvido)."""
    _garantir_arquivos()
    avaliacoes = []
    try:
        with open(AVALIACOES_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.rstrip('\n')
                if not s.strip() or s.startswith('#'):
                    continue
                partes = [p.strip() for p in s.split('|', 7)]
                if len(partes) < 8:
                    continue
                try:
                    votos_uteis = int(partes[5])
                except ValueError:
                    votos_uteis = 0
                avaliacoes.append({
                    'game_id':     partes[0],
                    'autor_id':    partes[1],
                    'recomenda':   partes[2] == 'sim',
                    'data':        partes[3],
                    'linguagem':   partes[4],
                    'votos_uteis': votos_uteis,
                    'voted_users': _desserializar_votos(partes[6]),
                    'comentario':  partes[7]
                })
    except FileNotFoundError:
        pass
    return avaliacoes


def _salvar_todas_avaliacoes(avaliacoes):
    """Reescreve o arquivo de avaliações preservando o cabeçalho."""
    _garantir_arquivos()
    cabecalho = []
    try:
        with open(AVALIACOES_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                if linha.startswith('#'):
                    cabecalho.append(linha)
                else:
                    break
    except FileNotFoundError:
        pass
    with open(AVALIACOES_FILE, 'w', encoding='utf-8') as f:
        f.writelines(cabecalho)
        for a in avaliacoes:
            recomenda = 'sim' if a['recomenda'] else 'nao'
            votos = _serializar_votos(a.get('voted_users', {}))
            f.write(
                f"{a['game_id']} | {a['autor_id']} | {recomenda} | {a['data']} | "
                f"{a['linguagem']} | {a.get('votos_uteis', 0)} | {votos} | {a['comentario']}\n"
            )


def ler_avaliacoes_jogo(game_id):
    """Retorna as avaliações do jogo enriquecidas com o nome do autor."""
    game_id = str(game_id)
    resultado = []
    for a in _ler_todas_avaliacoes():
        if a['game_id'] != game_id:
            continue
        autor = buscar_por_id(a['autor_id'])
        item = dict(a)
        item['author'] = autor['nome'] if autor else 'Usuário'
        resultado.append(item)
    return resultado


def salvar_avaliacao(game_id, autor_id, recomenda, comentario, linguagem_preferida):
    """Cria ou atualiza a avaliação do autor para o jogo.

    O idioma salvo é DETECTADO do texto do comentário (não a preferência do
    autor), para que o sistema saiba traduzir corretamente quando outro
    usuário visualizar. `linguagem_preferida` só é usada como fallback
    quando a detecção falha (texto curto demais, etc).
    """
    game_id   = str(game_id)
    autor_id  = str(autor_id)
    comentario = comentario.replace('|', '/').replace('\n', ' ').replace('\r', ' ').strip()
    if not comentario:
        return
    idioma_detectado = i18n.detectar_idioma(comentario)
    # Para textos muito curtos, langdetect erra; preferir a preferência do autor.
    if len(comentario) < 25 and linguagem_preferida in i18n.IDIOMAS_SUPORTADOS:
        idioma_detectado = linguagem_preferida
    todas = _ler_todas_avaliacoes()
    existente = next((a for a in todas if a['game_id'] == game_id and a['autor_id'] == autor_id), None)
    if existente:
        existente['recomenda']  = bool(recomenda)
        existente['comentario'] = comentario
        existente['linguagem']  = idioma_detectado
        existente['data']       = datetime.now().strftime("%d/%m/%Y")
    else:
        todas.append({
            'game_id':     game_id,
            'autor_id':    autor_id,
            'recomenda':   bool(recomenda),
            'data':        datetime.now().strftime("%d/%m/%Y"),
            'linguagem':   idioma_detectado,
            'votos_uteis': 0,
            'voted_users': {},
            'comentario':  comentario
        })
    _salvar_todas_avaliacoes(todas)


def votar_avaliacao(game_id, autor_id_alvo, votante_id, vote_type):
    """Registra/atualiza voto útil. Retorna (ok, mensagem, categoria_flash)."""
    game_id       = str(game_id)
    autor_id_alvo = str(autor_id_alvo)
    votante_id    = str(votante_id)
    if vote_type not in ('sim', 'nao'):
        return False, "Voto inválido.", "error"
    if autor_id_alvo == votante_id:
        return False, "Bloqueio: Você não pode classificar sua própria análise.", "error"
    todas = _ler_todas_avaliacoes()
    alvo = next((a for a in todas if a['game_id'] == game_id and a['autor_id'] == autor_id_alvo), None)
    if not alvo:
        return False, "Avaliação não encontrada.", "error"
    voto_anterior = alvo['voted_users'].get(votante_id)
    if voto_anterior == vote_type:
        return False, "Você já classificou esta análise com esta mesma opção.", "error"
    if vote_type == 'sim':
        alvo['votos_uteis'] = alvo.get('votos_uteis', 0) + 1
        msg = "Voto atualizado! O voto útil foi registrado e ajudará a comunidade."
    else:
        if voto_anterior == 'sim':
            alvo['votos_uteis'] = max(0, alvo.get('votos_uteis', 0) - 1)
        msg = "Voto atualizado! Registramos que esta análise não foi útil para você."
    alvo['voted_users'][votante_id] = vote_type
    _salvar_todas_avaliacoes(todas)
    return True, msg, "sucesso"


# ---- HORAS JOGADAS (SIMULAÇÃO ESTÁVEL POR USUÁRIO+JOGO) ----

def horas_jogadas(uid, gid):
    """Horas jogadas simuladas, estáveis para o mesmo par (usuário, jogo)."""
    rng = random.Random(f"{uid}-{gid}-ministeam")
    # Distribuição enviesada: maioria com poucas horas, alguns com muitas.
    if rng.random() < 0.25:
        return round(rng.uniform(40, 320), 1)
    return round(rng.uniform(0.5, 60), 1)


# ---- FUNÇÕES DE FAMÍLIA ----

def ler_familias():
    """Retorna lista de dicts com todas as famílias registradas."""
    _garantir_arquivos()
    familias = []
    try:
        with open(FAMILIAS_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#'):
                    continue
                try:
                    fam = json.loads(s)
                    # Compatibilidade: famílias antigas não possuíam 'creator'.
                    # O criador original é preservado (fallback para o fundador atual).
                    if 'creator' not in fam:
                        fam['creator'] = fam.get('founder', '')
                        fam['creator_id'] = fam.get('founder_id', '')
                    familias.append(fam)
                except json.JSONDecodeError:
                    pass
    except FileNotFoundError:
        pass
    return familias


def _reescrever_familias(familias):
    """Sobrescreve o arquivo de famílias com a lista fornecida."""
    _garantir_arquivos()
    with open(FAMILIAS_FILE, 'w', encoding='utf-8') as f:
        f.write("# =============================================================================\n")
        f.write("# MINISTEAM - Banco de Dados de Famílias\n")
        f.write("# Cada linha é um objeto JSON representando uma família.\n")
        f.write("# =============================================================================\n")
        for familia in familias:
            # Nunca salva o campo de sessão 'occupied_by_others'
            dados = {k: v for k, v in familia.items() if k != 'occupied_by_others'}
            f.write(json.dumps(dados, ensure_ascii=False) + '\n')


def salvar_nova_familia(familia):
    """Adiciona uma nova família ao final do arquivo."""
    _garantir_arquivos()
    dados = {k: v for k, v in familia.items() if k != 'occupied_by_others'}
    with open(FAMILIAS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(dados, ensure_ascii=False) + '\n')


def atualizar_familia(familia):
    """Atualiza os dados de uma família existente no arquivo."""
    familias = ler_familias()
    novas = []
    for f in familias:
        if f['id'] == familia['id']:
            dados = {k: v for k, v in familia.items() if k != 'occupied_by_others'}
            novas.append(dados)
        else:
            novas.append(f)
    _reescrever_familias(novas)


def remover_familia_db(family_id):
    """Remove uma família do arquivo pelo ID."""
    familias = [f for f in ler_familias() if f['id'] != family_id]
    _reescrever_familias(familias)


def buscar_familia_do_usuario(uid):
    """Retorna a família do usuário (como dict) ou None."""
    uid = str(uid)
    for familia in ler_familias():
        if uid in [str(m) for m in familia.get('member_ids', [])]:
            return familia
    return None


# ---- FUNÇÕES DE SESSÕES DE JOGO ATIVAS ----
# Persistem quem está jogando agora cada título do pool da família, para que o
# contador "Em uso por parentes" sobreviva à troca de conta na mesma máquina.

def ler_sessoes_jogo():
    """Retorna lista de dicts {user_id, family_id, game_id, modo}."""
    _garantir_arquivos()
    sessoes = []
    try:
        with open(SESSOES_FILE, 'r', encoding='utf-8') as f:
            for linha in f:
                s = linha.strip()
                if not s or s.startswith('#'):
                    continue
                partes = [p.strip() for p in s.split('|')]
                if len(partes) >= 3:
                    sessoes.append({
                        'user_id':   partes[0],
                        'family_id': partes[1],
                        'game_id':   partes[2],
                        'modo':      partes[3] if len(partes) > 3 else 'online'
                    })
    except FileNotFoundError:
        pass
    return sessoes


def _reescrever_sessoes_jogo(sessoes):
    _garantir_arquivos()
    with open(SESSOES_FILE, 'w', encoding='utf-8') as f:
        f.write("# =============================================================================\n")
        f.write("# MINISTEAM - Sessões de Jogo Ativas (Compartilhamento Familiar)\n")
        f.write("# Formato: user_id | family_id | game_id | modo  (modo: online|offline)\n")
        f.write("# =============================================================================\n")
        for s in sessoes:
            f.write(f"{s['user_id']} | {s['family_id']} | {s['game_id']} | {s['modo']}\n")


def iniciar_sessao_jogo(user_id, family_id, game_id, modo='online'):
    """Marca o usuário como jogando o título (um jogo por vez por usuário)."""
    user_id = str(user_id)
    sessoes = [s for s in ler_sessoes_jogo() if s['user_id'] != user_id]
    sessoes.append({
        'user_id':   user_id,
        'family_id': str(family_id),
        'game_id':   str(game_id),
        'modo':      modo
    })
    _reescrever_sessoes_jogo(sessoes)


def encerrar_sessao_jogo(user_id):
    """Remove a sessão de jogo ativa do usuário (Fechar Jogo). Idempotente."""
    user_id = str(user_id)
    sessoes = [s for s in ler_sessoes_jogo() if s['user_id'] != user_id]
    _reescrever_sessoes_jogo(sessoes)


def sessao_ativa_do_usuario(user_id, family_id):
    """Retorna a sessão de jogo ativa do usuário nesta família, ou None."""
    user_id, family_id = str(user_id), str(family_id)
    for s in ler_sessoes_jogo():
        if s['user_id'] == user_id and s['family_id'] == family_id:
            return s
    return None


def contar_em_uso(family_id, game_id):
    """Conta quantos membros estão jogando online (consomem licença) este título."""
    family_id, game_id = str(family_id), str(game_id)
    return sum(
        1 for s in ler_sessoes_jogo()
        if s['family_id'] == family_id and s['game_id'] == game_id and s['modo'] == 'online'
    )


def em_uso_total(family, game_id):
    """Licenças ocupadas = jogadores reais online + simulação de parente (testes)."""
    if not family:
        return 0
    npc = 1 if family.get('occupied_by_others', {}).get(str(game_id), False) else 0
    return contar_em_uso(family['id'], game_id) + npc


# ---- FUNÇÃO DE LOGIN ----

def fazer_login_sessao(usuario):
    """Limpa a sessão e a popula com os dados do usuário autenticado, carregando dados do banco."""
    session.clear()
    uid = str(usuario['id'])

    # Carrega biblioteca persistida
    biblioteca_db = ler_biblioteca_usuario(uid)

    # Carrega família persistida
    familia_db = buscar_familia_do_usuario(uid)
    familia_sessao = None
    if familia_db:
        familia_sessao = dict(familia_db)
        familia_sessao['occupied_by_others'] = {}  # campo de simulação, sempre começa vazio

    # Restaura jogo em andamento: se o usuário deixou um título rodando antes de
    # trocar de conta, ele continua "Executando..." ao voltar para esta conta.
    active_game = None
    if familia_sessao:
        sessao_jogo = sessao_ativa_do_usuario(uid, familia_sessao['id'])
        if sessao_jogo:
            active_game = sessao_jogo['game_id']

    session['logged_in']     = True
    session['user_id']       = uid
    session['wallet']        = ler_carteira_usuario(uid)
    session['library']       = biblioteca_db
    session['wishlist']      = ler_desejos_usuario(uid)
    session['cart']          = []
    session['gifts_sent']    = {}
    session['user_dob']      = usuario['dob']
    session['user_profile']  = {
        'name':      usuario['nome'],
        'details':   usuario.get('notas', ''),
        'linguagem': ler_linguagem_maquina()
    }
    session['family']          = familia_sessao
    session['family_cooldown'] = False
    session['offline_mode']    = False
    session['active_game']     = active_game
    session['show_pe01_for']   = None
    session.modified = True
    registrar_maquina(uid)


# ==============================================================================
# BEFORE REQUEST
# ==============================================================================

@app.before_request
def verificar_autenticacao():
    rotas_publicas = {'login', 'selecionar_usuario', 'register', 'static'}
    if request.endpoint in rotas_publicas:
        return
    if not session.get('logged_in'):
        return redirect(url_for('login'))


@app.before_request
def garantir_valores_sessao():
    if not session.get('logged_in'):
        return
    padroes = {
        'wallet': 100.00, 'library': [], 'wishlist': [], 'cart': [], 'gifts_sent': {},
        'user_dob': None, 'user_profile': {'name': 'Usuário', 'details': '', 'linguagem': i18n.IDIOMA_PADRAO},
        'family': None, 'family_cooldown': False,
        'offline_mode': False, 'active_game': None, 'show_pe01_for': None
    }
    for chave, valor in padroes.items():
        if chave not in session:
            session[chave] = valor


@app.context_processor
def injetar_promocao():
    """Disponibiliza a promoção ativa e a função preco_info() em todos os templates."""
    promo = ler_promocao()

    def preco_info(gid):
        gid  = str(gid)
        game = GAMES.get(gid)
        if not game:
            return {'original': 0.0, 'final': 0.0, 'pct': 0, 'on_sale': False}
        original = game['price']
        pct      = promo['descontos'].get(gid, 0) if promo['ativo'] else 0
        final    = round(original * (1 - pct / 100), 2)
        return {'original': original, 'final': final, 'pct': pct, 'on_sale': pct > 0}

    return {
        'promo_ativa':  promo['ativo'],
        'promo_modo':   promo['modo'],
        'promo_evento': promo['modo'] == 'evento' and promo['ativo'],
        'promo_nome':   promo['nome'],
        'promo_fim':    promo['data_fim'],
        'preco_info':   preco_info,
    }


# ==============================================================================
# ROTAS DE AUTENTICAÇÃO
# ==============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))

    ids_maquina      = ler_ids_maquina()
    usuarios_maquina = [buscar_por_id(uid) for uid in ids_maquina]
    usuarios_maquina = [u for u in usuarios_maquina if u]

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        senha    = request.form.get('password', '').strip()
        usuario  = buscar_por_username(username)
        if not usuario or usuario['senha'] != senha:
            flash('Usuário ou senha incorretos.', 'error')
            return render_template('login.html', usuarios_maquina=usuarios_maquina)
        fazer_login_sessao(usuario)
        return redirect(url_for('index'))

    return render_template('login.html', usuarios_maquina=usuarios_maquina)


@app.route('/login/selecionar/<user_id>')
def selecionar_usuario(user_id):
    usuario = buscar_por_id(user_id)
    if not usuario:
        flash('Conta não encontrada.', 'error')
        return redirect(url_for('login'))
    fazer_login_sessao(usuario)
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        senha    = request.form.get('password', '').strip()
        nome     = request.form.get('display_name', '').strip()
        dob      = request.form.get('dob', '').strip() or None

        if not username or not senha or not nome:
            flash('Preencha todos os campos obrigatórios.', 'error')
            return render_template('register.html')
        if buscar_por_username(username):
            flash('Este nome de usuário já está em uso. Escolha outro.', 'error')
            return render_template('register.html')
        if len(senha) < 4:
            flash('A senha deve ter pelo menos 4 caracteres.', 'error')
            return render_template('register.html')

        novo = {
            'id':       proximo_id(),
            'username': username,
            'senha':    senha,
            'dob':      dob,
            'nome':     nome,
            'notas':    'Novo usuário Ministeam.'
        }
        salvar_usuario(novo)
        fazer_login_sessao(novo)
        flash(f'Conta criada com sucesso! Bem-vindo(a), {nome}!', 'sucesso')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    # Finalizar sessão: apaga as informações deste usuário nesta máquina
    # (ele deixa de aparecer no seletor de contas).
    remover_maquina(session.get('user_id'))
    session.clear()
    return redirect(url_for('login'))


# ==============================================================================
# ROTAS DE AMIZADES
# ==============================================================================

@app.route('/amigos')
def amigos():
    uid         = session['user_id']
    meus_amigos = get_amigos_usuario(uid)
    ids_amigos  = {u['id'] for u in meus_amigos}
    q           = request.args.get('q', '').strip().lower()

    sugestoes      = []
    tipo_sugestao  = 'busca' if q else 'fof'

    if q:
        # Prefixo exato: apenas usuários cujo @ COMEÇA com a query
        todos = ler_usuarios()
        sugestoes = [
            u for u in todos
            if u['id'] != uid
            and u['id'] not in ids_amigos
            and u['username'].lower().startswith(q)
        ]
    else:
        # Sugestões de amigos de amigos (máx 5, sem repetição)
        vistos = set()
        for amigo in meus_amigos:
            for fof in get_amigos_usuario(amigo['id']):
                if fof['id'] != uid and fof['id'] not in ids_amigos and fof['id'] not in vistos:
                    vistos.add(fof['id'])
                    sugestoes.append(fof)
                    if len(sugestoes) >= 5:
                        break
            if len(sugestoes) >= 5:
                break

    return render_template('amigos.html',
                           meus_amigos=meus_amigos,
                           sugestoes=sugestoes,
                           query=q,
                           tipo_sugestao=tipo_sugestao)


@app.route('/amigos/buscar')
def amigos_buscar():
    from flask import jsonify
    uid       = session['user_id']
    q         = request.args.get('q', '').strip().lower()
    ids_amigos = {u['id'] for u in get_amigos_usuario(uid)}

    if not q:
        return jsonify([])

    todos = ler_usuarios()
    resultados = [
        {'id': u['id'], 'username': u['username'], 'nome': u['nome']}
        for u in todos
        if u['id'] != uid
        and u['id'] not in ids_amigos
        and u['username'].lower().startswith(q)
    ][:4]
    return jsonify(resultados)


@app.route('/amigos/adicionar/<friend_id>')
def amigos_adicionar(friend_id):
    uid     = session['user_id']
    usuario = buscar_por_id(friend_id)

    if not usuario:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('amigos'))
    if uid == friend_id:
        flash('Você não pode adicionar a si mesmo.', 'error')
        return redirect(url_for('amigos'))
    if sao_amigos(uid, friend_id):
        flash(f'{usuario["nome"]} já é seu amigo.', 'error')
        return redirect(url_for('amigos'))

    adicionar_amizade(uid, friend_id)
    flash(f'{usuario["nome"]} adicionado à sua lista de amigos!', 'sucesso')
    return redirect(url_for('amigos'))


@app.route('/amigos/remover/<friend_id>')
def amigos_remover(friend_id):
    uid     = session['user_id']
    usuario = buscar_por_id(friend_id)
    nome    = usuario['nome'] if usuario else friend_id
    remover_amizade(uid, friend_id)
    flash(f'{nome} foi removido da sua lista de amigos.', 'sucesso')
    return redirect(url_for('amigos'))


# ==============================================================================
# ROTAS DE PERFIL DO USUÁRIO
# ==============================================================================

@app.route('/perfil')
def meu_perfil():
    return redirect(url_for('perfil', user_id=session['user_id']))


@app.route('/perfil/<user_id>')
def perfil(user_id):
    usuario = buscar_por_id(user_id)
    if not usuario:
        flash('Perfil não encontrado.', 'error')
        return redirect(url_for('index'))

    uid     = str(user_id)
    is_self = (uid == str(session['user_id']))

    # Biblioteca pública (vitrine de jogos) com horas jogadas simuladas
    biblioteca_ids = ler_biblioteca_usuario(uid)
    jogos_biblioteca = [
        {'game': GAMES[g], 'horas': horas_jogadas(uid, g)}
        for g in biblioteca_ids if g in GAMES
    ]
    total_horas = round(sum(j['horas'] for j in jogos_biblioteca), 1)

    # Lista de desejos
    desejos_ids   = ler_desejos_usuario(uid)
    jogos_desejos = [GAMES[g] for g in desejos_ids if g in GAMES]

    # Amigos, família e comentários
    amigos      = get_amigos_usuario(uid)
    familia     = buscar_familia_do_usuario(uid)
    comentarios = ler_comentarios_perfil(uid)

    is_friend = (not is_self) and sao_amigos(session['user_id'], uid)

    # Trocas de @usuário restantes (somente relevante no próprio perfil)
    trocas_restantes = None
    if is_self:
        trocas_restantes = LIMITE_TROCAS_USERNAME - usuario.get('trocas_username', 0)

    # Bio: idioma de origem detectado e tradução opcional sob demanda
    bio_texto         = usuario.get('notas', '') or ''
    bio_idioma_origem = i18n.detectar_idioma(bio_texto) if bio_texto else i18n.IDIOMA_PADRAO
    idioma_leitor     = (session.get('user_profile') or {}).get('linguagem') or i18n.IDIOMA_PADRAO
    bio_pode_traduzir = bool(bio_texto) and bio_idioma_origem != idioma_leitor
    bio_traduzir_flag = request.args.get('bio_traduzida') == '1'
    bio_traduzida     = None
    if bio_traduzir_flag and bio_pode_traduzir:
        bio_traduzida = i18n.traduzir(bio_texto, idioma_leitor, bio_idioma_origem)

    return render_template('perfil.html',
                           perfil_user=usuario,
                           is_self=is_self,
                           is_friend=is_friend,
                           jogos_biblioteca=jogos_biblioteca,
                           total_horas=total_horas,
                           jogos_desejos=jogos_desejos,
                           amigos=amigos,
                           familia=familia,
                           comentarios=comentarios,
                           trocas_restantes=trocas_restantes,
                           limite_trocas=LIMITE_TROCAS_USERNAME,
                           bio_idioma_origem=bio_idioma_origem,
                           bio_idioma_nome=i18n.nome_idioma(bio_idioma_origem),
                           bio_bandeira=i18n.bandeira(bio_idioma_origem),
                           bio_pode_traduzir=bio_pode_traduzir,
                           bio_traduzir_flag=bio_traduzir_flag,
                           bio_traduzida=bio_traduzida)


@app.route('/perfil/<user_id>/comentar', methods=['POST'])
def perfil_comentar(user_id):
    if not buscar_por_id(user_id):
        flash('Perfil não encontrado.', 'error')
        return redirect(url_for('index'))
    texto = request.form.get('texto', '').strip()
    if texto:
        adicionar_comentario(user_id, session['user_id'], texto)
        flash('Comentário publicado!', 'sucesso')
    else:
        flash('Escreva algo antes de publicar.', 'error')
    return redirect(url_for('perfil', user_id=user_id))


@app.route('/perfil/trocar_username', methods=['POST'])
def trocar_username():
    """Troca o @usuário do usuário logado (limite de LIMITE_TROCAS_USERNAME por conta)."""
    uid           = session['user_id']
    usuario_atual = buscar_por_id(uid)
    if not usuario_atual:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('index'))

    usados    = usuario_atual.get('trocas_username', 0)
    restantes = LIMITE_TROCAS_USERNAME - usados
    novo      = request.form.get('novo_username', '').strip()

    if restantes <= 0:
        flash(f'Você já atingiu o limite de {LIMITE_TROCAS_USERNAME} trocas de @usuário.', 'error')
        return redirect(url_for('meu_perfil'))
    if not novo:
        flash('Informe um novo @usuário.', 'error')
        return redirect(url_for('meu_perfil'))
    if not re.fullmatch(r'[A-Za-z0-9_]+', novo):
        flash('O @usuário deve conter apenas letras, números e underscore (_).', 'error')
        return redirect(url_for('meu_perfil'))
    if novo.lower() == usuario_atual['username'].lower():
        flash('O novo @usuário é igual ao atual.', 'error')
        return redirect(url_for('meu_perfil'))
    existente = buscar_por_username(novo)
    if existente and str(existente['id']) != str(uid):
        flash('Este @usuário já está em uso. Escolha outro.', 'error')
        return redirect(url_for('meu_perfil'))

    atualizar_usuario_db(uid, username=novo, trocas=usados + 1)
    flash(f'@usuário alterado para @{novo}! Trocas restantes: {restantes - 1}.', 'sucesso')
    return redirect(url_for('meu_perfil'))


# ==============================================================================
# ROTAS DE CARTEIRA E CONTA
# ==============================================================================

@app.route('/carteira')
def carteira():
    return render_template('carteira.html')


@app.route('/carteira/comprar', methods=['POST'])
def carteira_comprar():
    """Inicia a compra de saldo (para si ou presente a um amigo): leva à tela de pagamento."""
    try:
        valor = float(request.form.get('valor', '0'))
    except ValueError:
        valor = 0
    if valor <= 0:
        flash('Valor inválido para adicionar à carteira.', 'error')
        return redirect(url_for('carteira'))

    para        = request.form.get('para', 'self')
    target_name = 'sua conta'
    if para != 'self':
        amigo = buscar_por_id(para)
        if not amigo or not sao_amigos(session['user_id'], para):
            flash('Você só pode presentear saldo para amigos.', 'error')
            return redirect(url_for('index'))
        target_name = amigo['nome']

    return render_template('comprar_saldo.html', valor=valor, para=para, target_name=target_name)


@app.route('/carteira/pagar', methods=['POST'])
def carteira_pagar():
    """Finaliza a compra de saldo: credita a carteira do destinatário (mesmo fluxo de pagamento de um jogo)."""
    try:
        valor = float(request.form.get('valor', '0'))
    except ValueError:
        valor = 0
    para   = request.form.get('para', 'self')
    metodo = request.form.get('payment_method')

    if valor <= 0:
        flash('Valor inválido.', 'error')
        return redirect(url_for('carteira'))
    if not metodo:
        flash('Selecione uma forma de pagamento.', 'error')
        return redirect(url_for('carteira'))

    if para == 'self':
        session['wallet'] = round(session.get('wallet', 0.0) + valor, 2)
        session.modified = True
        salvar_carteira_usuario(session['user_id'], session['wallet'])
        flash(f'R$ {valor:.2f} adicionados à sua Carteira Steam via {metodo}!', 'sucesso')
        return redirect(url_for('carteira'))

    amigo = buscar_por_id(para)
    if not amigo or not sao_amigos(session['user_id'], para):
        flash('Você só pode presentear saldo para amigos.', 'error')
        return redirect(url_for('index'))
    novo_saldo = round(ler_carteira_usuario(para) + valor, 2)
    salvar_carteira_usuario(para, novo_saldo)
    flash(f'Você presenteou R$ {valor:.2f} em saldo Steam para {amigo["nome"]} via {metodo}!', 'sucesso')
    return redirect(url_for('perfil', user_id=para))


@app.route('/trocar_usuario')
def trocar_usuario():
    """Encerra a sessão e volta ao seletor de contas (estilo 'trocar de conta' da Steam)."""
    session.clear()
    flash('Selecione uma conta para entrar.', 'sucesso')
    return redirect(url_for('login'))


# ==============================================================================
# ROTAS PRINCIPAIS DA LOJA
# ==============================================================================

@app.route('/')
def index():
    return render_template('index.html', games=GAMES)


@app.route('/game/<game_id>')
def game(game_id):
    game_data  = GAMES.get(game_id)
    if not game_data:
        return i18n.traduzir("Jogo não encontrado", _idioma_usuario(), i18n.IDIOMA_PADRAO), 404
    show_modal = request.args.get('added') == '1'
    na_wishlist = game_id in session.get('wishlist', [])

    selected_lang = request.args.get('lang', 'todos')
    all_reviews = ler_avaliacoes_jogo(game_id)

    if selected_lang != 'todos':
        filtered_reviews = [r for r in all_reviews if r.get('linguagem') == selected_lang]
    else:
        filtered_reviews = all_reviews

    filtered_reviews = sorted(filtered_reviews, key=lambda x: x.get('votos_uteis', 0), reverse=True)

    return render_template('game.html', game=game_data, show_modal=show_modal,
                           na_wishlist=na_wishlist,
                           reviews=filtered_reviews,
                           selected_lang=selected_lang)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    name    = request.form.get('name')
    details = request.form.get('details')
    dob_str = request.form.get('dob')
    linguagem = request.form.get('linguagem', i18n.IDIOMA_PADRAO)
    if linguagem not in i18n.IDIOMAS_SUPORTADOS:
        linguagem = i18n.IDIOMA_PADRAO
    session['user_profile'] = {'name': name, 'details': details, 'linguagem': linguagem}
    if dob_str:
        session['user_dob'] = dob_str
    session.modified = True
    # Dados do usuário ficam em usuarios.txt; idioma é da máquina (maquina.txt).
    atualizar_usuario_db(session['user_id'], nome=name, notas=details, dob=dob_str or None)
    salvar_linguagem_maquina(linguagem)
    flash('Dados do perfil atualizados com sucesso!', 'sucesso')
    return redirect(request.referrer or url_for('index'))


@app.route('/add_to_cart/<game_id>', methods=['POST'])
def add_to_cart(game_id):
    game_data     = GAMES.get(game_id)
    purchase_type = request.form.get('purchase_type', 'self')

    if not game_data:
        return i18n.traduzir("Jogo não encontrado", _idioma_usuario(), i18n.IDIOMA_PADRAO), 404

    if purchase_type == 'self':
        if game_id in session['library'] or any(i['id'] == game_id and not i['is_gift'] for i in session['cart']):
            flash('Você já possui este jogo ou ele já está no carrinho.', 'error')
            return redirect(url_for('game', game_id=game_id))

    if game_data['age_rating'] > 0 and purchase_type == 'self':
        user_dob_str = session.get('user_dob') or request.form.get('dob')
        if not user_dob_str or user_dob_str == 'none':
            flash('Por favor, configure ou confirme sua data de nascimento.', 'error')
            return redirect(url_for('game', game_id=game_id))
        try:
            dob      = datetime.strptime(user_dob_str, '%Y-%m-%d')
            hoje     = datetime.today()
            user_age = hoje.year - dob.year - ((hoje.month, hoje.day) < (dob.month, dob.day))
            if user_age < game_data['age_rating']:
                flash(f'Bloqueio: Sua idade ({user_age} anos) é inferior à classificação do jogo (+{game_data["age_rating"]}).', 'error')
                return redirect(url_for('game', game_id=game_id))
            if not session.get('user_dob'):
                session['user_dob'] = user_dob_str
                session.modified = True
        except ValueError:
            flash('Formato de data inválido.', 'error')
            return redirect(url_for('game', game_id=game_id))

    preco = calcular_preco(game_id)
    cart_item = {
        'cart_item_id':   f"{game_id}_{purchase_type}_{datetime.now().timestamp()}",
        'id':             game_data['id'],
        'name':           game_data['name'],
        'price':          preco['final'],
        'original_price': preco['original'],
        'discount_pct':   preco['pct'],
        'is_gift':        purchase_type == 'gift'
    }
    session['cart'].append(cart_item)
    session.modified = True
    return redirect(url_for('game', game_id=game_id, added=1))


@app.route('/game/<game_id>/review', methods=['POST'])
def submit_review(game_id):
    owned = game_id in session.get('library', [])
    if session.get('family') and game_id in session['family'].get('library_pool', []):
        owned = True

    if not owned:
        flash("Bloqueio [FE01]: Você precisa possuir este jogo para publicar uma análise.", "error")
        return redirect(url_for('game', game_id=game_id))

    recomenda = request.form.get('recomenda') == 'sim'
    comentario = request.form.get('comentario', '').strip()

    if not comentario:
        flash("Erro [FE02]: Por favor, escreva um comentário para descrever sua experiência.", "error")
        return redirect(url_for('game', game_id=game_id))

    idioma_usuario = session['user_profile'].get('linguagem', i18n.IDIOMA_PADRAO)
    salvar_avaliacao(game_id, session['user_id'], recomenda, comentario, idioma_usuario)
    flash("Sua análise foi publicada com sucesso!", "sucesso")
    return redirect(url_for('game', game_id=game_id))


@app.route('/game/<game_id>/review/<autor_id>/vote/<vote_type>')
def vote_review(game_id, autor_id, vote_type):
    ok, mensagem, categoria = votar_avaliacao(game_id, autor_id, session['user_id'], vote_type)
    flash(mensagem, categoria)
    return redirect(url_for('game', game_id=game_id))

@app.route('/cart')
def cart():
    uid                      = session['user_id']
    total                    = sum(item['price'] for item in session['cart'])
    friends                  = get_amigos_dict(uid)
    gift_items               = [item for item in session['cart'] if item['is_gift']]
    distinct_gift_ids        = set(item['id'] for item in gift_items)
    multiple_different_gifts = len(distinct_gift_ids) > 1
    return render_template('cart.html',
                           cart=session['cart'],
                           total=total,
                           friends=friends,
                           gift_items=gift_items,
                           multiple_different_gifts=multiple_different_gifts)


@app.route('/remove_from_cart/<cart_item_id>')
def remove_from_cart(cart_item_id):
    session['cart'] = [i for i in session['cart'] if i['cart_item_id'] != cart_item_id]
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/clear_cart')
def clear_cart():
    session['cart'] = []
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/proceed_checkout', methods=['POST'])
def proceed_checkout():
    cart_items = session.get('cart', [])
    uid        = session['user_id']
    friends    = get_amigos_dict(uid)

    for item in cart_items:
        if item['is_gift']:
            friend_id = request.form.get(f"recipient_{item['cart_item_id']}")
            if not friend_id:
                flash('Por favor, selecione o destinatário para todos os presentes.', 'error')
                return redirect(url_for('cart'))
            if friend_id not in friends:
                flash('Destinatário inválido. Selecione um amigo da sua lista.', 'error')
                return redirect(url_for('cart'))
            historico_amigo = session['gifts_sent'].get(friend_id, [])
            if item['id'] in historico_amigo:
                flash(f"Remova ou altere: {friends[friend_id]} já possui '{item['name']}'!", 'error')
                return redirect(url_for('cart'))
            item['recipient_id']   = friend_id
            item['recipient_name'] = friends[friend_id]

    session['cart'] = cart_items
    session.modified = True
    return redirect(url_for('checkout'))


@app.route('/library')
def library():
    uid          = session['user_id']
    user_dob_str = session.get('user_dob')
    user_age     = None

    if user_dob_str:
        try:
            dob      = datetime.strptime(user_dob_str, '%Y-%m-%d')
            hoje     = datetime.today()
            user_age = hoje.year - dob.year - ((hoje.month, hoje.day) < (dob.month, dob.day))
        except ValueError:
            pass

    minha_biblioteca = set(session.get('library', []) or [])
    familia_pool     = set()
    if session.get('family'):
        familia_pool = set(session['family'].get('library_pool', []))

    todos_ids = minha_biblioteca | familia_pool

    jogos_disponiveis   = {}
    ids_familia_pool    = []   # jogos disponíveis SOMENTE via Família Steam (o usuário não comprou)
    ids_minha_biblioteca = list(minha_biblioteca)

    for gid in todos_ids:
        if gid not in GAMES:
            continue
        game = GAMES[gid]
        # Filtro de idade: jogo com restrição NÃO aparece se usuário não tem DOB ou é menor de idade
        if game['age_rating'] > 0:
            if user_age is None or user_age < game['age_rating']:
                continue
        jogos_disponiveis[gid] = game
        # "Via Família" = está no pool E NÃO foi comprado pelo próprio usuário.
        # Assim o slider separa jogos próprios dos que existem graças à família.
        if gid in familia_pool and gid not in minha_biblioteca:
            ids_familia_pool.append(gid)

    tem_familia = bool(session.get('family'))

    return render_template('library.html',
                           games=jogos_disponiveis,
                           ids_familia_pool=ids_familia_pool,
                           ids_minha_biblioteca=ids_minha_biblioteca,
                           tem_familia=tem_familia)


# ==============================================================================
# ROTAS DE LISTA DE DESEJOS (WISHLIST)
# ==============================================================================

@app.route('/wishlist')
def wishlist():
    desejos_ids   = [g for g in session.get('wishlist', []) if g in GAMES]
    jogos_desejos = [GAMES[g] for g in desejos_ids]
    return render_template('wishlist.html', jogos=jogos_desejos)


@app.route('/wishlist/add/<game_id>')
def wishlist_add(game_id):
    if game_id not in GAMES:
        flash('Jogo não encontrado.', 'error')
        return redirect(request.referrer or url_for('index'))

    if game_id in session.get('library', []):
        flash('Você já possui este jogo na sua biblioteca.', 'error')
        return redirect(request.referrer or url_for('game', game_id=game_id))

    desejos = session.get('wishlist', [])
    if game_id in desejos:
        flash('Este jogo já está na sua lista de desejos.', 'error')
    else:
        desejos.append(game_id)
        session['wishlist'] = desejos
        session.modified = True
        salvar_desejos_usuario(session['user_id'], desejos)
        flash(f"'{GAMES[game_id]['name']}' foi adicionado à sua lista de desejos!", 'sucesso')
    return redirect(request.referrer or url_for('game', game_id=game_id))


@app.route('/wishlist/remove/<game_id>')
def wishlist_remove(game_id):
    desejos = [g for g in session.get('wishlist', []) if g != game_id]
    session['wishlist'] = desejos
    session.modified = True
    salvar_desejos_usuario(session['user_id'], desejos)
    nome = GAMES.get(game_id, {}).get('name', 'Jogo')
    flash(f"'{nome}' foi removido da sua lista de desejos.", 'sucesso')
    return redirect(request.referrer or url_for('wishlist'))


@app.route('/checkout')
def checkout():
    if not session['cart']:
        return redirect(url_for('index'))
    total = sum(item['price'] for item in session['cart'])
    return render_template('checkout.html', cart=session['cart'], total=total)


@app.route('/process_payment', methods=['POST'])
def process_payment():
    total          = sum(item['price'] for item in session['cart'])
    use_wallet     = 'use_wallet' in request.form and session['wallet'] > 0
    payment_method = request.form.get('payment_method')
    valor_a_pagar  = total
    detalhes       = []

    if use_wallet:
        if session['wallet'] >= valor_a_pagar:
            session['wallet'] -= valor_a_pagar
            detalhes.append(f"R$ {valor_a_pagar:.2f} da Carteira")
            valor_a_pagar = 0
        else:
            detalhes.append(f"R$ {session['wallet']:.2f} da Carteira")
            valor_a_pagar -= session['wallet']
            session['wallet'] = 0.0

    if valor_a_pagar > 0:
        detalhes.append(f"R$ {valor_a_pagar:.2f} via {payment_method}")

    familia_modificada = False

    for item in session['cart']:
        if item['is_gift']:
            fid = item['recipient_id']
            if fid not in session['gifts_sent']:
                session['gifts_sent'][fid] = []
            session['gifts_sent'][fid].append(item['id'])
            flash(f"Presente '{item['name']}' enviado para {item['recipient_name']}!", 'sucesso')
            if session.get('family'):
                amigo_na_familia = any(
                    str(m.get('id', '')) == str(fid) or m.get('name') == item['recipient_name']
                    for m in session['family']['members']
                )
                if amigo_na_familia:
                    if item['id'] not in session['family']['library_pool']:
                        session['family']['library_pool'].append(item['id'])
                    session['family']['licenses'][item['id']] = session['family']['licenses'].get(item['id'], 0) + 1
                    familia_modificada = True
                    flash(f"Como {item['recipient_name']} está na Família, '{item['name']}' foi adicionado ao Pool!", 'sucesso')
        else:
            if item['id'] not in session['library']:
                session['library'].append(item['id'])
                if session.get('family'):
                    if item['id'] not in session['family']['library_pool']:
                        session['family']['library_pool'].append(item['id'])
                    session['family']['licenses'][item['id']] = session['family']['licenses'].get(item['id'], 0) + 1
                    familia_modificada = True
            # Comprou para si: sai da lista de desejos (comportamento da Steam)
            if item['id'] in session.get('wishlist', []):
                session['wishlist'] = [g for g in session['wishlist'] if g != item['id']]

    # Persiste biblioteca do usuário
    salvar_biblioteca_usuario(session['user_id'], session['library'])

    # Persiste lista de desejos (jogos comprados saem dela)
    salvar_desejos_usuario(session['user_id'], session.get('wishlist', []))

    # Persiste o saldo da carteira (não se perde ao reconectar)
    salvar_carteira_usuario(session['user_id'], session['wallet'])

    # Persiste família se foi modificada
    if familia_modificada and session.get('family'):
        atualizar_familia(session['family'])

    session['cart'] = []
    session.modified = True
    flash(f"Compra finalizada! ({', '.join(detalhes)})", 'sucesso')
    return redirect(url_for('index'))


# ==============================================================================
# ROTAS DE FAMÍLIA
# ==============================================================================

@app.route('/family')
def family():
    uid     = session['user_id']
    friends = get_amigos_dict(uid)

    # Contagem persistida de licenças em uso por jogo (parentes jogando agora)
    em_uso_por_jogo = {}
    if session.get('family'):
        for gid in session['family'].get('library_pool', []):
            em_uso_por_jogo[gid] = em_uso_total(session['family'], gid)

    return render_template('family.html', friends=friends, games=GAMES,
                           em_uso_por_jogo=em_uso_por_jogo)


@app.route('/create_family', methods=['POST'])
def create_family():
    family_name = request.form.get('family_name')
    uid         = session['user_id']

    if session.get('family'):
        flash("Saia da sua família atual antes de criar uma nova.", "error")
        return redirect(url_for('family'))
    if session.get('family_cooldown'):
        flash("Bloqueio: Período de carência de 1 ano ativo para esta conta.", "error")
        return redirect(url_for('family'))

    shared_library = list(dict.fromkeys(session.get('library', [])))
    nova_familia = {
        'id':                 f"fam_{datetime.now().timestamp()}",
        'name':               family_name,
        'created_at':         datetime.now().strftime("%d/%m/%Y %H:%M"),
        'creator':            session['user_profile']['name'],   # criador original (nunca muda)
        'creator_id':         uid,
        'founder':            session['user_profile']['name'],   # líder atual (muda com transferência)
        'founder_id':         uid,
        'members':            [{'name': session['user_profile']['name'], 'id': uid}],
        'member_ids':         [uid],
        'library_pool':       shared_library,
        'licenses':           {gid: 1 for gid in shared_library},
        'occupied_by_others': {}
    }
    session['family'] = nova_familia
    session.modified  = True
    salvar_nova_familia(nova_familia)
    flash(f"Família '{family_name}' criada com sucesso!", "sucesso")
    return redirect(url_for('family'))


@app.route('/family/invite/<friend_id>')
def family_invite(friend_id):
    if not session.get('family'):
        flash("Você precisa criar uma família primeiro.", "error")
        return redirect(url_for('family'))

    family_data = session['family']

    if len(family_data['members']) >= 6:
        flash("Bloqueio: Uma Família não pode ter mais de 6 membros.", "error")
        return redirect(url_for('family'))

    uid     = session['user_id']
    friends = get_amigos_dict(uid)
    if friend_id not in friends:
        flash("Você só pode convidar amigos da sua lista.", "error")
        return redirect(url_for('family'))

    friend_name = friends[friend_id]

    # Garante que member_ids existe (compatibilidade)
    if 'member_ids' not in family_data:
        family_data['member_ids'] = [m.get('id', '') for m in family_data['members']]

    if friend_id in family_data['member_ids']:
        flash(f"{friend_name} já faz parte desta família.", "error")
        return redirect(url_for('family'))

    # Adiciona membro
    family_data['members'].append({'name': friend_name, 'id': friend_id})
    family_data['member_ids'].append(friend_id)

    # Adiciona jogos do amigo (biblioteca persistida) ao pool
    jogos_adicionados = []
    biblioteca_amigo  = ler_biblioteca_usuario(friend_id)
    for jogo_id in biblioteca_amigo:
        qtd = 1
        if jogo_id not in family_data['library_pool']:
            family_data['library_pool'].append(jogo_id)
        family_data['licenses'][jogo_id] = family_data['licenses'].get(jogo_id, 0) + qtd
        nome_jogo = GAMES.get(jogo_id, {}).get('name', 'Jogo Desconhecido')
        if nome_jogo not in jogos_adicionados:
            jogos_adicionados.append(nome_jogo)

    # Também considera presentes enviados nesta sessão
    jogos_do_amigo = session.get('gifts_sent', {}).get(friend_id, [])
    for jogo_id in set(jogos_do_amigo):
        qtd = jogos_do_amigo.count(jogo_id)
        if jogo_id not in family_data['library_pool']:
            family_data['library_pool'].append(jogo_id)
        family_data['licenses'][jogo_id] = family_data['licenses'].get(jogo_id, 0) + qtd
        nome_jogo = GAMES.get(jogo_id, {}).get('name', 'Jogo Desconhecido')
        if nome_jogo not in jogos_adicionados:
            jogos_adicionados.append(nome_jogo)

    session['family'] = family_data
    session.modified  = True
    atualizar_familia(family_data)

    if jogos_adicionados:
        flash(f"Convite aceito! {friend_name} entrou e trouxe para o Pool: {', '.join(jogos_adicionados)}.", "sucesso")
    else:
        flash(f"Convite aceito! {friend_name} entrou na família.", "sucesso")

    return redirect(url_for('family'))


@app.route('/family/transfer_leadership/<member_name>', methods=['POST'])
def family_transfer_leadership(member_name):
    if not session.get('family'):
        flash("Você não pertence a uma família.", "error")
        return redirect(url_for('family'))

    nome_atual = session['user_profile']['name']
    if session['family']['founder'] != nome_atual:
        flash("Apenas o fundador pode transferir a liderança.", "error")
        return redirect(url_for('family'))
    if not any(m['name'] == member_name for m in session['family']['members']):
        flash("Membro não encontrado na família.", "error")
        return redirect(url_for('family'))
    if member_name == nome_atual:
        flash("Você já é o líder da família.", "error")
        return redirect(url_for('family'))

    session['family']['founder'] = member_name
    # Atualiza founder_id também
    for m in session['family']['members']:
        if m['name'] == member_name:
            session['family']['founder_id'] = m.get('id', '')
            break
    session.modified = True
    atualizar_familia(session['family'])
    flash(f"Liderança transferida para {member_name}! Você continua como membro.", "sucesso")
    return redirect(url_for('family'))


# @app.route('/family/play/<game_id>')
# def family_play(game_id):
#     if not session.get('family'):
#         flash("Você não pertence a uma família.", "error")
#         return redirect(url_for('family'))

#     game_data = GAMES.get(game_id)

#     # Já está executando este mesmo título: nada a fazer (não recontabiliza).
#     if session.get('active_game') == game_id:
#         return redirect(url_for('family'))

#     if session.get('active_game') and session.get('active_game') != game_id:
#         jogo_anterior = GAMES.get(session['active_game'])['name']
#         flash(f"Bloqueio: Você já está jogando '{jogo_anterior}'. Feche-o primeiro.", "error")
#         return redirect(url_for('family'))

#     if game_id == '3':
#         flash("Bloqueio: Este jogo possui restrições do desenvolvedor que impedem o compartilhamento.", "error")
#         return redirect(url_for('family'))

#     if game_data['age_rating'] > 0:
#         user_dob_str = session.get('user_dob')
#         if not user_dob_str:
#             flash(f"Bloqueio: '{game_data['name']}' é classificado +{game_data['age_rating']} anos. "
#                   f"Registre sua data de nascimento no perfil.", "error")
#             return redirect(url_for('family'))
#         try:
#             dob      = datetime.strptime(user_dob_str, '%Y-%m-%d')
#             hoje     = datetime.today()
#             user_age = hoje.year - dob.year - ((hoje.month, hoje.day) < (dob.month, dob.day))
#             if user_age < game_data['age_rating']:
#                 flash(f"Bloqueio: Sua idade verificada ({user_age} anos) é inferior à classificação +{game_data['age_rating']}.", "error")
#                 return redirect(url_for('family'))
#         except ValueError:
#             flash("Erro ao verificar data de nascimento. Atualize seu perfil.", "error")
#             return redirect(url_for('family'))

#     # Modo Offline: a licença foi validada no último login online, então o jogo
#     # abre sem ocupar uma licença do pool (não soma +1 em "Em uso por parentes").
#     if session.get('offline_mode'):
#         iniciar_sessao_jogo(session['user_id'], session['family']['id'], game_id, modo='offline')
#         session['active_game'] = game_id
#         session['show_pe01_for'] = None
#         session.modified = True
#         flash("Modo Offline [A01]: Licença validada no último login online. Acesso permitido (não ocupa licença do pool).", "sucesso")
#         return redirect(url_for('family'))

#     total_licencas = session['family']['licenses'].get(game_id, 0)
#     if total_licencas == 0:
#         flash("Bloqueio: Ninguém da sua família comprou este jogo ainda.", "error")
#         return redirect(url_for('family'))

#     # Licenças ocupadas por OUTROS no momento (o usuário atual ainda não iniciou)
#     em_uso = em_uso_total(session['family'], game_id)
#     if em_uso >= total_licencas:
#         flash(f"Bloqueio: Todas as {total_licencas} licença(s) estão em uso no momento.", "error")
#         session['show_pe01_for'] = game_id
#         session.modified = True
#         return redirect(url_for('family'))

#     # Registra a sessão de forma persistente: continua valendo se trocar de conta.
#     iniciar_sessao_jogo(session['user_id'], session['family']['id'], game_id, modo='online')
#     session['active_game']   = game_id
#     session['show_pe01_for'] = None
#     session.modified = True
#     flash(f"'{game_data['name']}' iniciado! Licença temporária alocada. Saves e conquistas são individuais.", "sucesso")
#     return redirect(url_for('family'))


# @app.route('/family/stop')
# def family_stop():
#     # Devolve a licença ao pool (decrementa "Em uso por parentes" de forma persistente).
#     encerrar_sessao_jogo(session['user_id'])
#     session['active_game'] = None
#     session.modified = True
#     flash("Jogo encerrado. A licença foi devolvida ao banco da família.", "sucesso")
#     return redirect(url_for('family'))


@app.route('/play/<game_id>')
def play_game(game_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    game_data = GAMES.get(game_id)
    if not game_data:
        flash("Jogo não encontrado.", "error")
        return redirect(url_for('library'))

    # CAPTURA E PERSISTE A ORIGEM: se veio da biblioteca ou da família
    src = request.args.get('src', 'library')
    if src in ('library', 'family'):
        session['game_source'] = src

    # 1. Verifica Múltiplas Instâncias
    if session.get('active_game') == game_id:
        return render_template('playing.html', game=game_data, src=session.get('game_source', 'library'))
        
    if session.get('active_game') and session.get('active_game') != game_id:
        jogo_anterior = GAMES.get(session.get('active_game'))['name']
        flash(f"Bloqueio: Você já está jogando '{jogo_anterior}'. Feche-o primeiro antes de iniciar outro título.", "error")
        return redirect(url_for(session.get('game_source', 'library')))

    # 2. Restrição de Idade
    if game_data['age_rating'] > 0:
        user_dob_str = session.get('user_dob')
        if not user_dob_str or user_dob_str == 'none':
            flash(f"Bloqueio: Sua data de nascimento não está configurada no perfil.", "error")
            return redirect(url_for(session.get('game_source', 'library')))
        try:
            dob = datetime.strptime(user_dob_str, '%Y-%m-%d')
            hoje = datetime.today()
            user_age = hoje.year - dob.year - ((hoje.month, hoje.day) < (dob.month, dob.day))
            if user_age < game_data['age_rating']:
                flash(f"Bloqueio: Sua idade ({user_age} anos) é inferior à classificação exigida (+{game_data['age_rating']}).", "error")
                return redirect(url_for(session.get('game_source', 'library')))
        except ValueError:
            flash("Sua data de nascimento não está configurada corretamente.", "error")
            return redirect(url_for(session.get('game_source', 'library')))

    # 3. Verificação de Licenças Unificadas do Pool
    em_familia = bool(session.get('family'))
    if em_familia:
        if game_id not in session['family']['library_pool']:
            flash("Bloqueio: Ninguém da sua família possui a licença deste jogo.", "error")
            return redirect(url_for(session.get('game_source', 'library')))
            
        total_licencas = session['family']['licenses'].get(game_id, 0)
        em_uso = em_uso_total(session['family'], game_id)
        
        if not session.get('offline_mode') and em_uso >= total_licencas:
            flash(f"Bloqueio: Todas as {total_licencas} licença(s) unificadas deste jogo já estão em uso por outros membros.", "error")
            session['show_pe01_for'] = game_id
            session.modified = True
            return redirect(url_for(session.get('game_source', 'library')))
            
        if not session.get('offline_mode'):
            iniciar_sessao_jogo(session['user_id'], session['family']['id'], game_id, modo='online')
        else:
            iniciar_sessao_jogo(session['user_id'], session['family']['id'], game_id, modo='offline')
            flash("Modo Offline: Jogo iniciado via cache local (não ocupa licença da nuvem).", "sucesso")
    else:
        if game_id not in session.get('library', []):
            flash("Bloqueio: Você não possui a licença deste jogo.", "error")
            return redirect(url_for('library'))
            
        if session.get('offline_mode'):
            flash("Modo Offline: Jogo iniciado via cache local.", "sucesso")

    session['active_game'] = game_id
    session['show_pe01_for'] = None
    session.modified = True
    return render_template('playing.html', game=game_data, src=session.get('game_source', 'library'))


@app.route('/stop_game')
def stop_game():
    # Recupera o destino salvo antes de fechar
    destino = session.get('game_source', 'library')
    
    if session.get('active_game'):
        if session.get('family'):
            encerrar_sessao_jogo(session['user_id'])
            
        session['active_game'] = None
        session.modified = True
        flash("Jogo encerrado. A licença foi liberada e os saves sincronizados.", "sucesso")
        
    return redirect(url_for(destino))

@app.route('/family/toggle_npc/<game_id>')
def family_toggle_npc(game_id):
    if 'family' in session and session['family']:
        atual = session['family']['occupied_by_others'].get(game_id, False)
        session['family']['occupied_by_others'][game_id] = not atual
        session.modified = True
        status = "OCUPOU" if not atual else "LIBEROU"
        flash(f"Simulação: Outro membro da família {status} uma licença deste jogo!", "sucesso")
    return redirect(url_for('family'))


@app.route('/family/toggle_offline')
def family_toggle_offline():
    # Não permite alternar online/offline com um jogo em execução (evita
    # inconsistência na contagem de licenças do pool).
    if session.get('active_game'):
        flash("Bloqueio: Feche o jogo em execução antes de alterar o Modo Offline.", "error")
        return redirect(url_for('family'))
    session['offline_mode'] = not session.get('offline_mode', False)
    session.modified = True
    status = "LIGADO" if session['offline_mode'] else "DESLIGADO"
    flash(f"Modo Offline da Steam: {status} [A01]", "sucesso")
    return redirect(url_for('family'))


# ==============================================================================
# ROTA ADMINISTRATIVA OCULTA - SIMULAÇÃO DE PROMOÇÕES
# Acessível somente digitando /admin na URL (não há botões para chegar aqui).
# ==============================================================================

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        acao = request.form.get('acao', '').strip()

        if acao == 'criar':
            nome  = request.form.get('nome', '').strip() or 'Promoção'
            modo  = request.form.get('modo', 'evento')
            usar_agora = request.form.get('iniciar_agora') == 'on'
            data_inicio = _data_str_hoje() if usar_agora else request.form.get('data_inicio', '').strip()
            data_fim    = request.form.get('data_fim', '').strip()
            # Coleta descontos do form (cobre tanto seleção customizada quanto evento manual)
            descontos = {}
            for gid in GAMES:
                valor = request.form.get(f'desconto_{gid}', '').strip()
                if not valor:
                    continue
                try:
                    pct = int(float(valor))
                except ValueError:
                    pct = 0
                if pct > 0:
                    descontos[gid] = pct
            ok, resultado = criar_promocao(nome, modo, data_inicio, data_fim, descontos)
            flash(resultado if isinstance(resultado, str) else f"Promoção '{resultado['nome']}' criada.",
                  'sucesso' if ok else 'error')

        elif acao == 'aplicar_publisher':
            # Atalho: criar promoção aplicando o mesmo % a todos os jogos de um publisher
            publisher = request.form.get('publisher', '').strip()
            pct_raw   = request.form.get('pct_publisher', '').strip()
            nome      = request.form.get('nome_publisher', '').strip() or f"Promoção {publisher}"
            usar_agora  = request.form.get('iniciar_agora_pub') == 'on'
            data_inicio = _data_str_hoje() if usar_agora else request.form.get('data_inicio_pub', '').strip()
            data_fim    = request.form.get('data_fim_pub', '').strip()
            try:
                pct = int(float(pct_raw))
            except ValueError:
                pct = 0
            descontos = {gid: pct for gid, g in GAMES.items() if g.get('publisher') == publisher}
            if not descontos:
                flash("Publisher sem jogos cadastrados.", 'error')
            else:
                ok, resultado = criar_promocao(nome, 'evento', data_inicio, data_fim, descontos)
                flash(resultado if isinstance(resultado, str) else f"Promoção '{resultado['nome']}' criada para {publisher}.",
                      'sucesso' if ok else 'error')

        elif acao == 'remover_promocao':
            promo_id = request.form.get('promo_id', '').strip()
            ok, msg = remover_promocao(promo_id)
            flash(msg, 'sucesso' if ok else 'error')

        elif acao == 'remover_jogo':
            promo_id = request.form.get('promo_id', '').strip()
            game_id  = request.form.get('game_id', '').strip()
            ok, msg = remover_desconto_de_promocao(promo_id, game_id)
            flash(msg, 'sucesso' if ok else 'error')

        elif acao == 'remover_publisher':
            promo_id  = request.form.get('promo_id', '').strip()
            publisher = request.form.get('publisher', '').strip()
            ok, msg = remover_publisher_de_promocao(promo_id, publisher)
            flash(msg, 'sucesso' if ok else 'error')

        else:
            flash("Ação desconhecida.", 'error')

        return redirect(url_for('admin'))

    promo            = ler_promocao()
    publishers       = agrupar_jogos_por_publisher()
    historico        = ler_historico_promocoes()
    hoje             = _data_str_hoje()
    return render_template(
        'admin.html',
        promo=promo, games=GAMES, publishers=publishers,
        historico=list(reversed(historico)),  # mais recentes primeiro
        hoje=hoje,
    )


# ==============================================================================
# UTILITÁRIOS
# ==============================================================================

@app.route('/reset')
def reset_session():
    """Limpa todos os cookies (sessão) e zera todos os arquivos de dados,
    exceto usuarios.txt (as contas cadastradas são preservadas)."""
    session.clear()
    for caminho in (MAQUINA_FILE, AMIZADES_FILE, BIBLIOTECA_FILE,
                    FAMILIAS_FILE, CARTEIRAS_FILE, SESSOES_FILE,
                    DESEJOS_FILE, PROMOCOES_FILE, HISTORICO_PROMOCOES_FILE,
                    COMENTARIOS_FILE):
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
        except OSError:
            pass
    _garantir_arquivos()  # recria os arquivos vazios (apenas cabeçalhos)
    return redirect(url_for('login'))


if __name__ == '__main__':
    _garantir_arquivos()
    app.run(debug=True)
