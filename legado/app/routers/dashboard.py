"""Indicadores calculados a partir dos dados persistidos."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Deslocamento, StatusDeslocamento, StatusVeiculo, Veiculo
from app.schemas import Indicadores, ItemContagem

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

ROTULO_FINALIDADE = {
    "administrativa": "Administrativa",
    "operacional": "Operacional",
    "manutencao": "Manutenção",
    "entrega": "Entrega",
    "visita_tecnica": "Visita técnica",
    "outros": "Outros",
}


@router.get("/indicadores", response_model=Indicadores)
def indicadores(
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    db: Session = Depends(get_db),
):
    # Janela padrão: 90 dias de histórico + 30 dias de agenda futura,
    # para que previstas e realizadas apareçam no mesmo recorte.
    hoje = date.today()
    inicio = data_inicio or (hoje - timedelta(days=90))
    fim = data_fim or (hoje + timedelta(days=30))
    if fim < inicio:
        inicio, fim = fim, inicio

    no_periodo = [Deslocamento.data_saida >= inicio, Deslocamento.data_saida <= fim]

    # --- Frota -----------------------------------------------------------
    total_veiculos = db.query(func.count(Veiculo.id)).scalar() or 0
    disponiveis = (
        db.query(func.count(Veiculo.id))
        .filter(Veiculo.status == StatusVeiculo.disponivel)
        .scalar()
        or 0
    )
    em_viagem = (
        db.query(func.count(Veiculo.id))
        .filter(Veiculo.status == StatusVeiculo.em_viagem)
        .scalar()
        or 0
    )

    # --- Deslocamentos ---------------------------------------------------
    agregados = (
        db.query(
            func.count(Deslocamento.id),
            func.sum(
                case((Deslocamento.status == StatusDeslocamento.previsto, 1), else_=0)
            ),
            func.sum(
                case((Deslocamento.status == StatusDeslocamento.realizado, 1), else_=0)
            ),
            func.sum(
                case(
                    (
                        (Deslocamento.km_final.isnot(None))
                        & (Deslocamento.km_inicial.isnot(None)),
                        Deslocamento.km_final - Deslocamento.km_inicial,
                    ),
                    else_=0,
                )
            ),
        )
        .filter(*no_periodo)
        .one()
    )
    total_desl = agregados[0] or 0
    previstas = int(agregados[1] or 0)
    realizadas = int(agregados[2] or 0)
    km_total = round(float(agregados[3] or 0), 1)

    # Indicadores calculados
    base_programada = previstas + realizadas
    taxa_realizacao = round(realizadas / base_programada * 100, 1) if base_programada else 0.0
    media_km = round(km_total / realizadas, 1) if realizadas else 0.0

    veiculos_usados = (
        db.query(func.count(func.distinct(Deslocamento.veiculo_id)))
        .filter(*no_periodo)
        .scalar()
        or 0
    )
    taxa_utilizacao = (
        round(veiculos_usados / total_veiculos * 100, 1) if total_veiculos else 0.0
    )

    # --- Quebras ---------------------------------------------------------
    por_finalidade = [
        ItemContagem(
            rotulo=ROTULO_FINALIDADE.get(
                f.value if hasattr(f, "value") else str(f), str(f)
            ),
            valor=qtd,
        )
        for f, qtd in db.query(Deslocamento.finalidade, func.count(Deslocamento.id))
        .filter(*no_periodo)
        .group_by(Deslocamento.finalidade)
        .order_by(func.count(Deslocamento.id).desc())
        .all()
    ]

    top_destinos = [
        ItemContagem(rotulo=destino, valor=qtd)
        for destino, qtd in db.query(Deslocamento.destino, func.count(Deslocamento.id))
        .filter(*no_periodo)
        .group_by(Deslocamento.destino)
        .order_by(func.count(Deslocamento.id).desc())
        .limit(5)
        .all()
    ]

    serie_mensal = [
        ItemContagem(rotulo=mes, valor=qtd)
        for mes, qtd in db.query(
            func.strftime("%Y-%m", Deslocamento.data_saida),
            func.count(Deslocamento.id),
        )
        .filter(*no_periodo)
        .group_by(func.strftime("%Y-%m", Deslocamento.data_saida))
        .order_by(func.strftime("%Y-%m", Deslocamento.data_saida))
        .all()
    ]

    return Indicadores(
        periodo_inicio=inicio,
        periodo_fim=fim,
        total_veiculos=total_veiculos,
        veiculos_disponiveis=disponiveis,
        veiculos_em_viagem=em_viagem,
        total_deslocamentos=total_desl,
        viagens_previstas=previstas,
        viagens_realizadas=realizadas,
        taxa_realizacao=taxa_realizacao,
        km_total_percorrido=km_total,
        media_km_por_viagem=media_km,
        taxa_utilizacao_frota=taxa_utilizacao,
        deslocamentos_por_finalidade=por_finalidade,
        top_destinos=top_destinos,
        serie_mensal=serie_mensal,
    )
