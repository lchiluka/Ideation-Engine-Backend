# main.py
from typing import List, Optional, Any
from fastapi import FastAPI, Depends, Body, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from . import crud, models
from .db import get_db, engine
from .storage import get_container_client

# Initialize database schema
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Pydantic schemas
class ConceptBase(BaseModel):
    agent:                      Optional[str]
    title:                      str
    description:                Optional[str]
    novelty_reasoning:          Optional[str]
    feasibility_reasoning:      Optional[str]
    cost_estimate:              Optional[str]
    trl:                        Optional[float]
    trl_reasoning:              Optional[str]
    trl_citations:              Optional[Any]
    validated_trl:              Optional[float]
    validated_trl_reasoning:    Optional[str]
    validated_trl_citations:    Optional[Any]
    components:                 Optional[Any]
    references:                 Optional[Any]
    constructive_critique:      Optional[str]
    proposal_url:               Optional[str]

    class Config:
        orm_mode = True

class ConceptCreate(ConceptBase):
    problem_statement: str

class ConceptRead(ConceptBase):
    id: int
    problem_statement: str
    generated_at: datetime

    class Config:
        orm_mode = True

class SimilarConcepts(BaseModel):
    problem_statement: str
    similarity: float
    concepts: List[ConceptRead]

    class Config:
        orm_mode = True

class ProblemOut(BaseModel):
    problem_statement: str

    class Config:
        orm_mode = True

# Endpoints
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
    new_data = [c.model_dump(exclude={"problem_statement"}) for c in concepts]
    return crud.create_concepts(db, problem, new_data)

@app.get("/problems", response_model=List[ProblemOut])
def list_problems(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Concept.problem_statement)
          .distinct()
          .order_by(models.Concept.problem_statement)
          .all()
    )
    return [ProblemOut(problem_statement=stmt) for (stmt,) in rows]

@app.get("/concepts/similar", response_model=List[SimilarConcepts])
def get_similar_concepts_endpoint(
    problem_statement: str,
    top_k: int = 50,
    db: Session = Depends(get_db),
):
    try:
        results = crud.get_similar_concepts(db, problem_statement, top_k)
        filtered = [r for r in results if r.get("similarity", 0) > 0.7]
        return filtered
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/concepts/{concept_id}/proposal", response_model=ConceptRead)
def upload_proposal(
    concept_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    container = Depends(get_container_client),
):
    # Upload to Azure Blob Storage
    blob_name = f"{concept_id}/{uuid.uuid4()}-{file.filename}"
    try:
        container.upload_blob(name=blob_name, data=file.file, overwrite=True)
    except Exception as e:
        raise HTTPException(500, f"Blob upload failed: {e}")
    # Construct URL
    blob_client = container.get_blob_client(blob_name)
    url = blob_client.url

    # Persist URL in DB
    updated = crud.update_concept(db, concept_id, {"proposal_url": url})
    if not updated:
        raise HTTPException(404, f"Concept {concept_id} not found")
    return updated

@app.get("/concepts/{concept_id}/download")
def download_proposal(
    concept_id: int,
    db: Session = Depends(get_db),
    container = Depends(get_container_client),
):
    concept = crud.get_concept(db, concept_id)
    if not concept or not concept.proposal_url:
        raise HTTPException(404, "Not found or no proposal attached")
    try:
        blob_name = concept.proposal_url.split('/')[-1]
        stream = container.download_blob(blob_name)
        return StreamingResponse(stream.chunks(), media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(500, f"Blob download failed: {e}")
