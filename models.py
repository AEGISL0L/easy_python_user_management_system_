# models.py
from extensions import db
from flask_login import UserMixin
from datetime import datetime

# Modelo de Estado
class Estado(db.Model):
    __tablename__ = 'estado'
    id = db.Column(db.Integer, primary_key=True)  # Primary key for Estado
    nombre = db.Column(db.String(50), unique=True, nullable=False)  # Unique name for the state
    productos = db.relationship('Producto', backref='estado', lazy=True)  # One-to-many relationship with Producto

    def __repr__(self):
        return f'<Estado {self.nombre}>'

# Modelo de Producto
class Producto(db.Model):
    __tablename__ = 'producto'
    id = db.Column(db.Integer, primary_key=True)  # Primary key for Producto
    nombre = db.Column(db.String(150), nullable=False)  # Name of the product
    descripcion = db.Column(db.Text, nullable=True)  # Description of the product
    estado_id = db.Column(db.Integer, db.ForeignKey('estado.id'), nullable=False)  # Foreign key to Estado
    movimientos = db.relationship('Movimiento', back_populates='producto', lazy=True)  # One-to-many relationship with Movimiento

    def __repr__(self):
        return f'<Producto {self.nombre}>'

# Modelo de Auditoria
class Auditoria(db.Model):
    __tablename__ = 'auditoria'
    id = db.Column(db.Integer, primary_key=True)  # Primary key for Auditoria
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', name='fk_auditoria_usuario'), nullable=False)  # Foreign key to Usuario
    accion = db.Column(db.String(150), nullable=False)  # Action performed
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Timestamp of the action
    detalles = db.Column(db.Text, nullable=True)  # Details of the action

# Modelo de Movimiento
class Movimiento(db.Model):
    __tablename__ = 'movimiento'
    id = db.Column(db.Integer, primary_key=True)  # Primary key for Movimiento
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id', name='fk_movimiento_producto'), nullable=False)  # Foreign key to Producto
    estado_anterior_id = db.Column(db.Integer, db.ForeignKey('estado.id', name='fk_movimiento_estado_anterior'), nullable=False)  # Foreign key to previous Estado
    estado_nuevo_id = db.Column(db.Integer, db.ForeignKey('estado.id', name='fk_movimiento_estado_nuevo'), nullable=False)  # Foreign key to new Estado
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Timestamp of the movement
    producto = db.relationship('Producto', back_populates='movimientos')  # Relationship with Producto
    estado_anterior = db.relationship('Estado', foreign_keys=[estado_anterior_id])  # Relationship with previous Estado
    estado_nuevo = db.relationship('Estado', foreign_keys=[estado_nuevo_id])  # Relationship with new Estado

    def __repr__(self):
        return f'<Movimiento {self.producto.nombre} de {self.estado_anterior.nombre} a {self.estado_nuevo.nombre}>'

# Modelo de Notificacion
class Notificacion(db.Model):
    __tablename__ = 'notificacion'
    id = db.Column(db.Integer, primary_key=True)  # Primary key for Notificacion
    mensaje = db.Column(db.String(250), nullable=False)  # Notification message
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Timestamp of the notification
    leida = db.Column(db.Boolean, default=False)  # Read status of the notification
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', name='fk_notificacion_usuario'), nullable=True)  # Foreign key to Usuario

# Modelo de Usuario
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)  # Primary key for Usuario
    nombre_usuario = db.Column(db.String(150), unique=True, nullable=False)  # Unique username
    contraseña = db.Column(db.String(150), nullable=False)  # Password
    rol = db.Column(db.String(50), nullable=False)  # Role of the user
    auditorias = db.relationship('Auditoria', backref='usuario', lazy=True)  # One-to-many relationship with Auditoria
    notificaciones = db.relationship('Notificacion', backref='usuario', lazy=True)  # One-to-many relationship with Notificacion

    def __repr__(self):
        return f'<Usuario {self.nombre_usuario}>'