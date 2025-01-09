# Treadwall Projector System Overview

## 1. System Architecture

The projector system consists of three main components working together to provide accurate route visualization:

1. **Physical Tracking System**
   - Inductive proximity sensor for precise calibration
   - Continuous distance sensor for real-time movement tracking
   - Inclinometer for wall angle detection

2. **Projection System**
   - Short-throw projector for route visualization
   - Camera for alignment verification
   - Calibration markers for projector-wall alignment

3. **Control System**
   - Route management through web interface
   - Real-time coordinate transformation
   - Projection mapping and adjustment

## 2. Physical Tracking Implementation

### A. Primary Position Tracking
1. **Inductive Proximity Sensor (LJ18A3-8-Z/BY)**
   - Mounted on stationary frame
   - Detects metal targets every 5 feet (40 grid units)
   - Provides absolute position reference
   - Connected to GPIO pin 18 on Raspberry Pi
   ```python
   def setup_inductive_sensor():
       GPIO.setmode(GPIO.BCM)
       GPIO.setup(18, GPIO.IN)
       GPIO.add_event_detect(18, GPIO.RISING, callback=handle_calibration_point)
   ```

2. **Distance Sensor**
   - Continuous tracking between calibration points
   - Updates position at 60Hz
   - Provides relative movement data
   ```python
   def update_position(distance_delta):
       current_position += distance_delta
       if abs(current_position - last_calibration) > CALIBRATION_THRESHOLD:
           request_calibration()
   ```

3. **Calibration Targets**
   - Metal screws placed every 5 feet (40 grid units)
   - Corresponds to segment boundaries in route JSON
   - Position mapping: `segment_number * 40 = y_coordinate`

### B. Wall Angle Detection
1. **Inclinometer (Adafruit BNO055)**
   - Mounted on wall frame
   - Provides real-time angle data
   - Used for projection transformation
   ```python
   def update_wall_angle():
       angle = inclinometer.get_euler_angles()
       adjust_projection_matrix(angle)
   ```

## 3. Coordinate System Integration

### A. Physical to Virtual Mapping
1. **Grid System**
   - 8 columns (x: 0-7)
   - 40 rows per segment (y: 0-39)
   - Physical spacing:
     - Horizontal: 8 inches between holds
     - Vertical: 6 inches between holds

2. **Position Calculation**
   ```python
   def calculate_position(sensor_data):
       absolute_position = sensor_data.last_calibration_point
       relative_movement = sensor_data.distance_since_calibration
       current_y = absolute_position + relative_movement
       
       # Convert to route coordinates
       segment = int(current_y // 40)
       relative_y = current_y % 40
       return segment, relative_y
   ```

### B. Route Coordinate Translation
1. **JSON to Physical Mapping**
   ```python
   def translate_hold_position(hold, wall_position):
       physical_y = (hold.segment * 40) + hold.y - wall_position
       if 0 <= physical_y < 40:  # Hold is visible
           return {
               'x': hold.x * 8,  # 8 inches per column
               'y': physical_y * 6,  # 6 inches per row
               'type': hold.type
           }
       return None
   ```

## 4. Projection System

### A. Hardware Setup
1. **Projector Placement**
   - Short-throw projector mounted above wall
   - Projection area covers 8x40 grid
   - Calibrated to physical hold spacing

2. **Camera Alignment**
   - Raspberry Pi Camera Module
   - Monitors projection alignment
   - Detects calibration markers

### B. Projection Mapping
1. **Grid Transformation**
   ```python
   def calculate_projection_matrix(wall_angle, calibration_points):
       # Convert route coordinates to projector coordinates
       matrix = create_base_matrix()
       matrix = adjust_for_angle(matrix, wall_angle)
       matrix = fine_tune_with_calibration(matrix, calibration_points)
       return matrix
   ```

2. **Hold Visualization**
   ```python
   def project_hold(hold_data, projection_matrix):
       position = apply_matrix(projection_matrix, hold_data)
       color = HOLD_COLORS[hold_data.type]
       draw_hold(position, color)
   ```

## 5. Real-time Synchronization

### A. Position Updates
1. **Sensor Data Flow**
   ```python
   class WallTracker:
       def __init__(self):
           self.position = 0.0
           self.last_calibration = 0.0
           
       def handle_calibration_point(self, pin):
           segment = int(pin_to_segment[pin])
           self.position = segment * 40
           self.last_calibration = self.position
           
       def update_position(self, distance_delta):
           self.position += distance_delta
           self.update_projection()
   ```

2. **Route Projection Updates**
   ```python
   def update_projection(route, wall_position):
       visible_holds = []
       for hold in route.holds:
           physical_pos = translate_hold_position(hold, wall_position)
           if physical_pos:
               visible_holds.append(physical_pos)
       project_holds(visible_holds)
   ```

### B. Event Handling
1. **Calibration Events**
   ```python
   def handle_calibration_point(channel):
       # Inductive sensor detected calibration point
       segment = get_segment_from_channel(channel)
       wall_tracker.calibrate_position(segment * 40)
       update_all_projections()
   ```

2. **Continuous Updates**
   ```python
   def main_loop():
       while True:
           # Update sensors at 60Hz
           distance = distance_sensor.read()
           angle = inclinometer.read()
           
           # Update tracking and projection
           wall_tracker.update_position(distance)
           projection_system.update_angle(angle)
           
           time.sleep(1/60)
   ```

## 6. Integration with Web Interface

### A. Route Loading
1. **Route Selection**
   ```python
   def load_route(route_id):
       route_data = load_json_route(route_id)
       active_route = Route.from_dict(route_data)
       projection_system.set_active_route(active_route)
   ```

2. **Real-time Updates**
   ```python
   @app.route('/api/projection/status', methods=['GET'])
   def get_projection_status():
       return jsonify({
           'wall_position': wall_tracker.position,
           'wall_angle': inclinometer.angle,
           'active_route': active_route.to_dict() if active_route else None,
           'last_calibration': wall_tracker.last_calibration
       })
   ```

## 7. Calibration and Maintenance

### A. System Calibration
1. **Initial Setup**
   - Measure and mark hold grid spacing
   - Install calibration targets at segment boundaries
   - Configure projector alignment

2. **Regular Calibration**
   - Automatic calibration at each target detection
   - Manual calibration through web interface
   - Visual alignment verification

### B. Error Handling
1. **Position Drift**
   - Maximum allowed drift between calibrations
   - Automatic recalibration requests
   - Error logging and notification

2. **Sensor Failures**
   - Fallback to last known good position
   - Alert system for sensor issues
   - Graceful degradation of functionality

## 8. Performance Considerations

1. **Update Rates**
   - Position tracking: 60Hz
   - Projection updates: 30Hz
   - Web interface updates: 1Hz

2. **Latency Management**
   - Maximum 16ms processing time per frame
   - Prioritize position tracking over visualization
   - Buffer projection updates

## 9. Future Enhancements

1. **Multiple Route Support**
   - Simultaneous projection of multiple routes
   - Color coding for different climbers
   - Route difficulty visualization

2. **Advanced Features**
   - Dynamic route generation
   - Climber tracking integration
   - Performance analytics

## Security and Safety

1. **Physical Safety**
   - Emergency stop capability
   - Projector eye safety considerations
   - Sensor mounting security

2. **System Security**
   - Local network operation only
   - Regular backup of route data
   - Access control for calibration functions 