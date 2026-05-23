from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'chave_secreta_super_segura'

GAMES = {
    '1': {'id': '1', 'name': 'Aventura Épica', 'price': 150.00, 'age_rating': 10, 'description': 'Explore masmorras e derrote monstros com amigos nesta jornada incrível.'},
    '2': {'id': '2', 'name': 'Sobrevivência Sombria', 'price': 90.00, 'age_rating': 18, 'description': 'Jogo de terror com zumbis. Sobreviva a noites aterrorizantes com recursos escassos.'},
    '3': {'id': '3', 'name': 'Corrida Divertida', 'price': 45.00, 'age_rating': 0, 'description': 'Corridas para toda a família. Karts coloridos e pistas malucas!'},
    '4': {'id': '4', 'name': 'Lombriguinha', 'price': 120.00, 'age_rating': 16, 'description': 'Jogo de combate de guerra com os amigos. Que vença a lombriguinha melhor!'}

}

FRIENDS = {'1': 'Alan Turing', '2': 'Robert Ronald', '3': 'Isabelle Nazareth', '4': 'Hugo Barillo','5':'Ada Lovelace', '6': 'Grace Hopper'}

@app.before_request
def ensure_session_values():
    if 'wallet' not in session:
        session['wallet'] = 100.00
    if 'library' not in session:
        session['library'] = []
    if 'cart' not in session:
        session['cart'] = []
    if 'gifts_sent' not in session:
        session['gifts_sent'] = {}
    if 'user_dob' not in session:
        session['user_dob'] = None
        # dados
    if 'user_profile' not in session:
        session['user_profile'] = {
            'name': 'Usuário Muito Legal',
            'details': 'Suas informações ou notas de IHC aqui...'
        }
    
    if 'family' not in session:
        session['family'] = None
    if 'family_cooldown' not in session:
        session['family_cooldown'] = False
    if 'user_role' not in session:
        session['user_role'] = 'Adulto'  # RN03: Pode ser 'Adulto' ou 'Criança'
    if 'offline_mode' not in session:
        session['offline_mode'] = False  # A01: Simulação do modo offline
    if 'active_game' not in session:
        session['active_game'] = None  # Guarda o ID do jogo que o usuário está jogando agora
    if 'show_pe01_for' not in session:
        session['show_pe01_for'] = None  # Controla a exibição do ponto de extensão PE01

    if 'reviews' not in session:
        # Simulamos uma base de dados populada com os idiomas do EnumLinguagemAvaliacao do seu UML
        session['reviews'] = {
            '1': [
                {'author': 'Isabelle Nazareth', 'recomenda': True, 'comentario': 'Jogo excelente! Muito divertido para jogar em grupo.', 'data': '20/05/2026', 'linguagem': 'portuguesBrasil', 'votos_uteis': 12},
                {'author': 'John Doe', 'recomenda': True, 'comentario': 'Amazing gameplay and graphics. Highly recommended to play with friends!', 'data': '19/05/2026', 'linguagem': 'ingles', 'votos_uteis': 5},
                {'author': 'Hans Müller', 'recomenda': False, 'comentario': 'Das Spiel hat zu viele Bugs. Ich kann es im Moment nicht empfehlen.', 'data': '18/05/2026', 'linguagem': 'alemao', 'votos_uteis': 2},
                {'author': 'Alan Turing', 'recomenda': True, 'comentario': 'A lógica por trás dos puzzles deste jogo é fantástica.', 'data': '21/05/2026', 'linguagem': 'portuguesBrasil', 'votos_uteis': 8}
            ],
            '2': [
                {'author': 'Grace Hopper', 'recomenda': True, 'comentario': 'Great horror atmosphere! Found a few system bugs though.', 'data': '15/05/2026', 'linguagem': 'ingles', 'votos_uteis': 14}
            ]
        }
@app.route('/')
def index():
    return render_template('index.html', games=GAMES)


