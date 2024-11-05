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
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
    UserMixin
)
from decorators import requiere_roles
from datetime import datetime
from flask_migrate import Migrate
from models import Usuario, Estado, Producto, Auditoria, Movimiento, Notificacion, RoleEnum
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import openpyxl
from reportlab.lib import colors


from flask import Flask
from models import RoleEnum

app = Flask(__name__)

# Add RoleEnum to Jinja2 globals
app.jinja_env.globals['RoleEnum'] = RoleEnum
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

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

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



"""
    A Flask-WTF form for changing the state of a product.
    
    This form allows the user to select a new state for a product from a list of available states.
    
    Attributes:
        estado_nuevo (SelectField): A dropdown field for selecting the new state.
        submit (SubmitField): A submit button to save the new state.
    
    Methods:
        __init__(self, *args, **kwargs):
            Initializes the form and populates the `estado_nuevo` choices with all available states.
            Raises a `ValueError` if there are no states available in the system.
    """
class CambiarEstadoForm(FlaskForm):
        estado_nuevo = SelectField(
        'Nuevo Estado',
        choices=[],  # Will be filled dynamically
        validators=[DataRequired()]
    )
    submit = SubmitField('Cambiar Estado')

    def __init__(self, *args, **kwargs):
        super(CambiarEstadoForm, self).__init__(*args, **kwargs)
        estados = Estado.query.all()
        if not estados:
            raise ValueError("No hay estados disponibles en el sistema")
        self.estado_nuevo.choices = [(estado.id, estado.nombre) for estado in estados]    

from flask import redirect, url_for, flash
from flask_login import current_user
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
from models import Estado
from flask import render_template, redirect, url_for, flash
#from app import ProductoFormfrom models import Producto, Estado
from extensions import db


"""
        A Flask-WTF form for creating a new product.
    
        This form allows the user to input the name, description, code, and state of a new product.
    
        Attributes:
            nombre (StringField): The name of the product.
            descripcion (TextAreaField): The description of the product.
            codigo (StringField): The code of the product.
            estado_id (SelectField): The state of the product, selected from a dropdown.
            submit (SubmitField): A submit button to save the new product.
    
        Methods:
            __init__(self, *args, **kwargs):
                Initializes the form and populates the `estado_id` choices with all available states.
                Raises a `ValueError` if there are no states available in the system.
        """
