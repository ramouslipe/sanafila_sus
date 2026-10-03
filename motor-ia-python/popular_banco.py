import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker('pt_BR')

# Configuração de conexão com o seu PostgreSQL local (porta 5433)
DB_CONFIG = {
    'dbname': 'sanafila_sus',
    'user': 'postgres',
    'password': '', # Se o seu usuário postgres tiver senha, coloque aqui
    'host': 'localhost',
    'port': '5433'
}

ESPECIALIDADES = ['Ortopedia', 'Cardiologia', 'Neurologia', 'Oftalmologia']
CORES_MANCHESTER = ['Vermelho', 'Laranja', 'Amarelo', 'Verde', 'Azul']
CIDS = ['I10', 'E11', 'M54', 'H25', 'G40'] # Hipertensão, Diabetes, Dor nas costas, Catarata, Epilepsia

def gerar_cns():
    # Gera um número falso parecido com o Cartão Nacional de Saúde (15 dígitos)
    return str(random.randint(100000000000000, 999999999999999))

def popular_dados():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("Conectado ao banco. Gerando 50 pacientes falsos...")

        for _ in range(50):
            # 1. Insere Paciente no CadSUS
            cns = gerar_cns()
            nome = fake.name()
            # Gera idade entre 5 e 85 anos
            data_nasc = fake.date_of_birth(minimum_age=5, maximum_age=85)
            telefone = fake.phone_number()
            
            cur.execute("""
                INSERT INTO cadsus_paciente (cns, nome, data_nascimento, telefone)
                VALUES (%s, %s, %s, %s) RETURNING id;
            """, (cns, nome, data_nasc, telefone))
            
            paciente_id = cur.fetchone()[0]

            # 2. Insere Histórico na RNDS
            cid = random.choice(CIDS)
            diabetes = random.choices([True, False], weights=[0.2, 0.8])[0]
            hipertensao = random.choices([True, False], weights=[0.3, 0.7])[0]
            faltas = random.randint(0, 3)

            cur.execute("""
                INSERT INTO rnds_historico (paciente_id, cid_principal, diabetes, hipertensao, historico_faltas)
                VALUES (%s, %s, %s, %s, %s);
            """, (paciente_id, cid, diabetes, hipertensao, faltas))

            # 3. Insere na Fila de Regulação (SISREG)
            especialidade = random.choice(ESPECIALIDADES)
            risco = random.choices(CORES_MANCHESTER, weights=[0.05, 0.1, 0.2, 0.45, 0.2])[0]
            # Simula que o paciente entrou na fila entre hoje e 6 meses atrás
            dias_atras = random.randint(0, 180)
            data_entrada = datetime.now() - timedelta(days=dias_atras)

            cur.execute("""
                INSERT INTO sisreg_fila (paciente_id, especialidade, risco_inicial_manchester, data_entrada)
                VALUES (%s, %s, %s, %s);
            """, (paciente_id, especialidade, risco, data_entrada.date()))

        conn.commit()
        cur.close()
        conn.close()
        print("Sucesso! 50 pacientes inseridos na fila do SUS fictícia.")

    except Exception as e:
        print(f"Erro ao popular banco: {e}")

if __name__ == '__main__':
    popular_dados()