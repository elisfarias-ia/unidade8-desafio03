"""Registro, conclusão e histórico de deslocamentos, com as regras de agenda."""

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
from app.schemas import (
    ConclusaoDeslocamento,
    DeslocamentoCreate,
    DeslocamentoOut,
    DeslocamentoUpdate,
    validar_coerencia_deslocamento,
)

router = APIRouter(prefix="/api/deslocamentos", tags=["Deslocamentos"])

ATIVOS = (StatusDeslocamento.previsto, StatusDeslocamento.em_andamento)
SITUACAO_IMPEDIDA = {StatusVeiculo.manutencao: "em manutenção", StatusVeiculo.inativo: "inativo"}


def _buscar(db: Session, deslocamento_id: int) -> Deslocamento:
    d = db.get(Deslocamento, deslocamento_id)
    if not d:
        raise HTTPException(404, f"Deslocamento #{deslocamento_id} não encontrado.")
    return d


def _veiculo_escalavel(db: Session, veiculo_id: int) -> Veiculo:
    veiculo = db.get(Veiculo, veiculo_id)
    if not veiculo:
        raise HTTPException(404, f"Veículo #{veiculo_id} não encontrado.")
    if veiculo.status in SITUACAO_IMPEDIDA:
        raise HTTPException(
            409,
            f"O veículo {veiculo.placa} está {SITUACAO_IMPEDIDA[veiculo.status]} "
            "e não pode ser escalado. "
            "Escolha outro veículo ou altere a situação dele.",
        )
    return veiculo


def _motorista_escalavel(db: Session, motorista_id: int) -> Motorista:
    motorista = db.get(Motorista, motorista_id)
    if not motorista:
        raise HTTPException(404, f"Motorista #{motorista_id} não encontrado.")
    if not motorista.ativo:
        raise HTTPException(
            409,
            f"{motorista.nome} está inativo(a) e não pode ser escalado(a). "
            "Escolha outro motorista.",
        )
    return motorista


def _checar_conflito_agenda(
    db: Session,
    veiculo_id: int,
    data_saida: date,
    data_retorno: date | None,
    ignorar_id: int | None = None,
) -> None:
    """Regra 5: o mesmo veículo não pode estar em dois deslocamentos ativos sobrepostos."""
    fim = data_retorno or data_saida
    q = db.query(Deslocamento).filter(
        Deslocamento.veiculo_id == veiculo_id,
        Deslocamento.status.in_(ATIVOS),
        Deslocamento.data_saida <= fim,
    )
    if ignorar_id is not None:
        q = q.filter(Deslocamento.id != ignorar_id)
    for d in q.order_by(Deslocamento.data_saida).all():
        d_fim = d.data_retorno or d.data_saida
        if data_saida <= d_fim:
            raise HTTPException(
                409,
                f"Conflito de agenda: o veículo já está no deslocamento #{d.id} para {d.destino} "
                f"de {d.data_saida:%d/%m/%Y} a {d_fim:%d/%m/%Y}. "
                "Escolha outras datas ou outro veículo.",
            )


def _ha_outra_viagem_em_andamento(db: Session, veiculo_id: int, ignorar_id: int | None) -> bool:
    q = db.query(Deslocamento.id).filter(
        Deslocamento.veiculo_id == veiculo_id,
        Deslocamento.status == StatusDeslocamento.em_andamento,
    )
    if ignorar_id is not None:
        q = q.filter(Deslocamento.id != ignorar_id)
    return q.first() is not None


def _liberar_se_ocioso(db: Session, veiculo: Veiculo, ignorar_id: int | None) -> None:
    """O veículo só volta a 'disponível' quando não resta nenhuma viagem em andamento."""
    if veiculo.status == StatusVeiculo.em_viagem and not _ha_outra_viagem_em_andamento(
        db, veiculo.id, ignorar_id
    ):
        veiculo.status = StatusVeiculo.disponivel


def _sincronizar_veiculo(db: Session, veiculo: Veiculo, d: Deslocamento) -> None:
    """Regra 8: viagem em andamento ocupa o veículo; ao terminar, ele volta e o km avança."""
    if d.status == StatusDeslocamento.em_andamento:
        veiculo.status = StatusVeiculo.em_viagem
        return
    _liberar_se_ocioso(db, veiculo, d.id)
    if d.status == StatusDeslocamento.realizado and d.km_final is not None:
        veiculo.km_atual = max(veiculo.km_atual or 0, d.km_final)


@router.post("", response_model=DeslocamentoOut, status_code=status.HTTP_201_CREATED)
def registrar_deslocamento(dados: DeslocamentoCreate, db: Session = Depends(get_db)):
    veiculo = _veiculo_escalavel(db, dados.veiculo_id)
    _motorista_escalavel(db, dados.motorista_id)
    if dados.status in ATIVOS:
        _checar_conflito_agenda(db, dados.veiculo_id, dados.data_saida, dados.data_retorno)

    payload = dados.model_dump()
    if payload["km_inicial"] is None:
        payload["km_inicial"] = veiculo.km_atual
    # O km inicial pode ter vindo do veículo, então a regra 3 é conferida de novo aqui.
    if payload["km_final"] is not None and payload["km_final"] < payload["km_inicial"]:
        raise HTTPException(
            422,
            f"O km final ({payload['km_final']:g}) não pode ser menor que o km inicial "
            f"({payload['km_inicial']:g}).",
        )

    d = Deslocamento(**payload)
    db.add(d)
    _sincronizar_veiculo(db, veiculo, d)
    db.commit()
    db.refresh(d)
    return d


