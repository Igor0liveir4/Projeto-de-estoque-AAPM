from app.database import Session
from app.models.armario import Armario

db = Session()
active = db.query(Armario).filter(Armario.ativo==True).count()
inactive = db.query(Armario).filter(Armario.ativo==False).count()
print('ativos=', active, 'inativos=', inactive)
items = db.query(Armario).filter(Armario.ativo==False).all()
for a in items[:10]:
    print('-', a.id, a.numero, a.localizacao, getattr(a.status, 'value', str(a.status)))
db.close()
