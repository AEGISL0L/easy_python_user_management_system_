from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
    UserMixin
)
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta'  # Reemplaza por una clave segura
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'sqlite:////home/juav/Documentos/fp/rfid2/inventario/usuarios.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

from flask_migrate import Migrate

migrate = Migrate(app, db)

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Modelo de Estado
class Estado(db.Model):
    __tablename__ = 'estado'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    # Relaciones
    productos = db.relationship('Producto', backref='estado', lazy=True)

    def __repr__(self):
        return f'<Estado {self.nombre}>'

# Modelo de producto
class Producto(db.Model):
    __tablename__ = 'producto'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    estado_id = db.Column(
            db.Integer, 
            db.ForeignKey('estado.id'), 
            nullable=False
    )
    
    # Relaciones
    movimientos = db.relationship('Movimiento', back_populates='producto', lazy=True)

    def __repr__(self):
        return f'<Producto {self.nombre}>'


#Si utilizas Query.get() en otras partes de tu código, deberías reemplazarlo de la misma manera.

#usuario = Usuario.query.get(usuario_id)

#Después:
#usuario = db.session.get(Usuario, usuario_id)

# Modelo de auditoria
class Auditoria(db.Model):
    __tablename__ = 'auditoria'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey('usuario.id', name='fk_auditoria_usuario'),
        nullable=False
    )
    accion = db.Column(db.String(150), nullable=False)
    fecha_hora = db.Column(
            db.DateTime, 
            nullable=False, 
            default=datetime.utcnow
            )
    detalles = db.Column(db.Text, nullable=True)


# Modelo de Movimiento
class Movimiento(db.Model):
    __tablename__ = 'movimiento'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(
        db.Integer,
        db.ForeignKey('producto.id', name='fk_movimiento_producto'),
        nullable=False
    )
    estado_anterior_id = db.Column(
        db.Integer,
        db.ForeignKey('estado.id', name='fk_movimiento_estado_anterior'),
        nullable=False
    )
    estado_nuevo_id = db.Column(
        db.Integer,
        db.ForeignKey('estado.id', name='fk_movimiento_estado_nuevo'),
        nullable=False
    )
    fecha_hora = db.Column(
            db.DateTime, 
            nullable=False, 
            default=datetime.utcnow
    )
    # Relaciones
    producto = db.relationship('Producto', back_populates='movimientos')
    estado_anterior = db.relationship(
            'Estado', 
            foreign_keys=[estado_anterior_id]
    )
    estado_nuevo = db.relationship(
            'Estado', 
            foreign_keys=[estado_nuevo_id]
     )

    def __repr__(self):
        return f'<Movimiento {self.producto.nombre} de {self.estado_anterior.nombre} a {self.estado_nuevo.nombre}>'

# Modelo de Notificacion
class Notificacion(db.Model):
    __tablename__ = 'notificacion'
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.String(250), nullable=False)
    fecha_hora = db.Column(
            db.DateTime, 
            nullable=False, 
            default=datetime.utcnow
    )
    leida = db.Column(db.Boolean, default=False)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey('usuario.id', name='fk_notificacion_usuario'),
        nullable=True
    )


# Modelo de Usuario
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(150), unique=True, nullable=False)
    contraseña = db.Column(db.String(150), nullable=False)
    rol = db.Column(db.String(50), nullable=False)
    # Relaciones
    auditorias = db.relationship('Auditoria', backref='usuario', lazy=True)
    notificaciones = db.relationship(
            'Notificacion', 
            backref='usuario', 
            lazy=True
    )

    def __repr__(self):
        return f'<Usuario {self.nombre_usuario}>'

# Formulario CambiarEstadoForm
class CambiarEstadoForm(FlaskForm):
    estado_nuevo = SelectField(
        'Nuevo Estado',
        choices=[],  # Se llenará dinámicamente
        validators=[DataRequired()]
    )
    submit = SubmitField('Cambiar Estado')


# Decorador para Restricción por Roles
def requiere_roles(*roles):
    def decorador(f):
        @wraps(f)
        @login_required
        def envoltura(*args, **kwargs):
            if current_user.rol not in roles:
                flash(
                    'No tienes permiso para acceder a esta página.',
                    'danger'
                )
                return redirect(url_for('inicio'))
            return f(*args, **kwargs)
        return envoltura
    return decorador



# Ruta para Listar Productos
@app.route('/admin/productos')
@requiere_roles('Administrador')
def lista_productos():
    productos = Producto.query.all()
    return render_template('admin/lista_productos.html', productos=productos)

