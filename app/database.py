from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import settings

# Synchronous database
engine = create_engine(
    settings.database_url,
    pool_size=20,          # Aumenta il pool size
    max_overflow=30,       # Aumenta l'overflow
    pool_timeout=60,       # Aumenta il timeout
    pool_recycle=3600,     # Ricicla le connessioni ogni ora
    pool_pre_ping=True     # Verifica le connessioni prima dell'uso
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Asynchronous database - initialize only when needed
async_engine = None
AsyncSessionLocal = None

def get_async_engine():
    global async_engine, AsyncSessionLocal
    if async_engine is None:
        async_engine = create_async_engine(
            settings.database_url_async,
            pool_size=20,          # Aumenta il pool size
            max_overflow=30,        # Aumenta l'overflow
            pool_timeout=60,       # Aumenta il timeout
            pool_recycle=3600,     # Ricicla le connessioni ogni ora
            pool_pre_ping=True     # Verifica le connessioni prima dell'uso
        )
        AsyncSessionLocal = sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )
    return async_engine, AsyncSessionLocal

Base = declarative_base()
metadata = MetaData()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Dependency to get async database session"""
    _, AsyncSessionLocal = get_async_engine()
    async with AsyncSessionLocal() as session:
        yield session
