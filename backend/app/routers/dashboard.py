"""Indicadores do painel, sempre calculados por consulta (regra 9; ADR-010)."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Deslocamento, StatusDeslocamento, StatusVeiculo, Veiculo
from app.schemas import DeslocamentoOut, Indicadores, ItemContagem

router = APIRouter(prefix="/api/dashboard", tags=["Painel"])

DIAS_HISTORICO = 90
DIAS_AGENDA = 30

ROTULO_FINALIDADE = {
    "administrativa": "Administrativa",
    "operacional": "Operacional",
    "manutencao": "Manutenção",
    "entrega": "Entrega",
    "visita_tecnica": "Visita técnica",
    "outros": "Outros",
}


def _periodo(data_inicio: date | None, data_fim: date | None) -> tuple[date, date]:
    hoje = date.today()
    inicio = data_inicio or hoje - timedelta(days=DIAS_HISTORICO)
    fim = data_fim or hoje + timedelta(days=DIAS_AGENDA)
    if fim < inicio:
        raise HTTPException(
            422,
            f"A data final do período ({fim:%d/%m/%Y}) não pode ser anterior à data inicial "
            f"({inicio:%d/%m/%Y}). Ajuste o período.",
        )
    return inicio, fim


def _porcentagem(parte: int | float, total: int | float) -> float:
    return round(parte / total * 100, 1) if total else 0.0


@router.get("/indicadores", response_model=Indicadores)
def indicadores(
    data_inicio: date | None = Query(None, description="Padrão: 90 dias atrás"),
    data_fim: date | None = Query(None, description="Padrão: 30 dias à frente"),
    db: Session = Depends(get_db),
):
    inicio, fim = _periodo(data_inicio, data_fim)
    D = Deslocamento
    no_periodo = [D.data_saida >= inicio, D.data_saida <= fim]

    # --- Veículos: situação atual -----------------------------------------
    por_situacao = dict(db.query(Veiculo.status, func.count(Veiculo.id)).group_by(Veiculo.status))
    total_veiculos = sum(por_situacao.values())

    # --- Deslocamentos: uma consulta agregada -----------------------------
    def contar(situacao: StatusDeslocamento):
        return func.coalesce(func.sum(case((D.status == situacao, 1), else_=0)), 0)

    com_km = and_(
        D.status == StatusDeslocamento.realizado, D.km_inicial.isnot(None), D.km_final.isnot(None)
    )
    total, previstas, em_andamento, realizadas, canceladas, km_total, com_km_qtd = (
        db.query(
            func.count(D.id),
            contar(StatusDeslocamento.previsto),
            contar(StatusDeslocamento.em_andamento),
            contar(StatusDeslocamento.realizado),
            contar(StatusDeslocamento.cancelado),
            func.coalesce(func.sum(case((com_km, D.km_final - D.km_inicial), else_=0)), 0),
            func.coalesce(func.sum(case((com_km, 1), else_=0)), 0),
        )
        .filter(*no_periodo)
        .one()
    )
    km_total = round(float(km_total), 1)

    veiculos_usados = (
        db.query(func.count(func.distinct(D.veiculo_id)))
        .filter(*no_periodo, D.status != StatusDeslocamento.cancelado)
        .scalar()
        or 0
    )

    # --- Quebras (todas as situações, para a soma bater com o total) ------
    contagem = func.count(D.id)
    por_finalidade = [
        ItemContagem(rotulo=ROTULO_FINALIDADE.get(str(f), str(f)), valor=qtd)
        for f, qtd in db.query(D.finalidade, contagem)
        .filter(*no_periodo)
        .group_by(D.finalidade)
        .order_by(contagem.desc(), D.finalidade)
    ]
    top_destinos = [
        ItemContagem(rotulo=destino, valor=qtd)
        for destino, qtd in db.query(D.destino, contagem)
        .filter(*no_periodo)
        .group_by(D.destino)
        .order_by(contagem.desc(), D.destino)
        .limit(5)
    ]
    mes = func.strftime("%Y-%m", D.data_saida)
    serie_mensal = [
        ItemContagem(rotulo=m, valor=qtd)
        for m, qtd in db.query(mes, contagem).filter(*no_periodo).group_by(mes).order_by(mes)
    ]

    return Indicadores(
        periodo_inicio=inicio,
        periodo_fim=fim,
        total_veiculos=total_veiculos,
        veiculos_disponiveis=por_situacao.get(StatusVeiculo.disponivel, 0),
        veiculos_em_viagem=por_situacao.get(StatusVeiculo.em_viagem, 0),
        veiculos_manutencao=por_situacao.get(StatusVeiculo.manutencao, 0),
        veiculos_inativos=por_situacao.get(StatusVeiculo.inativo, 0),
        total_deslocamentos=total,
        viagens_previstas=int(previstas),
        viagens_em_andamento=int(em_andamento),
        viagens_realizadas=int(realizadas),
        viagens_canceladas=int(canceladas),
        taxa_realizacao=_porcentagem(int(realizadas), int(previstas) + int(realizadas)),
        km_total_percorrido=km_total,
        media_km_por_viagem=round(km_total / int(com_km_qtd), 1) if com_km_qtd else 0.0,
        taxa_utilizacao_frota=_porcentagem(veiculos_usados, total_veiculos),
        deslocamentos_por_finalidade=por_finalidade,
        top_destinos=top_destinos,
        serie_mensal=serie_mensal,
    )


@router.get("/proximas-saidas", response_model=list[DeslocamentoOut])
def proximas_saidas(limite: int = Query(5, ge=1, le=50), db: Session = Depends(get_db)):
    """Viagens previstas a partir de hoje, da mais próxima para a mais distante."""
    return (
        db.query(Deslocamento)
        .options(joinedload(Deslocamento.veiculo), joinedload(Deslocamento.motorista))
        .filter(
            Deslocamento.status == StatusDeslocamento.previsto,
            Deslocamento.data_saida >= date.today(),
        )
        .order_by(Deslocamento.data_saida, Deslocamento.id)
        .limit(limite)
        .all()
    )