class ProductoForm(FlaskForm):
        nombre = StringField('Nombre', validators=[DataRequired(), Length(max=150)])
    descripcion = TextAreaField('Descripción', validators=[Length(max=500)])
    codigo = StringField('Código', validators=[Length(max=50)])
    estado_id = SelectField('Estado', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Agregar Producto')

    def __init__(self, *args, **kwargs):
        super(ProductoForm, self).__init__(*args, **kwargs)
        self.estado_id.choices = [(estado.id, estado.nombre) for estado in Estado.query.all()]



"""
Renders the admin view for listing all products.

This route is only accessible to users with the 'ADMIN' role. 
It retrieves all products from the database and renders the 
'admin/lista_productos.html' template, passing the list of 
products as the 'productos' parameter.

"""
@app.route('/admin/productos')
@requiere_roles(RoleEnum.ADMIN.value)
def lista_productos():
    productos = Producto.query.all()
    return render_template('admin/lista_productos.html', productos=productos)


    
"""
Renders the admin view for creating a new product.

This route is only accessible to users with the 'ADMIN' role. 
It displays a form for creating a new product, including fields
for the product name, description, code, and initial state. 
When the form is submitted, a new `Producto` instance is created 
and added to the database.

If the form is valid and the product is successfully added, a success 
flash message is displayed and the user is redirected to the list of products. 
If there is an error adding the product, a danger flash message is displayed.

Args:
    None

Returns:
    A rendered template for the 'admin/agregar_producto.html' page, 
    with the `ProductoForm` instance 
    passed as the `form` parameter.
"""
@app.route('/admin/productos/nuevo', methods=['GET', 'POST'])
@login_required
@requiere_roles(RoleEnum.ADMIN.value)
def agregar_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        nuevo_producto = Producto(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            codigo=form.codigo.data,
            estado_id=form.estado_id.data
        )
        try:
            db.session.add(nuevo_producto)
            db.session.commit()
            flash('Producto agregado exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar producto: {str(e)}', 'danger')
        return redirect(url_for('lista_productos'))
    return render_template('admin/agregar_producto.html', form=form)



"""
Renders the admin view for changing the state of a product.

This route is only accessible to users with the 'ADMIN' role. 
It displays a form for changing the state of a product, allowing the
admin to select a new state from a dropdown. When the form is submitted,
the `actualizar_estado_producto` function is called to update the product's
state, create an audit record, register a movement, and create a notification
if necessary.

If the state is successfully updated, a success flash message is displayed
and the user is redirected to the list of products. If there is an error
updating the state, a danger flash message is displayed.

Args:
    producto_id (int): The ID of the product to update.

Returns:
    A rendered template for the 'admin/cambiar_estado.html' page, with the
    `Producto` instance and `CambiarEstadoForm` instance passed as the
    `producto` and `form` parameters, respectively.
"""

@app.route('/admin/producto/<int:producto_id>/cambiar_estado', methods=['GET', 'POST'])
@requiere_roles(RoleEnum.ADMIN.value)
def cambiar_estado_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    form = CambiarEstadoForm()
    form.estado_nuevo.choices = [(estado.id, estado.nombre) for estado in Estado.query.all()]

    if form.validate_on_submit():
        actualizar_estado_producto(producto, form.estado_nuevo.data)
        flash('Estado del producto actualizado correctamente.', 'success')
        return redirect(url_for('lista_productos'))

    return render_template('admin/cambiar_estado.html', producto=producto, form=form)



"""
    Updates the state of a product and performs related actions.
    
    This function updates the state of the given product to the new state specified by `estado_nuevo_id`. It also performs the following actions:
    
    - Retrieves the previous state of the product.
    - Registers an audit record for the state change.
    - Registers a movement record for the state change.
    - Creates a notification if the new state is one that requires a notification.
    
    Args:
        producto (Producto): The product whose state is to be updated.
        estado_nuevo_id (int): The ID of the new state for the product.
    """
def actualizar_estado_producto(producto, estado_nuevo_id):
    estado_anterior = producto.estado.nombre
    estado_nuevo = Estado.query.get(estado_nuevo_id)
    producto.estado = estado_nuevo
    db.session.commit()

    registrar_auditoria(producto, estado_anterior, estado_nuevo)
    registrar_movimiento(producto, estado_anterior, estado_nuevo)
    crear_notificacion_si_necesario(producto, estado_nuevo)
    


"""
        Registers an audit record for a change in the state of a product.
    
        This function creates an Auditoria record to log the change in state of the
        given product from the previous state to the new state.
    
        Args:
            producto (Producto): The product whose state has changed.
            estado_anterior (str): The previous state of the product.
            estado_nuevo (Estado): The new state of the product.

"""
def registrar_auditoria(producto, estado_anterior, estado_nuevo):
        auditoria = Auditoria(
        usuario_id=current_user.id,
        accion='Cambio de estado',
        detalle=f'Producto {producto.nombre} de {estado_anterior} a {estado_nuevo.nombre}'
    )
    db.session.add(auditoria)


"""
        Registers a movement record for a change in the state of a product.
    
        This function creates a Movimiento record to log the change in state of the
        given product from the previous state to the new state.
    
        Args:
            producto (Producto): The product whose state has changed.
            estado_anterior (str): The previous state of the product.
            estado_nuevo (Estado): The new state of the product.
"""
def registrar_movimiento(producto, estado_anterior, estado_nuevo):
        movimiento = Movimiento(
        producto_id=producto.id,
        usuario_id=current_user.id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo.nombre
    )
    db.session.add(movimiento)


"""
    Creates a notification if necessary based on the new product state.
    
    This function checks if the new product state is one that requires a notification to be
    created. If so, it creates a new Notificacion record and adds it to the database.
    
    Args:
        producto (Producto): The product whose state has changed.
        estado_nuevo (Estado): The new state of the product.
"""
def crear_notificacion_si_necesario(producto, estado_nuevo):
        estados_notificables = ['Reparación', 'Uso']
    if estado_nuevo and estado_nuevo.nombre in estados_notificables:
        try:
            notificacion = Notificacion(
                mensaje=f'El producto {producto.nombre} ha sido enviado a {estado_nuevo.nombre}.',
                usuario_id=None
            )
            db.session.add(notificacion)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error al crear notificación: {str(e)}')


"""
    Defines a Flask form for user registration.
    
    This form includes fields for the username, password, password confirmation, and user role. The username field is validated to ensure it is unique in the system.
    
    Args:
        nombre_usuario (str): The username entered by the user.
        contrasena (str): The password entered by the user.
        confirm_contrasena (str): The password confirmation entered by the user.
        rol (RoleEnum): The user role selected by the user.
    
    Raises:
        ValidationError: If the username already exists in the database.
"""
class FormularioRegistro(FlaskForm):
        nombre_usuario = StringField('Nombre de Usuario', 
        validators=[DataRequired(), Length(min=4, max=150)])
    contrasena = PasswordField('Contraseña', 
        validators=[DataRequired(), Length(min=6)])
    confirm_contrasena = PasswordField('Confirmar Contraseña', 
        validators=[DataRequired(), EqualTo('contrasena')])
    rol = SelectField('Rol',
        choices=[
            (RoleEnum.ADMIN.value, 'Administrador'),
            (RoleEnum.USUARIO.value, 'Usuario'),
            (RoleEnum.PROFESOR.value, 'Profesor'), 
            (RoleEnum.ALUMNO.value, 'Alumno')
        ],
        validators=[DataRequired()])
    submit = SubmitField('Registrarse')


"""
        Validates that the username is unique in the system.
        
        Args:
            nombre_usuario: Form field containing the username to validate
            
        Raises:
            ValidationError: If username already exists in database
"""
    def validate_nombre_usuario(self, nombre_usuario):
        usuario = Usuario.query.filter_by(
            nombre_usuario=nombre_usuario.data
        ).first()
        if usuario:
            raise ValidationError(
                'El nombre de usuario ya existe. Por favor, elige otro.'
            )


class FormularioLogin(FlaskForm):
"""
    Defines a Flask form for user login.
    
    This form includes fields for the username and password. 
    The username field is validated to ensure it is not empty 
    and is between 4 and 150 characters long. 
    The password field is validated to ensure it is not empty 
    and is at least 6 characters long.
    
    Args:
        nombre_usuario (str): The username entered by the user.
        contrasena (str): The password entered by the user.
    
    Raises:
        ValidationError: If the username or password is invalid.
    """
        nombre_usuario = StringField(
        'Nombre de Usuario',
        validators=[DataRequired(), Length(min=4, max=150)]
    )
    contrasena = PasswordField(
        'Contraseña',
        validators=[DataRequired(), Length(min=6)]
    )
    submit = SubmitField('Iniciar Sesión')



"""
Route handler for the application's home page.

If the current user is authenticated, they are redirected to the dashboard page.
Otherwise, the 'inicio.html' template is rendered.
"""

"""
Route handler for user registration.

This route is limited to 5 requests per minute using the Flask-Limiter extension.
"""
@app.route('/')
def inicio():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('inicio.html')

@app.route('/registro', methods=['GET', 'POST'])
@limiter.limit("5 per minute")


def registro():
"""
    Route handler for user registration.
    
    This route handles the registration of a new user. It takes a FormularioRegistro form as input, which includes fields for the username and password. If the form is valid, a new Usuario object is created with the provided username and role, and the password is set. The new user is then added to the database and the user is redirected to the login page.
    
    Args:
        form (FormularioRegistro): The registration form submitted by the user.
    
    Returns:
        A rendered template for the registration page, or a redirect to the login page if the registration is successful.
    """
        """
    Route handler for user registration.
"""
    form = FormularioRegistro()
    if form.validate_on_submit():
        nuevo_usuario = Usuario(
            nombre_usuario=form.nombre_usuario.data,
            rol=RoleEnum(form.rol.data)
        )
        nuevo_usuario.password = form.contrasena.data
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Usuario registrado exitosamente.', 'success')
        return redirect(url_for('login'))
    return render_template('registro.html', form=form)

"""
Route handler for user login.

This route handles the login process for a user. It takes a FormularioLogin form as input, which includes fields for the username and password. If the form is valid, the user is queried from the database using the provided username. If the user exists and the provided password matches the stored password, the user is logged in using the login_user() function. The user is then redirected to the dashboard page.

Args:
    form (FormularioLogin): The login form submitted by the user.

Returns:
    A rendered template for the login page, or a redirect to the dashboard page if the login is successful.
"""
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = FormularioLogin()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(nombre_usuario=form.nombre_usuario.data).first()
        if usuario and usuario.check_password(form.contrasena.data):
            login_user(usuario)
            flash('Has iniciado sesión correctamente.', 'success')
            return redirect(url_for('dashboard'))
        flash('Nombre de usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html', form=form)


"""
Route handler for user logout.

This route logs out the currently authenticated user by calling the logout_user() function. 
After the user is logged out, a success message is flashed and the user is redirected to the login page.
"""
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))


