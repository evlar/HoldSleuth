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
        
        # Set up display in windowed mode with 3:5 aspect ratio for tall display
        # Using 600x1000 as default size (maintains 3:5 ratio)
        # Swap dimensions for 90-degree rotation
        self.base_width = 600
        self.base_height = 1000
        # Create the actual display surface (swapped dimensions for 90° rotation)
        self.screen = pygame.display.set_mode((self.base_height, self.base_width), pygame.RESIZABLE)
        # Create a render surface for pre-rotation drawing
        self.render_surface = pygame.Surface((self.base_width, self.base_height))
        pygame.display.set_caption("HoldSleuth Projection Display")
        print(f"Created window: {self.base_width}x{self.base_height} (rotated)")
        
        # Track fullscreen state
        self.is_fullscreen = False
        
        # Keystone adjustment (0 = no adjustment)
        self.keystone = 0.0  # Range: -1.0 to 1.0
        
        # Calculate projection area (3:5 aspect ratio)
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
        
        self.proj_height = self.height - 40
        self.proj_width = int(self.proj_height * (3/5))
        if self.proj_width > self.width - 40:
            self.proj_width = self.width - 40
            self.proj_height = int(self.proj_width * (5/3))
            
        self.proj_x = (self.width - self.proj_width) // 2
        self.proj_y = (self.height - self.proj_height) // 2
        
        # Update render surface size
        self.render_surface = pygame.Surface((self.width, self.height))
        print(f"Updated projection area: {self.proj_width}x{self.proj_height} at ({self.proj_x}, {self.proj_y})")

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode"""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            # Get the current display info
            display_info = pygame.display.Info()
            screen_width = display_info.current_w
            screen_height = display_info.current_h
            
            # Calculate dimensions that maintain 3:5 aspect ratio
            # Remember we're rotated 90 degrees, so width:height should be 5:3
            target_ratio = 5/3  # Width:Height ratio we want after rotation
            current_ratio = screen_width / screen_height
            
            if current_ratio > target_ratio:
                # Screen is too wide, use height to calculate width
                new_width = int(screen_height * target_ratio)
                new_height = screen_height
            else:
                # Screen is too tall, use width to calculate height
                new_width = screen_width
                new_height = int(screen_width / target_ratio)
            
            # Switch to fullscreen mode
            self.screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
            # Store the dimensions for centered rendering
            self.fullscreen_dims = (new_width, new_height)
            self.fullscreen_offset = ((screen_width - new_width) // 2, (screen_height - new_height) // 2)
        else:
            # Switch back to windowed mode with swapped dimensions
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

    def apply_keystone(self, x: int, y: int) -> tuple[int, int]:
        """Apply keystone transformation to a point.
        Creates a proper trapezoidal correction where the top is wider/narrower than the bottom,
        and the content is scaled appropriately."""
        # Calculate relative position within projection area
        rel_x = (x - self.proj_x) / self.proj_width
        rel_y = (y - self.proj_y) / self.proj_height
        
        # Calculate the width at this y position
        # At rel_y = 0 (top), width is scaled by (1 + keystone)
        # At rel_y = 1 (bottom), width is scaled by (1 - keystone)
        scale_factor = 1.0 - (self.keystone * (2 * rel_y - 1))
        
        # Calculate new x position based on the scaled width
        # Center point of each horizontal line stays fixed
        scaled_x = self.proj_x + (self.proj_width * 0.5) + ((rel_x - 0.5) * self.proj_width * scale_factor)
        
        return int(scaled_x), y, scale_factor

    def draw_hold(self, x: int, y: int, hold_type: str):
        """Draw a hold with keystone correction."""
        adjusted_x, adjusted_y, scale_factor = self.apply_keystone(x, y)
        
        # Scale the hold size based on the keystone transformation
        adjusted_size = int(self.hold_size * scale_factor)
        
        color = self.HOLD_COLORS.get(hold_type, self.HOLD_COLORS['regular'])
        pygame.draw.circle(self.screen, color, (adjusted_x, adjusted_y), adjusted_size)
        pygame.draw.circle(self.screen, (255, 255, 255), (adjusted_x, adjusted_y), adjusted_size, 2)

    def render(self):
        """Render the current frame."""
        # Clear render surface and main screen
        self.render_surface.fill((0, 0, 0))
        self.screen.fill((0, 0, 0))
        
        # Calculate spacing for rows and columns
        col_spacing = self.proj_width / 8  # 8 columns (0-7)
        row_spacing = self.proj_height / 20  # Show 20 rows at a time (half segment)
        
        # Draw grid lines
        # Vertical lines (9 lines for 8 columns)
        for i in range(9):
            x = self.proj_x + (i * col_spacing)
            top_point = self.apply_keystone(int(x), self.proj_y)[0:2]
            bottom_point = self.apply_keystone(int(x), self.proj_y + self.proj_height)[0:2]
            pygame.draw.line(self.render_surface, (51, 51, 51), top_point, bottom_point)
        
        # Horizontal lines (21 lines for 20 rows)
        for i in range(21):
            y = self.proj_y + (i * row_spacing)
            for x in range(self.proj_x, self.proj_x + self.proj_width, 10):
                start = self.apply_keystone(x, int(y))[0:2]
                end = self.apply_keystone(min(x + 10, self.proj_x + self.proj_width), int(y))[0:2]
                pygame.draw.line(self.render_surface, (51, 51, 51), start, end)
        
        # Draw border
        border_points = [
            self.apply_keystone(self.proj_x, self.proj_y)[0:2],  # Top left
            self.apply_keystone(self.proj_x + self.proj_width, self.proj_y)[0:2],  # Top right
            self.apply_keystone(self.proj_x + self.proj_width, self.proj_y + self.proj_height)[0:2],  # Bottom right
            self.apply_keystone(self.proj_x, self.proj_y + self.proj_height)[0:2],  # Bottom left
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
                
                # Convert to screen coordinates
                screen_x = self.proj_x + (hold_x * col_spacing)
                
                # Calculate which part of the segment should be visible
                visible_start = row_offset - (segment_progress * 20)  # Starts at 20, moves down to 0
                visible_end = visible_start + 20  # Show 20 rows at a time
                
                # Only draw holds that are in the visible range
                if visible_start <= hold_y < visible_end:
                    # Map the hold's position to the display area
                    relative_y = hold_y - visible_start
                    screen_y = self.proj_y + (relative_y * row_spacing)
                    
                    # Only draw if within projection area
                    if self.proj_y <= screen_y <= self.proj_y + self.proj_height:
                        # Draw to render surface instead of screen
                        adjusted_x, adjusted_y, scale_factor = self.apply_keystone(int(screen_x), int(screen_y))
                        adjusted_size = int(self.hold_size * scale_factor)
                        color = self.HOLD_COLORS.get(hold['type'], self.HOLD_COLORS['regular'])
                        pygame.draw.circle(self.render_surface, color, (adjusted_x, adjusted_y), adjusted_size)
                        pygame.draw.circle(self.render_surface, (255, 255, 255), (adjusted_x, adjusted_y), adjusted_size, 2)
        
        # Rotate the render surface 90 degrees clockwise
        rotated = pygame.transform.rotate(self.render_surface, -90)  # Negative for clockwise
        
        # Handle fullscreen display with aspect ratio preservation
        if self.is_fullscreen and self.fullscreen_dims:
            # Scale the rotated surface to the calculated dimensions
            scaled = pygame.transform.scale(rotated, self.fullscreen_dims)
            # Blit to the center of the screen
            self.screen.blit(scaled, self.fullscreen_offset)
        else:
            # Normal windowed mode
            self.screen.blit(rotated, (0, 0))
        
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
                        # Add keystone adjustment controls
                        elif event.key == pygame.K_LEFT:
                            self.adjust_keystone(-0.1)  # Adjust left
                        elif event.key == pygame.K_RIGHT:
                            self.adjust_keystone(0.1)   # Adjust right
                
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