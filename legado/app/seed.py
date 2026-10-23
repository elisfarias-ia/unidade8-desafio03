"""Popula o banco com dados de demonstração.

Uso:  python -m app.seed
"""

import random
from datetime import date, timedelta

from app.database import SessionLocal, criar_tabelas
from app.models import (
    Deslocamento,
    Finalidade,
    Motorista,
    StatusDeslocamento,
    StatusVeiculo,
    Veiculo,
)

VEICULOS = [
    ("ABC1D23", "Fiat", "Strada", 2022, "Branco", "Caminhonete", 48230),
    ("DEF2G45", "Chevrolet", "Spin", 2021, "Prata", "Van", 73110),
    ("GHI3J67", "Renault", "Kwid", 2023, "Cinza", "Hatch", 19875),
    ("JKL4M89", "Toyota", "Corolla", 2020, "Preto", "Sedan", 96400),
    ("MNO5P01", "Mercedes-Benz", "Sprinter", 2019, "Branco", "Van", 184320),
    ("PQR6S23", "Volkswagen", "Saveiro", 2022, "Vermelho", "Caminhonete", 55600),
]

MOTORISTAS = [
    ("Joana Ribeiro Alves", "04512378901", "B", "Administrativo", "(11) 98100-2233"),
    ("Carlos Eduardo Pinto", "07834521190", "D", "Logística", "(11) 97444-1020"),
    ("Marcos Antônio Silva", "01298765432", "AB", "Manutenção", "(19) 99812-3344"),
    ("Patrícia Nunes Lima", "05566778899", "B", "Operações", "(11) 96123-7788"),
]

DESTINOS = [
    "Campinas - SP",
    "Santos - Porto",
    "São José dos Campos - SP",
    "Sede administrativa - Centro",
    "Ribeirão Preto - SP",
    "Sorocaba - Unidade 2",
    "Guarulhos - Aeroporto",
]


def rodar() -> None:
    criar_tabelas()
    db = SessionLocal()
    if db.query(Veiculo).count():
        print("O banco já possui dados. Nada foi alterado.")
        db.close()
        return

    for placa, marca, modelo, ano, cor, tipo, km in VEICULOS:
        db.add(
            Veiculo(
                placa=placa,
                marca=marca,
                modelo=modelo,
                ano=ano,
                cor=cor,
                tipo=tipo,
                km_atual=km,
                status=StatusVeiculo.disponivel,
            )
        )
    for nome, cnh, cat, setor, tel in MOTORISTAS:
        db.add(
            Motorista(
                nome=nome,
                cnh=cnh,
                categoria_cnh=cat,
                setor=setor,
                telefone=tel,
                validade_cnh=date.today() + timedelta(days=random.randint(120, 900)),
                ativo=1,
            )
        )
    db.commit()

    veiculos = db.query(Veiculo).all()
    motoristas = db.query(Motorista).all()
    hoje = date.today()
    random.seed(7)

    # Histórico realizado dos últimos 90 dias
    for _ in range(38):
        v = random.choice(veiculos)
        saida = hoje - timedelta(days=random.randint(3, 88))
        duracao = random.choice([0, 0, 1, 1, 2, 3])
        km_ini = round(v.km_atual - random.randint(400, 4000), 1)
        km_fim = round(km_ini + random.randint(35, 620), 1)
        db.add(
            Deslocamento(
                veiculo_id=v.id,
                motorista_id=random.choice(motoristas).id,
                destino=random.choice(DESTINOS),
                data_saida=saida,
                data_retorno=saida + timedelta(days=duracao),
                finalidade=random.choice(list(Finalidade)),
                km_inicial=km_ini,
                km_final=km_fim,
                status=StatusDeslocamento.realizado,
            )
        )

    # Viagens canceladas
    for _ in range(4):
        v = random.choice(veiculos)
        saida = hoje - timedelta(days=random.randint(5, 60))
        db.add(
            Deslocamento(
                veiculo_id=v.id,
                motorista_id=random.choice(motoristas).id,
                destino=random.choice(DESTINOS),
                data_saida=saida,
                data_retorno=saida,
                finalidade=Finalidade.administrativa,
                status=StatusDeslocamento.cancelado,
                observacao="Cancelada por indisponibilidade de agenda.",
            )
        )

    # Agenda futura (viagens previstas), uma por veículo para evitar conflito
    for i, v in enumerate(veiculos[:5]):
        saida = hoje + timedelta(days=i + 1)
        db.add(
            Deslocamento(
                veiculo_id=v.id,
                motorista_id=motoristas[i % len(motoristas)].id,
                destino=DESTINOS[i % len(DESTINOS)],
                data_saida=saida,
                data_retorno=saida + timedelta(days=random.choice([0, 1])),
                finalidade=random.choice(list(Finalidade)),
                km_inicial=v.km_atual,
                status=StatusDeslocamento.previsto,
            )
        )

    db.commit()
    print(
        f"Carga concluída: {len(veiculos)} veículos, {len(motoristas)} motoristas, "
        f"{db.query(Deslocamento).count()} deslocamentos."
    )
    db.close()


if __name__ == "__main__":
    rodar()