"""
Route handler for the dashboard page.

This route is responsible for redirecting the user to the appropriate dashboard page based on their role.
If the user is an admin, they are redirected to the admin dashboard. 
If the user is a professor, they are redirected to the professor dashboard. 
If the user is a student, they are redirected to the student dashboard. 
If the user is a regular user, they are redirected to the user dashboard. 
If the user's role is not recognized, they are redirected to the home page.

This route requires the user to be logged in, as it uses the @login_required decorator.

Returns:
    A redirect to the appropriate dashboard page based on the user's role.
"""
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol == RoleEnum.ADMIN:
        return redirect(url_for('admin_dashboard'))
    elif current_user.rol == RoleEnum.PROFESOR:
        return redirect(url_for('profesor_dashboard'))
    elif current_user.rol == RoleEnum.ALUMNO:
        return redirect(url_for('alumno_dashboard'))
    elif current_user.rol == RoleEnum.USUARIO:
        return redirect(url_for('usuario_dashboard'))
    return redirect(url_for('inicio'))

"""
Route handler for the user dashboard page.

This route is responsible for rendering the user dashboard page, which displays the products that have been assigned to the currently authenticated user.

The route is decorated with the `@requiere_roles` decorator, which ensures that only users with the `RoleEnum.USUARIO.value` role can access this route.

The route queries the `Producto` model to retrieve all products that have been assigned to the current user, and passes these products to the `usuario/dashboard.html` template for rendering.

Returns:
    A rendered template for the user dashboard page, displaying the products assigned to the current user.
"""
@app.route('/usuario/dashboard')
@requiere_roles(RoleEnum.USUARIO.value)
def usuario_dashboard():
    productos_asignados = Producto.query.filter_by(usuario_asignado=current_user.id).all()
    return render_template('usuario/dashboard.html', productos=productos_asignados)


