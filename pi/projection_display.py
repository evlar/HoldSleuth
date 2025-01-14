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
        
        self.width = 600
        self.height = 1000
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("HoldSleuth Projection Display")
        print(f"Created window: {self.width}x{self.height}")
        
        self.is_fullscreen = False
        self.keystone = 0.0  # Keystone adjustment
        
        self.update_projection_area()
        
        self.wall_position = 0
        self.hold_size = 20
        self.route = None
        self.running = True
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', port))
        self.sock.settimeout(0.1)
        print(f"Listening for UDP messages on port {port}")
        
        self.network_thread = None

    def update_projection_area(self):
        self.width, self.height = self.screen.get_size()
        self.proj_height = self.height - 40
        self.proj_width = int(self.proj_height * (3/5))
        if self.proj_width > self.width - 40:
            self.proj_width = self.width - 40
            self.proj_height = int(self.proj_width * (5/3))
        self.proj_x = (self.width - self.proj_width) // 2
        self.proj_y = (self.height - self.proj_height) // 2
        print(f"Updated projection area: {self.proj_width}x{self.proj_height} at ({self.proj_x}, {self.proj_y})")

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            display_info = pygame.display.Info()
            self.screen = pygame.display.set_mode((display_info.current_w, display_info.current_h), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((1000, 600), pygame.RESIZABLE)
        self.update_projection_area()

    def handle_network(self):
        print("Network thread started")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65536)
                print(f"\nReceived message from {addr}")
                try:
                    message = json.loads(data.decode())
                    msg_type = message.get('type')
                    msg_data = message.get('data')
                    print(f"Message type: {msg_type}")
                    if msg_type == 'route':
                        self.current_route = msg_data
                        print("Route loaded successfully")
                    elif msg_type == 'position':
                        self.wall_position = float(msg_data)
                    elif msg_type == 'hold_size':
                        self.hold_size = int(msg_data)
                except json.JSONDecodeError as e:
                    print(f"Error decoding message: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Network error: {e}")
        print("Network thread stopping")

    def draw_hold(self, x: int, y: int, hold_type: str, surface):
        color = self.HOLD_COLORS.get(hold_type, self.HOLD_COLORS['regular'])
        pygame.draw.circle(surface, color, (x, y), self.hold_size)
        pygame.draw.circle(surface, (255, 255, 255), (x, y), self.hold_size, 2)

    def render(self):
        content_surface = pygame.Surface((self.width, self.height))
        content_surface.fill((0, 0, 0))
        
        col_spacing = self.proj_width / 8
        row_spacing = self.proj_height / 20

        for i in range(9):  
            x = self.proj_x + (i * col_spacing)
            pygame.draw.line(content_surface, (51, 51, 51), (x, self.proj_y), (x, self.proj_y + self.proj_height))
        
        for i in range(21):  
            y = self.proj_y + (i * row_spacing)
            pygame.draw.line(content_surface, (51, 51, 51), (self.proj_x, y), (self.proj_x + self.proj_width, y))
        
        if hasattr(self, 'current_route') and self.current_route:
            for hold in self.current_route.get('holds', []):
                screen_x = self.proj_x + (hold['x'] * col_spacing)
                screen_y = self.proj_y + (hold['y'] * row_spacing)
                self.draw_hold(int(screen_x), int(screen_y), hold['type'], content_surface)
        
        rotated_surface = pygame.transform.rotate(content_surface, -90)
        self.screen.fill((0, 0, 0))
        self.screen.blit(rotated_surface, (0, 0))
        pygame.display.flip()

    def run(self):
        print("Starting main loop...")
        clock = pygame.time.Clock()
        self.network_thread = threading.Thread(target=self.handle_network)
        self.network_thread.start()
        try:
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False
                        elif event.key == pygame.K_f:
                            self.toggle_fullscreen()
                self.render()
                clock.tick(60)
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            print("Shutting down projection display...")
            self.running = False
            if self.network_thread and self.network_thread.is_alive():
                self.network_thread.join(timeout=1.0)
            self.sock.close()
            pygame.quit()
            print("Shutdown complete")

if __name__ == '__main__':
    display = ProjectionDisplay()
    display.run()
