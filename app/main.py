from fastapi import FastAPI
from database import engine, Base

from models.usuario import Usuario

Base.metadata.create_all(bind=engine)

app = FastAPI()