"""
Route handler for the professor dashboard page.

This route is responsible for rendering the professor dashboard page, which displays the products that are currently available for assignment, as well as the products that have been assigned to the currently authenticated professor.

The route is decorated with the `@requiere_roles` decorator, which ensures that only users with the `RoleEnum.PROFESOR.value` role can access this route.

The route queries the `Producto` model to retrieve all products that are currently available (i.e., have a status of 'Disponible'), as well as all products that have been assigned to the current professor. These products are then passed to the `profesor/dashboard.html` template for rendering.

Args:
    None

Returns:
    A rendered template for the professor dashboard page, displaying the available products and the products assigned to the current professor.
"""
@app.route('/profesor/dashboard')
@requiere_roles(RoleEnum.PROFESOR.value)
def profesor_dashboard():
    estado_disponible = Estado.query.filter_by(nombre='Disponible').first()
    if estado_disponible:
        productos_disponibles = Producto.query.filter_by(estado_id=estado_disponible.id).all()
    else:
        productos_disponibles = []
    productos_asignados = Producto.query.filter_by(usuario_asignado=current_user.id).all()
    return render_template('profesor/dashboard.html', 
                          productos_disponibles=productos_disponibles,
                          productos_asignados=productos_asignados)




"""
Route handler for the student dashboard page.

This route is responsible for rendering the student dashboard page, which displays the products that have been assigned to the currently authenticated student.

The route is decorated with the `@requiere_roles` decorator, which ensures that only users with the `RoleEnum.ALUMNO.value` role can access this route.

The route queries the `Producto` model to retrieve all products that have been assigned to the current student and have a status of 'Prestado', and passes these products to the `alumno/dashboard.html` template for rendering.

Returns:
    A rendered template for the student dashboard page, displaying the products assigned to the current student.
"""
@app.route('/alumno/dashboard')
@requiere_roles(RoleEnum.ALUMNO.value)
def alumno_dashboard():
    estado_prestado = Estado.query.filter_by(nombre='Prestado').first()
    if estado_prestado:
        productos_prestados = Producto.query.filter_by(
            usuario_asignado=current_user.id,
            estado_id=estado_prestado.id
        ).all()
    else:
        productos_prestados = []
    return render_template('alumno/dashboard.html', productos_prestados=productos_prestados)



"""
Route handler for the admin dashboard page.

This route is responsible for rendering the admin dashboard page, which displays 
various statistics and recent activities related to the application.

The route is decorated with the `@requiere_roles` decorator, which ensures that 
only users with the `RoleEnum.ADMIN.value` or `RoleEnum.PROFESOR.value` roles can access this route.

The route queries the `Producto`, `Usuario`, `Auditoria`, and `Movimiento` models to 
retrieve data for the dashboard, including the total number of products, users, movements, 
and audits, as well as the latest 5 audits and movements. This data is then passed to the 
`admin/dashboard.html` template for rendering.

Args:
    None

Returns:
    A rendered template for the admin dashboard page, displaying the application statistics and recent activities.
"""
@app.route('/admin/dashboard')
@requiere_roles(RoleEnum.ADMIN.value, RoleEnum.PROFESOR.value)
def admin_dashboard():
    productos = Producto.query.all()
    usuarios = Usuario.query.all()
    auditorias = Auditoria.query.order_by(Auditoria.fecha_hora.desc()).limit(5).all()
    movimientos = Movimiento.query.order_by(Movimiento.fecha_hora.desc()).limit(5).all()
    
    # Get latest activities
    actividades = []
    for auditoria in auditorias:
        actividades.append(f"{auditoria.accion} por {auditoria.usuario.nombre_usuario}")
    
    # Prepare dashboard stats
    stats = {
        'total_productos': len(productos),
        'total_usuarios': len(usuarios),
        'total_movimientos': Movimiento.query.count(),
        'total_auditorias': Auditoria.query.count()
    }
    
    return render_template('admin/dashboard.html', 
                          actividades=actividades,
                          stats=stats,
                          ultimos_movimientos=movimientos,
                          productos=productos)  # Pass productos to the template


