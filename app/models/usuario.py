from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func 
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, nullable=False)

    role = Column(String, default=True)

    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())



    

    

    