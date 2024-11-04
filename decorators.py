# decorators.py

from functools import wraps
from flask import flash, redirect, url_for, current_app
from flask_login import current_user
from models import RoleEnum  # Asegúrate de que la ruta de importación es correcta

def requiere_roles(*roles):
    """
    Decorador para restringir el acceso a vistas según los roles de usuario.

    :param roles: Roles permitidos para acceder a la vista (como cadenas de texto).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Añadir logging para depuración
            current_app.logger.debug(f"Usuario: {current_user.nombre_usuario}, Rol: {current_user.rol.value}")
            if not hasattr(current_user, 'rol') or current_user.rol.value not in roles:
                flash("No tienes permiso para acceder a esta página.", "danger")
                current_app.logger.debug("Redirigiendo al usuario debido a falta de permisos.")
                return redirect(url_for('inicio'))  # Asegúrate de que 'inicio' es una ruta válida
            return f(*args, **kwargs)
        return decorated_function
    return decorator
