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

@app.route('/admin/productos')
@requiere_roles(RoleEnum.ADMIN.value)
def lista_productos():
    productos = Producto.query.all()
    return render_template('admin/lista_productos.html', productos=productos)

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

def actualizar_estado_producto(producto, estado_nuevo_id):
    estado_anterior = producto.estado.nombre
    estado_nuevo = Estado.query.get(estado_nuevo_id)
    producto.estado = estado_nuevo
    db.session.commit()

    registrar_auditoria(producto, estado_anterior, estado_nuevo)
    registrar_movimiento(producto, estado_anterior, estado_nuevo)
    crear_notificacion_si_necesario(producto, estado_nuevo)

def registrar_auditoria(producto, estado_anterior, estado_nuevo):
    auditoria = Auditoria(
        usuario_id=current_user.id,
        accion='Cambio de estado',
        detalle=f'Producto {producto.nombre} de {estado_anterior} a {estado_nuevo.nombre}'
    )
    db.session.add(auditoria)

def registrar_movimiento(producto, estado_anterior, estado_nuevo):
    movimiento = Movimiento(
        producto_id=producto.id,
        usuario_id=current_user.id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo.nombre
    )
    db.session.add(movimiento)

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
    contrasena = PasswordField(
        'Contraseña',
        validators=[DataRequired(), Length(min=6)]
    )
    submit = SubmitField('Iniciar Sesión')

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

@app.route('/logout')
@login_required
def logout():
    """
    Route handler for user logout.
    """
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))
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
@app.route('/usuario/dashboard')
@requiere_roles(RoleEnum.USUARIO.value)
def usuario_dashboard():
    productos_asignados = Producto.query.filter_by(usuario_asignado=current_user.id).all()
    return render_template('usuario/dashboard.html', productos=productos_asignados)

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


@app.route('/admin/usuarios')
@requiere_roles(RoleEnum.ADMIN.value)
def lista_usuarios():
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/admin/auditoria')
@requiere_roles(RoleEnum.ADMIN.value)
def lista_auditoria():
    auditorias = Auditoria.query.order_by(Auditoria.fecha_hora.desc()).all()
    return render_template('admin/auditoria.html', auditorias=auditorias)

if __name__ == '__main__':
    app.run(debug=True)

class SolicitudProductoForm(FlaskForm):
    razon = TextAreaField('Razón de la solicitud', validators=[DataRequired()])
    duracion_dias = SelectField('Duración del préstamo', 
        choices=[(7, '1 semana'), (14, '2 semanas'), (30, '1 mes')],
        coerce=int,
        validators=[DataRequired()])
    submit = SubmitField('Solicitar Producto')

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

def get_filter_parameters():
    """Retrieve and set default filter parameters."""
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    estado_filter = request.args.get('estado', 'todos')

    if not fecha_inicio:
        fecha_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not fecha_fin:
        fecha_fin = datetime.now().strftime('%Y-%m-%d')

    return fecha_inicio, fecha_fin, estado_filter
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

def calculate_stats(productos_disponibles, productos_prestados):
    """Calculate and return statistics."""
    total_productos = Producto.query.count()
    return {
        'total_productos': total_productos,
        'productos_disponibles': productos_disponibles,
        'productos_prestados': productos_prestados
    }
def get_movimientos_por_usuario():
    """Get movements grouped by user."""
    return db.session.query(
        Usuario.nombre_usuario,
        func.count(Movimiento.id)
    ).join(Movimiento).group_by(Usuario.id).all()

def get_movimientos_por_dia(fecha_inicio, fecha_fin):
    """Get movements grouped by day."""
    return db.session.query(
        func.strftime('%Y-%m-%d', Movimiento.fecha_hora),
        func.count(Movimiento.id)
    ).filter(
        Movimiento.fecha_hora >= fecha_inicio,
        Movimiento.fecha_hora <= fecha_fin
    ).group_by(func.strftime('%Y-%m-%d', Movimiento.fecha_hora)).all()

def get_productos_frecuentes():
    """Get the most frequently moved products."""
    return db.session.query(
        Producto, func.count(Movimiento.id).label('total')
    ).join(Movimiento).group_by(Producto.id).order_by(func.count(Movimiento.id).desc()).limit(5).all()

def get_tiempo_prestamo_promedio():
    """Calculate the average loan duration for products."""
    return db.session.query(
        Producto.nombre,
        func.avg(func.julianday(Movimiento.fecha_hora_devolucion) - func.julianday(Movimiento.fecha_hora_prestamo)).label('dias_promedio')
    ).join(Movimiento).filter(Movimiento.fecha_hora_devolucion != None).group_by(Producto.id).all()

def get_productos_populares():
    """Get the most popular products based on movements."""
    return db.session.query(
        Producto.nombre, func.count(Movimiento.id).label('total')
    ).join(Movimiento).group_by(Producto.id).order_by(func.count(Movimiento.id).desc()).limit(5).all()

def get_ultimos_movimientos():
    """Get the most recent movements."""
    return Movimiento.query.order_by(Movimiento.fecha_hora.desc()).limit(10).all()

from openpyxl import Workbook
from datetime import timedelta
import json
from io import BytesIO

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
