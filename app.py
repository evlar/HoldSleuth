from flask import Flask, request, jsonify, render_template, send_file, url_for
import os
from werkzeug.utils import secure_filename
from utils.scanner import process_wall_scan
from utils.route_manager import save_route, load_route, list_routes

# Create Flask app with explicit template folder
app = Flask(__name__, 
           template_folder=os.path.abspath('templates'),
           static_folder=os.path.abspath('static'))

# Configure upload and routes folders
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['ROUTES_FOLDER'] = os.path.join('static', 'routes')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ROUTES_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'css'), exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan')
def scan_page():
    return render_template('scan.html')

@app.route('/scan', methods=['POST'])
def scan_wall():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            svg_path, grid_jpg_path = process_wall_scan(filepath)
            return jsonify({
                'message': 'Wall scan processed successfully',
                'svg_path': svg_path,
                'grid_jpg_path': grid_jpg_path
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/routes/create')
def create_route():
    grid_jpg_path = request.args.get('grid_jpg_path')
    if not grid_jpg_path:
        return "No wall image specified", 400
    return render_template('route_create.html', grid_jpg_path=grid_jpg_path)

@app.route('/routes')
def routes_page():
    return render_template('routes.html')

@app.route('/routes', methods=['GET', 'POST'])
def routes():
    if request.method == 'POST':
        route_data = request.json
        try:
            filename = save_route(route_data, app.config['ROUTES_FOLDER'])
            return jsonify({'message': 'Route saved successfully', 'filename': filename})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    # GET request - list all routes
    routes = list_routes(app.config['ROUTES_FOLDER'])
    return jsonify(routes)

@app.route('/routes/<filename>', methods=['GET'])
def get_route(filename):
    try:
        route_data = load_route(os.path.join(app.config['ROUTES_FOLDER'], filename))
        return jsonify(route_data)
    except FileNotFoundError:
        return jsonify({'error': 'Route not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    app.run(debug=True) 