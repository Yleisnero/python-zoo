import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from main import app, Base, AnimalORM, get_db


# --- Fixtures for test DB setup ---
@pytest.fixture(name="session")
def session_fixture():
    # Use in-memory SQLite (fast & isolated)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    # Override get_db dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_read_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == "Welcome to the Zoo"


def test_create_animal(client: TestClient):
    response = client.post(
        "/animals/",
        json={"name": "Simba", "species": "Lion", "age": 5, "is_endangered": True},
    )
    data = response.json()
    assert response.status_code == 200
    assert data["name"] == "Simba"
    assert data["species"] == "Lion"
    assert data["age"] == 5
    assert data["is_endangered"] is True
    assert "id" in data


def test_create_duplicate_animal(client: TestClient):
    client.post(
        "/animals/",
        json={"name": "Nemo", "species": "Fish", "age": 1, "is_endangered": False},
    )
    response = client.post(
        "/animals/",
        json={"name": "Nemo", "species": "Fish", "age": 2, "is_endangered": True},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_list_animals(session: Session, client: TestClient):
    # Insert directly into DB
    a1 = AnimalORM(name="Balu", species="Bear", age=10, is_endangered=False)
    a2 = AnimalORM(name="Kaa", species="Snake", age=7, is_endangered=True)
    session.add_all([a1, a2])
    session.commit()

    response = client.get("/animals/")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 2
    names = {a["name"] for a in data}
    assert names == {"Balu", "Kaa"}


def test_list_endangered_animals(session: Session, client: TestClient):
    a1 = AnimalORM(name="Panda", species="Bear", age=3, is_endangered=True)
    a2 = AnimalORM(name="Elephant", species="Mammal", age=25, is_endangered=False)
    session.add_all([a1, a2])
    session.commit()

    response = client.get("/animals/endangered/")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["name"] == "Panda"
