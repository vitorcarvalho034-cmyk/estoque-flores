import os
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta, timezone
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuração do Banco de Dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///estoque.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Função para horário local (Brasília)
def agora_local():
    utc_now = datetime.now(timezone.utc)
    return utc_now - timedelta(hours=3)  # Ajuste para seu fuso horário

# Modelo para Flores
class Flor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variedade = db.Column(db.String(100), nullable=False)
    data_colheita = db.Column(db.Date, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)

    def esta_expirada(self):
        return agora_local().date() > (self.data_colheita + timedelta(days=7))  # 7 dias de validade

    def dias_para_expirar(self):
        hoje = agora_local().date()
        return ((self.data_colheita + timedelta(days=7)) - hoje).days

# Modelo para Entradas
class Entrada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variedade = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    data_colheita = db.Column(db.Date, nullable=False)
    data_entrada = db.Column(db.DateTime, default=lambda: agora_local())

# Modelo para Metas de Colheita (com previsão semanal)
class MetaColheita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variedade = db.Column(db.String(100), nullable=False)
    meta_diaria = db.Column(db.Integer, nullable=False)  # Meta diária
    previsao_semanal = db.Column(db.Integer, nullable=False, default=0)  # Previsão de hastes por semana
    data = db.Column(db.Date, default=lambda: agora_local().date())

# Modelo para Colheitas (atualizado com cestos)
class Colheita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variedade = db.Column(db.String(100), nullable=False)
    cestos_mercado = db.Column(db.Integer, default=0)
    cestos_barracao = db.Column(db.Integer, default=0)
    cestos_oferta = db.Column(db.Integer, default=0)
    total_hastes = db.Column(db.Integer, nullable=False)  # Calculado
    data = db.Column(db.Date, default=lambda: agora_local().date())

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
    return render_template('index.html', lotes=lotes, alertas=alertas, total_quantidade=total_quantidade, now=agora_local())

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
    return render_template('relatorio.html', lotes=lotes, total_quantidade=total_quantidade, now=agora_local())

@app.route('/filtrar-semana', methods=['GET', 'POST'])
def filtrar_semana():
    lotes_filtrados = []
    periodo_selecionado = None
    if request.method == 'POST':
        data_inicio = request.form['data_inicio']
        data_fim = request.form['data_fim']
        data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d").date()
        periodo_selecionado = f"{data_inicio_dt.strftime('%d/%m/%Y')} - {data_fim_dt.strftime('%d/%m/%Y')}"
        flores = carregar_estoque()
        for flor in flores:
            if data_inicio_dt <= flor.data_colheita <= data_fim_dt:
                lotes_filtrados.append({
                    'variedade': flor.variedade,
                    'quantidade': flor.quantidade,
                    'data_colheita': flor.data_colheita,
                    'data_maxima': flor.data_colheita + timedelta(days=7),
                    'expirada': flor.esta_expirada(),
                    'dias_para_expirar': flor.dias_para_expirar()
                })
    return render_template('filtrar_semana.html', lotes=lotes_filtrados, periodo_selecionado=periodo_selecionado)

@app.route('/historico-entradas')
def historico_entradas():
    entradas = Entrada.query.order_by(Entrada.data_entrada.desc()).all()
    return render_template('historico.html', entradas=entradas)

@app.route('/metas', methods=['GET', 'POST'])
def metas():
    if request.method == 'POST':
        variedade = request.form['variedade']
        meta_diaria = int(request.form['meta_diaria'])
        previsao_semanal = int(request.form.get('previsao_semanal', 0))
        meta = MetaColheita(variedade=variedade, meta_diaria=meta_diaria, previsao_semanal=previsao_semanal)
        db.session.add(meta)
        db.session.commit()
        return redirect(url_for('metas'))
    metas = MetaColheita.query.order_by(MetaColheita.data.desc()).all()
    return render_template('metas.html', metas=metas)

