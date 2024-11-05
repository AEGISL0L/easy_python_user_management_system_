# models.py

from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum

class RoleEnum(Enum):
    ADMIN = 'admin'
    USUARIO = 'usuario'
    PROFESOR = 'profesor'
    ALUMNO = 'alumno'

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(150), unique=True, nullable=False, index=True)
    _password = db.Column('contrasena', db.String(255), nullable=False)
    rol = db.Column(db.Enum(RoleEnum), nullable=False, index=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    auditorias = db.relationship('Auditoria', backref='usuario', lazy=True, cascade='all, delete-orphan')
    notificaciones = db.relationship('Notificacion', backref='usuario', lazy=True, cascade='all, delete-orphan')
    productos_asignados = db.relationship('Producto', backref='usuario_asignado_rel', lazy=True,
                                        foreign_keys='Producto.usuario_asignado')
    movimientos = db.relationship('Movimiento', backref='usuario', lazy=True, cascade='all, delete-orphan')

    @property
    def password(self):
        return self._password
    
    @password.setter
    def password(self, plaintext):
        self._password = generate_password_hash(plaintext, method='pbkdf2:sha256', salt_length=16)
    
    def check_password(self, plaintext):
        return check_password_hash(self._password, plaintext)

class Estado(db.Model):
    __tablename__ = 'estado'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    color = db.Column(db.String(7))  # For UI representation
    orden = db.Column(db.Integer)    # For sorting
    
    productos = db.relationship('Producto', backref='estado', lazy=True, cascade='all, delete-orphan')

class Producto(db.Model):
    __tablename__ = 'producto'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    codigo = db.Column(db.String(50), unique=True)
    estado_id = db.Column(db.Integer, db.ForeignKey('estado.id'), nullable=False)
    usuario_asignado = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'))
    fecha_asignacion = db.Column(db.DateTime, nullable=True)
    fecha_devolucion = db.Column(db.DateTime, nullable=True)
    fecha_alta = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ultima_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow)
    rfid_tag = db.Column(db.String(100))
    ultimo_escaneo = db.Column(db.DateTime)
    ubicacion_actual = db.Column(db.String(100))
    
    __table_args__ = (
        db.UniqueConstraint('rfid_tag', name='uq_producto_rfid_tag'),
    )
    
    movimientos = db.relationship('Movimiento', backref='producto', lazy=True, cascade='all, delete-orphan')
    escaneos = db.relationship('EscaneoRFID', back_populates='producto', overlaps="historial_ubicaciones")
    historial_ubicaciones = db.relationship('EscaneoRFID', back_populates='producto', order_by='EscaneoRFID.fecha_hora.desc()')
    
class EscaneoRFID(db.Model):
    __tablename__ = 'escaneo_rfid'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ubicacion = db.Column(db.String(100))
    lector_id = db.Column(db.String(100))
    
    producto = db.relationship('Producto', back_populates='escaneos', overlaps="historial_ubicaciones")
    
class Movimiento(db.Model):
    __tablename__ = 'movimiento'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    estado_anterior = db.Column(db.String(50), nullable=False)
    estado_nuevo = db.Column(db.String(50), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    detalle = db.Column(db.Text)
    duracion_dias = db.Column(db.Integer)
    razon = db.Column(db.Text)
    fecha_hora_devolucion = db.Column(db.DateTime)  # Add this line if needed

class Auditoria(db.Model):
    __tablename__ = 'auditoria'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    accion = db.Column(db.String(150), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    detalle = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

class Notificacion(db.Model):
    __tablename__ = 'notificacion'
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.String(250), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    leida = db.Column(db.Boolean, default=False, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    tipo = db.Column(db.String(50))  # For different notification types
    prioridad = db.Column(db.Integer, default=0)
    link = db.Column(db.String(255))  # For notification action URL

class SolicitudPrestamo(db.Model):
    __tablename__ = 'solicitud_prestamo'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    duracion_dias = db.Column(db.Integer, nullable=False)
    razon = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(50), default='pendiente')
    fecha_aprobacion = db.Column(db.DateTime)
    aprobado_por = db.Column(db.Integer, db.ForeignKey('usuario.id'))

class Categoria(db.Model):
    __tablename__ = 'categoria'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    productos = db.relationship('Producto', backref='categoria', lazy=True)

class ConfiguracionSistema(db.Model):
    __tablename__ = 'configuracion_sistema'
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text, nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(50))
    ultima_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow)

# Add relationships to existing models
Usuario.solicitudes = db.relationship('SolicitudPrestamo', backref='solicitante', lazy=True,
                                    foreign_keys='SolicitudPrestamo.usuario_id')
Usuario.aprobaciones = db.relationship('SolicitudPrestamo', backref='aprobador', lazy=True,
                                     foreign_keys='SolicitudPrestamo.aprobado_por')
