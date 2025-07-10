from typing import List, Optional, Any
from fastapi import FastAPI, Depends, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from . import crud, models
from datetime import datetime
from .db import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

from .db import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ConceptBase(BaseModel):
    agent:                      Optional[str]
    title:                      str
    description:                Optional[str]
    novelty_reasoning:          Optional[str]
    feasibility_reasoning:      Optional[str]
    cost_estimate:              Optional[str]
    trl:                        Optional[float]
    trl_reasoning:              Optional[str]
    trl_citations:              Optional[Any]  # JSON
    validated_trl:              Optional[float]
    validated_trl_reasoning:    Optional[str]
    validated_trl_citations:    Optional[Any]  # JSON
    components:                 Optional[Any]
    references:                 Optional[Any]
    constructive_critique:      Optional[str]
    proposal_url:               Optional[str]

    class Config:
        orm_mode = True  # for reading

class ConceptCreate(ConceptBase):
    problem_statement: str

class ConceptRead(ConceptBase):
    id: int
    problem_statement: str
    generated_at: datetime
    class Config:
        orm_mode = True

@app.get("/concepts", response_model=List[ConceptRead])
def read_concepts(
    problem_statement: str,
    db: Session = Depends(get_db),
):
    return crud.get_concepts_by_problem(db, problem_statement)


@app.post("/concepts", response_model=List[ConceptRead])
def create_concepts_endpoint(
    concepts: List[ConceptCreate] = Body(...),
    db: Session = Depends(get_db),
):
    if not concepts:
        return []
    problem = concepts[0].problem_statement
    # use model_dump() instead of dict()
    new_data = [
        c.model_dump(exclude={"problem_statement"})
        for c in concepts
    ]
    created = crud.create_concepts(db, problem, new_data)
    return created


class SimilarConcepts(BaseModel):
    problem_statement: str
    similarity: float
    concepts: List[ConceptRead]

    class Config:
        orm_mode = True

from typing import List
from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy.orm import Session
from .db import get_db
from . import models

# --- Pydantic schema for problems ---
class ProblemOut(BaseModel):
    problem_statement: str

    class Config:
        orm_mode = True


@app.get("/problems", response_model=List[ProblemOut])
def list_problems(db: Session = Depends(get_db)):
    """
    Return a list of all distinct problem statements in the database
    """
    # Assuming your Concept model has a `problem_statement` column:
    rows = (
        db.query(models.Concept.problem_statement)
          .distinct()
          .order_by(models.Concept.problem_statement)
          .all()
    )
    # rows is List[Tuple[str]], so unpack
    return [ProblemOut(problem_statement=stmt) for (stmt,) in rows]


from fastapi import HTTPException

@app.get("/concepts/similar", response_model=List[SimilarConcepts])
def get_similar_concepts_endpoint(
    problem_statement: str,
    top_k: int = 50,
    db: Session = Depends(get_db),
):
    try:
        # 1️⃣ fetch the top_k results as before
        results: list[SimilarConcepts] = crud.get_similar_concepts(db, problem_statement, top_k)
        
        # 2️⃣ filter out anything below 0.7
        filtered = [r for r in results if r.get("similarity", 0) > 0.7]
        
        # 3️⃣ return only the high-scoring ones
        return filtered

    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import File, UploadFile, HTTPException
import os
from azure.storage.blob import BlobServiceClient

@app.post("/concepts/{concept_id}/proposal", response_model=ConceptRead)
def upload_proposal(
    concept_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1️⃣ Upload to Azure Blob
    conn_str = "DefaultEndpointsProtocol=https;AccountName=detailedproposals;AccountKey=RItFvGpxF0qAl3krYtC9LwxR4egIDZkU/oTkZjC70BAH0f4OmqCtYtzpsavkWF9MKpDUj5N3o5IS+AStUQ5zSQ==;EndpointSuffix=core.windows.net"
    if not conn_str:
        raise HTTPException(500, "Azure storage connection not configured")
    blob_service = BlobServiceClient.from_connection_string(conn_str)
    container = blob_service.get_container_client("proposals")
    blob_name = f"{concept_id}-{file.filename}"
    blob_client = container.get_blob_client(blob_name)
    blob_client.upload_blob(file.file.read(), overwrite=True)
    url = blob_client.url

    # 2️⃣ Persist URL in DB
    updated = crud.update_concept(db, concept_id, {"proposal_url": url})
    if not updated:
        raise HTTPException(404, f"Concept {concept_id} not found")
    return updated
