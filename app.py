from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import os
import json

app = Flask(__name__)
app.secret_key = 'chave_secreta_super_segura'

# ---- CATÁLOGO DE JOGOS (DADOS FIXOS) ----
GAMES = {
    '1': {'id': '1', 'name': 'Aventura Épica',       'price': 150.00, 'age_rating': 10, 'description': 'Explore masmorras e derrote monstros com amigos nesta jornada incrível.'},
    '2': {'id': '2', 'name': 'Sobrevivência Sombria', 'price': 90.00,  'age_rating': 18, 'description': 'Jogo de terror com zumbis. Sobreviva a noites aterrorizantes com recursos escassos.'},
    '3': {'id': '3', 'name': 'Corrida Divertida',     'price': 45.00,  'age_rating': 0,  'description': 'Corridas para toda a família. Karts coloridos e pistas malucas!'}
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

CARTEIRA_INICIAL = 100.00


def _garantir_arquivos():
    """Cria a pasta de dados e os arquivos base se não existirem."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if not os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Banco de Dados de Usuários\n")
            f.write("# Formato: id | usuario | senha | data_nascimento | nome_exibicao | notas\n")
            f.write("# Exemplo: 1 | joao123 | senha456 | 1990-05-15 | João Silva | Jogador casual\n")
            f.write("# Dica: data_nascimento como 'none' significa que o usuário não a cadastrou.\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(MAQUINA_FILE):
        with open(MAQUINA_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Contas desta Máquina\n")
            f.write("# Cada linha contém o ID de um usuário que já fez login neste computador.\n")
            f.write("# =============================================================================\n")

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
                        'notas':    partes[5] if len(partes) > 5 else ''
                    })
    except FileNotFoundError:
        pass
    return usuarios


def salvar_usuario(usuario):
    _garantir_arquivos()
    with open(USUARIOS_FILE, 'a', encoding='utf-8') as f:
        dob_val   = usuario['dob'] if usuario['dob'] else 'none'
        notas_val = usuario.get('notas', '').replace('|', '-')
        f.write(f"{usuario['id']} | {usuario['username']} | {usuario['senha']} | {dob_val} | {usuario['nome']} | {notas_val}\n")


def buscar_por_username(username):
    for u in ler_usuarios():
        if u['username'].lower() == username.lower():
            return u
    return None


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
                if linha and not linha.startswith('#'):
                    ids.append(linha)
    except FileNotFoundError:
        pass
    return ids


def registrar_maquina(uid):
    if str(uid) not in ler_ids_maquina():
        _garantir_arquivos()
        with open(MAQUINA_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{uid}\n")


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
    session['cart']          = []
    session['gifts_sent']    = {}
    session['user_dob']      = usuario['dob']
    session['user_profile']  = {
        'name':    usuario['nome'],
        'details': usuario.get('notas', '')
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
        'wallet': 100.00, 'library': [], 'cart': [], 'gifts_sent': {},
        'user_dob': None, 'user_profile': {'name': 'Usuário', 'details': ''},
        'family': None, 'family_cooldown': False,
        'offline_mode': False, 'active_game': None, 'show_pe01_for': None
    }
    for chave, valor in padroes.items():
        if chave not in session:
            session[chave] = valor


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
# ROTAS PRINCIPAIS DA LOJA
# ==============================================================================

@app.route('/')
def index():
    return render_template('index.html', games=GAMES)


@app.route('/game/<game_id>')
def game(game_id):
    game_data  = GAMES.get(game_id)
    if not game_data:
        return "Jogo não encontrado", 404
    show_modal = request.args.get('added') == '1'
    return render_template('game.html', game=game_data, show_modal=show_modal)


@app.route('/update_profile', methods=['POST'])
def update_profile():
    name    = request.form.get('name')
    details = request.form.get('details')
    dob_str = request.form.get('dob')
    session['user_profile'] = {'name': name, 'details': details}
    if dob_str:
        session['user_dob'] = dob_str
    session.modified = True
    flash('Dados do perfil atualizados com sucesso!', 'sucesso')
    return redirect(request.referrer or url_for('index'))


@app.route('/add_to_cart/<game_id>', methods=['POST'])
def add_to_cart(game_id):
    game_data     = GAMES.get(game_id)
    purchase_type = request.form.get('purchase_type', 'self')

    if not game_data:
        return "Jogo não encontrado", 404

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

    cart_item = {
        'cart_item_id': f"{game_id}_{purchase_type}_{datetime.now().timestamp()}",
        'id':      game_data['id'],
        'name':    game_data['name'],
        'price':   game_data['price'],
        'is_gift': purchase_type == 'gift'
    }
    session['cart'].append(cart_item)
    session.modified = True
    return redirect(url_for('game', game_id=game_id, added=1))


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

    # Persiste biblioteca do usuário
    salvar_biblioteca_usuario(session['user_id'], session['library'])

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


@app.route('/family/play/<game_id>')
def family_play(game_id):
    if not session.get('family'):
        flash("Você não pertence a uma família.", "error")
        return redirect(url_for('family'))

    game_data = GAMES.get(game_id)

    # Já está executando este mesmo título: nada a fazer (não recontabiliza).
    if session.get('active_game') == game_id:
        return redirect(url_for('family'))

    if session.get('active_game') and session.get('active_game') != game_id:
        jogo_anterior = GAMES.get(session['active_game'])['name']
        flash(f"Bloqueio: Você já está jogando '{jogo_anterior}'. Feche-o primeiro.", "error")
        return redirect(url_for('family'))

    if game_id == '3':
        flash("Bloqueio: Este jogo possui restrições do desenvolvedor que impedem o compartilhamento.", "error")
        return redirect(url_for('family'))

    if game_data['age_rating'] > 0:
        user_dob_str = session.get('user_dob')
        if not user_dob_str:
            flash(f"Bloqueio: '{game_data['name']}' é classificado +{game_data['age_rating']} anos. "
                  f"Registre sua data de nascimento no perfil.", "error")
            return redirect(url_for('family'))
        try:
            dob      = datetime.strptime(user_dob_str, '%Y-%m-%d')
            hoje     = datetime.today()
            user_age = hoje.year - dob.year - ((hoje.month, hoje.day) < (dob.month, dob.day))
            if user_age < game_data['age_rating']:
                flash(f"Bloqueio: Sua idade verificada ({user_age} anos) é inferior à classificação +{game_data['age_rating']}.", "error")
                return redirect(url_for('family'))
        except ValueError:
            flash("Erro ao verificar data de nascimento. Atualize seu perfil.", "error")
            return redirect(url_for('family'))

    # Modo Offline: a licença foi validada no último login online, então o jogo
    # abre sem ocupar uma licença do pool (não soma +1 em "Em uso por parentes").
    if session.get('offline_mode'):
        iniciar_sessao_jogo(session['user_id'], session['family']['id'], game_id, modo='offline')
        session['active_game'] = game_id
        session['show_pe01_for'] = None
        session.modified = True
        flash("Modo Offline [A01]: Licença validada no último login online. Acesso permitido (não ocupa licença do pool).", "sucesso")
        return redirect(url_for('family'))

    total_licencas = session['family']['licenses'].get(game_id, 0)
    if total_licencas == 0:
        flash("Bloqueio: Ninguém da sua família comprou este jogo ainda.", "error")
        return redirect(url_for('family'))

    # Licenças ocupadas por OUTROS no momento (o usuário atual ainda não iniciou)
    em_uso = em_uso_total(session['family'], game_id)
    if em_uso >= total_licencas:
        flash(f"Bloqueio: Todas as {total_licencas} licença(s) estão em uso no momento.", "error")
        session['show_pe01_for'] = game_id
        session.modified = True
        return redirect(url_for('family'))

    # Registra a sessão de forma persistente: continua valendo se trocar de conta.
    iniciar_sessao_jogo(session['user_id'], session['family']['id'], game_id, modo='online')
    session['active_game']   = game_id
    session['show_pe01_for'] = None
    session.modified = True
    flash(f"'{game_data['name']}' iniciado! Licença temporária alocada. Saves e conquistas são individuais.", "sucesso")
    return redirect(url_for('family'))


@app.route('/family/stop')
def family_stop():
    # Devolve a licença ao pool (decrementa "Em uso por parentes" de forma persistente).
    encerrar_sessao_jogo(session['user_id'])
    session['active_game'] = None
    session.modified = True
    flash("Jogo encerrado. A licença foi devolvida ao banco da família.", "sucesso")
    return redirect(url_for('family'))


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
# UTILITÁRIOS
# ==============================================================================

@app.route('/reset')
def reset_session():
    """Limpa todos os cookies (sessão) e zera todos os arquivos de dados,
    exceto usuarios.txt (as contas cadastradas são preservadas)."""
    session.clear()
    for caminho in (MAQUINA_FILE, AMIZADES_FILE, BIBLIOTECA_FILE,
                    FAMILIAS_FILE, CARTEIRAS_FILE, SESSOES_FILE):
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
