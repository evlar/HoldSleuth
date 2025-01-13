import socket
import json
from typing import Dict, Any

class ProjectionClient:
    def __init__(self, host='raspberrypi.local', port=5000):
        """Initialize projection client.
        Args:
            host: IP address or hostname of the Raspberry Pi (default: raspberrypi.local)
            port: UDP port to send messages to (default: 5000)
        """
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def send_message(self, msg_type: str, data: Any) -> None:
        """Send a message to the projection display."""
        message = {
            'type': msg_type,
            'data': data
        }
        try:
            print(f"Sending {msg_type} to {self.host}:{self.port}")
            self.sock.sendto(json.dumps(message).encode(), (self.host, self.port))
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def send_route(self, route: Dict) -> None:
        """Send route data to the projection display."""
        print("\nSending route to projection display:")
        print(f"Host: {self.host}")
        print(f"Port: {self.port}")
        print(f"Route name: {route.get('name')}")
        print(f"Number of holds: {len(route.get('holds', []))}")
        print(f"First hold: {route.get('holds', [])[0] if route.get('holds') else 'No holds'}")
        
        try:
            message = {
                'type': 'route',
                'data': route
            }
            encoded_message = json.dumps(message).encode()
            print(f"Message size: {len(encoded_message)} bytes")
            self.sock.sendto(encoded_message, (self.host, self.port))
            print("Route sent successfully")
        except Exception as e:
            print(f"Error sending route: {e}")
            raise
    
    def send_position(self, position: float) -> None:
        """Update the wall position in the projection display."""
        self.send_message('position', position)
    
    def send_hold_size(self, size: int) -> None:
        """Update the hold size in the projection display."""
        self.send_message('hold_size', size)
    
    def close(self) -> None:
        """Close the UDP socket."""
        self.sock.close() 