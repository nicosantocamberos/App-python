# Usamos una imagen base ligera de Python
FROM python:3.13-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos el archivo de dependencias y las instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código de la aplicación
COPY app.py .

# Creamos el directorio donde se guardarán las notas
# (En K8s montaremos un volumen aquí, pero lo creamos por seguridad)
RUN mkdir -p /app/data

# Variable de entorno por defecto para el puerto
ENV PORT=8080

# Expone el puerto que usará la aplicación
EXPOSE 8080

# Comando para iniciar la aplicación
CMD ["python", "app.py"]