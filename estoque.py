from datetime import datetime, timedelta

class Flor:
    def __init__(self, variedade, data_colheita):
        self.variedade = variedade
        self.data_colheita = datetime.strptime(data_colheita, "%Y-%m-%d")
        self.data_maxima = self.data_colheita + timedelta(days=7)
    
    def esta_expirada(self):
        return datetime.now() > self.data_maxima
    
    def __str__(self):
        status = "Expirada" if self.esta_expirada() else "Válida"
        return f"Variedade: {self.variedade}, Colheita: {self.data_colheita.date()}, Máxima: {self.data_maxima.date()}, Status: {status}"

estoque = []

def adicionar_flor(variedade, data_colheita):
    flor = Flor(variedade, data_colheita)
    estoque.append(flor)
    print(f"Flor adicionada: {flor}")

def listar_estoque():
    if not estoque:
        print("Estoque vazio.")
        return
    print("Estoque atual:")
    for flor in estoque:
        print(flor)

def remover_expiradas():
    global estoque
    estoque = [flor for flor in estoque if not flor.esta_expirada()]
    print("Flores expiradas removidas.")

if __name__ == "__main__":
    while True:
        print("\n--- Menu do Estoque de Flores ---")
        print("1. Adicionar flor")
        print("2. Listar estoque")
        print("3. Remover expiradas")
        print("4. Sair")
        opcao = input("Escolha uma opção (1-4): ")
        
        if opcao == "1":
            variedade = input("Digite a variedade da flor: ")
            data = input("Digite a data de colheita (YYYY-MM-DD): ")
            adicionar_flor(variedade, data)
        elif opcao == "2":
            listar_estoque()
        elif opcao == "3":
            remover_expiradas()
        elif opcao == "4":
            print("Saindo...")
            break
        else:
            print("Opção inválida. Tente novamente.")