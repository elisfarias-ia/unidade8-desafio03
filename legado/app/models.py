"""Entidades do domínio: Veículo, Motorista e Deslocamento."""

from datetime import datetime, date
import enum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class StatusVeiculo(str, enum.Enum):
    disponivel = "disponivel"
    em_viagem = "em_viagem"
    manutencao = "manutencao"
    inativo = "inativo"


class StatusDeslocamento(str, enum.Enum):
    previsto = "previsto"
    em_andamento = "em_andamento"
    realizado = "realizado"
    cancelado = "cancelado"


class Finalidade(str, enum.Enum):
    administrativa = "administrativa"
    operacional = "operacional"
    manutencao = "manutencao"
    entrega = "entrega"
    visita_tecnica = "visita_tecnica"
    outros = "outros"


class Veiculo(Base):
    __tablename__ = "veiculos"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(8), unique=True, nullable=False, index=True)
    modelo = Column(String(80), nullable=False)
    marca = Column(String(60), nullable=False)
    ano = Column(Integer, nullable=False)
    cor = Column(String(30), nullable=True)
    tipo = Column(String(40), nullable=True)  # sedan, van, caminhonete...
    km_atual = Column(Float, nullable=False, default=0)
    status = Column(
        Enum(StatusVeiculo), nullable=False, default=StatusVeiculo.disponivel
    )
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    deslocamentos = relationship("Deslocamento", back_populates="veiculo")


class Motorista(Base):
    __tablename__ = "motoristas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    cnh = Column(String(20), unique=True, nullable=False, index=True)
    categoria_cnh = Column(String(5), nullable=False, default="B")
    validade_cnh = Column(Date, nullable=True)
    telefone = Column(String(20), nullable=True)
    setor = Column(String(60), nullable=True)
    ativo = Column(Integer, nullable=False, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    deslocamentos = relationship("Deslocamento", back_populates="motorista")


class Deslocamento(Base):
    __tablename__ = "deslocamentos"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(
        Integer, ForeignKey("veiculos.id", ondelete="RESTRICT"), nullable=False
    )
    motorista_id = Column(
        Integer, ForeignKey("motoristas.id", ondelete="RESTRICT"), nullable=False
    )
    destino = Column(String(160), nullable=False)
    data_saida = Column(Date, nullable=False, index=True)
    data_retorno = Column(Date, nullable=True)
    finalidade = Column(Enum(Finalidade), nullable=False)
    observacao = Column(Text, nullable=True)
    km_inicial = Column(Float, nullable=True)
    km_final = Column(Float, nullable=True)
    status = Column(
        Enum(StatusDeslocamento),
        nullable=False,
        default=StatusDeslocamento.previsto,
        index=True,
    )
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    veiculo = relationship("Veiculo", back_populates="deslocamentos")
    motorista = relationship("Motorista", back_populates="deslocamentos")

    @property
    def km_percorrido(self) -> float | None:
        if self.km_inicial is not None and self.km_final is not None:
            return round(self.km_final - self.km_inicial, 1)
        return None
