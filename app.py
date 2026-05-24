from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'chave_secreta_super_segura'

# ---- CATÁLOGO DE JOGOS (DADOS FIXOS) ----
GAMES = {
    '1': {'id': '1', 'name': 'Aventura Épica',      'price': 150.00, 'age_rating': 10, 'description': 'Explore masmorras e derrote monstros com amigos nesta jornada incrível.'},
    '2': {'id': '2', 'name': 'Sobrevivência Sombria', 'price': 90.00,  'age_rating': 18, 'description': 'Jogo de terror com zumbis. Sobreviva a noites aterrorizantes com recursos escassos.'},
    '3': {'id': '3', 'name': 'Corrida Divertida',    'price': 45.00,  'age_rating': 0,  'description': 'Corridas para toda a família. Karts coloridos e pistas malucas!'}
}

# ==============================================================================
# BANCO DE DADOS EM ARQUIVO DE TEXTO
# ==============================================================================
DATA_DIR       = os.path.join(os.path.dirname(__file__), 'data')
USUARIOS_FILE  = os.path.join(DATA_DIR, 'usuarios.txt')
MAQUINA_FILE   = os.path.join(DATA_DIR, 'maquina.txt')
AMIZADES_FILE  = os.path.join(DATA_DIR, 'amizades.txt')


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
            f.write("# Este arquivo permite a seleção rápida de conta na tela de login.\n")
            f.write("# =============================================================================\n")

    if not os.path.exists(AMIZADES_FILE):
        with open(AMIZADES_FILE, 'w', encoding='utf-8') as f:
            f.write("# =============================================================================\n")
            f.write("# MINISTEAM - Banco de Dados de Amizades\n")
            f.write("# Cada linha representa uma amizade mútua entre dois usuários.\n")
            f.write("# Formato: id_menor | id_maior  (IDs ordenados para evitar duplicatas)\n")
            f.write("# Exemplo: 1 | 3  (usuário 1 e usuário 3 são amigos)\n")
            f.write("# =============================================================================\n")


# ---- FUNÇÕES DE USUÁRIOS ----

def ler_usuarios():
    """Lê todos os usuários do arquivo de banco de dados."""
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
    """Adiciona um novo usuário ao final do arquivo de banco de dados."""
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
    """Retorna lista de tuplas (id_a, id_b) de todas as amizades."""
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
    """Sobrescreve o arquivo de amizades com a lista fornecida."""
    _garantir_arquivos()
    with open(AMIZADES_FILE, 'w', encoding='utf-8') as f:
        f.write("# =============================================================================\n")
        f.write("# MINISTEAM - Banco de Dados de Amizades\n")
        f.write("# Cada linha representa uma amizade mútua entre dois usuários.\n")
        f.write("# Formato: id_menor | id_maior  (IDs ordenados para evitar duplicatas)\n")
        f.write("# Exemplo: 1 | 3  (usuário 1 e usuário 3 são amigos)\n")
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
    """Retorna lista de objetos de usuário que são amigos do uid dado."""
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
    """Retorna {friend_id: nome_exibicao} para uso nos templates."""
    return {u['id']: u['nome'] for u in get_amigos_usuario(uid)}


# ---- FUNÇÃO DE LOGIN ----