@app.route('/game/<game_id>')
def game(game_id):
    game_data = GAMES.get(game_id)
    if not game_data:
        return "Jogo não encontrado", 404
    show_modal = request.args.get('added') == '1'
    
    selected_lang = request.args.get('lang', 'todos') # Padrão exibe 'todos' [FA02]
    all_reviews = session.get('reviews', {}).get(game_id, [])
    
    # Aplica o filtro comparando com as strings do Enum
    if selected_lang != 'todos':
        filtered_reviews = [r for r in all_reviews if r['linguagem'] == selected_lang]
    else:
        filtered_reviews = all_reviews
        
    #Ordena a lista de forma decrescente pelos votos úteis
    filtered_reviews = sorted(filtered_reviews, key=lambda x: x.get('votos_uteis', 0), reverse=True)
        
    return render_template('game.html', 
                           game=game_data, 
                           show_modal=show_modal, 
                           reviews=filtered_reviews, 
                           selected_lang=selected_lang)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    name = request.form.get('name')
    institution = request.form.get('institution')
    details = request.form.get('details')
    dob_str = request.form.get('dob')
    linguagem = request.form.get('linguagem', 'portuguesBrasil') # Captura o idioma

    session['user_profile'] = {
        'name': name,
        'institution': institution,
        'details': details,
        'linguagem': linguagem # Salva a preferência
    }
    if dob_str:
        session['user_dob'] = dob_str

    session.modified = True
    flash('Dados do perfil atualizados com sucesso!', 'sucesso')
    return redirect(request.referrer or url_for('index'))

