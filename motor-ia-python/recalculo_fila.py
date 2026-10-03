import psycopg2
from datetime import datetime

# Configuração de conexão com o PostgreSQL
DB_CONFIG = {
    'dbname': 'sanafila_sus',
    'user': 'postgres',
    'password': '', 
    'host': 'localhost',
    'port': '5433'
}

# Tabela de pesos do Protocolo de Manchester
PESOS_RISCO = {
    'Vermelho': 100,
    'Laranja': 80,
    'Amarelo': 60,
    'Verde': 30,
    'Azul': 10
}

def calcular_idade(data_nascimento):
    hoje = datetime.now().date()
    idade = hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))
    return idade

def recalcular_fila():
    print("Iniciando motor de recálculo da Matriz Dinâmica...")
    hoje = datetime.now().date()

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Busca todos os pacientes aguardando na fila, cruzando dados com o CadSUS e a RNDS
        query_busca = """
            SELECT 
                f.id, p.nome, p.data_nascimento, h.diabetes, h.hipertensao, 
                f.risco_inicial_manchester, f.data_entrada, f.especialidade
            FROM sisreg_fila f
            JOIN cadsus_paciente p ON f.paciente_id = p.id
            JOIN rnds_historico h ON h.paciente_id = p.id
            WHERE f.status = 'AGUARDANDO';
        """
        cur.execute(query_busca)
        pacientes = cur.fetchall()

        for paciente in pacientes:
            fila_id, nome, data_nasc, diabetes, hipertensao, risco, data_entrada, especialidade = paciente
            
            score_total = 0

            # 1. Pontuação de Risco Clínico Base
            score_total += PESOS_RISCO.get(risco, 0)

            # 2. Pontuação de Vulnerabilidade (Idade)
            idade = calcular_idade(data_nasc)
            if idade >= 60 or idade <= 12:
                score_total += 20  # Bônus para prioridade legal

            # 3. Pontuação de Histórico Clínico (Comorbidades)
            if diabetes and hipertensao:
                score_total += 15

            # 4. Pontuação de Tempo na Fila (Equidade)
            dias_na_fila = (hoje - data_entrada).days
            score_total += dias_na_fila  # 1 ponto por cada dia de espera

            # Atualiza o score dinâmico do paciente no banco de dados
            cur.execute("""
                UPDATE sisreg_fila 
                SET score_dinamico = %s 
                WHERE id = %s;
            """, (score_total, fila_id))

        conn.commit()
        print(f"Recálculo concluído com sucesso para {len(pacientes)} pacientes.\n")

        # Exibe um "Top 10" para visualizarmos a fila reorganizada
        cur.execute("""
            SELECT p.nome, f.especialidade, f.risco_inicial_manchester, f.score_dinamico, (CURRENT_DATE - f.data_entrada) as dias
            FROM sisreg_fila f
            JOIN cadsus_paciente p ON f.paciente_id = p.id
            WHERE f.status = 'AGUARDANDO'
            ORDER BY f.score_dinamico DESC
            LIMIT 10;
        """)
        
        top10 = cur.fetchall()
        print("--- TOP 10 PACIENTES COM MAIOR PRIORIDADE AGORA ---")
        print(f"{'NOME'.ljust(30)} | {'ESPECIALIDADE'.ljust(15)} | {'RISCO'.ljust(10)} | {'DIAS'.ljust(5)} | {'SCORE'}")
        print("-" * 75)
        for p in top10:
            nome, esp, risco, score, dias = p
            print(f"{nome[:28].ljust(30)} | {esp.ljust(15)} | {risco.ljust(10)} | {str(dias).ljust(5)} | {score}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao processar a matriz de priorização: {e}")

if __name__ == '__main__':
    recalcular_fila()