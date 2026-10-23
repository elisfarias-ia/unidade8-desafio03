"""CRUD de motoristas."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Deslocamento, Motorista
from app.schemas import MotoristaCreate, MotoristaOut, MotoristaUpdate

router = APIRouter(prefix="/api/motoristas", tags=["Motoristas"])


@router.post("", response_model=MotoristaOut, status_code=status.HTTP_201_CREATED)
def cadastrar_motorista(dados: MotoristaCreate, db: Session = Depends(get_db)):
    if db.query(Motorista).filter(Motorista.cnh == dados.cnh).first():
        raise HTTPException(409, "Já existe um motorista com essa CNH.")
    motorista = Motorista(**dados.model_dump())
    db.add(motorista)
    db.commit()
    db.refresh(motorista)
    return motorista


@router.get("", response_model=list[MotoristaOut])
def listar_motoristas(
    busca: str | None = Query(None),
    apenas_ativos: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(Motorista)
    if busca:
        q = q.filter(Motorista.nome.ilike(f"%{busca.strip()}%"))
    if apenas_ativos:
        q = q.filter(Motorista.ativo == 1)
    return q.order_by(Motorista.nome).all()


@router.get("/{motorista_id}", response_model=MotoristaOut)
def obter_motorista(motorista_id: int, db: Session = Depends(get_db)):
    motorista = db.get(Motorista, motorista_id)
    if not motorista:
        raise HTTPException(404, "Motorista não encontrado.")
    return motorista


@router.put("/{motorista_id}", response_model=MotoristaOut)
def atualizar_motorista(
    motorista_id: int, dados: MotoristaUpdate, db: Session = Depends(get_db)
):
    motorista = db.get(Motorista, motorista_id)
    if not motorista:
        raise HTTPException(404, "Motorista não encontrado.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(motorista, campo, valor)
    db.commit()
    db.refresh(motorista)
    return motorista


@router.delete("/{motorista_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_motorista(motorista_id: int, db: Session = Depends(get_db)):
    motorista = db.get(Motorista, motorista_id)
    if not motorista:
        raise HTTPException(404, "Motorista não encontrado.")
    vinculos = (
        db.query(Deslocamento)
        .filter(Deslocamento.motorista_id == motorista_id)
        .count()
    )
    if vinculos:
        raise HTTPException(
            409,
            f"O motorista tem {vinculos} deslocamento(s) registrado(s). "
            "Desative o cadastro em vez de excluir.",
        )
    db.delete(motorista)
    db.commit()
