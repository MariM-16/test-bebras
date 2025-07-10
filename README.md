# TEST BEBRAS

## 📝 Descripción del Proyecto

Este es un proyecto de aplicación web desarrollado con Django que gestiona la creación, asignación y realización de pruebas (exámenes), con un enfoque en preguntas de tipo Test Bebras. Incluye funcionalidades para la administración de usuarios, la gestión de preguntas y habilidades, la configuración de exámenes con distintas lógicas de puntuación, y la visualización de resultados.

### Características Principales:

* **Gestión de Preguntas:** Creación de preguntas con diferentes formatos (selección múltiple, texto, numérico).
* **Habilidades:** Asociación de preguntas a habilidades específicas.
* **Exámenes Personalizables:** Configuración de tiempo máximo, tipo de penalización y puntos por dificultad.
* **Autenticación:** Soporte para autenticación de usuario local y con Google OAuth (a través de `django-allauth`).
* **Almacenamiento en la Nube:** Uso de Google Cloud Storage para el manejo de archivos multimedia y estáticos.
* **Envío de Correos:** Configuración para el envío de notificaciones vía SMTP.

## 🚀 Tecnologías Utilizadas

Este proyecto fue construido usando las siguientes tecnologías clave:

* **Python 3.10+** como lenguaje de programación principal.
* **Django 2.0+** como el framework web principal.
* **Base de Datos:**
    * **SQLite** para desarrollo local.
* **Servicios Cloud:**
    * [Google Cloud Storage](https://cloud.google.com/storage) para almacenamiento de archivos.
    * [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2) para autenticación social.

## 🛠️ Configuración e Instalación (Desarrollo Local)

Sigue estos pasos para configurar el proyecto en tu máquina local.

### Pasos

1.  **Clonar el Repositorio:**
    ```bash
    git clone [https://github.com/marim-16/test-bebras.git](https://github.com/marim-16/test-bebras.git)
    cd test-bebras/pdt2 
    ```

2.  **Crear y Activar un Entorno Virtual:**
    Es altamente recomendable usar un entorno virtual para aislar las dependencias del proyecto.
    ```bash
    python3 -m venv venv
    source venv/bin/activate 
    # venv\Scripts\activate  
    # venv\Scripts\Activate.ps1 
    ```

3.  **Instalar Dependencias:**
    Instala todas las librerías necesarias utilizando `pip` y el archivo `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno (`.env`):**
    Crea un archivo llamado `.env` en la raíz del proyecto (`test-bebras/pdt2/.env`) con la siguiente estructura. **¡No compartas este archivo públicamente!**

    ```ini
    # .env
    WEB_CONCURRENCY=2 # Para Heroku, o puedes omitirlo para desarrollo local
    SECRET_KEY=TU_CLAVE_SECRETA_DE_DJANGO_AQUI # Genera una nueva y compleja
    DEBUG=True # Cambiar a False en producción

    # Google Cloud Storage
    GS_BUCKET_NAME=tu_nombre_de_bucket_gcs
    GS_CREDENTIALS_FILE=tu_archivo_credenciales_gcs.json # Ejemplo: brave-watch-458608-a4-86b1a196411c.json

    # Email (Configuración para Gmail - Usa una "Contraseña de aplicación" si tienes 2FA)
    EMAIL_HOST_USER=tu_correo@gmail.com
    EMAIL_HOST_PASSWORD=tu_contraseña_de_aplicacion_o_normal

    # Google OAuth (Allauth)
    SOCIAL_AUTH_GOOGLE_CLIENT_ID=tu_client_id_google.apps.googleusercontent.com
    SOCIAL_AUTH_GOOGLE_SECRET=tu_secret_google
    ```

    * **`SECRET_KEY`**: Genera una clave segura. Puedes usar `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
    * **`GS_BUCKET_NAME`**: El nombre de tu bucket de GCS.
    * **`GS_CREDENTIALS_FILE`**: El nombre de tu archivo JSON de credenciales de servicio de Google. Asegúrate de que este archivo esté en la ruta especificada en `settings.py` (ej. `test_bebras/static/tu_archivo.json`). **¡No lo subas a Git!**
    * **`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`**: Tu cuenta de Gmail y, si tienes 2FA activado, una "contraseña de aplicación" generada por Google.
    * **`SOCIAL_AUTH_GOOGLE_CLIENT_ID`/`SOCIAL_AUTH_GOOGLE_SECRET`**: Credenciales de tu aplicación OAuth de Google.

5.  **Ejecutar Migraciones de Base de Datos:**
    Aplica las migraciones para crear las tablas de la base de datos.
    ```bash
    python manage.py migrate
    ```

6.  **Crear un Superusuario (Opcional, pero recomendado para el Admin):**
    Esto te permitirá acceder al panel de administración de Django.
    ```bash
    python manage.py createsuperuser
    ```
    admin
    

7.  **Iniciar el Servidor de Desarrollo:**
    ```bash
    python manage.py runserver
    ```
    La aplicación debería estar disponible en `http://127.0.0.1:8000/`. El panel de administración estará en `http://127.0.0.1:8000/admin/`.
