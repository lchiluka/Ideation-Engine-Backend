# crud.py

from sqlalchemy.orm import Session
import models

from embedding import embed_text, cosine_similarity
import numpy as np

def get_concepts_by_problem(db: Session, problem_statement: str):
    """
    Retrieve all Concept records matching a given problem statement.
    """
    return (
        db.query(models.Concept)
        # return any records whose problem_statement contains the input (case-insensitive)
        .filter(models.Concept.problem_statement.ilike(f"%{problem_statement}%"))
        .order_by(models.Concept.generated_at)
        .all()
    )

def create_concept(db: Session, concept_data: dict):
    """
    Insert a single concept into the database.
    `concept_data` should include all Concept fields except `id` and `generated_at`.
    """
    concept = models.Concept(**concept_data)
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


def create_concepts(db: Session, problem_statement: str, new_concepts: list[dict]):
    """
    Bulk-insert multiple new concepts for a given problem statement.
    Each dict in `new_concepts` may omit `problem_statement`; it will be applied.
    Returns the list of created Concept objects.
    """
    created = []
    for data in new_concepts:
        # ensure problem_statement is set
        data_with_problem = {**data, "problem_statement": problem_statement}
        obj = create_concept(db, data_with_problem)
        created.append(obj)
    return created


def get_similar_concepts(db: Session, problem_statement: str, top_k: int = 5):
    """Return concepts whose problem statements are semantically similar."""
    # embed query
    q_emb = embed_text(problem_statement)

    # fetch unique problem statements
    stmt_rows = (
        db.query(models.Concept.problem_statement)
        .distinct(models.Concept.problem_statement)
        .all()
    )

    sims = []
    for (stmt,) in stmt_rows:
        emb = embed_text(stmt)
        sim = cosine_similarity(q_emb, emb)
        sims.append((stmt, sim))

    sims.sort(key=lambda x: x[1], reverse=True)
    results = []
    for stmt, sim in sims[:top_k]:
        concepts = get_concepts_by_problem(db, stmt)
        results.append({"problem_statement": stmt, "similarity": sim, "concepts": concepts})
    return results

def update_concept(db: Session, concept_id: int, update_data: dict):
    concept = db.query(models.Concept).get(concept_id)
    if not concept:
        return None
    for field, val in update_data.items():
        setattr(concept, field, val)
    db.commit()
    db.refresh(concept)
    return concept