@app.route('/colheitas', methods=['GET', 'POST'])
def colheitas():
    if request.method == 'POST':
        variedade = request.form['variedade']
        cestos_mercado = int(request.form.get('cestos_mercado', 0))
        cestos_barracao = int(request.form.get('cestos_barracao', 0))
        cestos_oferta = int(request.form.get('cestos_oferta', 0))

        # Cálculo de hastes com regras
        hastes_mercado = cestos_mercado * 60
        hastes_barracao = cestos_barracao * 50
        if variedade in ['Cipria', 'Green Dark', 'Chispa', 'Sunny']:
            hastes_oferta = cestos_oferta * 80
        else:
            hastes_oferta = cestos_oferta * 60
        total_hastes = hastes_mercado + hastes_barracao + hastes_oferta

        colheita = Colheita(variedade=variedade, cestos_mercado=cestos_mercado, cestos_barracao=cestos_barracao, cestos_oferta=cestos_oferta, total_hastes=total_hastes)
        db.session.add(colheita)
        db.session.commit()
        return redirect(url_for('colheitas'))
    colheitas = Colheita.query.order_by(Colheita.data.desc()).all()
    return render_template('colheitas.html', colheitas=colheitas)

@app.route('/dashboard')
def dashboard():
    # Estatísticas de estoque
    flores = carregar_estoque()
    total_estoque = sum(flor.quantidade for flor in flores)
    variedades_estoque = {}
    for flor in flores:
        variedades_estoque[flor.variedade] = variedades_estoque.get(flor.variedade, 0) + flor.quantidade

    # Estatísticas de colheita
    entradas = Entrada.query.all()
    total_colhido = sum(entrada.quantidade for entrada in entradas)
    colheita_por_variedade = {}
    colheita_por_mes = {}
    for entrada in entradas:
        colheita_por_variedade[entrada.variedade] = colheita_por_variedade.get(entrada.variedade, 0) + entrada.quantidade
        mes = entrada.data_entrada.strftime('%Y-%m')
        colheita_por_mes[mes] = colheita_por_mes.get(mes, 0) + entrada.quantidade

    # Progresso vs. Meta
    metas = MetaColheita.query.filter_by(data=agora_local().date()).all()
    colheitas_hoje = Colheita.query.filter_by(data=agora_local().date()).all()
    progresso = {}
    alertas_meta = []
    for meta in metas:
        total_colhido_hoje = sum(c.total_hastes for c in colheitas_hoje if c.variedade == meta.variedade)
        percentual = (total_colhido_hoje / meta.meta_diaria) * 100 if meta.meta_diaria > 0 else 0
        progresso[meta.variedade] = {'meta': meta.meta_diaria, 'colhido': total_colhido_hoje, 'percentual': percentual}
        if percentual < 80:
            alertas_meta.append(f"{meta.variedade}: {total_colhido_hoje}/{meta.meta_diaria} ({percentual:.1f}%) - Abaixo da meta!")

    # Previsão semanal vs. real
    data_inicio_semana = agora_local().date() - timedelta(days=agora_local().weekday())
    data_fim_semana = data_inicio_semana + timedelta(days=6)
    metas = MetaColheita.query.filter(MetaColheita.data.between(data_inicio_semana, data_fim_semana)).all()
    colheitas_semana = Colheita.query.filter(Colheita.data.between(data_inicio_semana, data_fim_semana)).all()
    previsao_semanal = {}
    real_semanal = {}
    for meta in metas:
        previsao_semanal[meta.variedade] = meta.previsao_semanal
    for colheita in colheitas_semana:
        real_semanal[colheita.variedade] = real_semanal.get(colheita.variedade, 0) + colheita.total_hastes

    return render_template('dashboard.html', 
                           total_estoque=total_estoque, 
                           variedades_estoque=variedades_estoque,
                           total_colhido=total_colhido,
                           colheita_por_variedade=colheita_por_variedade,
                           colheita_por_mes=colheita_por_mes,
                           progresso=progresso,
                           alertas_meta=alertas_meta,
                           previsao_semanal=previsao_semanal,
                           real_semanal=real_semanal)
@app.route('/init-db')
def init_db():
    db.create_all()
    return "Tabelas criadas com sucesso!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)