def fazer_login_sessao(usuario):
    """Limpa a sessão e a popula com os dados do usuário autenticado."""
    session.clear()
    session['logged_in']     = True
    session['user_id']       = usuario['id']
    session['wallet']        = 100.00
    session['library']       = []
    session['cart']          = []
    session['gifts_sent']    = {}
    session['user_dob']      = usuario['dob']
    session['user_profile']  = {
        'name':    usuario['nome'],
        'details': usuario.get('notas', '')
    }
    session['family']          = None
    session['family_cooldown'] = False
    session['offline_mode']    = False
    session['active_game']     = None
    session['show_pe01_for']   = None
    session.modified = True
    registrar_maquina(usuario['id'])


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
    uid          = session['user_id']
    meus_amigos  = get_amigos_usuario(uid)
    ids_amigos   = {u['id'] for u in meus_amigos}
    # Todos os outros usuários registrados que ainda não são amigos
    outros       = [u for u in ler_usuarios() if u['id'] != uid and u['id'] not in ids_amigos]
    return render_template('amigos.html', meus_amigos=meus_amigos, outros_usuarios=outros)


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
    game_data = GAMES.get(game_id)
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
    uid    = session['user_id']
    total  = sum(item['price'] for item in session['cart'])
    # Apenas amigos reais do usuário logado podem ser destinatários de presentes
    friends              = get_amigos_dict(uid)
    gift_items           = [item for item in session['cart'] if item['is_gift']]
    distinct_gift_ids    = set(item['id'] for item in gift_items)
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

            # Valida que o destinatário ainda é amigo do usuário
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
    jogos_disponiveis = set(session['library'])
    if session.get('family'):
        jogos_disponiveis.update(session['family']['library_pool'])
    owned_games = {gid: GAMES[gid] for gid in jogos_disponiveis if gid in GAMES}
    return render_template('library.html', games=owned_games)


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

    for item in session['cart']:
        if item['is_gift']:
            fid = item['recipient_id']
            if fid not in session['gifts_sent']:
                session['gifts_sent'][fid] = []
            session['gifts_sent'][fid].append(item['id'])
            flash(f"Presente '{item['name']}' enviado para {item['recipient_name']}!", 'sucesso')
            if session.get('family'):
                amigo_na_familia = any(m['name'] == item['recipient_name'] for m in session['family']['members'])
                if amigo_na_familia:
                    if item['id'] not in session['family']['library_pool']:
                        session['family']['library_pool'].append(item['id'])
                    session['family']['licenses'][item['id']] = session['family']['licenses'].get(item['id'], 0) + 1
                    flash(f"Como {item['recipient_name']} está na Família, '{item['name']}' foi adicionado ao Pool!", 'sucesso')
        else:
            if item['id'] not in session['library']:
                session['library'].append(item['id'])
                if session.get('family'):
                    if item['id'] not in session['family']['library_pool']:
                        session['family']['library_pool'].append(item['id'])
                    session['family']['licenses'][item['id']] = session['family']['licenses'].get(item['id'], 0) + 1

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
    return render_template('family.html', friends=friends, games=GAMES)


@app.route('/create_family', methods=['POST'])
def create_family():
    family_name = request.form.get('family_name')
    if session.get('family'):
        flash("Saia da sua família atual antes de criar uma nova.", "error")
        return redirect(url_for('family'))
    if session.get('family_cooldown'):
        flash("Bloqueio: Período de carência de 1 ano ativo para esta conta.", "error")
        return redirect(url_for('family'))

    shared_library = list(set(session.get('library', [])))
    session['family'] = {
        'id':                 f"fam_{datetime.now().timestamp()}",
        'name':               family_name,
        'created_at':         datetime.now().strftime("%d/%m/%Y %H:%M"),
        'founder':            session['user_profile']['name'],
        'members':            [{'name': session['user_profile']['name']}],
        'library_pool':       shared_library,
        'licenses':           {gid: 1 for gid in shared_library},
        'occupied_by_others': {}
    }
    session.modified = True
    flash(f"Família '{family_name}' criada com sucesso!", "sucesso")
    return redirect(url_for('family'))


@app.route('/family/invite/<friend_id>')
def family_invite(friend_id):
    """Convida um amigo real (da lista de amizades) para a família."""
    if not session.get('family'):
        flash("Você precisa criar uma família primeiro.", "error")
        return redirect(url_for('family'))

    family_data = session['family']

    if len(family_data['members']) >= 6:
        flash("Bloqueio: Uma Família não pode ter mais de 6 membros.", "error")
        return redirect(url_for('family'))

    # Valida que é de fato um amigo do usuário logado
    uid     = session['user_id']
    friends = get_amigos_dict(uid)
    if friend_id not in friends:
        flash("Você só pode convidar amigos da sua lista.", "error")
        return redirect(url_for('family'))

    friend_name = friends[friend_id]

    if any(m['name'] == friend_name for m in family_data['members']):
        flash(f"{friend_name} já faz parte desta família.", "error")
        return redirect(url_for('family'))

    family_data['members'].append({'name': friend_name})

    # Unifica licenças dos presentes que este amigo recebeu
    jogos_do_amigo    = session.get('gifts_sent', {}).get(friend_id, [])
    jogos_adicionados = []
    for jogo_id in set(jogos_do_amigo):
        qtd = jogos_do_amigo.count(jogo_id)
        if jogo_id not in family_data['library_pool']:
            family_data['library_pool'].append(jogo_id)
        family_data['licenses'][jogo_id] = family_data['licenses'].get(jogo_id, 0) + qtd
        jogos_adicionados.append(GAMES.get(jogo_id, {}).get('name', 'Jogo Desconhecido'))

    session['family'] = family_data
    session.modified = True

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
    session.modified = True
    flash(f"Liderança transferida para {member_name}! Você continua como membro.", "sucesso")
    return redirect(url_for('family'))