# Ruta para Cambiar el Estado de un Producto
@app.route('/admin/producto/<int:producto_id>/cambiar_estado', methods=['GET', 'POST'])
@requiere_roles('Administrador')
def cambiar_estado_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    form = CambiarEstadoForm()
    # Llenar las opciones del SelectField con los estados disponibles
    form.estado_nuevo.choices = [(estado.id, estado.nombre) for estado in Estado.query.all()]

    if form.validate_on_submit():
        estado_anterior = producto.estado.nombre
        estado_nuevo_id = form.estado_nuevo.data
        estado_nuevo = Estado.query.get(estado_nuevo_id)
        producto.estado = estado_nuevo
        db.session.commit()

        # Registrar en auditoría
        auditoria = Auditoria(
            usuario_id=current_user.id,
            accion='Cambio de estado',
            detalle=f'Producto {producto.nombre} de {estado_anterior} a {estado_nuevo.nombre}'
        )
        db.session.add(auditoria)

        # Registrar movimiento
        movimiento = Movimiento(
            producto_id=producto.id,
            usuario_id=current_user.id,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo.nombre
        )
        db.session.add(movimiento)

        # Crear notificación si es necesario
        if estado_nuevo.nombre in ['Reparación', 'Uso']:
            notificacion = Notificacion(
                mensaje=f'El producto {producto.nombre} ha sido enviado a {estado_nuevo.nombre}.',
                usuario_id=None  # Notificación general para administradores
            )
            db.session.add(notificacion)

        db.session.commit()
        flash('Estado del producto actualizado correctamente.', 'success')
        return redirect(url_for('lista_productos'))

    return render_template('admin/cambiar_estado.html', producto=producto, form=form)


# Carga de usuario para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


# Formulario de Registro
class FormularioRegistro(FlaskForm):
    nombre_usuario = StringField(
        'Nombre de Usuario',
        validators=[DataRequired(), Length(min=4, max=150)]
    )
    contraseña = PasswordField(
        'Contraseña',
        validators=[DataRequired(), Length(min=6)]
    )
    rol = SelectField(
        'Rol',
        choices=[
            ('Alumno', 'Alumno'),
            ('Profesor', 'Profesor'),
            ('Administrador', 'Administrador')
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Registrarse')

    def validate_nombre_usuario(self, nombre_usuario):
        usuario = Usuario.query.filter_by(
            nombre_usuario=nombre_usuario.data
        ).first()
        if usuario:
            raise ValidationError(
                'El nombre de usuario ya existe. Por favor, elige otro.'
            )


# Formulario de Inicio de Sesión
class FormularioLogin(FlaskForm):
    nombre_usuario = StringField(
        'Nombre de Usuario',
        validators=[DataRequired(), Length(min=4, max=150)]
    )
    contraseña = PasswordField(
        'Contraseña',
        validators=[DataRequired(), Length(min=6)]
    )
    submit = SubmitField('Iniciar Sesión')

class FormularioCambioEstado(FlaskForm):
    producto_id = SelectField('Producto', coerce=int, validators=[DataRequired()])
    estado_nuevo_id = SelectField('Nuevo Estado', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Cambiar Estado')


# Ruta de Registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    form = FormularioRegistro()
    if form.validate_on_submit():
        nuevo_usuario = Usuario(
            nombre_usuario=form.nombre_usuario.data,
            contraseña=generate_password_hash(form.contraseña.data),
            rol=form.rol.data
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Usuario registrado con éxito', 'success')
        return redirect(url_for('login'))
    return render_template('registro.html', form=form)


# Ruta de Inicio de Sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = FormularioLogin()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(
            nombre_usuario=form.nombre_usuario.data
        ).first()
        if usuario and check_password_hash(
            usuario.contraseña, form.contraseña.data
        ):
            login_user(usuario)
            flash('Has iniciado sesión correctamente.', 'success')
            # Redireccionar según el rol
            if usuario.rol == 'Administrador':
                return redirect(url_for('admin'))
            elif usuario.rol == 'Profesor':
                return redirect(url_for('profesor_dashboard'))
            elif usuario.rol == 'Alumno':
                return redirect(url_for('alumno_dashboard'))
            else:
                return redirect(url_for('inicio'))
        else:
            flash('Nombre de usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html', form=form)


# Ruta de Cierre de Sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))


# Ruta de Inicio
@app.route('/')
def inicio():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return render_template('inicio.html')


# Ruta del Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol == 'Administrador':
        return redirect(url_for('admin'))
    elif current_user.rol == 'Profesor':
        return redirect(url_for('profesor_dashboard'))
    elif current_user.rol == 'Alumno':
        return redirect(url_for('alumno_dashboard'))
    else:
        return "Rol no reconocido."


# Decorador para Restricción por Roles
def requiere_roles(*roles):
    def decorador(f):
        @wraps(f)
        @login_required
        def envoltura(*args, **kwargs):
            if current_user.rol not in roles:
                flash(
                    'No tienes permiso para acceder a esta página.',
                    'danger'
                )
                return redirect(url_for('inicio'))
            return f(*args, **kwargs)
        return envoltura
    return decorador


# Ruta Protegida para Administradores
@app.route('/admin')
@requiere_roles('Administrador')
def admin():
    return "Bienvenido al panel de administrador."


# Ruta Protegida para Profesores
@app.route('/profesor')
@requiere_roles('Profesor')
def profesor_dashboard():
    return "Bienvenido al panel del profesor."


# Ruta Protegida para Alumnos
@app.route('/alumno')
@requiere_roles('Alumno')
def alumno_dashboard():
    return "Bienvenido al panel del alumno."


# Manejadores de Errores
@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def error_servidor(e):
    return render_template('500.html'), 500



# Ejecutar la Aplicación
if __name__ == '__main__':
    app.run(debug=True)

