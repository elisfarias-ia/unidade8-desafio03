"""CRUD completo de veículos."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Deslocamento, StatusVeiculo, Veiculo
from app.schemas import VeiculoCreate, VeiculoOut, VeiculoUpdate

router = APIRouter(prefix="/api/veiculos", tags=["Veículos"])


@router.post("", response_model=VeiculoOut, status_code=status.HTTP_201_CREATED)
def cadastrar_veiculo(dados: VeiculoCreate, db: Session = Depends(get_db)):
    if db.query(Veiculo).filter(Veiculo.placa == dados.placa).first():
        raise HTTPException(409, f"Já existe um veículo com a placa {dados.placa}.")
    veiculo = Veiculo(**dados.model_dump())
    db.add(veiculo)
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.get("", response_model=list[VeiculoOut])
def listar_veiculos(
    busca: str | None = Query(None, description="Placa, modelo ou marca"),
    status_: StatusVeiculo | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    q = db.query(Veiculo)
    if busca:
        termo = f"%{busca.strip()}%"
        q = q.filter(
            Veiculo.placa.ilike(termo)
            | Veiculo.modelo.ilike(termo)
            | Veiculo.marca.ilike(termo)
        )
    if status_:
        q = q.filter(Veiculo.status == status_)
    return q.order_by(Veiculo.placa).all()


@router.get("/{veiculo_id}", response_model=VeiculoOut)
def obter_veiculo(veiculo_id: int, db: Session = Depends(get_db)):
    veiculo = db.get(Veiculo, veiculo_id)
    if not veiculo:
        raise HTTPException(404, "Veículo não encontrado.")
    return veiculo


@router.put("/{veiculo_id}", response_model=VeiculoOut)
def atualizar_veiculo(
    veiculo_id: int, dados: VeiculoUpdate, db: Session = Depends(get_db)
):
    veiculo = db.get(Veiculo, veiculo_id)
    if not veiculo:
        raise HTTPException(404, "Veículo não encontrado.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(veiculo, campo, valor)
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.delete("/{veiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_veiculo(veiculo_id: int, db: Session = Depends(get_db)):
    veiculo = db.get(Veiculo, veiculo_id)
    if not veiculo:
        raise HTTPException(404, "Veículo não encontrado.")
    vinculos = (
        db.query(Deslocamento).filter(Deslocamento.veiculo_id == veiculo_id).count()
    )
    if vinculos:
        raise HTTPException(
            409,
            f"O veículo tem {vinculos} deslocamento(s) registrado(s). "
            "Mude o status para inativo em vez de excluir.",
        )
    db.delete(veiculo)
    db.commit()
