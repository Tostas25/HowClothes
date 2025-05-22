from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from PIL import Image
import os
from sklearn.cluster import KMeans
import numpy as np

app = Flask(__name__, instance_relative_config=True)
app.secret_key = 'Tatimami2005'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'usuarios.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#Conf enviar correos
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'howclothesoficial@gmail.com'
app.config['MAIL_PASSWORD'] = 'bpcn vslk hkid cyqk'

mail = Mail(app)
db = SQLAlchemy(app)
serializer = URLSafeTimedSerializer(app.secret_key)

#BBDD
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    contraseña = db.Column(db.String(200), nullable=False)
    confirmado = db.Column(db.Boolean, default=False)

#Token 
def generate_confirmation_token(email):
    return serializer.dumps(email, salt='email-confirmation-salt')

def confirm_token(token, expiration=3600):
    try:
        return serializer.loads(token, salt='email-confirmation-salt', max_age=expiration)
    except:
        return False

def generate_reset_token(email):
    return serializer.dumps(email, salt='password-reset-salt')

def confirm_reset_token(token, expiration=3600):
    try:
        return serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except:
        return False

#Envio correo
def send_confirmation_email(user_email):
    token = generate_confirmation_token(user_email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = f"""
    <p>Hola, por favor confirma tu correo haciendo click en el siguiente enlace:</p>
    <a href="{confirm_url}">Confirmar Email</a>
    """
    msg = Message("Confirma tu correo en How Clothes", sender=app.config['MAIL_USERNAME'], recipients=[user_email])
    msg.html = html
    mail.send(msg)

def send_password_reset_email(user_email):
    token = generate_reset_token(user_email)
    reset_url = url_for('reset_password', token=token, _external=True)
    html = f"""
    <p>Haz click en el siguiente enlace para restablecer tu contraseña:</p>
    <a href="{reset_url}">Restablecer Contraseña</a>
    """
    msg = Message("Restablece tu contraseña en How Clothes", sender=app.config['MAIL_USERNAME'], recipients=[user_email])
    msg.html = html
    mail.send(msg)

#Colores
colores_rgb = {
    "amarillo": [255, 255, 0], "verde limón": [192, 255, 0], "verde": [0, 128, 0],
    "turquesa": [64, 224, 208], "azul": [0, 0, 255], "azul violeta": [138, 43, 226],
    "violeta": [148, 0, 211], "vino": [128, 0, 64], "rojo": [255, 0, 0], "rojo-naranja": [255, 69, 0],
    "naranja": [255, 140, 0], "amarillo-naranja": [255, 200, 0], "lila": [200, 162, 200],
    "café": [139, 69, 19], "gris": [128, 128, 128], "negro": [0, 0, 0], "blanco": [255, 255, 255],
    "amarillo claro": [255, 255, 153], "verde claro": [144, 238, 144], "verde oscuro": [0, 100, 0],
    "turquesa claro": [175, 238, 238], "azul claro": [173, 216, 230], "azul oscuro": [0, 0, 139],
    "violeta claro": [221, 160, 221], "violeta oscuro": [75, 0, 130],
    "rosa": [255, 105, 180], "rosado": [255, 182, 193], "nude": [210, 180, 140],
}

colores_calidos = {"amarillo", "amarillo claro", "amarillo-naranja", "naranja", "rojo", "rojo-naranja", "rosado", "rosa", "vino", "nude", "café"}
colores_frios = {"verde", "verde claro", "verde oscuro", "verde limón", "turquesa", "turquesa claro",
                 "azul", "azul claro", "azul oscuro", "azul violeta", "violeta", "violeta claro", "violeta oscuro", "lila"}
neutros = {"negro", "blanco", "gris"}

def obtener_colores_predominantes(img):
    img = img.resize((img.width // 5, img.height // 5))
    img_array = np.array(img).reshape((-1, 3))
    kmeans = KMeans(n_clusters=5, random_state=42).fit(img_array)
    return kmeans.cluster_centers_

def rgb_to_nombre_color(rgb):
    return min(colores_rgb, key=lambda nombre: np.linalg.norm(np.array(rgb) - np.array(colores_rgb[nombre])))

def analizar_colores(colores):
    nombres = [rgb_to_nombre_color(color) for color in colores]
    unicos = list(set(nombres))
    cant_calidos = sum(1 for c in unicos if c in colores_calidos)
    cant_frios = sum(1 for c in unicos if c in colores_frios)
    cant_neutros = sum(1 for c in unicos if c in neutros)
    if len(unicos) == 1:
        return True
    if len(unicos) >= 5:
        return False
    if cant_calidos > 0 and cant_frios > 0 and cant_neutros == 0:
        return False
    if cant_calidos > 2 and cant_frios > 1:
        return False
    if cant_frios > 2 and cant_calidos > 1:
        return False
    return True

#Rutas
@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    error = None
    if request.method == 'POST':
        nombre = request.form['username']
        email = request.form['email']
        contraseña = request.form['password']
        confirmar_contraseña = request.form['confirm_password']

        if contraseña != confirmar_contraseña:
            error = "⚠ Las contraseñas no coinciden."
        elif 'politicas' not in request.form:
            error = "⚠ Debes aceptar las políticas."
        elif Usuario.query.filter_by(nombre=nombre).first():
            error = "⚠ El nombre de usuario ya está registrado."
        elif Usuario.query.filter_by(email=email).first():
            error = "⚠ El correo electrónico ya está registrado."
        else:
            hash_pw = generate_password_hash(contraseña)
            usuario = Usuario(nombre=nombre, email=email, contraseña=hash_pw)
            db.session.add(usuario)
            db.session.commit()
            send_confirmation_email(email)
            flash("Registro exitoso. Revisa tu correo para confirmar tu cuenta.", "success")
            return redirect(url_for('login'))

    return render_template('registro.html', error=error)

@app.route('/confirm/<token>')
def confirm_email(token):
    email = confirm_token(token)
    if not email:
        flash('El enlace de confirmación no es válido o expiró.', 'danger')
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(email=email).first()
    if usuario:
        if not usuario.confirmado:
            usuario.confirmado = True
            db.session.commit()
            flash('¡Correo confirmado con éxito! Ya puedes iniciar sesión.', 'success')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        nombre = request.form['nombre']
        contraseña = request.form['contraseña']
        usuario = Usuario.query.filter_by(nombre=nombre).first()

        if usuario and check_password_hash(usuario.contraseña, contraseña):
            if not usuario.confirmado:
                error = "⚠ Debes confirmar tu correo."
            else:
                session['usuario'] = usuario.nombre
                return redirect(url_for('dashboard'))
        else:
            error = "⚠ Usuario o contraseña incorrectos."
    return render_template('login.html', error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    resultado = None
    if request.method == 'POST':
        foto = request.files['foto']
        if foto:
            img = Image.open(foto)
            colores = obtener_colores_predominantes(img)
            resultado = "✅ ¡Los colores combinan!" if analizar_colores(colores) else "❌ Los colores no combinan."
    return render_template('dashboard.html', resultado=resultado)

@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    error = None
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        usuario = Usuario.query.filter_by(nombre=nombre, email=email).first()
        if usuario:
            send_password_reset_email(email)
            flash("Se ha enviado un correo para restablecer tu contraseña.", "info")
            return redirect(url_for('login'))
        else:
            error = "⚠ Usuario o correo no encontrado."
    return render_template('recuperar.html', error=error)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirm_reset_token(token)
    if not email:
        flash('El enlace para restablecer la contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        nueva = request.form['password']
        confirmar = request.form['confirm_password']
        if nueva != confirmar:
            error = "⚠ Las contraseñas no coinciden."
        else:
            usuario.contraseña = generate_password_hash(nueva)
            db.session.commit()
            flash('Contraseña actualizada.', 'success')
            return redirect(url_for('login'))

    return render_template('reset_password.html', error=error)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/politicas')
def politicas():
    return render_template('politicas.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

if __name__ == '__main__':
    os.makedirs(app.instance_path, exist_ok=True)
    if not os.path.exists(os.path.join(app.instance_path, 'usuarios.db')):
        with app.app_context():
            db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)