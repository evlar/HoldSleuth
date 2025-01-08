# Web Interface Overview for Treadwall Coordinate Tracking System

## Purpose of the Web Interface

The web interface serves as a user-friendly platform for managing and visualizing climbing routes on the treadwall. It provides the following functionalities:

1. **Route Creation and Editing:**
   - Users can create new climbing routes by selecting hold positions on a virtual representation of the treadwall.
   - Existing routes can be edited to adjust hold positions, add or remove holds, and change route metadata.

2. **Route Visualization:**
   - The interface displays a visual representation of the climbing routes, allowing users to see the layout of holds and their types.
   - Users can preview how routes will appear when projected onto the treadwall.

3. **Route Management:**
   - Users can save, load, and delete routes from the system.
   - The interface provides options to categorize and filter routes based on difficulty, author, or other metadata.

4. **Integration with Physical System:**
   - The web interface communicates with the treadwall's hardware to synchronize route data and ensure accurate projection.
   - It allows users to initiate calibration and alignment processes directly from the interface.

## Saved Route File Type Convention

Routes are saved as JSON files with a specific structure to ensure compatibility with the treadwall projection system. The format is designed to capture essential route information and facilitate easy conversion from SVG data.

### JSON Route File Structure
```json
{
    "name": "Route Name",
    "grade": "5.11a",           // Optional
    "author": "Climber Name",   // Optional
    "created_at": "2024-03-19T10:30:00Z",  // ISO 8601 format
    "holds": [
        {
            "x": 3,             // Column (0-7)
            "y": 5.5,           // Vertical position (can be any positive float)
            "type": "start"     // One of: "start", "foot", "regular", "finish"
        }
    ]
}
```

### Key Attributes

- **Name:** The name of the route.
- **Grade:** The difficulty level of the route, which is optional.
- **Author:** The creator of the route, which is optional.
- **Created At:** The timestamp when the route was created, in ISO 8601 format.
- **Holds:** A list of hold objects, each specifying:
  - `x`: The column position (0-7).
  - `y`: The vertical position, which can be any positive float.
  - `type`: The type of hold, which can be "start", "foot", "regular", or "finish".

### Coordinate System

- **Horizontal (X) Position:** Uses zero-based indexing (0-7) and maps directly to the SVG's `data-grid-x` value.
- **Vertical (Y) Position:** Zero (0.0) represents the bottom of the initial wall position, with one full wall height being 40 units. For holds beyond the first rotation, the y-coordinate is calculated as `base_position + (rotation_number * 40)`.

### Validation Rules

A valid route must have:
1. At least one "start" hold.
2. At least one "finish" hold.
3. All x values must be integers 0-7.
4. All y values must be positive floats.
5. All hold types must be one of the four specified types.

### Example Route

```json
{
    "name": "Infinite Traverse",
    "grade": "V3",
    "author": "John Climber",
    "created_at": "2024-03-19T10:30:00Z",
    "holds": [
        {"x": 3, "y": 5.0, "type": "start"},
        {"x": 4, "y": 5.0, "type": "start"},
        {"x": 2, "y": 6.5, "type": "foot"},
        {"x": 5, "y": 15.75, "type": "regular"},
        {"x": 3, "y": 25.5, "type": "regular"},
        {"x": 4, "y": 35.25, "type": "regular"},
        {"x": 2, "y": 45.0, "type": "finish"}
    ]
}
```

### Implementation Notes

- The projection system automatically handles the wrapping of y-coordinates to the physical wall height based on the current wall position.
- Routes can span any number of rotations, with no upper limit on y values.
- Coordinates should be saved with at least 2 decimal places of precision for accurate hold placement.
- The web interface should validate routes before saving to ensure they meet these specifications.

### References

- **Route Format Specification:** For more details on the route file format and conversion from SVG, please refer to `docs/route_format_specification.md`.
