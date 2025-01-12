# JSON-to-Projection Mapping for Rotated Projector

## Overview
This document explains how to transform climbing route JSON data for projection onto a climbing wall using a **ViewSonic M1+ Portable Smart Wi-Fi Projector** rotated 90 degrees counterclockwise. The projection must maintain the correct aspect ratio and alignment for a **10ft tall by 6ft wide wall**, with the projector oriented such that content moves right-to-left to appear top-to-bottom on the wall.

---

## Coordinate Mapping for Rotated Projection

### Original Coordinate System in JSON
- **`x`:** Horizontal position (0-7), corresponding to the 8 columns of the wall.
- **`y`:** Vertical position (positive floats), representing the height on the wall.

### Rotated Projector's Coordinate System
- The **horizontal axis (X)** of the projector maps to the **vertical (Y)** axis of the wall.
- The **vertical axis (Y)** of the projector maps to the **horizontal (X)** axis of the wall.

### Adjusted Projection Mapping
- **`x_projected` = `y_original` scaled** to fit the projector's height (corresponding to the wall’s 10ft height).
- **`y_projected` = `7 - x_original` scaled** to fit the projector's width (corresponding to the wall’s 6ft width).

---

## Aspect Ratio Considerations

The climbing wall has an aspect ratio of **5:3 (10ft tall by 6ft wide)**, while the projector’s native aspect ratio is **16:9 (1.78)**. To match the wall’s proportions:

1. **Vertical Scaling:**
   - The projector’s **vertical axis** (Y) must scale to match the 10ft height.

2. **Horizontal Scaling:**
   - The projector’s **horizontal axis** (X) must scale to match the 6ft width.

3. **Coordinate Transformation:**
   - New `x_projected` = **`y_original` scaled to the projector's vertical resolution**.
   - New `y_projected` = **`7 - x_original` scaled to the projector's horizontal resolution**.

---

## Steps for JSON-to-Projection Conversion

1. **Adjust Coordinates:**
   For each hold in the JSON file:
   ```python
   x_projected = y_original * (projector_height / wall_height)
   y_projected = (7 - x_original) * (projector_width / wall_width)
   ```

2. **Account for Wall Scaling:**
   Ensure that the transformed coordinates fit within the projector’s resolution (e.g., 854x480 or 1280x720, depending on settings).

3. **Visualize Holds:**
   Render each hold as a shape (circle, rectangle, etc.) based on its type (`start`, `foot`, `regular`, `finish`).

4. **Handle Segments and Wrapping:**
   For holds spanning multiple wall rotations, adjust `y_projected` based on the segment number:
   ```python
   y_projected += segment * (wall_height / segment_height)
   ```

5. **Output for Projection:**
   Render the transformed coordinates into a format suitable for projection (e.g., SVG, WebGL, or a 2D canvas object).

---

## Example

### Input JSON
```json
{
    "name": "Example Route",
    "grade": "V3",
    "holds": [
        {"x": 3, "y": 5.0, "segment": 0, "type": "start"},
        {"x": 5, "y": 15.75, "segment": 0, "type": "regular"},
        {"x": 4, "y": 25.5, "segment": 1, "type": "finish"}
    ]
}
```

### Transformed for Projection

1. **First Hold (`x=3, y=5.0`):**
   ```python
   x_projected = 5.0 * (projector_height / 10.0)
   y_projected = (7 - 3) * (projector_width / 6.0)
   ```

2. **Second Hold (`x=5, y=15.75`):**
   ```python
   x_projected = 15.75 * (projector_height / 10.0)
   y_projected = (7 - 5) * (projector_width / 6.0)
   ```

3. **Third Hold (`x=4, y=25.5, segment=1`):**
   ```python
   x_projected = 25.5 * (projector_height / 10.0)
   y_projected = (7 - 4) * (projector_width / 6.0)
   y_projected += segment * (wall_height / segment_height)
   ```

---

## Summary
Rotating the projector 90° counterclockwise requires:

1. Swapping and flipping coordinates (`x` becomes `y`, and `y` is flipped for correct orientation).
2. Scaling to match the climbing wall’s aspect ratio.
3. Adjusting for multiple wall segments.

This ensures the route is displayed **top-to-bottom** and aligns perfectly with your climbing wall when projected.

Let me know if further clarification or implementation assistance is needed!
