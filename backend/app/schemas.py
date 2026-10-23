"""Contratos de entrada e saída da API (Pydantic v2).

Aqui ficam as validações de formato e de coerência entre campos.
Regras que dependem do banco (unicidade, agenda, situação) ficam nos routers.
"""

import re
from datetime import date, datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import Finalidade, StatusDeslocamento, StatusVeiculo

# ABC1234 (padrão antigo) ou ABC1D23 (Mercosul), já sem hífen e em maiúsculas.
PLACA_RE = re.compile(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$")
CATEGORIAS_CNH = {"A", "B", "C", "D", "E", "AB", "AC", "AD", "AE"}
ANO_MAXIMO = date.today().year + 1


def normalizar_placa(valor: str) -> str:
    placa = re.sub(r"[\s-]", "", valor).upper()
    if not PLACA_RE.match(placa):
        raise ValueError("Placa inválida. Use o padrão ABC1234 ou ABC1D23.")
    return placa


def normalizar_cnh(valor: str) -> str:
    cnh = re.sub(r"\D", "", valor)
    if len(cnh) != 11:
        raise ValueError("A CNH deve ter 11 dígitos numéricos.")
    return cnh


def normalizar_categoria(valor: str) -> str:
    categoria = valor.strip().upper()
    if categoria not in CATEGORIAS_CNH:
        opcoes = ", ".join(sorted(CATEGORIAS_CNH))
        raise ValueError(f"Categoria de CNH inválida. Use uma destas: {opcoes}.")
    return categoria


class Entrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class Atualizacao(Entrada):
    """Base das atualizações parciais: campo obrigatório não pode virar nulo."""

    obrigatorios: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def recusar_nulos(self):
        for campo in self.obrigatorios & self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"O campo '{campo}' não pode ficar vazio.")
        return self


# --------------------------------------------------------------------------- #
# Veículo
# --------------------------------------------------------------------------- #
class VeiculoBase(Entrada):
    placa: str = Field(..., max_length=8, examples=["ABC1D23"])
    marca: str = Field(..., min_length=2, max_length=60)
    modelo: str = Field(..., min_length=2, max_length=80)
    ano: int = Field(..., ge=1950, le=ANO_MAXIMO)
    cor: str | None = Field(None, max_length=30)
    tipo: str | None = Field(None, max_length=40)
    km_atual: float = Field(0, ge=0)
    status: StatusVeiculo = StatusVeiculo.disponivel

    @field_validator("placa")
    @classmethod
    def validar_placa(cls, v: str) -> str:
        return normalizar_placa(v)


class VeiculoCreate(VeiculoBase):
    pass


class VeiculoUpdate(Atualizacao):
    obrigatorios: ClassVar[frozenset[str]] = frozenset(
        {"placa", "marca", "modelo", "ano", "km_atual", "status"}
    )

    placa: str | None = Field(None, max_length=8)
    marca: str | None = Field(None, min_length=2, max_length=60)
    modelo: str | None = Field(None, min_length=2, max_length=80)
    ano: int | None = Field(None, ge=1950, le=ANO_MAXIMO)
    cor: str | None = Field(None, max_length=30)
    tipo: str | None = Field(None, max_length=40)
    km_atual: float | None = Field(None, ge=0)
    status: StatusVeiculo | None = None

    @field_validator("placa")
    @classmethod
    def validar_placa(cls, v: str | None) -> str | None:
        return normalizar_placa(v) if v is not None else v


