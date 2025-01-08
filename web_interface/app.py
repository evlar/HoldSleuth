from flask import Flask, request, jsonify, render_template, send_file, url_for
import os
from werkzeug.utils import secure_filename
from utils.scanner import get_initial_detections, process_final_holds
from utils.route_manager import save_route, load_route, list_routes
import cv2
from image_detection.yolo_hold_detector import YOLOHoldDetector

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