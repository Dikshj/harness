
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, Integer, JSON, Text, ForeignKey, Enum
from harness.models.base import Base
import enum

def utc_now():
    return datetime.now(timezone.utc)

class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"

class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    agent = Column(String, nullable=False)
    tool = Column(String)
    input_payload = Column(JSON)
    output_payload = Column(JSON)
    logs = Column(Text)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)