class VeiculoOut(VeiculoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime


# --------------------------------------------------------------------------- #
# Motorista
# --------------------------------------------------------------------------- #
class MotoristaBase(Entrada):
    nome: str = Field(..., min_length=3, max_length=120)
    cnh: str = Field(..., examples=["00000000001"])
    categoria_cnh: str = "B"
    validade_cnh: date | None = None
    telefone: str | None = Field(None, max_length=20)
    setor: str | None = Field(None, max_length=60)
    ativo: bool = True

    @field_validator("cnh")
    @classmethod
    def validar_cnh(cls, v: str) -> str:
        return normalizar_cnh(v)

    @field_validator("categoria_cnh")
    @classmethod
    def validar_categoria(cls, v: str) -> str:
        return normalizar_categoria(v)


class MotoristaCreate(MotoristaBase):
    pass


class MotoristaUpdate(Atualizacao):
    obrigatorios: ClassVar[frozenset[str]] = frozenset({"nome", "cnh", "categoria_cnh", "ativo"})

    nome: str | None = Field(None, min_length=3, max_length=120)
    cnh: str | None = None
    categoria_cnh: str | None = None
    validade_cnh: date | None = None
    telefone: str | None = Field(None, max_length=20)
    setor: str | None = Field(None, max_length=60)
    ativo: bool | None = None

    @field_validator("cnh")
    @classmethod
    def validar_cnh(cls, v: str | None) -> str | None:
        return normalizar_cnh(v) if v is not None else v

    @field_validator("categoria_cnh")
    @classmethod
    def validar_categoria(cls, v: str | None) -> str | None:
        return normalizar_categoria(v) if v is not None else v


class MotoristaOut(MotoristaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime


# --------------------------------------------------------------------------- #
# Deslocamento
# --------------------------------------------------------------------------- #
def validar_coerencia_deslocamento(
    data_saida: date,
    data_retorno: date | None,
    km_inicial: float | None,
    km_final: float | None,
    status: StatusDeslocamento,
) -> None:
    """Regras 3 e 4. Usada no cadastro (schema) e na atualização (router)."""
    if data_retorno is not None and data_retorno < data_saida:
        raise ValueError("A data de retorno não pode ser anterior à data de saída.")
    if km_inicial is not None and km_final is not None and km_final < km_inicial:
        raise ValueError("O km final não pode ser menor que o km inicial.")
    if status == StatusDeslocamento.realizado and data_retorno is None:
        raise ValueError("Um deslocamento realizado precisa de data de retorno.")


class DeslocamentoBase(Entrada):
    veiculo_id: int
    motorista_id: int
    destino: str = Field(..., min_length=2, max_length=160)
    data_saida: date
    data_retorno: date | None = None
    finalidade: Finalidade
    observacao: str | None = Field(None, max_length=1000)
    km_inicial: float | None = Field(None, ge=0)
    km_final: float | None = Field(None, ge=0)
    status: StatusDeslocamento = StatusDeslocamento.previsto


class DeslocamentoCreate(DeslocamentoBase):
    @model_validator(mode="after")
    def validar_coerencia(self):
        validar_coerencia_deslocamento(
            self.data_saida, self.data_retorno, self.km_inicial, self.km_final, self.status
        )
        return self


class DeslocamentoUpdate(Atualizacao):
    obrigatorios: ClassVar[frozenset[str]] = frozenset(
        {"veiculo_id", "motorista_id", "destino", "data_saida", "finalidade", "status"}
    )

    veiculo_id: int | None = None
    motorista_id: int | None = None
    destino: str | None = Field(None, min_length=2, max_length=160)
    data_saida: date | None = None
    data_retorno: date | None = None
    finalidade: Finalidade | None = None
    observacao: str | None = Field(None, max_length=1000)
    km_inicial: float | None = Field(None, ge=0)
    km_final: float | None = Field(None, ge=0)
    status: StatusDeslocamento | None = None


class ConclusaoDeslocamento(Entrada):
    km_final: float = Field(..., ge=0)
    data_retorno: date | None = Field(None, description="Padrão: data de hoje")


class ResumoVeiculo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    placa: str
    marca: str
    modelo: str


class ResumoMotorista(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class DeslocamentoOut(DeslocamentoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime
    km_percorrido: float | None = None
    veiculo: ResumoVeiculo
    motorista: ResumoMotorista


# --------------------------------------------------------------------------- #
# Painel (S3) — definições dos indicadores em docs/Arquitetura.md (ADR-010)
# --------------------------------------------------------------------------- #
class ItemContagem(BaseModel):
    rotulo: str
    valor: int


class Indicadores(BaseModel):
    periodo_inicio: date
    periodo_fim: date
    # Veículos (situação atual; não depende do período)
    total_veiculos: int
    veiculos_disponiveis: int
    veiculos_em_viagem: int
    veiculos_manutencao: int
    veiculos_inativos: int
    # Deslocamentos no período: total = previstas + em andamento + realizadas + canceladas
    total_deslocamentos: int
    viagens_previstas: int
    viagens_em_andamento: int
    viagens_realizadas: int
    viagens_canceladas: int
    # Calculados
    taxa_realizacao: float
    km_total_percorrido: float
    media_km_por_viagem: float
    taxa_utilizacao_frota: float
    # Quebras
    deslocamentos_por_finalidade: list[ItemContagem]
    top_destinos: list[ItemContagem]
    serie_mensal: list[ItemContagem]
