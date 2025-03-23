
from OpenGL.GL import *
from OpenGL.GLU import gluLookAt, gluPerspective
from Entity import Player
from pygame.locals import *
import math
from MeshMap import MeshMap


class Camera():
    def __init__(self, player:Player, mesh_map:MeshMap, display, far_plane, zoom_distance=20.0, elevation_angle=45.0):
        self.player = player
        self.mesh_map = mesh_map
        self.zoom_distance = zoom_distance
        self.user_zoom_distance = zoom_distance
        self.zoom_cooldown = 0
        self.elevation_angle = elevation_angle
        
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.5, 0.7, 1.0, 1.0)  # light blue sky background
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (display[0] / display[1]), 0.01, far_plane)
        glMatrixMode(GL_MODELVIEW)
     
    # Use this to update the camera position and what it's looking at
    def apply(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        player_position = self.player.get_position()
        player_height = self.player.get_height() * 5 / 6

        # Compute initial camera position at the current zoom level
        camera_x = player_position[0] - self.zoom_distance * math.sin(math.radians(player_position[3]))
        camera_z = player_position[2] + self.zoom_distance * math.cos(math.radians(player_position[3]))
        camera_y = player_position[1] + self.zoom_distance * math.sin(math.radians(self.elevation_angle)) + player_height

        # Get terrain height at the camera's (x, z) position
        terrain_height = self.mesh_map.get_tile_height((camera_x, camera_z)) + 1.0  

        if camera_y < terrain_height:
            # If colliding, zoom in
            self.zoom_distance = max(1.0, self.zoom_distance - 1)
            self.zoom_cooldown = 20  # Set cooldown to prevent immediate zoom-out
        elif self.zoom_distance < self.user_zoom_distance:
            if self.zoom_cooldown > 0:
                self.zoom_cooldown -= 1  # Decrease cooldown timer
            else:
                # If no collision and cooldown expired, zoom out
                self.zoom_distance = min(self.user_zoom_distance, self.zoom_distance + 1)
        elif self.zoom_distance > self.user_zoom_distance:
            self.zoom_distance = max(self.user_zoom_distance, self.zoom_distance - 1)


        # Recalculate camera position after zoom adjustments
        camera_x = player_position[0] - self.zoom_distance * math.sin(math.radians(player_position[3]))
        camera_z = player_position[2] + self.zoom_distance * math.cos(math.radians(player_position[3]))
        camera_y = player_position[1] + self.zoom_distance * math.sin(math.radians(self.elevation_angle)) + player_height

        # Apply gluLookAt with the adjusted zoom distance
        gluLookAt(camera_x, camera_y, camera_z,  
                  player_position[0], player_position[1] + player_height, player_position[2],  
                  0, 1, 0)   

    # Use this to update the camera position attributes with use controls
    def update(self, keys):
        if keys[K_q]:
            self.user_zoom_distance = max(1.0, self.user_zoom_distance - 1)  # Prevent getting too close
        if keys[K_e]:
            self.user_zoom_distance = min(50.0, self.user_zoom_distance + 1) # Prevent getting too far away
        
        
        if keys[K_w]:
            self.elevation_angle = max(-85, self.elevation_angle - 2)  # Lower the camera, look upwards
        if keys[K_s]:
            self.elevation_angle = min(85, self.elevation_angle + 2)  # Raise the camera, look downwards
