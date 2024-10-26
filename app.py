# app.py
import os
from flask import Flask, render_template, redirect, url_for, flash, request
from extensions import db
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SelectField,
    SubmitField,
    TextAreaField
)
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

from flask_migrate import Migrate
from models import db, Usuario, Estado, Producto, Auditoria, Movimiento, Notificacion

app = Flask(__name__)

# Define basedir before using it
basedir = os.path.abspath(os.path.dirname(__file__))


# Ensure the instance directory exists
instance_dir = os.path.join(basedir, 'instance')
if not os.path.exists(instance_dir):
    os.makedirs(instance_dir)

app.config['SECRET_KEY'] = 'tu_clave_secreta'  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'usuarios.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests to prevent 404 errors"""
    return '', 204

@app.errorhandler(404)
def pagina_no_encontrada(e):
    """Handle 404 Not Found errors by rendering custom template"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def error_servidor(e):
    """Handle 500 Internal Server Error by rendering custom template"""
    return render_template('500.html'), 500

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login authentication"""
    return Usuario.query.get(int(user_id))

class CambiarEstadoForm(FlaskForm):
    estado_nuevo = SelectField(
        'Nuevo Estado',
        choices=[],  # Will be filled dynamically
        validators=[DataRequired()]
    )
    submit = SubmitField('Cambiar Estado')

def requiere_roles(*roles):
    """
    Decorator that restricts access to routes based on user roles.
    
    Args:
        *roles: Variable number of role names that are allowed to access the route
        
    Returns:
        Function: Decorated route function that checks user role before allowing access
        
    Example:
        @requiere_roles('Administrador', 'Supervisor')
        def admin_route():
            # Only users with Administrador or Supervisor roles can access
            pass
    """
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

@app.route('/admin/productos')
@requiere_roles('Administrador')
def lista_productos():
    """
    Route handler for listing all products in the admin interface.
    Only accessible by users with Administrator role.
    
    Returns:
        rendered template: Admin product list page with all products
    """
    productos = Producto.query.all()
    return render_template('admin/lista_productos.html', productos=productos)

@app.route('/admin/producto/<int:producto_id>/cambiar_estado', methods=['GET', 'POST'])
@requiere_roles('Administrador')
def cambiar_estado_producto(producto_id):
    """
    Route handler for changing a product's state in the admin interface.
    Only accessible by users with Administrator role.
    
    Args:
        producto_id (int): ID of the product to modify
        
    Returns:
        rendered template: Form to change product state on GET,
        redirects to product list on successful POST
    """
    producto = Producto.query.get_or_404(producto_id)
    form = CambiarEstadoForm()
    form.estado_nuevo.choices = [(estado.id, estado.nombre) for estado in Estado.query.all()]

    if form.validate_on_submit():
        actualizar_estado_producto(producto, form.estado_nuevo.data)
        flash('Estado del producto actualizado correctamente.', 'success')
        return redirect(url_for('lista_productos'))

    return render_template('admin/cambiar_estado.html', producto=producto, form=form)

def actualizar_estado_producto(producto, estado_nuevo_id):
    """
    Updates the state of a product and records the change in audit trail,
    movement history and notifications.
    
    Args:
        producto (Producto): Product object to update
        estado_nuevo_id (int): ID of the new state
        
    Side effects:
        - Updates product state in database
        - Creates audit trail entry
        - Creates movement history entry
        - Creates notification if product moves to repair or use state
    """
    estado_anterior = producto.estado.nombre
    estado_nuevo = Estado.query.get(estado_nuevo_id)
    producto.estado = estado_nuevo
    db.session.commit()

    registrar_auditoria(producto, estado_anterior, estado_nuevo)
    registrar_movimiento(producto, estado_anterior, estado_nuevo)
    crear_notificacion_si_necesario(producto, estado_nuevo)

def registrar_auditoria(producto, estado_anterior, estado_nuevo):
    """
    Records an audit trail entry for a product state change.
    
    Args:
        producto (Producto): Product object being modified
        estado_anterior (str): Previous state name
        estado_nuevo (Estado): New state object
        
    Side effects:
        - Creates new Auditoria record in database
    """
    auditoria = Auditoria(
        usuario_id=current_user.id,
        accion='Cambio de estado',
        detalle=f'Producto {producto.nombre} de {estado_anterior} a {estado_nuevo.nombre}'
    )
    db.session.add(auditoria)

def registrar_movimiento(producto, estado_anterior, estado_nuevo):
    """
    Records a movement history entry for a product state change.
    
    Args:
        producto (Producto): Product object being moved
        estado_anterior (str): Previous state name
        estado_nuevo (Estado): New state object
        
    Side effects:
        - Creates new Movimiento record in database
    """
    movimiento = Movimiento(
        producto_id=producto.id,
        usuario_id=current_user.id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo.nombre
    )
    db.session.add(movimiento)

def crear_notificacion_si_necesario(producto, estado_nuevo):
    """
    Creates a notification if a product is moved to repair or use state.
    
    Args:
        producto (Producto): Product object being moved
        estado_nuevo (Estado): New state object
        
    Side effects:
        - Creates new Notificacion record in database if state is 'Reparación' or 'Uso'
    """
    if estado_nuevo.nombre in ['Reparación', 'Uso']:
        notificacion = Notificacion(
            mensaje=f'El producto {producto.nombre} ha sido enviado a {estado_nuevo.nombre}.',
            usuario_id=None
        )
        db.session.add(notificacion)
    db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    """
    User loader callback for Flask-Login.
    
    Args:
        user_id: The user ID to load
        
    Returns:
        Usuario: The user object if found, None otherwise
    """
    return db.session.get(Usuario, int(user_id))

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
        """
        Validates that the username is unique in the system.
        
        Args:
            nombre_usuario: Form field containing the username to validate
            
        Raises:
            ValidationError: If username already exists in database
        """
        usuario = Usuario.query.filter_by(
            nombre_usuario=nombre_usuario.data
        ).first()
        if usuario:
            raise ValidationError(
                'El nombre de usuario ya existe. Por favor, elige otro.'
            )

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

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """
    Route handler for user registration.
    """
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Route handler for user login.
    """
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

@app.route('/logout')
@login_required
def logout():
    """
    Route handler for user logout.
    """
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def inicio():
    """
    Route handler for the home/landing page.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return render_template('inicio.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Route handler for the main dashboard.
    """
    if current_user.rol == 'Administrador':
        return redirect(url_for('admin'))
    elif current_user.rol == 'Profesor':
        return redirect(url_for('profesor_dashboard'))
    elif current_user.rol == 'Alumno':
        return redirect(url_for('alumno_dashboard'))
    else:
        return "Rol no reconocido."

@app.route('/admin')
@requiere_roles('Administrador')
def admin():
    """
    Route handler for the admin dashboard.
    """
    return "Bienvenido al panel de administrador."

@app.route('/profesor')
@requiere_roles('Profesor')
def profesor_dashboard():
    """
    Route handler for the profesor dashboard.
    """
    return "Bienvenido al panel del profesor."

@app.route('/alumno')
@requiere_roles('Alumno')
def alumno_dashboard():
    """
    Route handler for the alumno dashboard.
    """
    return "Bienvenido al panel del alumno."

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True, use_debugger=True)
