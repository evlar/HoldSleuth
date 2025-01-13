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
        
        # Set up display in windowed mode with 5:3 aspect ratio for wide display
        # Using 1000x600 as default size (maintains 5:3 ratio)
        self.width = 1000
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("HoldSleuth Projection Display")
        print(f"Created window: {self.width}x{self.height}")
        
        # Track fullscreen state
        self.is_fullscreen = False
        
        # Keystone adjustment (0 = no adjustment, positive = right side wider, negative = left side wider)
        self.keystone = 0.0  # Range: -1.0 to 1.0
        
        # Calculate projection area (5:3 aspect ratio)
        self.update_projection_area()
        
        # Projection state
        self.wall_position = 0
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
        self.width, self.height = self.screen.get_size()
        self.proj_width = self.width - 40
        self.proj_height = int(self.proj_width * (3/5))
        if self.proj_height > self.height - 40:
            self.proj_height = self.height - 40
            self.proj_width = int(self.proj_height * (5/3))
            
        self.proj_x = (self.width - self.proj_width) // 2
        self.proj_y = (self.height - self.proj_height) // 2
        print(f"Updated projection area: {self.proj_width}x{self.proj_height} at ({self.proj_x}, {self.proj_y})")

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode"""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            # Get the current display info
            display_info = pygame.display.Info()
            # Switch to fullscreen mode using the current display resolution
            self.screen = pygame.display.set_mode((display_info.current_w, display_info.current_h), pygame.FULLSCREEN)
        else:
            # Switch back to windowed mode with wide dimensions
            self.screen = pygame.display.set_mode((1000, 600), pygame.RESIZABLE)
        
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
        Creates a proper trapezoidal correction where one side is taller than the other,
        and the content is scaled appropriately."""
        # Calculate relative position within projection area
        rel_x = (x - self.proj_x) / self.proj_width
        rel_y = (y - self.proj_y) / self.proj_height
        
        # Calculate the height at this x position
        # At rel_x = 0 (left), height is scaled by (1 - keystone)
        # At rel_x = 1 (right), height is scaled by (1 + keystone)
        scale_factor = 1.0 + (self.keystone * (2 * rel_x - 1))
        
        # Calculate new y position based on the scaled height
        # Center point of each vertical line stays fixed
        scaled_y = self.proj_y + (self.proj_height * 0.5) + ((rel_y - 0.5) * self.proj_height * scale_factor)
        
        return x, int(scaled_y), scale_factor

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
        # Clear screen
        self.screen.fill((0, 0, 0))
        
        # Draw projection border with keystone
        # Draw grid matching climbing wall dimensions (20 units wide x 8 units tall)
        
        # Draw horizontal lines (8 divisions for height)
        for i in range(9):  # 0 to 8 inclusive
            y = self.proj_y + (i * self.proj_height / 8)
            for x in range(self.proj_x, self.proj_x + self.proj_width, 10):
                start = self.apply_keystone(x, int(y))[0:2]
                end = self.apply_keystone(min(x + 10, self.proj_x + self.proj_width), int(y))[0:2]
                pygame.draw.line(self.screen, (51, 51, 51), start, end)
        
        # Draw vertical lines (20 divisions for width - half a segment)
        for i in range(21):  # 0 to 20 inclusive
            x = self.proj_x + (i * self.proj_width / 20)
            top_point = self.apply_keystone(int(x), self.proj_y)[0:2]
            bottom_point = self.apply_keystone(int(x), self.proj_y + self.proj_height)[0:2]
            pygame.draw.line(self.screen, (51, 51, 51), top_point, bottom_point)
        
        # Draw border
        border_points = [
            self.apply_keystone(self.proj_x, self.proj_y)[0:2],  # Top left
            self.apply_keystone(self.proj_x + self.proj_width, self.proj_y)[0:2],  # Top right
            self.apply_keystone(self.proj_x + self.proj_width, self.proj_y + self.proj_height)[0:2],  # Bottom right
            self.apply_keystone(self.proj_x, self.proj_y + self.proj_height)[0:2],  # Bottom left
        ]
        pygame.draw.lines(self.screen, (255, 255, 255), True, border_points, 2)

        # Draw route if loaded
        if hasattr(self, 'current_route') and self.current_route:
            segment_width = self.proj_width / 20  # Each visible segment is 20 units wide
            
            # Draw segment boundaries
            for seg in range(3):  # Assuming max 3 segments
                # Calculate segment line x position
                # Start from right edge and move left with segments
                seg_x = (self.proj_x + self.proj_width) - ((seg * 20 + self.wall_position) * segment_width)
                
                if self.proj_x <= seg_x <= self.proj_x + self.proj_width:
                    # Draw segment line with keystone correction
                    for y in range(self.proj_y, self.proj_y + self.proj_height, 10):
                        start = self.apply_keystone(int(seg_x), y)[0:2]
                        end = self.apply_keystone(int(seg_x), min(y + 10, self.proj_y + self.proj_height))[0:2]
                        pygame.draw.line(self.screen, (51, 51, 51), start, end)
            
            # Draw holds
            for hold in self.current_route.get('holds', []):
                # Calculate base position within segment
                hold_x = hold['x']  # 0-7 for columns
                hold_y = hold['y']  # Position within column
                segment = hold['segment']
                
                # Convert to screen coordinates
                # Start from right edge (proj_x + proj_width) and move left
                screen_x = (self.proj_x + self.proj_width) - (hold_y * segment_width)
                
                # Y coordinate goes top to bottom, scaled to height
                screen_y = self.proj_y + (hold_x * self.proj_height / 8)
                
                # Apply segment offset (segments move leftward)
                # Subtract wall position to move left
                segment_offset = (segment * 20 + self.wall_position) * segment_width
                screen_x -= segment_offset
                
                # Only draw if within projection area
                if self.proj_x <= screen_x <= self.proj_x + self.proj_width:
                    self.draw_hold(int(screen_x), int(screen_y), hold['type'])
        
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