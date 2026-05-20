from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'chave_secreta_super_segura'

GAMES = {
    '1': {'id': '1', 'name': 'Aventura Épica', 'price': 150.00, 'age_rating': 10, 'description': 'Explore masmorras e derrote monstros com amigos nesta jornada incrível.'},
    '2': {'id': '2', 'name': 'Sobrevivência Sombria', 'price': 90.00, 'age_rating': 18, 'description': 'Jogo de terror com zumbis. Sobreviva a noites aterrorizantes com recursos escassos.'},
    '3': {'id': '3', 'name': 'Corrida Divertida', 'price': 45.00, 'age_rating': 0, 'description': 'Corridas para toda a família. Karts coloridos e pistas malucas!'}
}

FRIENDS = {'1': 'Alan Turing', '2': 'Robert Ronald', '3': 'Isabelle Nazareth', '4': 'Hugo Barillo'}

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
    name = request.form.get('name')
    institution = request.form.get('institution')
    details = request.form.get('details')
    dob_str = request.form.get('dob')

    session['user_profile'] = {
        'name': name,
        'institution': institution,
        'details': details
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
    owned_games = {gid: GAMES[gid] for gid in session['library'] if gid in GAMES}
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
        else:
            if item['id'] not in session['library']:
                session['library'].append(item['id'])

    session['cart'] = []
    session.modified = True

    flash(f"Compra finalizada com sucesso! ({', '.join(detalhes_pagamento)})", 'sucesso')
    return redirect(url_for('index'))

#limpeza dos cookies
@app.route('/reset')
def reset_session():
    session.clear()
    flash('Sessão e cookies reiniciados com sucesso! Estado limpo para novos testes.', 'sucesso')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)