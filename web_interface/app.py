from flask import Flask, request, jsonify, render_template, send_file, url_for
import os
from werkzeug.utils import secure_filename
from utils.scanner import get_initial_detections, process_final_holds
from utils.route_manager import save_route, load_route, list_routes
import cv2
from image_detection.yolo_hold_detector import YOLOHoldDetector
from datetime import datetime

# Create Flask app with explicit template folder
app = Flask(__name__, 
           template_folder=os.path.abspath('templates'),
           static_folder=os.path.abspath('static'))

# Configure upload and routes folders
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['ROUTES_FOLDER'] = os.path.join('static', 'routes')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['GRID_JPG_PATH'] = None  # Store the latest grid image path

# Register template filters
@app.template_filter('datetime')
def format_datetime(value, format='%B %d, %Y at %I:%M %p'):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value.strftime(format)

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ROUTES_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'css'), exist_ok=True)

# Create output directories needed by treadwallscan.py
project_root = os.path.dirname(os.path.dirname(__file__))
os.makedirs(os.path.join(project_root, 'output', 'svg'), exist_ok=True)
os.makedirs(os.path.join(project_root, 'output', 'svg', 'grid'), exist_ok=True)
os.makedirs(os.path.join(project_root, 'output', 'grid'), exist_ok=True)

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
            # Initialize YOLO detector
            yolo_detector = YOLOHoldDetector(
                confidence_threshold=0.25,
                nms_iou_threshold=0.4
            )
            
            # Load and preprocess image
            image = cv2.imread(filepath)
            if image is None:
                raise ValueError(f"Failed to load image: {filepath}")
            
            # Enhance contrast using CLAHE
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            image = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            
            # Detect holds using YOLO
            holds = yolo_detector.detect_holds(image)
            
            # Draw initial detections
            detection_image = yolo_detector.draw_holds(image, holds)
            
            # Save detection image for review
            base_name = os.path.splitext(filename)[0]
            detection_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_name}_detections.jpg")
            cv2.imwrite(detection_path, detection_image)
            
            # Store original image path and holds for later processing
            if not hasattr(app, 'pending_scans'):
                app.pending_scans = {}
            
            # Convert holds to a format suitable for JSON
            holds_data = []
            for hold in holds:
                holds_data.append({
                    'center': [int(hold.center[0]), int(hold.center[1])],
                    'bbox': [int(x) for x in hold.bbox],
                    'confidence': float(hold.confidence),
                    'color': hold.color
                })
            
            app.pending_scans[base_name] = {
                'image_path': filepath,
                'holds': holds_data
            }
            
            return jsonify({
                'message': 'Initial detections ready for review',
                'scan_id': base_name,
                'detection_path': os.path.join('static', 'uploads', f"{base_name}_detections.jpg"),
                'holds': holds_data
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/scan/finalize', methods=['POST'])
def finalize_scan():
    data = request.json
    scan_id = data.get('scan_id')
    approved_holds = data.get('holds')
    
    if not scan_id or not approved_holds:
        return jsonify({'error': 'Missing scan_id or holds data'}), 400
        
    if not hasattr(app, 'pending_scans') or scan_id not in app.pending_scans:
        return jsonify({'error': 'Invalid or expired scan_id'}), 400
    
    try:
        # Process the approved holds
        image_path = app.pending_scans[scan_id]['image_path']
        svg_path, grid_jpg_path = process_final_holds(image_path, approved_holds)
        
        # Store the grid image path in app config
        app.config['GRID_JPG_PATH'] = grid_jpg_path
        
        # Clean up
        del app.pending_scans[scan_id]
        
        return jsonify({
            'message': 'Wall scan processed successfully',
            'svg_path': svg_path,
            'grid_jpg_path': grid_jpg_path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/routes/create')
def route_create():
    print("\n=== Route Create Debug Info ===")
    print(f"Project root: {project_root}")
    
    # Check if grid_jpg_path was provided in query parameters
    grid_jpg_path = request.args.get('grid_jpg_path')
    if grid_jpg_path:
        # Convert relative path to absolute if needed
        if grid_jpg_path.startswith('..'):
            grid_jpg_path = os.path.abspath(os.path.join(project_root, grid_jpg_path))
        print(f"Grid JPG path from query param: {grid_jpg_path}")
    else:
        # Get the grid image path from config
        grid_jpg_path = app.config['GRID_JPG_PATH']
        print(f"Grid JPG path from config: {grid_jpg_path}")
    
    print(f"Grid JPG exists: {grid_jpg_path and os.path.exists(grid_jpg_path)}")
    
    if not grid_jpg_path or not os.path.exists(grid_jpg_path):
        # Try to find any grid JPG in the grid directory
        grid_dir = os.path.join(project_root, 'output', 'grid')
        if os.path.exists(grid_dir):
            jpg_files = [f for f in os.listdir(grid_dir) if f.startswith('converted_grid_') and f.endswith('.jpg')]
            if jpg_files:
                grid_jpg_path = os.path.join(grid_dir, jpg_files[0])
                print(f"Found grid JPG: {grid_jpg_path}")
                app.config['GRID_JPG_PATH'] = grid_jpg_path
    
    if not grid_jpg_path or not os.path.exists(grid_jpg_path):
        print(f"No grid JPG found")
        return "No wall scan found. Please scan your wall first.", 400
    
    # Get the corresponding SVG file
    base_name = os.path.splitext(os.path.basename(grid_jpg_path))[0]
    if base_name.startswith('converted_grid_'):
        base_name = base_name[len('converted_grid_'):]
    grid_svg_path = os.path.join(project_root, 'output', 'svg', 'grid', f"{base_name}_grid.svg")
    print(f"Looking for SVG at: {grid_svg_path}")
    print(f"SVG path exists: {os.path.exists(grid_svg_path)}")
    
    # Try to find any SVG file in the grid directory if the matching one doesn't exist
    if not os.path.exists(grid_svg_path):
        grid_dir = os.path.join(project_root, 'output', 'svg', 'grid')
        if os.path.exists(grid_dir):
            svg_files = [f for f in os.listdir(grid_dir) if f.endswith('_grid.svg')]
            if svg_files:
                grid_svg_path = os.path.join(grid_dir, svg_files[0])
                print(f"Found alternative SVG: {grid_svg_path}")
    
    if not os.path.exists(grid_svg_path):
        print(f"No SVG file found in grid directory")
        return "No wall scan found. Please scan your wall first.", 400
    
    with open(grid_svg_path, 'r') as f:
        wall_svg = f.read()
        # Clean up SVG content
        wall_svg = (wall_svg
            .replace('ns0:', '')  # Remove namespace prefix
            .replace('xmlns:ns0', 'xmlns')  # Fix namespace declaration
            .replace('<?xml version=\'1.0\' encoding=\'utf-8\'?>\n', '')  # Remove XML declaration
        )
        print(f"SVG content length: {len(wall_svg)}")
        print("SVG content preview (first 1000 chars):")
        print(wall_svg[:1000])
    
    # Get available grades
    grades = ['5.6', '5.7', '5.8', '5.9', '5.10a', '5.10b', '5.10c', '5.10d', 
             '5.11a', '5.11b', '5.11c', '5.11d', '5.12a', '5.12b', '5.12c', '5.12d']
    
    return render_template('route_create.html', 
                         wall_svg=wall_svg,
                         grades=grades)

@app.route('/routes')
def routes_page():
    # Get all routes and pass them to the template
    routes_list = list_routes(app.config['ROUTES_FOLDER'])
    # Get unique grades and authors for filters
    grades = sorted(set(route.get('grade') for route in routes_list if route.get('grade')))
    authors = sorted(set(route.get('author') for route in routes_list if route.get('author')))
    return render_template('routes.html', routes=routes_list, grades=grades, authors=authors)

@app.route('/routes/<route_id>')
def route_view(route_id):
    try:
        route_data = load_route(os.path.join(app.config['ROUTES_FOLDER'], f"{route_id}.json"))
        # Get the grid SVG file for visualization
        grid_svg_path = os.path.join(project_root, 'output', 'svg', 'grid', 'treadwall_grid.svg')
        if not os.path.exists(grid_svg_path):
            return "No wall scan found. Please scan your wall first.", 400
        
        with open(grid_svg_path, 'r') as f:
            wall_svg = f.read()
            # Clean up SVG content
            wall_svg = (wall_svg
                .replace('ns0:', '')  # Remove namespace prefix
                .replace('xmlns:ns0', 'xmlns')  # Fix namespace declaration
                .replace('<?xml version=\'1.0\' encoding=\'utf-8\'?>\n', '')  # Remove XML declaration
            )
        
        return render_template('route_view.html', route=route_data, wall_svg=wall_svg)
    except FileNotFoundError:
        return "Route not found", 404

@app.route('/routes/<route_id>/edit')
def route_edit(route_id):
    try:
        # Load route data
        route_data = load_route(os.path.join(app.config['ROUTES_FOLDER'], f"{route_id}.json"))
        
        # Get the grid SVG file
        grid_svg_path = os.path.join(project_root, 'output', 'svg', 'grid', 'treadwall_grid.svg')
        if not os.path.exists(grid_svg_path):
            return "No wall scan found. Please scan your wall first.", 400
        
        with open(grid_svg_path, 'r') as f:
            wall_svg = f.read()
        
        # Get available grades
        grades = ['5.6', '5.7', '5.8', '5.9', '5.10a', '5.10b', '5.10c', '5.10d', 
                 '5.11a', '5.11b', '5.11c', '5.11d', '5.12a', '5.12b', '5.12c', '5.12d']
        
        return render_template('route_create.html', 
                             route=route_data,
                             wall_svg=wall_svg,
                             grades=grades)
    except FileNotFoundError:
        return "Route not found", 404

@app.route('/api/routes', methods=['GET', 'POST'])
def api_routes():
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

@app.route('/api/routes/<route_id>', methods=['GET', 'PUT', 'DELETE'])
def api_route(route_id):
    route_path = os.path.join(app.config['ROUTES_FOLDER'], f"{route_id}.json")
    
    if request.method == 'GET':
        try:
            route_data = load_route(route_path)
            return jsonify(route_data)
        except FileNotFoundError:
            return jsonify({'error': 'Route not found'}), 404
    
    elif request.method == 'PUT':
        try:
            route_data = request.json
            save_route(route_data, app.config['ROUTES_FOLDER'], filename=f"{route_id}.json")
            return jsonify({'message': 'Route updated successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            os.remove(route_path)
            return jsonify({'message': 'Route deleted successfully'})
        except FileNotFoundError:
            return jsonify({'error': 'Route not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    app.run(debug=True) 