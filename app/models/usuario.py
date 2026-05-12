from sqlalchemy import Coumn, Integer, String, Bollean
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, nullable=False)

    role = Column(String, default=True)

    criado_em = Column(
        DateTime,
        default=datetime.utcnow
    )

    expira_em = Column(
        DateTime,
        default=lambda: datetime.utcnow() + timedelta(days)
    )




    

    

    