"""
Route handler for the admin users page.

This route is responsible for rendering the admin users page, which displays a list of all registered users.

The route is decorated with the `@requiere_roles` decorator, which ensures that only users with the `RoleEnum.ADMIN.value` role can access this route.

The route queries the `Usuario` model to retrieve all registered users, and passes this data to the `admin/usuarios.html` template for rendering.

Args:
    None

Returns:
    A rendered template for the admin users page, displaying a list of all registered users.
"""
@app.route('/admin/usuarios')
@requiere_roles(RoleEnum.ADMIN.value)
def lista_usuarios():
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)


"""
Route handler for the admin audit log page.

This route is responsible for rendering the admin audit log page, which displays 
a list of all auditing events recorded in the system.

The route is decorated with the `@requiere_roles` decorator, which ensures that 
only users with the `RoleEnum.ADMIN.value` role can access this route.

The route queries the `Auditoria` model to retrieve all auditing events, ordered 
by the `fecha_hora` field in descending order, and passes this data to the 
`admin/auditoria.html` template for rendering.

Args:
    None

Returns:
    A rendered template for the admin audit log page, displaying a list of all auditing events.
"""
@app.route('/admin/auditoria')
@requiere_roles(RoleEnum.ADMIN.value)
def lista_auditoria():
    auditorias = Auditoria.query.order_by(Auditoria.fecha_hora.desc()).all()
    return render_template('admin/auditoria.html', auditorias=auditorias)

if __name__ == '__main__':
    app.run(debug=True)



"""
    Form for requesting a product.
    
    This form allows users to request a product by providing a reason for the request
    and selecting the desired duration of the loan (1 week, 2 weeks, or 1 month).
"""
class SolicitudProductoForm(FlaskForm):
    razon = TextAreaField('Razón de la solicitud', validators=[DataRequired()])
    duracion_dias = SelectField('Duración del préstamo', 
        choices=[(7, '1 semana'), (14, '2 semanas'), (30, '1 mes')],
        coerce=int,
        validators=[DataRequired()])
    submit = SubmitField('Solicitar Producto')


