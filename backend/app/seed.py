"""Popula o banco com dados de demonstração FICTÍCIOS.

Uso (PowerShell, na raiz):  .\\scripts\\seed.ps1

Só roda com o banco vazio; nunca sobrescreve dados existentes.
CNHs (000…), telefones (DDD 00) e nomes são inventados de propósito.
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
    # placa, marca, modelo, ano, cor, tipo, km inicial, situação
    ("TST1A01", "Fiat", "Strada", 2022, "Branco", "Caminhonete", 48000, StatusVeiculo.disponivel),
    ("TST2B02", "Chevrolet", "Spin", 2021, "Prata", "Van", 73000, StatusVeiculo.disponivel),
    ("TST3C03", "Renault", "Kwid", 2023, "Cinza", "Hatch", 19000, StatusVeiculo.disponivel),
    ("TST4D04", "Toyota", "Corolla", 2020, "Preto", "Sedan", 96000, StatusVeiculo.disponivel),
    (
        "TST5005",
        "Volkswagen",
        "Saveiro",
        2019,
        "Vermelho",
        "Caminhonete",
        55000,
        StatusVeiculo.disponivel,
    ),
    (
        "TST6006",
        "Mercedes-Benz",
        "Sprinter",
        2018,
        "Branco",
        "Van",
        184000,
        StatusVeiculo.manutencao,
    ),
]

MOTORISTAS = [
    # nome, CNH, categoria, setor, telefone, ativo
    ("Ana Exemplo", "00000000001", "B", "Administrativo", "(00) 90000-0001", True),
    ("Bruno Exemplo", "00000000002", "D", "Logística", "(00) 90000-0002", True),
    ("Carla Exemplo", "00000000003", "AB", "Manutenção", "(00) 90000-0003", True),
    ("Diego Exemplo", "00000000004", "B", "Operações", "(00) 90000-0004", False),
]

DESTINOS = [
    "Unidade Centro",
    "Almoxarifado Central",
    "Escritório Regional Norte",
    "Escritório Regional Sul",
    "Oficina Credenciada",
    "Depósito Leste",
    "Polo Rural",
]


def rodar() -> None:
    criar_tabelas()
    db = SessionLocal()
    try:
        if db.query(Veiculo).count() or db.query(Motorista).count():
            print("O banco já possui dados. Nada foi alterado.")
            return

        sorteio = random.Random(42)  # resultado reproduzível
        hoje = date.today()

        veiculos = []
        for placa, marca, modelo, ano, cor, tipo, km, situacao in VEICULOS:
            v = Veiculo(
                placa=placa,
                marca=marca,
                modelo=modelo,
                ano=ano,
                cor=cor,
                tipo=tipo,
                km_atual=km,
                status=StatusVeiculo.disponivel,
            )
            v.situacao_final = situacao
            veiculos.append(v)
        motoristas = [
            Motorista(
                nome=n,
                cnh=c,
                categoria_cnh=cat,
                setor=s,
                telefone=t,
                ativo=True,
                validade_cnh=hoje + timedelta(days=365 * 2),
            )
            for n, c, cat, s, t, _ in MOTORISTAS
        ]
        db.add_all(veiculos + motoristas)
        db.flush()

        total = 0
        em_andamento_usado = False
        for v in veiculos:
            # veículo em manutenção só tem histórico passado
            limite = (
                hoje - timedelta(days=10)
                if v.situacao_final != StatusVeiculo.disponivel
                else hoje + timedelta(days=30)
            )
            cursor = hoje - timedelta(days=90) + timedelta(days=sorteio.randint(0, 4))
            while cursor < limite:
                fim = cursor + timedelta(days=sorteio.randint(0, 2))
                if fim < hoje:
                    status = (
                        StatusDeslocamento.cancelado
                        if sorteio.random() < 0.1
                        else StatusDeslocamento.realizado
                    )
                elif cursor <= hoje and not em_andamento_usado:
                    status = StatusDeslocamento.em_andamento
                    em_andamento_usado = True
                elif cursor <= hoje:
                    cursor = hoje + timedelta(days=1)
                    continue
                else:
                    status = StatusDeslocamento.previsto

                # motorista inativo (último) aparece só em viagens passadas
                aptos = motoristas if fim < hoje else motoristas[:-1]
                d = Deslocamento(
                    veiculo_id=v.id,
                    motorista_id=sorteio.choice(aptos).id,
                    destino=sorteio.choice(DESTINOS),
                    data_saida=cursor,
                    data_retorno=fim,
                    finalidade=sorteio.choice(list(Finalidade)),
                    km_inicial=v.km_atual,
                    status=status,
                )
                if status == StatusDeslocamento.realizado:
                    d.km_final = v.km_atual + sorteio.randint(20, 380)
                    v.km_atual = d.km_final
                elif status == StatusDeslocamento.em_andamento:
                    v.status = StatusVeiculo.em_viagem
                db.add(d)
                total += 1
                cursor = fim + timedelta(days=sorteio.randint(1, 6))

            if v.situacao_final != StatusVeiculo.disponivel:
                v.status = v.situacao_final
        motoristas[-1].ativo = False

        db.commit()
        print(
            f"Dados fictícios criados: {len(veiculos)} veículos, "
            f"{len(motoristas)} motoristas, {total} deslocamentos."
        )
    finally:
        db.close()


if __name__ == "__main__":
    rodar()
