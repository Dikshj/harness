
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from harness.config import get_settings
from harness.models.base import Base
from harness.models import task, execution  # noqa: F401

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
