import math
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class ProjectorConfig:
    width: int = 1280  # Default projector resolution
    height: int = 720
    wall_width_ft: float = 6.0  # Physical wall dimensions
    wall_height_ft: float = 10.0
    segment_height_ft: float = 20.0  # Height of one full rotation

class ProjectionSystem:
    def __init__(self):
        self.config = ProjectorConfig()
        self.active_route: Optional[Dict[str, Any]] = None
        self.wall_position: float = 0.0  # Current wall position in grid units
        self.wall_angle: float = 0.0  # Current wall angle in degrees
        self.last_calibration: float = 0.0
        self._running: bool = False
        self._update_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start_projection(self, route: Dict[str, Any]) -> None:
        """Start projecting a route."""
        with self._lock:
            if self._running:
                raise RuntimeError("Projection already running")
            
            self.active_route = route
            self._running = True
            self._update_thread = threading.Thread(target=self._projection_loop)
            self._update_thread.daemon = True
            self._update_thread.start()

    def stop_projection(self) -> None:
        """Stop the current projection."""
        with self._lock:
            self._running = False
            if self._update_thread:
                self._update_thread.join()
                self._update_thread = None
            self.active_route = None

    def update_wall_position(self, position: float) -> None:
        """Update the current wall position."""
        self.wall_position = position

    def update_wall_angle(self, angle: float) -> None:
        """Update the current wall angle."""
        self.wall_angle = angle

    def update_calibration(self, position: float) -> None:
        """Update the last calibration position."""
        self.last_calibration = position

    def get_status(self) -> Dict[str, Any]:
        """Get the current projection system status."""
        return {
            'active': self._running,
            'wall_position': self.wall_position,
            'wall_angle': self.wall_angle,
            'last_calibration': self.last_calibration,
            'active_route': self.active_route.get('name') if self.active_route else None
        }

    def transform_coordinates(self, hold: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Transform hold coordinates from route space to projector space."""
        # Extract hold coordinates
        x = hold['x']  # 0-7 for columns
        y = float(hold['y'])  # Continuous value
        segment = int(hold['segment'])

        # Calculate the absolute y position including segment
        absolute_y = y + (segment * 40)  # 40 grid units per segment

        # Calculate relative position based on current wall position
        relative_y = absolute_y - self.wall_position

        # Check if the hold is currently visible
        if not (0 <= relative_y < 40):
            return None

        # Transform coordinates according to projection_explanation.md
        # 1. Swap x and y (90° rotation)
        # 2. Scale to projector resolution
        # 3. Flip x coordinate (7 - x) for correct orientation

        # Calculate scaling factors
        scale_x = self.config.height / self.config.wall_height_ft
        scale_y = self.config.width / self.config.wall_width_ft

        # Transform coordinates
        x_projected = relative_y * scale_x  # y becomes x in projector space
        y_projected = (7 - x) * scale_y  # Flipped x becomes y in projector space

        # Adjust for wall angle if needed
        if self.wall_angle != 0:
            angle_rad = math.radians(self.wall_angle)
            # Apply rotation transformation
            x_rot = x_projected * math.cos(angle_rad) - y_projected * math.sin(angle_rad)
            y_rot = x_projected * math.sin(angle_rad) + y_projected * math.cos(angle_rad)
            x_projected = x_rot
            y_projected = y_rot

        return {
            'x': x_projected,
            'y': y_projected,
            'type': hold['type']
        }

    def _projection_loop(self) -> None:
        """Main projection update loop."""
        while self._running:
            try:
                if not self.active_route:
                    continue

                # Transform all visible holds
                visible_holds = []
                for hold in self.active_route['holds']:
                    transformed = self.transform_coordinates(hold)
                    if transformed:
                        visible_holds.append(transformed)

                # TODO: Send transformed coordinates to projector
                # This would interface with the actual projector hardware
                # For now, we'll just print for debugging
                print(f"Projecting {len(visible_holds)} holds")

                time.sleep(1/30)  # Update at 30Hz
            except Exception as e:
                print(f"Error in projection loop: {e}")
                time.sleep(1)  # Wait before retrying

# Global instance
projection_system = ProjectionSystem() 