"""CRUD completo de veículos."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Deslocamento, StatusVeiculo, Veiculo
from app.schemas import VeiculoCreate, VeiculoOut, VeiculoUpdate

router = APIRouter(prefix="/api/veiculos", tags=["Veículos"])


def _buscar(db: Session, veiculo_id: int) -> Veiculo:
    veiculo = db.get(Veiculo, veiculo_id)
    if not veiculo:
        raise HTTPException(404, f"Veículo #{veiculo_id} não encontrado.")
    return veiculo


def _garantir_placa_livre(db: Session, placa: str, ignorar_id: int | None = None) -> None:
    q = db.query(Veiculo).filter(Veiculo.placa == placa)
    if ignorar_id is not None:
        q = q.filter(Veiculo.id != ignorar_id)
    if q.first():
        raise HTTPException(
            409,
            f"Já existe um veículo com a placa {placa}. "
            "Confira a placa ou edite o cadastro existente.",
        )


@router.post("", response_model=VeiculoOut, status_code=status.HTTP_201_CREATED)
def cadastrar_veiculo(dados: VeiculoCreate, db: Session = Depends(get_db)):
    _garantir_placa_livre(db, dados.placa)
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
            Veiculo.placa.ilike(termo) | Veiculo.modelo.ilike(termo) | Veiculo.marca.ilike(termo)
        )
    if status_:
        q = q.filter(Veiculo.status == status_)
    return q.order_by(Veiculo.placa).all()


@router.get("/{veiculo_id}", response_model=VeiculoOut)
def obter_veiculo(veiculo_id: int, db: Session = Depends(get_db)):
    return _buscar(db, veiculo_id)


@router.put("/{veiculo_id}", response_model=VeiculoOut)
def atualizar_veiculo(veiculo_id: int, dados: VeiculoUpdate, db: Session = Depends(get_db)):
    veiculo = _buscar(db, veiculo_id)
    alteracoes = dados.model_dump(exclude_unset=True)
    if "placa" in alteracoes:
        _garantir_placa_livre(db, alteracoes["placa"], ignorar_id=veiculo_id)
    for campo, valor in alteracoes.items():
        setattr(veiculo, campo, valor)
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.delete("/{veiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_veiculo(veiculo_id: int, db: Session = Depends(get_db)):
    veiculo = _buscar(db, veiculo_id)
    vinculos = db.query(Deslocamento).filter(Deslocamento.veiculo_id == veiculo_id).count()
    if vinculos:
        raise HTTPException(
            409,
            f"O veículo {veiculo.placa} tem {vinculos} deslocamento(s) registrado(s) "
            "e não pode ser excluído. Mude a situação para inativo.",
        )
    db.delete(veiculo)
    db.commit()
