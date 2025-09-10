from pydantic import ConfigDict
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./animals.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ORM Model
class AnimalORM(Base):
    __tablename__ = "animals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    species = Column(String)
    age = Column(Integer)
    is_endangered = Column(Boolean)


# Pydantic Schema
class AnimalCreate(BaseModel):
    name: str
    species: str
    age: int
    is_endangered: bool


class AnimalRead(AnimalCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Create database tables
Base.metadata.create_all(bind=engine)


# Dependency: get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()


@app.get("/")
def read_root():
    return "Welcome to the Zoo"


# Create a new animal
@app.post("/animals/", response_model=AnimalRead)
def create_animal(animal: AnimalCreate, db: Session = Depends(get_db)):
    existing_animal = db.query(AnimalORM).filter(AnimalORM.name == animal.name).first()
    if existing_animal:
        raise HTTPException(
            status_code=400, detail=f"Animal with name '{animal.name}' already exists."
        )
    db_animal = AnimalORM(**animal.model_dump())
    db.add(db_animal)
    db.commit()
    db.refresh(db_animal)
    return db_animal


# Get animal by ID
@app.get("/animals/{animal_id}/", response_model=AnimalRead)
def read_animal(animal_id: int, db: Session = Depends(get_db)):
    db_animal = db.query(AnimalORM).filter(AnimalORM.id == animal_id).first()
    if db_animal is None:
        raise HTTPException(status_code=404, detail="Animal not found")
    return db_animal


# List all animals
@app.get("/animals/", response_model=list[AnimalRead])
def list_animals(db: Session = Depends(get_db)):
    return db.query(AnimalORM).all()


# Get endangered animals only
@app.get("/animals/endangered/", response_model=list[AnimalRead])
def list_endangered_animals(db: Session = Depends(get_db)):
    return db.query(AnimalORM).filter(AnimalORM.is_endangered == True).all()


# Get oldest animal
@app.get("/animals/oldest/", response_model=AnimalRead)
def read_oldest_animal(db: Session = Depends(get_db)):
    return db.query(AnimalORM).order_by(AnimalORM.age.desc()).first()

