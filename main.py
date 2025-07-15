# main.py
from typing import List, Optional, Any
from fastapi import Request
from fastapi import FastAPI, Depends, Body, File, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import traceback
import logging

import crud
import models
from db import get_db, engine
from storage import get_container_client

# Initialize database schema
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    body = await request.body()
    logger.error("🚨 422 Validation Error:")
    logger.error(f"→ Details: {exc.errors()}")
    logger.error(f"→ Payload: {body.decode('utf-8')}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    logger.error("⚠️ HTTPException:")
    logger.error(f"→ Status Code: {exc.status_code}")
    logger.error(f"→ Detail: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request, exc: StarletteHTTPException):
    logger.error("⚠️ StarletteHTTPException:")
    logger.error(f"→ Status Code: {exc.status_code}")
    logger.error(f"→ Detail: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    logger.error("💥 Unhandled Exception:")
    logger.error(f"→ Type: {type(exc).__name__}")
    logger.error(f"→ Error: {str(exc)}")
    logger.error(f"→ Traceback:\n{traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "error": str(exc)})

# Pydantic schemas
class ConceptBase(BaseModel):
    agent: Optional[str]= None
    title: str
    description: Optional[str]= None
    novelty_reasoning: Optional[str]= None
    feasibility_reasoning: Optional[str]= None
    cost_estimate: Optional[str]= None
    industry: Optional[str] = None
    original_solution: Optional[str] = None
    adaptation_challenges: Optional[str] = None
    trl: Optional[float]= None
    trl_reasoning: Optional[str]= None
    trl_citations: Optional[Any]= None
    validated_trl: Optional[float]= None
    validated_trl_reasoning: Optional[str]= None
    validated_trl_citations: Optional[Any]= None
    components: Optional[Any]= None
    references: Optional[Any]= None
    constructive_critique: Optional[str]= None
    proposal_url: Optional[str]= None

    class Config:
        orm_mode = True
        extra = "ignore"

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
def read_concepts(problem_statement: str, db: Session = Depends(get_db)):
    return crud.get_concepts_by_problem(db, problem_statement)

@app.post("/concepts", response_model=List[ConceptRead])
def create_concepts_endpoint(
    *,
    workflow: str = Query("traditional", description="Ideation workflow: 'cross-industry' for cross-industry, else traditional"),
    concepts: List[ConceptCreate] = Body(...),
    db: Session = Depends(get_db),
):
    if not concepts:
        return []
    problem = concepts[0].problem_statement
    new_data = [c.model_dump(exclude={"problem_statement"}) for c in concepts]

    # Strip unused fields based on workflow
    if workflow.lower() == "cross-industry":
        for d in new_data:
            d.pop("novelty_reasoning", None)
            d.pop("feasibility_reasoning", None)
            d.pop("cost_estimate", None)
    else:
        for d in new_data:
            d.pop("industry", None)
            d.pop("original_solution", None)
            d.pop("adaptation_challenges", None)

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
def get_similar_concepts_endpoint(problem_statement: str, top_k: int = 50, db: Session = Depends(get_db)):
    try:
        results = crud.get_similar_concepts(db, problem_statement, top_k)
        return [r for r in results if r.get("similarity", 0) > 0.7]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/concepts/{concept_id}/proposal", response_model=ConceptRead)
def upload_proposal(concept_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), container = Depends(get_container_client)):
    blob_name = f"{concept_id}/{uuid.uuid4()}-{file.filename}"
    try:
        container.upload_blob(name=blob_name, data=file.file, overwrite=True)
    except Exception as e:
        raise HTTPException(500, f"Blob upload failed: {e}")
    blob_client = container.get_blob_client(blob_name)
    url = blob_client.url
    updated = crud.update_concept(db, concept_id, {"proposal_url": url})
    if not updated:
        raise HTTPException(404, f"Concept {concept_id} not found")
    return updated

@app.get("/concepts/{concept_id}/download")
def download_proposal(concept_id: int, db: Session = Depends(get_db), container = Depends(get_container_client)):
    concept = crud.get_concept(db, concept_id)
    if not concept or not concept.proposal_url:
        raise HTTPException(404, "Not found or no proposal attached")
    blob_name = concept.proposal_url.split('/')[-1]
    try:
        stream = container.download_blob(blob_name)
        return StreamingResponse(stream.chunks(), media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(500, f"Blob download failed: {e}")

