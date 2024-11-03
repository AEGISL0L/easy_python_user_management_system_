CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
CREATE TABLE estado (
	id INTEGER NOT NULL, 
	nombre VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);
CREATE TABLE usuario (
	id INTEGER NOT NULL, 
	nombre_usuario VARCHAR(150) NOT NULL, 
	"contraseña" VARCHAR(150) NOT NULL, 
	rol VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre_usuario)
);
CREATE TABLE producto (
	id INTEGER NOT NULL, 
	nombre VARCHAR(150) NOT NULL, 
	descripcion TEXT, 
	estado_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(estado_id) REFERENCES estado (id)
);
CREATE TABLE auditoria (
	id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	accion VARCHAR(150) NOT NULL, 
	fecha_hora DATETIME NOT NULL, 
	detalles TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_auditoria_usuario FOREIGN KEY(usuario_id) REFERENCES usuario (id)
);
CREATE TABLE notificacion (
	id INTEGER NOT NULL, 
	mensaje VARCHAR(250) NOT NULL, 
	fecha_hora DATETIME NOT NULL, 
	leida BOOLEAN, 
	usuario_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_notificacion_usuario FOREIGN KEY(usuario_id) REFERENCES usuario (id)
);
CREATE TABLE movimiento (
	id INTEGER NOT NULL, 
	producto_id INTEGER NOT NULL, 
	estado_anterior_id INTEGER NOT NULL, 
	estado_nuevo_id INTEGER NOT NULL, 
	fecha_hora DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_movimiento_producto FOREIGN KEY(producto_id) REFERENCES producto (id), 
	CONSTRAINT fk_movimiento_estado_anterior FOREIGN KEY(estado_anterior_id) REFERENCES estado (id), 
	CONSTRAINT fk_movimiento_estado_nuevo FOREIGN KEY(estado_nuevo_id) REFERENCES estado (id)
);
