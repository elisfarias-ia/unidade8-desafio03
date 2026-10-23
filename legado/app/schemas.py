"""Contratos de entrada e saída da API (Pydantic v2)."""

from datetime import date, datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import Finalidade, StatusDeslocamento, StatusVeiculo

PLACA_RE = re.compile(r"^([A-Z]{3}-?\d{4}|[A-Z]{3}\d[A-Z]\d{2})$")


# --------------------------------------------------------------------------- #
# Veículo
# --------------------------------------------------------------------------- #
class VeiculoBase(BaseModel):
    placa: str = Field(..., max_length=8, examples=["ABC1D23"])
    modelo: str = Field(..., min_length=2, max_length=80)
    marca: str = Field(..., min_length=2, max_length=60)
    ano: int = Field(..., ge=1950, le=date.today().year + 1)
    cor: str | None = Field(None, max_length=30)
    tipo: str | None = Field(None, max_length=40)
    km_atual: float = Field(0, ge=0)
    status: StatusVeiculo = StatusVeiculo.disponivel

    @field_validator("placa")
    @classmethod
    def validar_placa(cls, v: str) -> str:
        v = v.strip().upper().replace("-", "")
        if not PLACA_RE.match(v):
            raise ValueError("Placa inválida. Use o padrão ABC1234 ou ABC1D23.")
        return v


class VeiculoCreate(VeiculoBase):
    pass


class VeiculoUpdate(BaseModel):
    modelo: str | None = Field(None, min_length=2, max_length=80)
    marca: str | None = Field(None, min_length=2, max_length=60)
    ano: int | None = Field(None, ge=1950, le=date.today().year + 1)
    cor: str | None = None
    tipo: str | None = None
    km_atual: float | None = Field(None, ge=0)
    status: StatusVeiculo | None = None


class VeiculoOut(VeiculoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime


# --------------------------------------------------------------------------- #
# Motorista
# --------------------------------------------------------------------------- #
class MotoristaBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=120)
    cnh: str = Field(..., min_length=5, max_length=20)
    categoria_cnh: str = Field("B", max_length=5)
    validade_cnh: date | None = None
    telefone: str | None = Field(None, max_length=20)
    setor: str | None = Field(None, max_length=60)
    ativo: bool = True


class MotoristaCreate(MotoristaBase):
    pass


class MotoristaUpdate(BaseModel):
    nome: str | None = Field(None, min_length=3, max_length=120)
    categoria_cnh: str | None = None
    validade_cnh: date | None = None
    telefone: str | None = None
    setor: str | None = None
    ativo: bool | None = None


class MotoristaOut(MotoristaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime


# --------------------------------------------------------------------------- #
# Deslocamento
# --------------------------------------------------------------------------- #
class DeslocamentoBase(BaseModel):
    veiculo_id: int
    motorista_id: int
    destino: str = Field(..., min_length=2, max_length=160)
    data_saida: date
    data_retorno: date | None = None
    finalidade: Finalidade
    observacao: str | None = None
    km_inicial: float | None = Field(None, ge=0)
    km_final: float | None = Field(None, ge=0)
    status: StatusDeslocamento = StatusDeslocamento.previsto

    @model_validator(mode="after")
    def validar_coerencia(self):
        if self.data_retorno and self.data_retorno < self.data_saida:
            raise ValueError("A data de retorno não pode ser anterior à data de saída.")
        if (
            self.km_inicial is not None
            and self.km_final is not None
            and self.km_final < self.km_inicial
        ):
            raise ValueError("O km final não pode ser menor que o km inicial.")
        if self.status == StatusDeslocamento.realizado and self.data_retorno is None:
            raise ValueError("Um deslocamento realizado precisa de data de retorno.")
        return self


class DeslocamentoCreate(DeslocamentoBase):
    pass


class DeslocamentoUpdate(BaseModel):
    destino: str | None = None
    data_saida: date | None = None
    data_retorno: date | None = None
    finalidade: Finalidade | None = None
    observacao: str | None = None
    km_inicial: float | None = Field(None, ge=0)
    km_final: float | None = Field(None, ge=0)
    status: StatusDeslocamento | None = None
    veiculo_id: int | None = None
    motorista_id: int | None = None


class ResumoVeiculo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    placa: str
    modelo: str
    marca: str


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
# Dashboard
# --------------------------------------------------------------------------- #
class ItemContagem(BaseModel):
    rotulo: str
    valor: float


class Indicadores(BaseModel):
    periodo_inicio: date
    periodo_fim: date
    total_veiculos: int
    veiculos_disponiveis: int
    veiculos_em_viagem: int
    total_deslocamentos: int
    viagens_previstas: int
    viagens_realizadas: int
    taxa_realizacao: float          # indicador calculado (%)
    km_total_percorrido: float      # indicador calculado
    media_km_por_viagem: float      # indicador calculado
    taxa_utilizacao_frota: float    # indicador calculado (%)
    deslocamentos_por_finalidade: list[ItemContagem]
    top_destinos: list[ItemContagem]
    serie_mensal: list[ItemContagem]
