from app.database import Session
from app.models.armario import Armario, StatusArmario
from sqlalchemy.exc import IntegrityError

def main():
    db = Session()
    try:
        # Limpa entradas de teste anteriores (opcional)
        db.query(Armario).filter(Armario.numero == 'A01').delete()
        db.commit()

        # Cria A01 em Bloco A
        a1 = Armario(numero='A01', localizacao='Bloco A')
        db.add(a1)
        db.commit()
        print('Criado:', a1.id, a1.numero, a1.localizacao)

        # Cria A01 em Bloco B
        a2 = Armario(numero='A01', localizacao='Bloco B')
        db.add(a2)
        db.commit()
        print('Criado:', a2.id, a2.numero, a2.localizacao)

    except IntegrityError as e:
        db.rollback()
        print('IntegrityError:', e)
    finally:
        # Lista todos os armários com numero A01
        items = db.query(Armario).filter(Armario.numero == 'A01').order_by(Armario.localizacao).all()
        print('\nArmários encontrados com numero A01:')
        for it in items:
            print('-', it.id, it.numero, it.localizacao)
        db.close()

if __name__ == '__main__':
    main()
