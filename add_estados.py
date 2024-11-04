from app import app
from extensions import db
from models import Estado
from Flask_Limiter import Flask_Limiter


def add_test_estados():
    with app.app_context():
        # Define test estados
        test_estados = [
            {'nombre': 'Disponible', 'descripcion': 'Producto disponible para uso', 'color': '#28a745', 'orden': 1},
            {'nombre': 'Prestado', 'descripcion': 'Producto prestado temporalmente', 'color': '#ffc107', 'orden': 2},
            {'nombre': 'Reparación', 'descripcion': 'Producto en mantenimiento o reparación', 'color': '#dc3545', 'orden': 3},
            {'nombre': 'Uso', 'descripcion': 'Producto actualmente en uso', 'color': '#17a2b8', 'orden': 4}
        ]


        # Add estados to the database
        for estado_data in test_estados:
            estado = Estado.query.filter_by(nombre=estado_data['nombre']).first()
            if not estado:
                nuevo_estado = Estado(
                    nombre=estado_data['nombre'],
                    descripcion=estado_data['descripcion'],
                    color=estado_data['color'],
                    orden=estado_data['orden']
                )
                db.session.add(nuevo_estado)
        
        # Commit changes
        db.session.commit()
        print("Test estados added successfully.")

if __name__ == '__main__':
    add_test_estados()