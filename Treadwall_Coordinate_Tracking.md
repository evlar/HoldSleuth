
# Comprehensive Outline for Treadwall Coordinate Tracking and Synchronization

---

## 1. Goal
Create a system that tracks the **(x, y)** coordinates of holds on a treadwall and synchronizes them with a **camera-projector setup** for dynamic route visualization. Ensure accurate alignment of physical holds with projected routes by using periodic calibration with an **inductive proximity sensor** and continuous tracking.

---

## 2. Hardware Components

### A. Position Tracking
1. **Inductive Proximity Sensor:**
   - Model: **LJ18A3-8-Z/BY**.
   - Purpose: Detect ferrous targets (e.g., screws) placed at fixed intervals (every 5 feet) for periodic calibration.
   - Detection Range: 8mm.
   - Placement: Mounted on the stationary frame of the treadwall.

2. **Climbing Distance Sensor (Existing):**
   - Detects and tracks continuous movement of the wall between calibration points.
   - Provides intermediate position data.

3. **Ferrous Targets:**
   - Small screws or bolts installed every 5 feet on the treadwall’s moving surface.
   - Serve as reference points for the proximity sensor.

4. **Inclinometer (Wall Angle Sensor):**
   - Example: **Adafruit BNO055**.
   - Purpose: Measure the treadwall’s tilt angle to adjust the projected grid dynamically.

---

### B. Projection and Alignment
1. **Short-Throw Projector:**
   - Projects climbing routes onto the wall.
   - Must cover the entire climbing surface with minimal distortion.

2. **Camera:**
   - Raspberry Pi Camera Module.
   - Optional: Detect visual markers (e.g., reflective tape) for secondary alignment verification.

3. **Reflective Marker:**
   - Placed at a fixed position on the treadwall to aid in projector-camera alignment.
   - Detected by the camera for fine-tuning.

---

## 3. Coordinate System
1. **Grid Definition:**
   - 8 columns (x-axis) and 40 rows (y-axis) to match the t-nut layout.
   - Each cell corresponds to a t-nut location.

2. **Origin Point:**
   - Bottom-left corner of the wall is **(0, 0)**.

3. **Reference Points:**
   - Ferrous targets provide calibration points at regular intervals (e.g., 0 ft, 5 ft, 10 ft, etc.).

---

## 4. Workflow

### A. Position Tracking
1. **Initial Calibration:**
   - At startup, the inductive sensor detects the nearest ferrous target to set the system’s initial position.

2. **Continuous Tracking:**
   - The climbing distance sensor measures movement between calibration points.
   - Interpolate the current position based on the last detected reference point.

3. **Periodic Recalibration:**
   - When the inductive sensor detects a ferrous target, snap the system’s position to the exact reference coordinate (e.g., 5 ft).

---

### B. Synchronizing the Projector
1. **Adjust for Wall Angle:**
   - Use inclinometer data to compensate for the treadwall’s tilt dynamically.
   - Apply the angle adjustment to the projection matrix.

2. **Recalibrate Projection:**
   - When the inductive sensor detects a ferrous target, recalibrate the projector grid to ensure alignment with the physical wall.

3. **Camera-Based Alignment (Optional):**
   - Detect reflective markers to fine-tune projector alignment.

---

## 5. Software Workflow

### A. Sensor Integration
1. **Inductive Sensor:**
   - Connect the sensor to a Raspberry Pi GPIO pin to detect ferrous targets.
   - Monitor the sensor’s output using a script:
     ```python
     import RPi.GPIO as GPIO

     GPIO.setmode(GPIO.BCM)
     GPIO.setup(18, GPIO.IN)

     def sensor_callback(channel):
         print("Inductive sensor triggered!")
         # Update position to match the reference point

     GPIO.add_event_detect(18, GPIO.RISING, callback=sensor_callback)

     try:
         while True:
             pass
     except KeyboardInterrupt:
         GPIO.cleanup()
     ```

2. **Climbing Distance Sensor:**
   - Use this sensor to provide fine-grained tracking between calibration points.
   - Continuously update the system’s position.

3. **Inclinometer:**
   - Read tilt angle data to adjust the projection grid dynamically.

---

### B. Coordinate Calculation
1. **Combine Data:**
   - Use the inductive sensor to snap to reference points.
   - Interpolate the position using data from the climbing distance sensor.

2. **Handle Drift:**
   - Periodic recalibration ensures drift is corrected.

---

### C. Projector Alignment
1. **Generate Projected Grid:**
   - Dynamically calculate the projected climbing grid based on the wall’s current position and tilt.

2. **Recalibrate:**
   - Snap the projector’s grid to match the physical holds when the inductive sensor detects a reference point.

3. **Camera Integration (Optional):**
   - Detect reflective markers or other visual features to verify alignment.

---

## 6. Integration of Multiple Raspberry Pis
If you are using multiple Raspberry Pis (e.g., one for tracking and one for projection), ensure they communicate via a local network:
1. **Network Setup:**
   - Connect all Raspberry Pis to the same Wi-Fi or Ethernet network.
   - Assign static IPs for reliable communication.

2. **Data Sharing:**
   - Use **MQTT**, **HTTP API**, or **WebSockets** for real-time communication.
   - Example: The Pi tracking sensors sends position data to the Pi controlling the projector.

---

## 7. Testing and Optimization
1. **Hardware Testing:**
   - Verify that the inductive sensor detects targets accurately.
   - Ensure smooth operation of the climbing distance sensor.

2. **Software Debugging:**
   - Test the coordinate calculation logic under various conditions.
   - Simulate edge cases, such as skipped targets or fast movement.

3. **Alignment Verification:**
   - Use test patterns projected onto the wall to verify proper grid alignment.
   - Adjust projection parameters as needed.

---

## 8. Key Considerations
1. **Sensor Placement:**
   - Ensure the inductive sensor is securely mounted and aligned with the targets.

2. **Wire Management:**
   - Route wires neatly to avoid interference or damage.

3. **Latency:**
   - Minimize delays between sensor readings and projection updates.

4. **Redundancy:**
   - Use multiple sensors or periodic recalibration to handle potential drift.

---

## Conclusion
This approach integrates **inductive proximity sensors**, a **climbing distance sensor**, and an **inclinometer** for reliable tracking and synchronization with a **camera-projector system**. The periodic recalibration ensures accuracy, while continuous tracking and dynamic adjustments maintain precise alignment. By testing and fine-tuning each component, this system can provide a robust solution for your climbing visualization project.