"""
Route handler for the product request page.

This route is responsible for rendering the product request page, which allows users to request a product 
by providing a reason for the request and selecting the desired duration of the loan (1 week, 2 weeks, or 1 month).

The route is decorated with the `@login_required` decorator, which ensures that only authenticated users can access this route.

The route first retrieves the requested product from the database using the `producto_id` parameter. 
It then creates an instance of the `SolicitudProductoForm` form and passes it to the template for rendering.

If the form is submitted and validated, the route checks if the product is currently available. 
If so, it updates the product's status to 'Prestado' (Loaned), sets the user who requested the product, and calculates 
the due date based on the selected loan duration. It then creates a new `Movimiento` (Movement) record to track the status
 change and a `Notificacion` (Notification) to inform other users about the request.

Finally, the route commits the changes to the database and redirects the user to the professor dashboard.

Args:
    producto_id (int): The ID of the product being requested.

Returns:
    A rendered template for the product request page, displaying the product information and the request form.
"""
@app.route('/solicitar-producto/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def solicitar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    form = SolicitudProductoForm()
    
    if form.validate_on_submit():
        if producto.estado.nombre == 'Disponible':
            producto.usuario_asignado = current_user.id
            producto.fecha_asignacion = datetime.utcnow()
            producto.fecha_devolucion = datetime.utcnow() + timedelta(days=form.duracion_dias.data)
            producto.estado = Estado.query.filter_by(nombre='Prestado').first()
            
            movimiento = Movimiento(
                producto_id=producto.id,
                usuario_id=current_user.id,
                estado_anterior='Disponible',
                estado_nuevo='Prestado',
                detalle=form.razon.data
            )
            
            notificacion = Notificacion(
                mensaje=f'Producto {producto.nombre} solicitado por {current_user.nombre_usuario} por {form.duracion_dias.data} días',
                usuario_id=None
            )
            
            db.session.add(movimiento)
            db.session.add(notificacion)
            db.session.commit()
            
            flash('Producto solicitado exitosamente', 'success')
            return redirect(url_for('profesor_dashboard'))
            
    return render_template('solicitar_producto.html', producto=producto, form=form)




"""
Handles the process of returning a product by the user who has it assigned.

This route is responsible for updating the product's status to 'Disponible' (Available), removing the assigned user, and setting the return date. It also creates a new `Movimiento` (Movement) record to track the status change and a `Notificacion` (Notification) to inform other users about the return.

Finally, the route commits the changes to the database and redirects the user to the professor dashboard.

Args:
    producto_id (int): The ID of the product being returned.

Returns:
    A rendered template for the product return page, displaying the product information.
"""
@app.route('/devolver-producto/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def devolver_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    if request.method == 'POST':
        estado_anterior = producto.estado.nombre
        producto.usuario_asignado = None
        producto.fecha_devolucion = datetime.utcnow()
        producto.estado = Estado.query.filter_by(nombre='Disponible').first()
        
        movimiento = Movimiento(
            producto_id=producto.id,
            usuario_id=current_user.id,
            estado_anterior=estado_anterior,
            estado_nuevo='Disponible'
        )
        
        notificacion = Notificacion(
            mensaje=f'Producto {producto.nombre} devuelto por {current_user.nombre_usuario}',
            usuario_id=None
        )
        
        db.session.add(movimiento)
        db.session.add(notificacion)
        db.session.commit()
        
        flash('Producto devuelto exitosamente', 'success')
        return redirect(url_for('profesor_dashboard'))
        
    return render_template('devolver_producto.html', producto=producto)


"""
Retrieves the history of movements (Movimiento) for a specific product (Producto) 
and renders the 'historial_producto.html' template with the product and movement data.

Args:
    producto_id (int): The ID of the product to retrieve the history for.

Returns:
    A rendered template for the product history page, displaying the product 
    information and its movement history.
"""
@app.route('/producto/<int:producto_id>/historial')
@login_required
def historial_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    movimientos = Movimiento.query.filter_by(producto_id=producto_id).order_by(Movimiento.fecha_hora.desc()).all()
    return render_template('historial_producto.html', producto=producto, movimientos=movimientos)



from flask import request, render_template
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime, timedelta
from models import Producto, Estado, Movimiento, Usuario
from decorators import requiere_roles
from app import app, db

# app.py

from decorators import requiere_roles
from flask import Flask, render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import login_required, current_user
from models import Producto, Estado, Movimiento, Usuario, RoleEnum
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from extensions import db  # Asegúrate de que 'extensions.py' está correctamente configurado

"""
Renders the 'reportes.html' template with various statistics and 
analytics related to products and their movements.

This route is accessible only to users with the 'ADMIN' 
or 'PROFESOR' role, and requires the user to be logged in.

The route retrieves the filter parameters (start date, end date, 
and state filter) using the `get_filter_parameters()` function, 
and then obtains the product statistics (available and borrowed products)
 using the `get_product_statistics()` function.

Additional statistics and analytics are calculated, such as total products, 
movements per user, movements per day, most frequent products, average loan duration, 
most popular products, and the latest movements.

All of this data is then passed to the 'reportes.html' template for rendering.
"""
@app.route('/reportes', methods=['GET'])
@login_required
@requiere_roles(RoleEnum.ADMIN.value, RoleEnum.PROFESOR.value)
def reportes():
    app.logger.debug("Accediendo a la ruta /reportes")

    # Obtener parámetros de filtro
    fecha_inicio, fecha_fin, estado_filter = get_filter_parameters()

    # Obtener estadísticas de productos
    productos_disponibles, productos_prestados = get_product_statistics(estado_filter)

    # Calcular estadísticas adicionales
    stats = calculate_stats(productos_disponibles, productos_prestados)

    # Obtener datos analíticos
    movimientos_por_usuario = get_movimientos_por_usuario()
    movimientos_por_dia = get_movimientos_por_dia(fecha_inicio, fecha_fin)
    productos_frecuentes = get_productos_frecuentes()
    tiempo_prestamo_promedio = 0  # Temporary fix until fecha_hora_prestamo is added
    productos_populares = get_productos_populares()
    ultimos_movimientos = get_ultimos_movimientos()

    app.logger.debug(f"Estadísticas: {stats}")

    # Renderizar la plantilla con el contexto
    return render_template(
        'reportes.html',
        stats=stats,
        productos_disponibles=productos_disponibles,
        productos_prestados=productos_prestados,
        movimientos_por_usuario=movimientos_por_usuario,
        movimientos_por_dia=movimientos_por_dia,
        productos_frecuentes=productos_frecuentes,
        tiempo_prestamo_promedio=tiempo_prestamo_promedio,
        productos_populares=productos_populares,
        ultimos_movimientos=ultimos_movimientos,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estados=Estado.query.all(),
        estado_filter=estado_filter
    )


"""
Retrieve and set default filter parameters.
    
Returns:
    tuple: A tuple containing the start date, end date, and state filter.
    
"""
"""Retrieve and set default filter parameters."""
def get_filter_parameters():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    estado_filter = request.args.get('estado', 'todos')

    if not fecha_inicio:
        fecha_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not fecha_fin:
        fecha_fin = datetime.now().strftime('%Y-%m-%d')

    return fecha_inicio, fecha_fin, estado_filter


"""
Obtain product statistics based on the state filter.
    
    Args:
        estado_filter (str): The state filter to apply. If 'todos', retrieve statistics for both available and loaned products.
    
    Returns:
        tuple: A tuple containing the number of available products and the number of loaned products.
"""    
def get_product_statistics(estado_filter):
        """Obtener estadísticas de productos basadas en el filtro de estado."""
    if estado_filter == 'todos':
        estado_disponible = Estado.query.filter_by(nombre='Disponible').first()
        estado_prestado = Estado.query.filter_by(nombre='Prestado').first()

        if not estado_disponible or not estado_prestado:
            app.logger.error("Faltan estados necesarios en la tabla 'Estado'.")
            flash("Error interno: faltan estados necesarios.", "danger")
            return 0, 0

        productos_disponibles = Producto.query.filter_by(estado_id=estado_disponible.id).count()
        productos_prestados = Producto.query.filter_by(estado_id=estado_prestado.id).count()
    else:
        estado = Estado.query.filter_by(nombre=estado_filter).first()
        if not estado:
            app.logger.error(f"Estado '{estado_filter}' no encontrado en la tabla 'Estado'.")
            flash(f"Estado '{estado_filter}' no encontrado.", "warning")
            productos_disponibles = 0
            productos_prestados = 0
        else:
            productos_disponibles = Producto.query.filter_by(estado_id=estado.id).count()
            productos_prestados = 0  # Ajusta la lógica según sea necesario

    return productos_disponibles, productos_prestados


"""
Calculate and return statistics about the available and loaned products.
    
    Args:
        productos_disponibles (int): The number of available products.
        productos_prestados (int): The number of loaned products.
    
    Returns:
        dict: A dictionary containing the total number of products, the number of available products, and the number of loaned products.
"""
def calculate_stats(productos_disponibles, productos_prestados):
        """Calculate and return statistics."""
    total_productos = Producto.query.count()
    return {
        'total_productos': total_productos,
        'productos_disponibles': productos_disponibles,
        'productos_prestados': productos_prestados
    }


"""
Get movements grouped by user.
    
    Returns:
        list: A list of tuples, where each tuple contains the user's name and the count of movements for that user.

"""
def get_movimientos_por_usuario():
        """Get movements grouped by user."""
    return db.session.query(
        Usuario.nombre_usuario,
        func.count(Movimiento.id)
    ).join(Movimiento).group_by(Usuario.id).all()


"""
    Get movements grouped by day.
    
    Args:
        fecha_inicio (datetime): The start date for the date range.
        fecha_fin (datetime): The end date for the date range.
    
    Returns:
        list: A list of tuples, where each tuple contains the date (in the format 'YYYY-MM-DD') and the count of movements for that day.
"""
def get_movimientos_por_dia(fecha_inicio, fecha_fin):
        """Get movements grouped by day."""
    return db.session.query(
        func.strftime('%Y-%m-%d', Movimiento.fecha_hora),
        func.count(Movimiento.id)
    ).filter(
        Movimiento.fecha_hora >= fecha_inicio,
        Movimiento.fecha_hora <= fecha_fin
    ).group_by(func.strftime('%Y-%m-%d', Movimiento.fecha_hora)).all()


"""
    Get the most frequently moved products.
    
    Returns:
        list: A list of tuples, where each tuple contains a Producto object and 
        the total count of movements for that product. The list is ordered by the
         total count in descending order, and limited to the top 5 products.
"""


"""
    Get the most frequently moved products.
    
    Returns:
        list: A list of tuples, where each tuple contains a Producto object and 
        the total count of movements for that product. The list is ordered by the
         total count in descending order, and limited to the top 5 products.
"""
def get_productos_frecuentes():
        """Get the most frequently moved products."""
    return db.session.query(
        Producto, func.count(Movimiento.id).label('total')
    ).join(Movimiento).group_by(Producto.id).order_by(func.count(Movimiento.id).desc()).limit(5).all()



"""
        Calculate the average loan duration for products.
    
        Returns:
            list: A list of tuples, where each tuple contains 
            the product name and the average number of days the 
            product was loaned out. The list is ordered by the 
            average loan duration in descending order.
"""
def get_tiempo_prestamo_promedio():
        """Calculate the average loan duration for products."""
    return db.session.query(
        Producto.nombre,
        func.avg(func.julianday(Movimiento.fecha_hora_devolucion) - func.julianday(Movimiento.fecha_hora_prestamo)).label('dias_promedio')
    ).join(Movimiento).filter(Movimiento.fecha_hora_devolucion != None).group_by(Producto.id).all()


"""
        Get the most popular products based on movements.
        
        Returns:
            list: A list of tuples, where each tuple contains the product name and the 
            total count of movements for that product. The list is ordered by the total 
            count in descending order, and limited to the top 5 products.
"""
def get_productos_populares():

        """Get the most popular products based on movements."""
    return db.session.query(
        Producto.nombre, func.count(Movimiento.id).label('total')
    ).join(Movimiento).group_by(Producto.id).order_by(func.count(Movimiento.id).desc()).limit(5).all()


"""
        Get the most recent movements.
    
        Returns:
            list: A list of the 10 most recent Movimiento objects, ordered by the
            fecha_hora attribute in descending order.
"""
def get_ultimos_movimientos():

        """Get the most recent movements."""
    return Movimiento.query.order_by(Movimiento.fecha_hora.desc()).limit(10).all()

from openpyxl import Workbook
from datetime import timedelta
import json
from io import BytesIO

"""
Export movements report in various formats.

This function handles the export of the movements report in different formats, such as Excel, JSON, and CSV. It retrieves the movements from the database, orders them by the most recent, and then generates the appropriate output based on the requested format.

Args:
    formato (str): The requested format for the report, can be 'excel', 'json', or 'csv'.

Returns:
    Response: A response object containing the generated report in the requested format, with the appropriate content type and headers.
"""
@app.route('/reportes/exportar/<formato>')
@requiere_roles(RoleEnum.ADMIN.value)
def exportar_reportes(formato):
    movimientos = Movimiento.query.order_by(Movimiento.fecha_hora.desc()).all()
    
    if formato == 'excel':
        wb = Workbook()
        ws = wb.active
        ws.append(['Fecha', 'Producto', 'Usuario', 'Estado Anterior', 'Estado Nuevo'])
        
        for mov in movimientos:
            ws.append([
                mov.fecha_hora.strftime('%Y-%m-%d %H:%M'),
                mov.producto.nombre,
                mov.usuario.nombre_usuario,
                mov.estado_anterior,
                mov.estado_nuevo
            ])
            
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename=reporte_movimientos.xlsx'}
        )
        
    elif formato == 'json':
        data = [{
            'fecha': mov.fecha_hora.strftime('%Y-%m-%d %H:%M'),
            'producto': mov.producto.nombre,
            'usuario': mov.usuario.nombre_usuario,
            'estado_anterior': mov.estado_anterior,
            'estado_nuevo': mov.estado_nuevo
        } for mov in movimientos]
        
        return jsonify(data)
    
    elif formato == 'csv':
        from io import StringIO
        import csv
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Fecha', 'Producto', 'Usuario', 'Estado Anterior', 'Estado Nuevo'])
        
        for mov in movimientos:
            writer.writerow([
                mov.fecha_hora.strftime('%Y-%m-%d %H:%M'),
                mov.producto.nombre,
                mov.usuario.nombre_usuario,
                mov.estado_anterior,
                mov.estado_nuevo
            ])
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=reporte_movimientos.csv'}
        )

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO


