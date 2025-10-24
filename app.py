import os
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuração do Banco de Dados (PostgreSQL no Render)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///estoque.db')  # Fallback para SQLite local
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo para Flores
class Flor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variedade = db.Column(db.String(100), nullable=False)
    data_colheita = db.Column(db.Date, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)

    def esta_expirada(self):
        return datetime.now().date() > (self.data_colheita + timedelta(days=7))

    def dias_para_expirar(self):
        hoje = datetime.now().date()
        return ((self.data_colheita + timedelta(days=7)) - hoje).days

# Modelo para Entradas (Histórico)
class Entrada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variedade = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    data_colheita = db.Column(db.Date, nullable=False)
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)

# Criar tabelas
with app.app_context():
    db.create_all()

# Funções auxiliares
def carregar_estoque():
    return Flor.query.all()

def salvar_flor(variedade, data, quantidade):
    flor = Flor(variedade=variedade, data_colheita=datetime.strptime(data, "%Y-%m-%d").date(), quantidade=quantidade)
    db.session.add(flor)
    db.session.commit()

def salvar_entrada(variedade, quantidade, data):
    entrada = Entrada(variedade=variedade, quantidade=quantidade, data_colheita=datetime.strptime(data, "%Y-%m-%d").date())
    db.session.add(entrada)
    db.session.commit()

# Rotas
@app.route('/')
def index():
    flores = carregar_estoque()
    lotes = []
    alertas = []
    total_quantidade = 0
    for flor in flores:
        lote = {
            'variedade': flor.variedade,
            'quantidade': flor.quantidade,
            'data_colheita': flor.data_colheita,
            'data_maxima': flor.data_colheita + timedelta(days=7),
            'expirada': flor.esta_expirada(),
            'dias_para_expirar': flor.dias_para_expirar()
        }
        lotes.append(lote)
        total_quantidade += flor.quantidade
        if not flor.esta_expirada() and flor.dias_para_expirar() <= 2:
            alertas.append(lote)
    lotes.sort(key=lambda x: (x['variedade'], x['data_colheita']))
    return render_template('index.html', lotes=lotes, alertas=alertas, total_quantidade=total_quantidade, now=datetime.now())

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar():
    if request.method == 'POST':
        variedade = request.form['variedade']
        data = request.form['data']
        quantidade = int(request.form['quantidade'])
        salvar_flor(variedade, data, quantidade)
        salvar_entrada(variedade, quantidade, data)
        return redirect(url_for('index'))
    return render_template('adicionar.html')

@app.route('/remover')
def remover():
    flores_expiradas = Flor.query.filter(Flor.data_colheita + timedelta(days=7) < datetime.now().date()).all()
    for flor in flores_expiradas:
        db.session.delete(flor)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/saida', methods=['GET', 'POST'])
def saida():
    if request.method == 'POST':
        index_lote = int(request.form['lote_index'])
        quantidade_saida = int(request.form['quantidade_saida'])
        flores = carregar_estoque()
        if 0 <= index_lote < len(flores):
            flor = flores[index_lote]
            if flor.quantidade >= quantidade_saida:
                flor.quantidade -= quantidade_saida
                if flor.quantidade == 0:
                    db.session.delete(flor)
                db.session.commit()
        return redirect(url_for('index'))
    flores = carregar_estoque()
    lotes_disponiveis = [(i, f"{flor.variedade} - {flor.data_colheita} (Qtd: {flor.quantidade})") for i, flor in enumerate(flores)]
    return render_template('saida.html', lotes=lotes_disponiveis)

@app.route('/relatorio')
def relatorio():
    flores = carregar_estoque()
    lotes = []
    total_quantidade = 0
    for flor in flores:
        lote = {
            'variedade': flor.variedade,
            'quantidade': flor.quantidade,
            'data_colheita': flor.data_colheita,
            'data_maxima': flor.data_colheita + timedelta(days=7),
            'expirada': flor.esta_expirada(),
            'dias_para_expirar': flor.dias_para_expirar()
        }
        lotes.append(lote)
        total_quantidade += flor.quantidade
    lotes.sort(key=lambda x: (x['variedade'], x['data_colheita']))
    return render_template('relatorio.html', lotes=lotes, total_quantidade=total_quantidade, now=datetime.now())

@app.route('/filtrar-semana', methods=['GET', 'POST'])
def filtrar_semana():
    lotes_filtrados = []
    semana_selecionada = None
    if request.method == 'POST':
        semana_inicio = request.form['semana']
        semana_inicio_dt = datetime.strptime(semana_inicio, "%Y-%m-%d")
        semana_fim = semana_inicio_dt + timedelta(days=6)
        semana_selecionada = f"{semana_inicio_dt.strftime('%d/%m/%Y')} - {semana_fim.strftime('%d/%m/%Y')}"
        flores = carregar_estoque()
        for flor in flores:
            if semana_inicio_dt.date() <= flor.data_colheita <= semana_fim.date():
                lotes_filtrados.append({
                    'variedade': flor.variedade,
                    'quantidade': flor.quantidade,
                    'data_colheita': flor.data_colheita,
                    'data_maxima': flor.data_colheita + timedelta(days=7),
                    'expirada': flor.esta_expirada(),
                    'dias_para_expirar': flor.dias_para_expirar()
                })
    return render_template('filtrar_semana.html', lotes=lotes_filtrados, semana_selecionada=semana_selecionada)

@app.route('/historico-entradas')
def historico_entradas():
    entradas = Entrada.query.order_by(Entrada.data_entrada.desc()).all()
    return render_template('historico.html', entradas=entradas)

if __name__ == '__main__':
    app.run(debug=True)