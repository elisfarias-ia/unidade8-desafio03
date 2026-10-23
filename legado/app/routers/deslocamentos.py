"""Registro e consulta de deslocamentos."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Deslocamento,
    Finalidade,
    Motorista,
    StatusDeslocamento,
    StatusVeiculo,
    Veiculo,
)
from app.schemas import DeslocamentoCreate, DeslocamentoOut, DeslocamentoUpdate

router = APIRouter(prefix="/api/deslocamentos", tags=["Deslocamentos"])


def _validar_vinculos(db: Session, veiculo_id: int, motorista_id: int):
    veiculo = db.get(Veiculo, veiculo_id)
    if not veiculo:
        raise HTTPException(404, "Veículo não encontrado.")
    if veiculo.status in (StatusVeiculo.manutencao, StatusVeiculo.inativo):
        raise HTTPException(
            409,
            f"O veículo {veiculo.placa} está em {veiculo.status.value} "
            "e não pode ser escalado.",
        )
    motorista = db.get(Motorista, motorista_id)
    if not motorista:
        raise HTTPException(404, "Motorista não encontrado.")
    if not motorista.ativo:
        raise HTTPException(409, f"O motorista {motorista.nome} está inativo.")
    return veiculo, motorista


def _checar_conflito_agenda(
    db: Session,
    veiculo_id: int,
    data_saida: date,
    data_retorno: date | None,
    ignorar_id: int | None = None,
):
    """Impede o mesmo veículo em duas viagens no mesmo intervalo."""
    fim = data_retorno or data_saida
    q = db.query(Deslocamento).filter(
        Deslocamento.veiculo_id == veiculo_id,
        Deslocamento.status.in_(
            [StatusDeslocamento.previsto, StatusDeslocamento.em_andamento]
        ),
    )
    if ignorar_id:
        q = q.filter(Deslocamento.id != ignorar_id)
    for d in q.all():
        d_fim = d.data_retorno or d.data_saida
        if data_saida <= d_fim and d.data_saida <= fim:
            raise HTTPException(
                409,
                f"Conflito de agenda: o veículo já tem o deslocamento #{d.id} "
                f"para {d.destino} entre {d.data_saida} e {d_fim}.",
            )


def _sincronizar_status_veiculo(db: Session, veiculo: Veiculo, d: Deslocamento):
    if d.status == StatusDeslocamento.em_andamento:
        veiculo.status = StatusVeiculo.em_viagem
    elif d.status in (StatusDeslocamento.realizado, StatusDeslocamento.cancelado):
        if veiculo.status == StatusVeiculo.em_viagem:
            veiculo.status = StatusVeiculo.disponivel
        if d.km_final is not None and d.km_final > (veiculo.km_atual or 0):
            veiculo.km_atual = d.km_final


@router.post("", response_model=DeslocamentoOut, status_code=status.HTTP_201_CREATED)
def registrar_deslocamento(dados: DeslocamentoCreate, db: Session = Depends(get_db)):
    veiculo, _ = _validar_vinculos(db, dados.veiculo_id, dados.motorista_id)
    _checar_conflito_agenda(db, dados.veiculo_id, dados.data_saida, dados.data_retorno)

    payload = dados.model_dump()
    if payload.get("km_inicial") is None:
        payload["km_inicial"] = veiculo.km_atual

    deslocamento = Deslocamento(**payload)
    db.add(deslocamento)
    db.flush()
    _sincronizar_status_veiculo(db, veiculo, deslocamento)
    db.commit()
    db.refresh(deslocamento)
    return deslocamento


@router.get("", response_model=list[DeslocamentoOut])
def consultar_historico(
    veiculo_id: int | None = None,
    motorista_id: int | None = None,
    destino: str | None = None,
    finalidade: Finalidade | None = None,
    status_: StatusDeslocamento | None = Query(None, alias="status"),
    data_inicio: date | None = None,
    data_fim: date | None = None,
    limite: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(Deslocamento).options(
        joinedload(Deslocamento.veiculo), joinedload(Deslocamento.motorista)
    )
    if veiculo_id:
        q = q.filter(Deslocamento.veiculo_id == veiculo_id)
    if motorista_id:
        q = q.filter(Deslocamento.motorista_id == motorista_id)
    if destino:
        q = q.filter(Deslocamento.destino.ilike(f"%{destino.strip()}%"))
    if finalidade:
        q = q.filter(Deslocamento.finalidade == finalidade)
    if status_:
        q = q.filter(Deslocamento.status == status_)
    if data_inicio:
        q = q.filter(Deslocamento.data_saida >= data_inicio)
    if data_fim:
        q = q.filter(Deslocamento.data_saida <= data_fim)
    return q.order_by(Deslocamento.data_saida.desc(), Deslocamento.id.desc()).limit(
        limite
    ).all()


@router.get("/{deslocamento_id}", response_model=DeslocamentoOut)
def obter_deslocamento(deslocamento_id: int, db: Session = Depends(get_db)):
    d = db.get(Deslocamento, deslocamento_id)
    if not d:
        raise HTTPException(404, "Deslocamento não encontrado.")
    return d


@router.put("/{deslocamento_id}", response_model=DeslocamentoOut)
def atualizar_deslocamento(
    deslocamento_id: int, dados: DeslocamentoUpdate, db: Session = Depends(get_db)
):
    d = db.get(Deslocamento, deslocamento_id)
    if not d:
        raise HTTPException(404, "Deslocamento não encontrado.")

    alteracoes = dados.model_dump(exclude_unset=True)
    for campo, valor in alteracoes.items():
        setattr(d, campo, valor)

    if d.data_retorno and d.data_retorno < d.data_saida:
        raise HTTPException(422, "A data de retorno não pode ser anterior à saída.")
    if d.km_inicial is not None and d.km_final is not None and d.km_final < d.km_inicial:
        raise HTTPException(422, "O km final não pode ser menor que o km inicial.")
    if d.status == StatusDeslocamento.realizado and d.data_retorno is None:
        raise HTTPException(422, "Informe a data de retorno para concluir a viagem.")

    if {"veiculo_id", "data_saida", "data_retorno"} & alteracoes.keys():
        _checar_conflito_agenda(
            db, d.veiculo_id, d.data_saida, d.data_retorno, ignorar_id=d.id
        )

    _sincronizar_status_veiculo(db, d.veiculo, d)
    db.commit()
    db.refresh(d)
    return d


@router.post("/{deslocamento_id}/concluir", response_model=DeslocamentoOut)
def concluir_deslocamento(
    deslocamento_id: int,
    km_final: float = Query(..., ge=0),
    data_retorno: date | None = None,
    db: Session = Depends(get_db),
):
    """Atalho usado pela interface para fechar uma viagem."""
    d = db.get(Deslocamento, deslocamento_id)
    if not d:
        raise HTTPException(404, "Deslocamento não encontrado.")
    if d.status == StatusDeslocamento.cancelado:
        raise HTTPException(409, "Deslocamento cancelado não pode ser concluído.")
    if d.km_inicial is not None and km_final < d.km_inicial:
        raise HTTPException(422, "O km final não pode ser menor que o km inicial.")

    d.km_final = km_final
    d.data_retorno = data_retorno or date.today()
    if d.data_retorno < d.data_saida:
        d.data_retorno = d.data_saida
    d.status = StatusDeslocamento.realizado
    _sincronizar_status_veiculo(db, d.veiculo, d)
    db.commit()
    db.refresh(d)
    return d


@router.delete("/{deslocamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_deslocamento(deslocamento_id: int, db: Session = Depends(get_db)):
    d = db.get(Deslocamento, deslocamento_id)
    if not d:
        raise HTTPException(404, "Deslocamento não encontrado.")
    veiculo = d.veiculo
    db.delete(d)
    if veiculo.status == StatusVeiculo.em_viagem:
        veiculo.status = StatusVeiculo.disponivel
    db.commit()
