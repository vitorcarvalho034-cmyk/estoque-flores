import json
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta

app = Flask(__name__)

class Flor:
    def __init__(self, variedade, data_colheita, quantidade):
        self.variedade = variedade
        self.data_colheita = datetime.strptime(data_colheita, "%Y-%m-%d")
        self.data_maxima = self.data_colheita + timedelta(days=7)
        self.quantidade = int(quantidade)
    
    def esta_expirada(self):
        return datetime.now() > self.data_maxima
    
    def dias_para_expirar(self):
        hoje = datetime.now().date()
        return (self.data_maxima.date() - hoje).days
    
    def to_dict(self):
        return {
            'variedade': self.variedade,
            'data_colheita': self.data_colheita.strftime("%Y-%m-%d"),
            'quantidade': self.quantidade
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(data['variedade'], data['data_colheita'], data['quantidade'])
    
    def __str__(self):
        status = "Expirada" if self.esta_expirada() else "Válida"
        return f"Variedade: {self.variedade}, Quantidade: {self.quantidade}, Colheita: {self.data_colheita.date()}, Máxima: {self.data_maxima.date()}, Status: {status}"

estoque = []

def salvar_estoque():
    with open('estoque.json', 'w') as f:
        json.dump([flor.to_dict() for flor in estoque if flor.quantidade > 0], f)

def carregar_estoque():
    global estoque
    try:
        with open('estoque.json', 'r') as f:
            data = json.load(f)
            estoque = [Flor.from_dict(item) for item in data]
    except FileNotFoundError:
        estoque = []

# Carregar dados ao iniciar
carregar_estoque()

@app.route('/')
def index():
    # Mostrar lotes separados por variedade + data de colheita
    lotes = []
    alertas = []
    total_quantidade = 0  # Somatória total
    for flor in estoque:
        lote = {
            'variedade': flor.variedade,
            'quantidade': flor.quantidade,
            'data_colheita': flor.data_colheita.date(),
            'data_maxima': flor.data_maxima.date(),
            'expirada': flor.esta_expirada(),
            'dias_para_expirar': flor.dias_para_expirar()
        }
        lotes.append(lote)
        total_quantidade += flor.quantidade  # Soma a quantidade
        # Adicionar a alertas se expira em <=2 dias e não expirada
        if not flor.esta_expirada() and flor.dias_para_expirar() <= 2:
            alertas.append(lote)
    # Ordenar por variedade e data
    lotes.sort(key=lambda x: (x['variedade'], x['data_colheita']))
    return render_template('index.html', lotes=lotes, alertas=alertas, total_quantidade=total_quantidade)

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar():
    if request.method == 'POST':
        variedade = request.form['variedade']
        data = request.form['data']
        quantidade = request.form['quantidade']
        flor = Flor(variedade, data, quantidade)
        estoque.append(flor)
        salvar_estoque()  # Salvar após adicionar
        return redirect(url_for('index'))
    return render_template('adicionar.html')

@app.route('/remover')
def remover():
    global estoque
    estoque = [flor for flor in estoque if not flor.esta_expirada()]
    salvar_estoque()  # Salvar após remover
    return redirect(url_for('index'))

@app.route('/saida', methods=['GET', 'POST'])
def saida():
    global estoque
    if request.method == 'POST':
        index_lote = int(request.form['lote_index'])
        quantidade_saida = int(request.form['quantidade_saida'])
        if 0 <= index_lote < len(estoque):
            flor = estoque[index_lote]
            if flor.quantidade >= quantidade_saida:
                flor.quantidade -= quantidade_saida
            else:
                flor.quantidade = 0
            # Remover se quantidade 0
            if flor.quantidade == 0:
                estoque.pop(index_lote)
        salvar_estoque()  # Salvar após saída
        return redirect(url_for('index'))
    # Passar lista de lotes para o template
    lotes_disponiveis = [(i, f"{flor.variedade} - {flor.data_colheita.date()} (Qtd: {flor.quantidade})") for i, flor in enumerate(estoque)]
    return render_template('saida.html', lotes=lotes_disponiveis)

@app.route('/relatorio')
def relatorio():
    # Mesmo cálculo do index
    lotes = []
    total_quantidade = 0
    for flor in estoque:
        lote = {
            'variedade': flor.variedade,
            'quantidade': flor.quantidade,
            'data_colheita': flor.data_colheita.date(),
            'data_maxima': flor.data_maxima.date(),
            'expirada': flor.esta_expirada(),
            'dias_para_expirar': flor.dias_para_expirar()
        }
        lotes.append(lote)
        total_quantidade += flor.quantidade
    lotes.sort(key=lambda x: (x['variedade'], x['data_colheita']))
    return render_template('relatorio.html', lotes=lotes, total_quantidade=total_quantidade, now=datetime.now())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)