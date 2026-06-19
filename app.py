import os
import signal
import sys
from datetime import datetime
from flask import Flask, request, jsonify

# --- CONFIGURACIÓN DESDE VARIABLES DE ENTORNO ---
PORT = int(os.getenv('PORT', 5000))
# Usar ruta relativa 'data' para desarrollo local, o variable de entorno para K8s
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv('DATA_DIR', os.path.join(BASE_DIR, 'data'))
NOTAS_FILE = os.path.join(DATA_DIR, 'notas.txt')
# --- INICIALIZAR FLASK ---
app = Flask(__name__)

# Contador de visitas (en memoria - se reinicia al restart del Pod)
visit_counter = 0

# --- FUNCIONES AUXILIARES PARA PERSISTENCIA ---

def ensure_data_dir():
    """Asegura que el directorio de datos exista"""
    os.makedirs(DATA_DIR, exist_ok=True)

def read_notas():
    """Lee todas las notas desde el archivo persistente"""
    try:
        if os.path.exists(NOTAS_FILE):
            with open(NOTAS_FILE, 'r', encoding='utf-8') as f:
                lineas = f.readlines()
                return [linea.strip() for linea in lineas if linea.strip()]
        return []
    except Exception as e:
        print(f"Error leyendo notas: {e}")
        return []

def write_nota(texto):
    """Escribe una nueva nota en el archivo persistente"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        nota_completa = f"[{timestamp}] {texto}\n"
        
        with open(NOTAS_FILE, 'a', encoding='utf-8') as f:
            f.write(nota_completa)
        
        return True
    except Exception as e:
        print(f"Error escribiendo nota: {e}")
        return False
    



# --- HEALTH PROBES PARA KUBERNETES ---

@app.route('/healthz', methods=['GET'])
def healthz():
    """
    Liveness Probe: Verifica que la aplicación esté viva.
    Kubernetes reiniciará el Pod si este endpoint no responde.
    """
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

@app.route('/ready', methods=['GET'])
def ready():
    """
    Readiness Probe: Verifica que la aplicación esté lista para recibir tráfico.
    Kubernetes no enviará tráfico al Pod hasta que este endpoint responda 200.
    """
    try:
        # Verificar que podemos acceder al directorio de datos
        ensure_data_dir()
        
        # Verificar que podemos escribir en el archivo
        if not os.access(DATA_DIR, os.W_OK):
            return jsonify({
                "status": "not_ready", 
                "reason": "No write permission on data directory"
            }), 503
        
        return jsonify({
            "status": "ready", 
            "data_dir": DATA_DIR,
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "not_ready", 
            "reason": str(e)
        }), 503
   

# --- ENDPOINTS PRINCIPALES ---

@app.route('/', methods=['GET'])
def home():
    """
    Endpoint principal que muestra contador de visitas y nombre del Pod.
    Demuestra balanceo de carga al cambiar el Pod name en cada request.
    """
    global visit_counter
    visit_counter += 1
    
    pod_name = os.getenv('HOSTNAME', 'unknown')
    
    return jsonify({
        "message": "Bienvenido a la API de Notas",
        "pod_name": pod_name,
        "visit_number": visit_counter,
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/notas', methods=['POST'])
def crear_nota():
    """
    Crea una nueva nota y la persiste en disco.
    Espera JSON: {"texto": "Comprar leche"}
    """
    try:
        data = request.get_json()
        
        if not data or 'texto' not in data:
            return jsonify({"error": "Se requiere campo 'texto'"}), 400
        
        texto = data['texto'].strip()
        
        if not texto:
            return jsonify({"error": "El texto no puede estar vacío"}), 400
        
        # Asegurar directorio existe antes de escribir
        ensure_data_dir()
        
        # Escribir nota en archivo persistente
        if write_nota(texto):
            return jsonify({
                "message": "Nota creada exitosamente",
                "nota": texto,
                "pod_name": os.getenv('HOSTNAME', 'unknown')
            }), 201
        else:
            return jsonify({"error": "Error al guardar la nota"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/notas', methods=['GET'])
def listar_notas():
    """
    Lista todas las notas almacenadas persistentemente.
    """
    try:
        notas = read_notas()
        
        return jsonify({
            "total_notas": len(notas),
            "notas": notas,
            "pod_name": os.getenv('HOSTNAME', 'unknown')
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    






# --- PUNTO DE ENTRADA ---

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Iniciando API de Notas Cloud-Native")
    print("=" * 50)
    print(f"📍 Puerto: {PORT}")
    print(f"📁 Directorio de datos: {DATA_DIR}")
    print(f"🏷️  Nombre del Pod: {os.getenv('HOSTNAME', 'local')}")
    print("=" * 50)
    
    # Asegurar que el directorio de datos exista al inicio
    ensure_data_dir()
    
    # Iniciar servidor Flask
    app.run(
        host='0.0.0.0',  # Escuchar en todas las interfaces (necesario para Docker/K8s)
        port=PORT,
        debug=False  # Desactivar debug en producción
    )