@app.route('/family/play/<game_id>')
def family_play(game_id):
    if not session.get('family'):
        flash("Você não pertence a uma família.", "error")
        return redirect(url_for('family'))

    game_data = GAMES.get(game_id)

    if session.get('active_game') and session.get('active_game') != game_id:
        jogo_anterior = GAMES.get(session['active_game'])['name']
        flash(f"Bloqueio: Você já está jogando '{jogo_anterior}'. Feche-o primeiro.", "error")
        return redirect(url_for('family'))

    if game_id == '3':
        flash("Bloqueio: Este jogo possui restrições do desenvolvedor que impedem o compartilhamento.", "error")
        return redirect(url_for('family'))

    # Verificação de idade por data de nascimento
    if game_data['age_rating'] > 0:
        user_dob_str = session.get('user_dob')
        if not user_dob_str:
            flash(f"Bloqueio: '{game_data['name']}' é classificado +{game_data['age_rating']} anos. "
                  f"Registre sua data de nascimento no perfil para verificar sua elegibilidade.", "error")
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

    if session.get('offline_mode') and session.get('active_game') != game_id:
        flash("Modo Offline [A01]: Licença validada no último login online. Acesso permitido.", "sucesso")
        session['active_game'] = game_id
        session.modified = True
        return redirect(url_for('family'))

    total_licencas = session['family']['licenses'].get(game_id, 0)
    if total_licencas == 0:
        flash("Bloqueio: Ninguém da sua família comprou este jogo ainda.", "error")
        return redirect(url_for('family'))

    em_uso = 1 if session['family']['occupied_by_others'].get(game_id, False) else 0
    if em_uso >= total_licencas:
        flash(f"Bloqueio: Todas as {total_licencas} licença(s) estão em uso no momento.", "error")
        session['show_pe01_for'] = game_id
        session.modified = True
        return redirect(url_for('family'))

    session['active_game']   = game_id
    session['show_pe01_for'] = None
    session.modified = True
    flash(f"'{game_data['name']}' iniciado! Licença temporária alocada. Saves e conquistas são individuais.", "sucesso")
    return redirect(url_for('family'))


@app.route('/family/stop')
def family_stop():
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
    session['offline_mode'] = not session.get('offline_mode', False)
    session.modified = True
    status = "LIGADO" if session['offline_mode'] else "DESLIGADO"
    flash(f"Modo Offline da Steam: {status} [A01]", "sucesso")
    return redirect(url_for('family'))


@app.route('/family/buy_extra/<game_id>')
def family_buy_extra(game_id):
    game_data = GAMES.get(game_id)
    if session['wallet'] >= game_data['price']:
        session['wallet'] -= game_data['price']
        session['family']['licenses'][game_id] = session['family']['licenses'].get(game_id, 1) + 1
        session['show_pe01_for'] = None
        session.modified = True
        qtd = session['family']['licenses'][game_id]
        flash(f"[PE01] Cópia adicional comprada! Pool agora possui {qtd} licenças de '{game_data['name']}'.", "sucesso")
    else:
        flash("Saldo insuficiente na carteira.", "error")
    return redirect(url_for('family'))


# ==============================================================================
# UTILITÁRIOS
# ==============================================================================

@app.route('/reset')
def reset_session():
    """Reseta os dados de jogo da sessão mantendo o usuário logado."""
    if session.get('logged_in'):
        uid     = session.get('user_id')
        usuario = buscar_por_id(uid)
        if usuario:
            fazer_login_sessao(usuario)
            flash('Estado de jogo reiniciado! Carteira, biblioteca e família foram resetadas.', 'sucesso')
            return redirect(url_for('index'))
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    _garantir_arquivos()
    app.run(debug=True)