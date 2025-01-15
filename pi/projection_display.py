#!/usr/bin/env python3
import pygame
import sys
import json
import socket
import threading
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Hold:
    segment: int
    type: str
    x: float
    y: float

class ProjectionDisplay:
    # Hold colors matching web interface
    HOLD_COLORS = {
        'start': (40, 167, 69),    # #28a745
        'foot': (255, 193, 7),     # #ffc107
        'regular': (13, 110, 253),  # #0d6efd
        'finish': (111, 66, 193)    # #6f42c1
    }

    def __init__(self, port=5000):
        print("Starting projection display...")
        pygame.init()
        
        # Set up display with 28:57 aspect ratio (width:height)
        self.base_width = 560  # 28 * 20
        self.base_height = 1140  # 57 * 20
        
        # Calculate border dimensions
        col_spacing = self.base_width / 7  # 7 spaces for 8 lines
        row_spacing = self.base_height / 19  # 19 spaces for 20 lines
        
        # Store border dimensions as class attributes
        self.border_x = col_spacing / 2
        self.border_width = self.base_width - col_spacing
        self.border_y = row_spacing / 2
        self.border_height = self.base_height - row_spacing
        
        # Get the display info for fullscreen setup
        display_info = pygame.display.Info()
        screen_width = display_info.current_w
        screen_height = display_info.current_h
        
        # Create surfaces with normal orientation, rotation happens at display time
        self.render_surface = pygame.Surface((self.base_width, self.base_height))
        
        # Start in fullscreen mode
        self.screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
        pygame.display.set_caption("HoldSleuth Projection Display")
        print(f"Created window: {screen_width}x{screen_height} (fullscreen)")
        
        # Track fullscreen state
        self.is_fullscreen = True
        
        # Calculate initial fullscreen dimensions
        target_ratio = 28/57  # Original width:height ratio
        rotated_ratio = 57/28  # After 90-degree rotation
        
        # Calculate the maximum size that fits in the screen while maintaining ratio
        if screen_width / screen_height > rotated_ratio:
            # Too wide, use height to determine width
            new_height = screen_height
            new_width = int(screen_height * rotated_ratio)
        else:
            # Too tall, use width to determine height
            new_width = screen_width
            new_height = int(new_width / rotated_ratio)
        
        # Store the dimensions and offset for centered rendering
        self.fullscreen_dims = (new_width, new_height)
        self.fullscreen_offset = ((screen_width - new_width) // 2, (screen_height - new_height) // 2)
        
        # Keystone adjustment (0 = no adjustment)
        self.keystone = 0.0  # Range: -1.0 to 1.0
        
        # Calculate projection area
        self.update_projection_area()
        
        # Projection state
        self.wall_position = 0  # Position between 0-40 within current segment
        self.hold_size = 20
        self.route = None
        self.running = True
        
        # Network setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', port))
        self.sock.settimeout(0.1)  # Set a shorter timeout for more responsive shutdown
        print(f"Listening for UDP messages on port {port}")
        
        # Initialize network thread but don't start it yet
        self.network_thread = None

    def update_projection_area(self):
        """Recalculate projection area based on current window size"""
        # Get the rotated dimensions from screen
        rotated_width, rotated_height = self.screen.get_size()
        # Swap back for internal calculations
        self.width = rotated_height
        self.height = rotated_width
        
        # Create render surface at base dimensions to maintain ratio
        self.render_surface = pygame.Surface((self.base_width, self.base_height))
        
        # Calculate maximum projection area that maintains 28:57 ratio
        target_ratio = 28/57  # Width:Height ratio
        
        # Calculate dimensions that will fill the available space while maintaining ratio
        if self.width / self.height > target_ratio:
            # Too wide, use height to determine width
            self.proj_height = self.height
            self.proj_width = int(self.height * target_ratio)
        else:
            # Too tall, use width to determine height
            self.proj_width = self.width
            self.proj_height = int(self.width / target_ratio)
        
        # Center the projection area
        self.proj_x = (self.width - self.proj_width) // 2
        self.proj_y = (self.height - self.proj_height) // 2
        
        print(f"Updated projection area: {self.proj_width}x{self.proj_height} at ({self.proj_x}, {self.proj_y})")

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode"""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            # Get the current display info
            display_info = pygame.display.Info()
            screen_width = display_info.current_w
            screen_height = display_info.current_h
            
            # Switch to fullscreen mode
            self.screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
            
            # Calculate dimensions that maintain 28:57 ratio after rotation
            target_ratio = 28/57  # Original width:height ratio
            rotated_ratio = 25/57  # After 90-degree rotation
            
            # Calculate the maximum size that fits in the screen while maintaining ratio
            if screen_width / screen_height > rotated_ratio:
                # Too wide, use height to determine width
                new_height = screen_height
                new_width = int(screen_height * rotated_ratio)
            else:
                # Too tall, use width to determine height
                new_width = screen_width
                new_height = int(new_width / rotated_ratio)
            
            # Store the dimensions and offset for centered rendering
            self.fullscreen_dims = (new_width, new_height)
            self.fullscreen_offset = ((screen_width - new_width) // 2, (screen_height - new_height) // 2)
        else:
            # Switch back to windowed mode with swapped dimensions for rotation
            self.screen = pygame.display.set_mode((self.base_height, self.base_width), pygame.RESIZABLE)
            self.fullscreen_dims = None
            self.fullscreen_offset = None
        
        # Update projection area for new window size
        self.update_projection_area()

    def handle_network(self):
        """Handle incoming network messages."""
        print("Network thread started")
        
        while self.running:  # Use self.running instead of True for proper shutdown
            try:
                data, addr = self.sock.recvfrom(65536)  # Max UDP packet size
                print(f"\nReceived message from {addr}")
                
                try:
                    message = json.loads(data.decode())
                    msg_type = message.get('type')
                    msg_data = message.get('data')
                    
                    print(f"Message type: {msg_type}")
                    
                    if msg_type == 'route':
                        print("Processing route data:")
                        print(f"Route name: {msg_data.get('name')}")
                        print(f"Number of holds: {len(msg_data.get('holds', []))}")
                        self.current_route = msg_data
                        print("Route loaded successfully")
                    
                    elif msg_type == 'position':
                        old_pos = self.wall_position
                        self.wall_position = float(msg_data)
                        print(f"Updated position: {old_pos} -> {self.wall_position}")
                    
                    elif msg_type == 'hold_size':
                        old_size = self.hold_size
                        self.hold_size = int(msg_data)
                        print(f"Updated hold size: {old_size} -> {self.hold_size}")
                    
                except json.JSONDecodeError as e:
                    print(f"Error decoding message: {e}")
                except Exception as e:
                    print(f"Error processing message: {e}")
                    
            except socket.timeout:
                # This is normal, just continue
                continue
            except Exception as e:
                if self.running:  # Only print error if we're still supposed to be running
                    print(f"Network error: {e}")
        
        print("Network thread stopping")

    def adjust_keystone(self, amount):
        """Adjust the keystone value within bounds."""
        self.keystone = max(-1.0, min(1.0, self.keystone + amount))
        print(f"Keystone adjusted to: {self.keystone}")

    def apply_keystone(self, x: int, y: int, base_scale: float = 1.0) -> tuple[int, int, float]:
        """Apply keystone transformation to a point.
        Creates a proper trapezoidal correction where the top is wider/narrower than the bottom,
        and the content is scaled appropriately."""
        # Calculate relative position within the entire projection area
        rel_x = x / self.base_width
        rel_y = y / self.base_height
        
        # Calculate the width at this y position
        # At rel_y = 0 (top), width is scaled by (1 + keystone)
        # At rel_y = 1 (bottom), width is scaled by (1 - keystone)
        scale_factor = (1.0 + (self.keystone * (1.0 - 2.0 * rel_y))) * base_scale
        
        # Calculate new x position based on the scaled width
        # Center point of each horizontal line stays fixed
        center_x = self.base_width * 0.5
        scaled_x = center_x + ((x - center_x) * scale_factor)
        
        return int(scaled_x), y, scale_factor

    def draw_hold(self, x: int, y: int, hold_type: str, scale_factor: float = 1.0):
        """Draw a hold with keystone correction."""
        adjusted_x, adjusted_y, adj_scale = self.apply_keystone(x, y, scale_factor)
        
        # Scale the hold size based on the keystone transformation and base scale
        adjusted_size = int(self.hold_size * scale_factor * adj_scale)
        
        color = self.HOLD_COLORS.get(hold_type, self.HOLD_COLORS['regular'])
        pygame.draw.circle(self.render_surface, color, (adjusted_x, adjusted_y), adjusted_size)
        pygame.draw.circle(self.render_surface, (255, 255, 255), (adjusted_x, adjusted_y), adjusted_size, 2)

    def render(self):
        """Render the current frame."""
        # Clear render surface and main screen
        self.render_surface.fill((0, 0, 0))
        self.screen.fill((0, 0, 0))
        
        # Calculate spacing based on the render surface dimensions
        col_spacing = self.base_width / 7  # 7 spaces for 8 lines
        row_spacing = self.base_height / 19  # 19 spaces for 20 lines
        
        # Calculate maximum scale needed for keystone
        # The widest part will be scaled by (1 + |keystone|)
        max_scale = 1.0 + abs(self.keystone)
        
        # Scale down the entire display proportionally to prevent cropping
        scale_factor = 1.0 / max_scale
        
        # Adjust all dimensions for scaling
        scaled_width = self.base_width * scale_factor
        scaled_height = self.base_height * scale_factor
        scaled_x_offset = (self.base_width - scaled_width) / 2
        scaled_y_offset = (self.base_height - scaled_height) / 2
        
        # Adjust border dimensions for scaling
        scaled_border_x = scaled_x_offset + (self.border_x * scale_factor)
        scaled_border_width = self.border_width * scale_factor
        scaled_border_y = scaled_y_offset + (self.border_y * scale_factor)
        scaled_border_height = self.border_height * scale_factor
        
        # Draw grid lines with scaled coordinates
        # Vertical lines (8 internal lines)
        for i in range(9):  # 0 to 8 inclusive for 8 lines
            if i == 0 or i == 8:  # Skip first and last positions (borders)
                continue
            x = scaled_border_x + ((i - 1) * (scaled_border_width / 7))
            top_point = self.apply_keystone(int(x), scaled_border_y, scale_factor)[0:2]
            bottom_point = self.apply_keystone(int(x), scaled_border_y + scaled_border_height, scale_factor)[0:2]
            pygame.draw.line(self.render_surface, (51, 51, 51), top_point, bottom_point)
        
        # Horizontal lines (20 internal lines)
        for i in range(21):  # 0 to 20 inclusive for 20 lines
            if i == 0 or i == 20:  # Skip first and last positions (borders)
                continue
            y = scaled_border_y + ((i - 1) * (scaled_border_height / 19))
            left_point = self.apply_keystone(scaled_border_x, int(y), scale_factor)[0:2]
            right_point = self.apply_keystone(scaled_border_x + scaled_border_width, int(y), scale_factor)[0:2]
            pygame.draw.line(self.render_surface, (51, 51, 51), left_point, right_point)
        
        # Draw border
        border_points = [
            self.apply_keystone(scaled_border_x, scaled_border_y, scale_factor)[0:2],
            self.apply_keystone(scaled_border_x + scaled_border_width, scaled_border_y, scale_factor)[0:2],
            self.apply_keystone(scaled_border_x + scaled_border_width, scaled_border_y + scaled_border_height, scale_factor)[0:2],
            self.apply_keystone(scaled_border_x, scaled_border_y + scaled_border_height, scale_factor)[0:2],
        ]
        pygame.draw.lines(self.render_surface, (255, 255, 255), True, border_points, 2)

        # Draw route if loaded
        if hasattr(self, 'current_route') and self.current_route:
            # Calculate which segments are visible based on wall_position
            base_segment = int(self.wall_position / 40)  # Current base segment
            segment_progress = (self.wall_position % 40) / 40  # Progress through current segment
            
            # Calculate the row offset within the segment (20-39 initially visible)
            row_offset = 20  # Start showing from row 20
            
            for hold in self.current_route.get('holds', []):
                segment = hold['segment']
                if segment != base_segment:
                    continue
                
                # Get hold coordinates (0,0 is top-left of segment)
                hold_x = hold['x']  # 0-7 horizontal position
                hold_y = hold['y']  # 0-39 vertical position within segment
                
                # Convert to screen coordinates using scaled spacing
                screen_x = scaled_border_x + (hold_x * (scaled_border_width / 7))
                
                # Calculate which part of the segment should be visible
                visible_start = row_offset - (segment_progress * 20)  # Starts at 20, moves down to 0
                visible_end = visible_start + 20  # Show 20 rows at a time
                
                # Only draw holds that are in the visible range
                if visible_start <= hold_y < visible_end:
                    # Map the hold's position to the display area
                    relative_y = hold_y - visible_start
                    screen_y = scaled_border_y + (relative_y * (scaled_border_height / 19))
                    
                    if scaled_border_y <= screen_y <= scaled_border_y + scaled_border_height:
                        self.draw_hold(int(screen_x), int(screen_y), hold['type'], scale_factor)
        
        # Rotate the render surface 90 degrees clockwise
        rotated = pygame.transform.rotate(self.render_surface, -90)
        
        # Handle fullscreen display with aspect ratio preservation
        if self.is_fullscreen and self.fullscreen_dims:
            # Scale the rotated surface to the calculated fullscreen dimensions
            scaled = pygame.transform.smoothscale(rotated, self.fullscreen_dims)
            self.screen.blit(scaled, self.fullscreen_offset)
        else:
            # Scale for windowed mode
            scaled = pygame.transform.smoothscale(rotated, (self.screen.get_height(), self.screen.get_width()))
            self.screen.blit(scaled, (0, 0))
        
        # Update display
        pygame.display.flip()

    def run(self):
        """Main loop for the projection display."""
        print("Starting main loop...")
        clock = pygame.time.Clock()
        
        # Start network thread
        self.network_thread = threading.Thread(target=self.handle_network)
        self.network_thread.start()
        
        try:
            while self.running:
                # Handle Pygame events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False
                        elif event.key == pygame.K_f:
                            self.toggle_fullscreen()
                
                # Handle keystone adjustment with smoother control
                keys = pygame.key.get_pressed()
                if keys[pygame.K_LEFT]:
                    self.adjust_keystone(-0.02)  # Smaller adjustment for finer control
                if keys[pygame.K_RIGHT]:
                    self.adjust_keystone(0.02)   # Smaller adjustment for finer control
                
                # Render the current frame
                self.render()
                
                # Cap at 60 FPS
                clock.tick(60)
        
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            print("Shutting down projection display...")
            self.running = False  # Signal threads to stop
            
            # Wait for network thread to finish
            if self.network_thread and self.network_thread.is_alive():
                print("Waiting for network thread to stop...")
                self.network_thread.join(timeout=1.0)  # Wait up to 1 second
            
            # Close socket and quit pygame
            print("Closing socket...")
            self.sock.close()
            print("Quitting pygame...")
            pygame.quit()
            print("Shutdown complete")

if __name__ == '__main__':
    display = ProjectionDisplay()
    display.run() 