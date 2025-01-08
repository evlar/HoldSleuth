import os
import json
from datetime import datetime
import uuid

def validate_route(route_data):
    """
    Validate route data according to the specification.
    
    Args:
        route_data (dict): Route data to validate
        
    Raises:
        ValueError: If route data is invalid
    """
    required_fields = ['name', 'holds']
    if not all(field in route_data for field in required_fields):
        raise ValueError("Missing required fields: name and holds")
    
    holds = route_data['holds']
    if not holds:
        raise ValueError("Route must have at least one hold")
    
    # Check for start and finish holds
    has_start = any(hold['type'] == 'start' for hold in holds)
    has_finish = any(hold['type'] == 'finish' for hold in holds)
    
    if not has_start:
        raise ValueError("Route must have at least one start hold")
    if not has_finish:
        raise ValueError("Route must have at least one finish hold")
    
    # Validate each hold
    valid_types = {'start', 'foot', 'regular', 'finish'}
    for hold in holds:
        if 'x' not in hold or 'y' not in hold or 'type' not in hold:
            raise ValueError("Each hold must have x, y, and type properties")
        
        if not isinstance(hold['x'], int) or not (0 <= hold['x'] <= 7):
            raise ValueError("Hold x position must be an integer between 0 and 7")
            
        if not isinstance(hold['y'], (int, float)) or hold['y'] < 0:
            raise ValueError("Hold y position must be a positive number")
            
        if hold['type'] not in valid_types:
            raise ValueError(f"Invalid hold type. Must be one of: {', '.join(valid_types)}")

def save_route(route_data, routes_folder):
    """
    Save a route to a JSON file.
    
    Args:
        route_data (dict): Route data to save
        routes_folder (str): Path to the routes folder
        
    Returns:
        str: Filename of the saved route
    """
    # Validate route data
    validate_route(route_data)
    
    # Add creation timestamp if not present
    if 'created_at' not in route_data:
        route_data['created_at'] = datetime.utcnow().isoformat() + 'Z'
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}.json"
    filepath = os.path.join(routes_folder, filename)
    
    # Save route to file
    with open(filepath, 'w') as f:
        json.dump(route_data, f, indent=4)
    
    return filename

def load_route(filepath):
    """
    Load a route from a JSON file.
    
    Args:
        filepath (str): Path to the route file
        
    Returns:
        dict: Route data
    """
    with open(filepath, 'r') as f:
        route_data = json.load(f)
    return route_data

def list_routes(routes_folder):
    """
    List all routes in the routes folder.
    
    Args:
        routes_folder (str): Path to the routes folder
        
    Returns:
        list: List of route data dictionaries
    """
    routes = []
    for filename in os.listdir(routes_folder):
        if filename.endswith('.json'):
            filepath = os.path.join(routes_folder, filename)
            try:
                route_data = load_route(filepath)
                route_data['filename'] = filename
                routes.append(route_data)
            except Exception as e:
                print(f"Error loading route {filename}: {e}")
    
    # Sort routes by creation date
    routes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return routes 