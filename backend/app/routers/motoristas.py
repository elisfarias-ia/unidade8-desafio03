"""CRUD completo de motoristas."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Deslocamento, Motorista
from app.schemas import MotoristaCreate, MotoristaOut, MotoristaUpdate

router = APIRouter(prefix="/api/motoristas", tags=["Motoristas"])


def _buscar(db: Session, motorista_id: int) -> Motorista:
    motorista = db.get(Motorista, motorista_id)
    if not motorista:
        raise HTTPException(404, f"Motorista #{motorista_id} não encontrado.")
    return motorista


def _garantir_cnh_livre(db: Session, cnh: str, ignorar_id: int | None = None) -> None:
    q = db.query(Motorista).filter(Motorista.cnh == cnh)
    if ignorar_id is not None:
        q = q.filter(Motorista.id != ignorar_id)
    if q.first():
        raise HTTPException(
            409,
            "Já existe um motorista com essa CNH. Confira o número ou edite o cadastro existente.",
        )


@router.post("", response_model=MotoristaOut, status_code=status.HTTP_201_CREATED)
def cadastrar_motorista(dados: MotoristaCreate, db: Session = Depends(get_db)):
    _garantir_cnh_livre(db, dados.cnh)
    motorista = Motorista(**dados.model_dump())
    db.add(motorista)
    db.commit()
    db.refresh(motorista)
    return motorista


@router.get("", response_model=list[MotoristaOut])
def listar_motoristas(
    busca: str | None = Query(None, description="Nome, CNH ou setor"),
    apenas_ativos: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(Motorista)
    if busca:
        termo = f"%{busca.strip()}%"
        q = q.filter(
            Motorista.nome.ilike(termo) | Motorista.cnh.ilike(termo) | Motorista.setor.ilike(termo)
        )
    if apenas_ativos:
        q = q.filter(Motorista.ativo.is_(True))
    return q.order_by(Motorista.nome).all()


@router.get("/{motorista_id}", response_model=MotoristaOut)
def obter_motorista(motorista_id: int, db: Session = Depends(get_db)):
    return _buscar(db, motorista_id)


@router.put("/{motorista_id}", response_model=MotoristaOut)
def atualizar_motorista(motorista_id: int, dados: MotoristaUpdate, db: Session = Depends(get_db)):
    motorista = _buscar(db, motorista_id)
    alteracoes = dados.model_dump(exclude_unset=True)
    if "cnh" in alteracoes:
        _garantir_cnh_livre(db, alteracoes["cnh"], ignorar_id=motorista_id)
    for campo, valor in alteracoes.items():
        setattr(motorista, campo, valor)
    db.commit()
    db.refresh(motorista)
    return motorista


@router.delete("/{motorista_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_motorista(motorista_id: int, db: Session = Depends(get_db)):
    motorista = _buscar(db, motorista_id)
    vinculos = db.query(Deslocamento).filter(Deslocamento.motorista_id == motorista_id).count()
    if vinculos:
        raise HTTPException(
            409,
            f"{motorista.nome} tem {vinculos} deslocamento(s) registrado(s) "
            "e não pode ser excluído(a). Desative o cadastro.",
        )
    db.delete(motorista)
    db.commit()