@router.get("", response_model=list[DeslocamentoOut])
def consultar_historico(
    veiculo_id: int | None = None,
    motorista_id: int | None = None,
    destino: str | None = None,
    finalidade: Finalidade | None = None,
    status_: StatusDeslocamento | None = Query(None, alias="status"),
    data_inicio: date | None = Query(None, description="Data de saída a partir de"),
    data_fim: date | None = Query(None, description="Data de saída até"),
    limite: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    if data_inicio and data_fim and data_fim < data_inicio:
        raise HTTPException(422, "A data final do filtro não pode ser anterior à data inicial.")
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
    ordem = (Deslocamento.data_saida.desc(), Deslocamento.id.desc())
    return q.order_by(*ordem).limit(limite).all()


@router.get("/{deslocamento_id}", response_model=DeslocamentoOut)
def obter_deslocamento(deslocamento_id: int, db: Session = Depends(get_db)):
    return _buscar(db, deslocamento_id)


@router.put("/{deslocamento_id}", response_model=DeslocamentoOut)
def atualizar_deslocamento(
    deslocamento_id: int, dados: DeslocamentoUpdate, db: Session = Depends(get_db)
):
    d = _buscar(db, deslocamento_id)
    alteracoes = dados.model_dump(exclude_unset=True)

    status_anterior = d.status
    veiculo_anterior = d.veiculo
    if "veiculo_id" in alteracoes and alteracoes["veiculo_id"] != d.veiculo_id:
        _veiculo_escalavel(db, alteracoes["veiculo_id"])
    if "motorista_id" in alteracoes and alteracoes["motorista_id"] != d.motorista_id:
        _motorista_escalavel(db, alteracoes["motorista_id"])

    for campo, valor in alteracoes.items():
        setattr(d, campo, valor)

    try:
        validar_coerencia_deslocamento(
            d.data_saida, d.data_retorno, d.km_inicial, d.km_final, d.status
        )
    except ValueError as erro:
        db.rollback()
        raise HTTPException(422, str(erro)) from None

    # Regra 6 também vale ao iniciar ou reativar uma viagem (ex.: previsto → em andamento).
    if d.status in ATIVOS and d.status != status_anterior:
        _veiculo_escalavel(db, d.veiculo_id)
        _motorista_escalavel(db, d.motorista_id)

    campos_de_agenda = {"veiculo_id", "data_saida", "data_retorno", "status"}
    if d.status in ATIVOS and campos_de_agenda & alteracoes.keys():
        _checar_conflito_agenda(db, d.veiculo_id, d.data_saida, d.data_retorno, ignorar_id=d.id)

    db.flush()
    db.refresh(d, ["veiculo"])
    if veiculo_anterior.id != d.veiculo_id:
        _liberar_se_ocioso(db, veiculo_anterior, d.id)
    _sincronizar_veiculo(db, d.veiculo, d)
    db.commit()
    db.refresh(d)
    return d


@router.post("/{deslocamento_id}/concluir", response_model=DeslocamentoOut)
def concluir_deslocamento(
    deslocamento_id: int, dados: ConclusaoDeslocamento, db: Session = Depends(get_db)
):
    """Fecha a viagem: registra km final e retorno, atualiza o km do veículo."""
    d = _buscar(db, deslocamento_id)
    if d.status == StatusDeslocamento.cancelado:
        raise HTTPException(409, "Este deslocamento foi cancelado e não pode ser concluído.")
    if d.status == StatusDeslocamento.realizado:
        raise HTTPException(
            409, "Este deslocamento já foi concluído. Para corrigir, edite o registro."
        )

    data_retorno = dados.data_retorno or date.today()
    if data_retorno < d.data_saida:
        raise HTTPException(
            422,
            f"A data de retorno ({data_retorno:%d/%m/%Y}) não pode ser anterior à saída "
            f"({d.data_saida:%d/%m/%Y}). Informe a data de retorno correta.",
        )
    if d.km_inicial is not None and dados.km_final < d.km_inicial:
        raise HTTPException(
            422,
            f"O km final ({dados.km_final:g}) não pode ser menor que o km inicial "
            f"({d.km_inicial:g}).",
        )

    d.km_final = dados.km_final
    d.data_retorno = data_retorno
    d.status = StatusDeslocamento.realizado
    _sincronizar_veiculo(db, d.veiculo, d)
    db.commit()
    db.refresh(d)
    return d


@router.delete("/{deslocamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_deslocamento(deslocamento_id: int, db: Session = Depends(get_db)):
    d = _buscar(db, deslocamento_id)
    veiculo = d.veiculo
    if d.status == StatusDeslocamento.em_andamento:
        _liberar_se_ocioso(db, veiculo, d.id)
    db.delete(d)
    db.commit()