@app.route('/add_to_cart/<game_id>', methods=['POST'])
def add_to_cart(game_id):
    game_data = GAMES.get(game_id)
    if not game_data:
        return "Jogo não encontrado", 404

    purchase_type = request.form.get('purchase_type', 'self')

    if purchase_type == 'self':
        if game_id in session['library'] or any(item['id'] == game_id and not item['is_gift'] for item in session['cart']):
            flash('Você já possui este jogo ou ele já está no carrinho para sua conta.', 'error')
            return redirect(url_for('game', game_id=game_id))

    if game_data['age_rating'] > 0 and purchase_type == 'self':
        user_dob_str = session.get('user_dob') or request.form.get('dob')

        if not user_dob_str or user_dob_str == 'none':
            flash('Por favor, configure ou confirme sua data de nascimento.', 'error')
            return redirect(url_for('game', game_id=game_id))
        try:
            dob = datetime.strptime(user_dob_str, '%Y-%m-%d')
            hoje = datetime.today()
            user_age = hoje.year - dob.year - ((hoje.month, hoje.day) < (dob.month, dob.day))

            if user_age < game_data['age_rating']:
                flash(f'Bloqueio automático: Sua idade cadastrada ({user_age} anos) é inferior à classificação do jogo.', 'error')
                return redirect(url_for('game', game_id=game_id))

            if not session.get('user_dob'):
                session['user_dob'] = user_dob_str
                session.modified = True
        except ValueError:
            flash('Formato de data inválido.', 'error')
            return redirect(url_for('game', game_id=game_id))

    cart_item = {
        'cart_item_id': f"{game_id}_{purchase_type}_{datetime.now().timestamp()}",
        'id': game_data['id'],
        'name': game_data['name'],
        'price': game_data['price'],
        'is_gift': purchase_type == 'gift'
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

    if game_id not in session['reviews']:
        session['reviews'][game_id] = []

    user_name = session['user_profile']['name']
    
    #  Unicidade: Remove análise anterior do mesmo usuário
    session['reviews'][game_id] = [r for r in session['reviews'][game_id] if r['author'] != user_name]

    # Busca o idioma do perfil do usuário. Se não existir, o padrão é 'portuguesBrasil'
    idioma_usuario = session['user_profile'].get('linguagem', 'portuguesBrasil')

    nova_analise = {
        'author': user_name,
        'recomenda': recomenda, 
        'comentario': comentario,
        'data': datetime.now().strftime("%d/%m/%Y"),
        'linguagem': idioma_usuario, 
        'voted_users': {} # Dicionário para guardar 'sim' ou 'nao'
    }
    
    session['reviews'][game_id].append(nova_analise)
    session.modified = True
    flash("Sua análise foi publicada com sucesso!", "sucesso")
    return redirect(url_for('game', game_id=game_id))

@app.route('/game/<game_id>/review/<author>/vote/<vote_type>')
def vote_review(game_id, author, vote_type):
    reviews = session.get('reviews', {}).get(game_id, [])
    current_user = session['user_profile']['name']
    
    for r in reviews:
        if r['author'] == author:
            # Trava 1: Não permite que o usuário vote na própria avaliação
            if author == current_user:
                flash("Bloqueio: Você não pode classificar sua própria análise.", "error")
                return redirect(url_for('game', game_id=game_id))
            
            # Garante que a estrutura de votos existe e é um dicionário (prevenção de erros antigos)
            if 'voted_users' not in r or isinstance(r['voted_users'], list):
                r['voted_users'] = {}
                
            voto_anterior = r['voted_users'].get(current_user)
            
            # Trava 2: Se clicar no mesmo botão que já tinha votado
            if voto_anterior == vote_type:
                flash("Você já classificou esta análise com esta mesma opção.", "error")
                return redirect(url_for('game', game_id=game_id))
            
            # Lógica de Atualização / Troca de Voto
            if vote_type == 'sim':
                r['votos_uteis'] = r.get('votos_uteis', 0) + 1
                flash("Voto atualizado! O voto útil foi registrado e ajudará a comunidade.", "sucesso")
            elif vote_type == 'nao':
                # Se o voto anterior era 'sim', temos que subtrair aquele voto útil que ele tinha dado!
                if voto_anterior == 'sim':
                    r['votos_uteis'] = max(0, r.get('votos_uteis', 0) - 1)
                flash("Voto atualizado! Registramos que esta análise não foi útil para você.", "sucesso")
                
            # Salva o novo voto do usuário no dicionário
            r['voted_users'][current_user] = vote_type
            
            session.modified = True
            break
            
    return redirect(url_for('game', game_id=game_id))

@app.route('/cart')
def cart():
    total = sum(item['price'] for item in session['cart'])
    gift_items = [item for item in session['cart'] if item['is_gift']]

    distinct_gift_ids = set(item['id'] for item in gift_items)
    multiple_different_gifts = len(distinct_gift_ids) > 1

    return render_template('cart.html',
                           cart=session['cart'],
                           total=total,
                           friends=FRIENDS,
                           gift_items=gift_items,
                           multiple_different_gifts=multiple_different_gifts)

@app.route('/remove_from_cart/<cart_item_id>')
def remove_from_cart(cart_item_id):
    session['cart'] = [item for item in session['cart'] if item['cart_item_id'] != cart_item_id]
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/clear_cart')
def clear_cart():
    session['cart'] = []
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/proceed_checkout', methods=['POST'])
def proceed_checkout():
    """NOVO: Guarda os destinatários e valida os presentes antes do pagamento"""
    cart_items = session.get('cart', [])

    # valida e associa os destinatarios de cada item do carrinho
    for item in cart_items:
        if item['is_gift']:
            friend_id = request.form.get(f"recipient_{item['cart_item_id']}")
            if not friend_id:
                flash('Por favor, selecione o destinatário para todos os presentes no carrinho.', 'error')
                return redirect(url_for('cart'))

            # verifica se o amigo ja tem o jogo
            historico_amigo = session['gifts_sent'].get(friend_id, [])
            if item['id'] in historico_amigo:
                flash(f"Remova ou altere o item: {FRIENDS[friend_id]} já possui o jogo '{item['name']}'!", 'error')
                return redirect(url_for('cart'))

            # guarda a escolha diretamente no item do carrinho
            item['recipient_id'] = friend_id
            item['recipient_name'] = FRIENDS[friend_id]

    session['cart'] = cart_items
    session.modified = True
    return redirect(url_for('checkout'))

@app.route('/library')
def library():
    # Usa a estrutura 'set' para juntar a biblioteca pessoal e a da família sem duplicatas
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
    # O Checkout agora apenas lida com o resumo e o dinheiro
    return render_template('checkout.html', cart=session['cart'], total=total)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    total = sum(item['price'] for item in session['cart'])
    use_wallet = 'use_wallet' in request.form and session['wallet'] > 0
    payment_method = request.form.get('payment_method')

    valor_a_pagar = total
    detalhes_pagamento = []

    if use_wallet:
        if session['wallet'] >= valor_a_pagar:
            session['wallet'] -= valor_a_pagar
            detalhes_pagamento.append(f"R$ {valor_a_pagar:.2f} da Carteira")
            valor_a_pagar = 0
        else:
            detalhes_pagamento.append(f"R$ {session['wallet']:.2f} da Carteira")
            valor_a_pagar -= session['wallet']
            session['wallet'] = 0.0

    if valor_a_pagar > 0:
        detalhes_pagamento.append(f"R$ {valor_a_pagar:.2f} via {payment_method}")

    # entrega dos itens
    for item in session['cart']:
        if item['is_gift']:
            fid = item['recipient_id'] # Puxa o dado já salvo no carrinho
            if fid not in session['gifts_sent']:
                session['gifts_sent'][fid] = []
            session['gifts_sent'][fid].append(item['id'])
            flash(f"Presente '{item['name']}' enviado para {item['recipient_name']}!", 'sucesso')
            
            # CORREÇÃO: Unificar licença de presente caso o destinatário seja da família
            if session.get('family'):
                # Verifica se o nome do destinatário existe na lista de membros da família
                amigo_na_familia = any(m['name'] == item['recipient_name'] for m in session['family']['members'])
                
                if amigo_na_familia:
                    if item['id'] not in session['family']['library_pool']:
                        session['family']['library_pool'].append(item['id'])
                    
                    session['family']['licenses'][item['id']] = session['family']['licenses'].get(item['id'], 0) + 1
                    flash(f"Como {item['recipient_name']} está na sua Família, a cópia de '{item['name']}' foi adicionada ao Pool Unificado!", 'sucesso')

        else:
            if item['id'] not in session['library']:
                session['library'].append(item['id'])
                
                # Sincronização automática de compras próprias com a Família
                if session.get('family'):
                    if item['id'] not in session['family']['library_pool']:
                        session['family']['library_pool'].append(item['id'])
                    
                    session['family']['licenses'][item['id']] = session['family']['licenses'].get(item['id'], 0) + 1

    session['cart'] = []
    session.modified = True

    flash(f"Compra finalizada com sucesso! ({', '.join(detalhes_pagamento)})", 'sucesso')
    return redirect(url_for('index'))

@app.route('/family')
def family():
    return render_template('family.html', friends=FRIENDS, games=GAMES)

@app.route('/create_family', methods=['POST'])
def create_family():
    family_name = request.form.get('family_name')

    if session.get('family'):
        flash("Você precisa sair da sua família atual antes de criar uma nova.", "error")
        return redirect(url_for('family'))

    if session.get('family_cooldown'):
        flash("Ação bloqueada: Período de carência de 1 ano ativo para esta conta.", "error")
        return redirect(url_for('family'))

    # Mapeia os jogos que o usuário logado possui para o pool inicial
    shared_library = list(set(session.get('library', [])))

    # [RN01 / RN03] Criamos a família APENAS com o fundador logado por padrão
    session['family'] = {
        'id': f"fam_{datetime.now().timestamp()}",
        'name': family_name,
        'created_at': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'founder': session['user_profile']['name'],
        # Agora members é uma lista de dicionários para guardar o cargo/role de cada um
        'members': [{'name': session['user_profile']['name'], 'role': session.get('user_role', 'Adulto')}],
        'library_pool': shared_library,
        'licenses': {gid: 1 for gid in shared_library}, 
        'occupied_by_others': {} 
    }
    
    session.modified = True
    flash(f"Família '{family_name}' criada com sucesso!", "sucesso")
    return redirect(url_for('family'))

# ---- ROTAS EXCLUSIVAS DO FLUXO "COMPARTILHAR BIBLIOTECA" ----

@app.route('/family/play/<game_id>')
def family_play(game_id):
    if not session.get('family'):
        flash("Você não pertence a uma família.", "error")
        return redirect(url_for('family'))

    game_data = GAMES.get(game_id)

    # TRAVA: Impede de abrir um jogo se já houver outro em execução
    if session.get('active_game') and session.get('active_game') != game_id:
        jogo_anterior = GAMES.get(session['active_game'])['name']
        flash(f"Bloqueio: Você já está jogando '{jogo_anterior}'. Feche-o primeiro antes de iniciar outro título.", "error")
        return redirect(url_for('family'))

    # [FE03] Jogo Não Elegível para Compartilhamento (Simulando que o jogo '3' possui trava de desenvolvedor)
    if game_id == '3':
        flash("Bloqueio: Este jogo possui restrições do Desenvolvedor/Estúdio que impedem o compartilhamento familiar.", "error")
        return redirect(url_for('family'))

    # [RN03] Controles Parentais (Se for Criança, bloqueia jogos com classificação 18 anos)
    if session.get('user_role') == 'Criança' and game_data['age_rating'] >= 18:
        flash(f"Bloqueio: Controle Parental Ativo. Membros classificados como 'Criança' não podem jogar {game_data['name']} (+18).", "error")
        return redirect(url_for('family'))

    # [A01] Validação de Licença prévia para Modo Offline
    if session.get('offline_mode') and session.get('active_game') != game_id:
        # Na simulação, se já estava jogando antes de ficar offline, permite continuar. Se não, bloqueia.
        flash("Modo Offline [A01]: O sistema permitiu a execução pois validou a licença no último login online.", "sucesso")
        session['active_game'] = game_id
        session.modified = True
        return redirect(url_for('family'))

    # Contagem de Licenças 
    total_licencas = session['family']['licenses'].get(game_id, 0) 
    
    # NOVA TRAVA: Se a família não tem o jogo, bloqueia logo de cara!
    if total_licencas == 0:
        flash("Bloqueio: Ninguém da sua família comprou este jogo ainda.", "error")
        return redirect(url_for('family'))

    em_uso_por_outros = 1 if session['family']['occupied_by_others'].get(game_id, False) else 0
    

    if em_uso_por_outros >= total_licencas:
        flash(f"Bloqueio: Todas as licenças ({total_licencas}) estão em uso. Sua família não possui licenças disponíveis para este título no momento.", "error")
        session['show_pe01_for'] = game_id 
        session.modified = True
        return redirect(url_for('family'))

    # Fluxo Principal - Sucesso
    session['active_game'] = game_id
    session['show_pe01_for'] = None
    session.modified = True
    flash(f"Jogo '{game_data['name']}' iniciado! Licença temporária alocada com sucesso. Saves e Conquistas serão individuais.", "sucesso")
    return redirect(url_for('family'))

@app.route('/family/stop')
def family_stop():
    session['active_game'] = None
    session.modified = True
    flash("Jogo encerrado. A licença foi devolvida ao banco da família.", "sucesso")
    return redirect(url_for('family'))

# ---- ROTAS DE SIMULAÇÃO PARA APRESENTAÇÃO ACADÊMICA ----

@app.route('/family/toggle_npc/<game_id>')
def family_toggle_npc(game_id):
    """ Simula que outro membro da família abriu o jogo em outro computador """
    if 'family' in session and session['family']:
        atual = session['family']['occupied_by_others'].get(game_id, False)
        session['family']['occupied_by_others'][game_id] = not atual
        session.modified = True
        status = "OCUPOU" if not atual else "LIBEROU"
        flash(f"Simulação: Outro membro da família {status} uma licença deste jogo!", "sucesso")
    return redirect(url_for('family'))

@app.route('/family/toggle_role')
def family_toggle_role():
    """ Alterna o perfil entre Adulto e Criança para testar a RN03 """
    session['user_role'] = 'Criança' if session.get('user_role', 'Adulto') == 'Adulto' else 'Adulto'
    session.modified = True
    flash(f"Perfil alterado para: {session['user_role']}", "sucesso")
    return redirect(url_for('family'))

@app.route('/family/toggle_offline')
def family_toggle_offline():
    """ Alterna o modo offline para testar o fluxo alternativo A01 """
    session['offline_mode'] = not session.get('offline_mode', False)
    session.modified = True
    status = "LIGADO" if session['offline_mode'] else "DESLIGADO"
    flash(f"Modo Offline da Steam: {status} [A01]", "sucesso")
    return redirect(url_for('family'))

@app.route('/family/buy_extra/<game_id>')
def family_buy_extra(game_id):
    """Compra uma cópia extra para o banco da família """
    game_data = GAMES.get(game_id)
    if session['wallet'] >= game_data['price']:
        session['wallet'] -= game_data['price']
        session['family']['licenses'][game_id] = session['family']['licenses'].get(game_id, 1) + 1
        session['show_pe01_for'] = None
        session.modified = True
        flash(f"Sucesso: Cópia adicional comprada! Banco da família agora possui {session['family']['licenses'][game_id]} licenças unificadas de '{game_data['name']}'.", "sucesso")
    else:
        flash("Saldo insuficiente na carteira para comprar uma cópia adicional.", "error")
    return redirect(url_for('family'))

@app.route('/family/invite/<friend_id>/<role>')
def family_invite(friend_id, role):
    if not session.get('family'):
        flash("Você precisa criar uma família primeiro.", "error")
        return redirect(url_for('family'))
    
    family_data = session['family']
    
    # [RN01] Restrição de Cardinalidade: Limite Máximo de 6 membros
    if len(family_data['members']) >= 6:
        flash("Bloqueio: Uma Família não pode conter mais do que 6 instâncias de Usuário ativas.", "error")
        return redirect(url_for('family'))
    
    friend_name = FRIENDS.get(friend_id)
    if not friend_name:
        flash("Amigo não encontrado.", "error")
        return redirect(url_for('family'))
    
    # Valida se o amigo já foi adicionado
    if any(m['name'] == friend_name for m in family_data['members']):
        flash(f"{friend_name} já faz parte desta família.", "error")
        return redirect(url_for('family'))
    
    # Adiciona o novo membro com a função escolhida (Adulto ou Criança) [RN03]
    family_data['members'].append({'name': friend_name, 'role': role})
    
    # CORREÇÃO [RN04]: Buscar os jogos REAIS que o amigo já possuía antes de entrar na família
    jogos_do_amigo = session.get('gifts_sent', {}).get(friend_id, [])
    jogos_adicionados = []
    
    # Usamos set() para agrupar os IDs únicos que o amigo tem
    for jogo_id in set(jogos_do_amigo):
        qtd_copias = jogos_do_amigo.count(jogo_id)
        
        # Se a família ainda não tinha esse título, adiciona à lista visual do pool
        if jogo_id not in family_data['library_pool']:
            family_data['library_pool'].append(jogo_id)
            
        # Soma as licenças reais do amigo com as que a família já possuía
        family_data['licenses'][jogo_id] = family_data['licenses'].get(jogo_id, 0) + qtd_copias
        
        # Salva o nome do jogo para mostrar na mensagem de sucesso
        game_name = GAMES.get(jogo_id, {}).get('name', 'Jogo Desconhecido')
        jogos_adicionados.append(game_name)
    
    session['family'] = family_data
    session.modified = True
    
    # Mensagem dinâmica: avisa se ele trouxe jogos ou se entrou de mãos vazias
    if jogos_adicionados:
        nomes_jogos = ", ".join(jogos_adicionados)
        flash(f"Convite aceito! {friend_name} entrou como '{role}' e trouxe os seguintes jogos para o Pool: {nomes_jogos}.", "sucesso")
    else:
        flash(f"Convite aceito! {friend_name} entrou como '{role}', mas não possuía jogos anteriores para adicionar à Família.", "sucesso")
        
    return redirect(url_for('family'))
#limpeza dos cookies
@app.route('/reset')
def reset_session():
    session.clear()
    flash('Sessão e cookies reiniciados com sucesso! Estado limpo para novos testes.', 'sucesso')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)