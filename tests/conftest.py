import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cybersim.db")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.cybersim.local")
os.environ.setdefault("ADMIN_PASSWORD", "TestOnly!Passphrase2026")

import pytest
from fastapi.testclient import TestClient

from app.core.runtime import get_orchestrator
from app.db.base import Base
from app.db.models import User
from app.db.session import SessionLocal, engine
from app.core.security import hash_password
from app.main import app


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    get_orchestrator.cache_clear()
    with SessionLocal() as db:
        db.add(User(
            email="admin@test.cybersim.local",
            password_hash=hash_password("TestOnly!Passphrase2026"),
            role="admin",
        ))
        db.commit()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        yield db