"""
Exports a PDF report of all product movements, including the date, product, user, and previous and new states.

This function requires the ADMIN role to access. It generates a PDF report using the ReportLab library, with a table displaying the movement details.

The report is downloaded as an attachment with the filename "reporte_movimientos.pdf".
"""
@app.route('/reportes/exportar/pdf')
@requiere_roles(RoleEnum.ADMIN.value)
def exportar_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    elements.append(Paragraph("Reporte de Movimientos", styles['Heading1']))
    elements.append(Spacer(1, 12))
    
    # Table data
    data = [['Fecha', 'Producto', 'Usuario', 'Estado Anterior', 'Estado Nuevo']]
    movimientos = Movimiento.query.order_by(Movimiento.fecha_hora.desc()).all()
    
    for mov in movimientos:
        data.append([
            mov.fecha_hora.strftime('%Y-%m-%d %H:%M'),
            mov.producto.nombre,
            mov.usuario.nombre_usuario,
            mov.estado_anterior,
            mov.estado_nuevo
        ])
    
    # Create table
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(t)
    doc.build(elements)
    
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=reporte_movimientos.pdf'}
    )



"""
    Initializes the required product states in the database.
    
    This function checks if the required product states (Disponible, Prestado, Reparación, and Uso) 
    exist in the database. If any of the required states are missing, it creates them with the 
    specified name, description, color, and order.
    
    The function is typically called during application initialization or setup to ensure the 
    necessary product states are available in the system.
    
"""
def initialize_estados():
        required_estados = [
        {'nombre': 'Disponible', 'descripcion': 'Producto disponible para uso', 'color': '#28a745', 'orden': 1},
        {'nombre': 'Prestado', 'descripcion': 'Producto prestado temporalmente', 'color': '#ffc107', 'orden': 2},
        {'nombre': 'Reparación', 'descripcion': 'Producto en mantenimiento o reparación', 'color': '#dc3545', 'orden': 3},
        {'nombre': 'Uso', 'descripcion': 'Producto actualmente en uso', 'color': '#17a2b8', 'orden': 4}
    ]
    
    for estado_data in required_estados:
        estado = Estado.query.filter_by(nombre=estado_data['nombre']).first()
        if not estado:
            nuevo_estado = Estado(
                nombre=estado_data['nombre'],
                descripcion=estado_data['descripcion'],
                color=estado_data['color'],
                orden=estado_data['orden']
            )
            db.session.add(nuevo_estado)
    
    db.session.commit()
