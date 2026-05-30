
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, Integer, JSON, Text, Enum
from harness.models.base import Base
import enum

def utc_now():
    return datetime.now(timezone.utc)

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    EVALUATING = "evaluating"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text)
    repo_url = Column(String)
    issue_url = Column(String)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    plan = Column(JSON)
    results = Column(JSON)
    scores = Column(JSON)
    token_usage = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    retries = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
