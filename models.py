# models.py

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Float, func
from db import Base

class Concept(Base):
    __tablename__ = "concepts"

    id                          = Column(Integer, primary_key=True, index=True)
    problem_statement           = Column(Text,   nullable=False)
    agent                       = Column(String(100), nullable=True)
    title                       = Column(String(255), nullable=False)
    description                 = Column(Text,   nullable=True)
    novelty_reasoning           = Column(Text,   nullable=True)
    feasibility_reasoning       = Column(Text,   nullable=True)
    cost_estimate               = Column(Text,   nullable=True)    # switched to Text if your DF has formatted strings
    trl                         = Column(Float,  nullable=True)
    trl_reasoning               = Column(Text,   nullable=True)
    trl_citations               = Column(JSON,   nullable=True)
    validated_trl               = Column(Float,  nullable=True)
    validated_trl_reasoning     = Column(Text,   nullable=True)
    validated_trl_citations     = Column(JSON,   nullable=True)
    components                  = Column(JSON,   nullable=True)
    references                  = Column(JSON,   nullable=True)
    constructive_critique       = Column(Text,   nullable=True)
    proposal_url                = Column(String(512), nullable=True)
    generated_at                = Column(DateTime(timezone=True), server_default=func.now())
