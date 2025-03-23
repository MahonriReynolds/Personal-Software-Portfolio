
import numpy as np
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import random
import math

class Entity():
    def __init__(self, 
                 placement:tuple, 
                 max_speed:float, 
                 max_acceleration:float, 
                 friction_coefficient:int,
                 jump_power:float,
                 gravity:float,
                 max_fall_velocity:float,
                 
                 width: float
                ):
        
        self.position = np.array(placement, dtype=np.float32)
        self.velocity = np.zeros(4, dtype=np.float32)
        self.max_speed = max_speed
        self.max_acceleration = max_acceleration
        self.friction_coefficient = friction_coefficient
        self.jump_power = jump_power
        self.gravity = gravity
        self.max_fall_velocity = max_fall_velocity
        
        self.width = width
        self.height = width * 2
        
        
    def get_width(self):
        return self.width 
     
    def get_height(self):
        return self.height
    
    def set_position(self, x, y, z, r):
        self.position = np.array([x, y, z, r], dtype=np.float32)
    
    def get_position(self):
        return tuple(self.position)
    
    def set_velocity(self, vx, vy, vz, vr):
        self.velocity = np.array([vx, vy, vz, vr], dtype=np.float32)
    
    def get_velocity(self):
        return tuple(self.velocity)
    
    def apply_friction(self):
        self.velocity[0] *= self.friction_coefficient
        self.velocity[2] *= self.friction_coefficient
    
    def apply_gravity(self):
        if self.position[1] > 0:
            if self.velocity[1] > self.max_fall_velocity:
                self.velocity[1] -= self.gravity
        else:
            self.velocity[1] = 0
        
    def jump(self):
        self.velocity[1] += self.jump_power
            
    def push(self, input_velocity):
        velocity_delta = np.array(input_velocity, dtype=np.float32)
        current_velocity = np.array((self.velocity[0], self.velocity[2]), dtype=np.float32)
        current_speed = np.linalg.norm(current_velocity)
        new_velocity = current_velocity + velocity_delta
        new_speed = np.linalg.norm(new_velocity)

        speed_change = new_speed - current_speed
        if speed_change > self.max_acceleration:
            scale_factor = (current_speed + self.max_acceleration) / new_speed
            new_velocity *= scale_factor

        final_speed = np.linalg.norm(new_velocity)
        if final_speed > self.max_speed:
            scale_factor = self.max_speed / final_speed
            new_velocity *= scale_factor

        self.velocity[0] = new_velocity[0]
        self.velocity[2] = new_velocity[1]

        # Update position based on velocity in x, z
        self.position[0] += self.velocity[0]
        self.position[2] += self.velocity[2]
        
    def rotate(self, r):
        self.position[3] += r
        self.position[3] %= 360

    def draw_entity_box(self, color=(0.0, 0.0, 0.0)):
        glPushMatrix()
        glTranslatef(self.position[0], self.position[1], self.position[2])
        glRotatef(-self.position[3], 0, 1, 0)
        
        half_width = self.width / 2
        
        vertices = [
            (half_width, 0, half_width),
            (half_width, 0, -half_width),
            (-half_width, 0, -half_width),
            (-half_width, 0, half_width),
            (half_width, self.height, half_width),
            (half_width, self.height, -half_width),
            (-half_width, self.height, -half_width),
            (-half_width, self.height, half_width)
        ]
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7)
        ]
        
        glLineWidth(2.0)
        glColor3f(*color)
        glBegin(GL_LINES)
        for edge in edges:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()
        glLineWidth(1.0)
        glPopMatrix()

    def __repr__(self):
        speed = np.linalg.norm(self.velocity[:3])
        return f"Entity: position=({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f}, {self.position[3]:.2f}), speed={speed:.2f}"


class Player(Entity):
    def __init__(self, placement, max_speed, max_acceleration, friction_coefficient, jump_power, gravity, max_fall_velocity, width, max_attack_range=3.0, attack_cooldown=1.0):
        super().__init__(placement, max_speed, max_acceleration, friction_coefficient, jump_power, gravity, max_fall_velocity, width)
        self.is_attacking = False
        self.attack_timer = 0.0
        self.attack_duration = 0.2  # Attack lasts 0.2 seconds
        self.max_attack_range = max_attack_range  # Maximum distance the attack reaches
        
        # Cooldown logic
        self.attack_cooldown = attack_cooldown  # Cooldown time seconds
        self.cooldown_timer = 0.0  # Timer to track time until the next attack is allowed

    def update(self, keys, map_height, dt):  
        direction_angle = np.radians(self.position[3])
        
        if (self.position[1] - map_height) < self.width / 2:
            if keys[K_a]:
                self.rotate(-3)
            if keys[K_d]:
                self.rotate(3)
        
            move_left_right = 0
            move_forward_backward = 0
        
            self.apply_friction()
            
            if keys[K_LEFT] and not keys[K_RIGHT]:
                move_left_right -= 1
            if keys[K_RIGHT] and not keys[K_LEFT]:
                move_left_right += 1
            if keys[K_UP] and not keys[K_DOWN]:
                move_forward_backward += 1
            if keys[K_DOWN] and not keys[K_UP]:
                move_forward_backward -= 1
                    
            if move_left_right != 0 or move_forward_backward != 0:
                self.push([
                    move_left_right * np.cos(direction_angle) + move_forward_backward * np.sin(direction_angle),
                    move_left_right * np.sin(direction_angle) - move_forward_backward * np.cos(direction_angle)
                ])
            
            if keys[K_SPACE]:
                self.jump()
        
        else:
            self.apply_gravity()
            
        self.position += self.velocity

        if self.position[1] <= map_height:
            self.position[1] = map_height
            self.velocity[1] = 0
        
        # Handle cooldown before allowing another attack
        self.cooldown_timer += dt  # Increase the cooldown timer by the delta time
        if keys[K_m] and self.cooldown_timer >= self.attack_cooldown:  # Check if cooldown is finished
            self.melee_attack()
            self.cooldown_timer = 0.0  # Reset the cooldown timer after the attack
    
        # Update attack timer if an attack is in progress.
        if self.is_attacking:
            self.attack_timer += dt
            if self.attack_timer >= self.attack_duration:
                self.is_attacking = False
                self.attack_timer = 0.0
        

    def render(self):
        glPushMatrix()
        glTranslatef(self.position[0], self.position[1], self.position[2])
        glRotatef(-self.position[3], 0, 1, 0)
        
        quad = gluNewQuadric()
        
        theta = math.radians(self.position[3])
        x_relative_velocity = self.velocity[0] * math.cos(theta) + self.velocity[2] * math.sin(theta)
        z_relative_velocity = -self.velocity[0] * math.sin(theta) + self.velocity[2] * math.cos(theta)
        
        x_tilt = x_relative_velocity / self.max_speed * 90
        z_tilt = z_relative_velocity / self.max_speed * 90
        
        glPushMatrix()
        glTranslatef(0, self.height * (2/3), 0)  # Position the body
        glRotatef(90, 1, 0, 0)  # Original orientation of the cone
        glColor3f(0.5, 0.5, 0.5)  # Grey body
        
        # Tilt, print, untilt to show directional movement
        glRotatef(z_tilt, 1, 0, 0)
        glRotatef(-x_tilt, 0, 1, 0)
        gluCylinder(quad, self.width / 2, 0, self.height * (2/3), 50, 50)
        glRotatef(-z_tilt, 1, 0, 0)
        glRotatef(x_tilt, 0, 1, 0)

        glPopMatrix()

        # Draw the head (a sphere)
        glPushMatrix()
        glTranslatef(0, self.height * 5 / 6, 0)
        glColor3f(0.0, 0.0, 0.0)  # Black head
        gluSphere(quad, self.width / 3, 50, 50)
        
        glPopMatrix()

        gluDeleteQuadric(quad)

        # Render the melee attack animation (a spinning cone) if active.
        if self.is_attacking:
            glPushMatrix()
            glColor3f(0.0, 0.0, 0.0)  # Black attack shape

            # Compute progress (0.0 to 1.0) over the attack duration.
            progress = self.attack_timer / self.attack_duration  
            # Full spin: rotate 360 degrees over the attack.
            spin_angle = 360 * progress

            # The tip of the cone moves outward following a sine wave (peaking at progress=0.5).
            tip_distance = self.max_attack_range * np.sin(np.pi * progress)

            # Set the cone's pivot point halfway up the player's height.
            pivot_y = self.height / 2
            attack_offset = self.width * 0.5  # how far out from the pivot to place the cone

            glTranslatef(0, pivot_y, 0)  # Move the cone to the player’s center (halfway up the height)
            glRotatef(180, 0, 1, 0)
            glRotatef(spin_angle, 0, 1, 0)  # Spin the cone
            glTranslatef(0, 0, attack_offset)  # Move the cone out from the player

            cone_base_radius = self.width * 0.2
            quad = gluNewQuadric()
            gluCylinder(quad, cone_base_radius, 0.0, tip_distance, 20, 5)  # cone's tip moves in/out smoothly
            gluDeleteQuadric(quad)
            glPopMatrix()
        glPopMatrix()

    def melee_attack(self):
        if not self.is_attacking:
            self.is_attacking = True
            self.attack_timer = 0.0
    
    def get_attack_area(self):
        """
        Returns a tuple ((attack_center_x, attack_center_z), attack_radius)
        that lines up with the melee attack animation.
        The effective attack area is defined using the same attack_offset used
        in the animation (self.width * 0.5).
        """
        center = (self.position[0], self.position[2])  # Attack area centered on the player
        attack_radius = self.max_attack_range  # The radius extends to the tip of the cone.
        return center, attack_radius


class Enemy(Entity):
    def __init__(self, 
                 placement: tuple, 
                 max_speed: float, 
                 max_acceleration: float, 
                 friction_coefficient: int, 
                 jump_power: float, 
                 gravity: float, 
                 max_fall_velocity: float, 
                 width: float, 
                 max_health: float):
        super().__init__(placement, max_speed, max_acceleration, friction_coefficient, 
                         jump_power, gravity, max_fall_velocity, width)
        self.max_health = max_health
        self.health = max_health

    def take_damage(self, damage: float):
        self.health -= damage
        if self.health < 0:
            self.health = 0

    def is_alive(self):
        return self.health > 0

    def __repr__(self):
        return f"Enemy: position=({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f}), health={self.health}/{self.max_health}"


class EnemyManager:
    def __init__(self, mesh_map, spawn_radius, spawn_rate, group_spawn_size):
        self.mesh_map = mesh_map            # Reference to the mesh map for tile height lookups
        self.spawn_radius = spawn_radius    # Maximum distance from the player for spawning
        self.spawn_rate = spawn_rate        # Time (in seconds) between spawns
        self.group_spawn_size = group_spawn_size  # Average number of enemies per group
        self.enemies = []                   # List to hold enemies
        self.time_since_last_spawn = 0      # Timer to track spawn intervals

        self.attack_damage = 20  # Damage dealt per hit when the player attacks (I'll move this to player later)

    def spawn_enemy_group(self, player_position):
        """Spawn a group of enemies randomly within the spawn radius around the player."""
        group_size = int(self.group_spawn_size + random.uniform(-2, 2))
        for _ in range(group_size):
            spawn_distance = random.uniform(0, self.spawn_radius / 4) + self.spawn_radius
            spawn_angle = random.uniform(0, 2 * np.pi)
            x_offset = spawn_distance * np.cos(spawn_angle)
            z_offset = spawn_distance * np.sin(spawn_angle)
            spawn_position = (player_position[0] + x_offset, 0, player_position[2] + z_offset)
            spawn_height = self.mesh_map.get_tile_height((spawn_position[0], spawn_position[2]))
            enemy = Enemy(
                placement=(spawn_position[0], spawn_height, spawn_position[2], 0),
                max_speed=2,
                max_acceleration=0.1,
                friction_coefficient=0.7,
                jump_power=0.7,
                gravity=0.1,
                max_fall_velocity=-1.5,
                width=0.75,
                max_health=100
            )
            self.enemies.append(enemy)

    def update(self, player_position, dt):
        """Update enemy spawning and move all enemies toward the player.
           Also adjust each enemy's y position based on the terrain.
        """
        self.time_since_last_spawn += dt
        if self.time_since_last_spawn >= self.spawn_rate:
            self.spawn_enemy_group(player_position)
            self.time_since_last_spawn = 0

        # Move each enemy toward the player and fix y-position.
        for enemy in self.enemies:
            target = np.array(player_position[:3])
            enemy_pos = enemy.position[:3]
            direction = target - enemy_pos
            distance = np.linalg.norm(direction)
            if distance > 0:
                direction /= distance  # Normalize
                velocity = direction * enemy.max_speed
                enemy.position[:3] += velocity * dt

            # Adjust enemy's y-coordinate based on the terrain.
            tile_height = self.mesh_map.get_tile_height((enemy.position[0], enemy.position[2]))
            enemy.position[1] = tile_height

    def handle_player_attacks(self, attack_center, attack_radius):
        """
        Given the affected x,z coordinates of an attack and its effective radius,
        apply damage to any enemy within that area.
        """
        attack_center = np.array(attack_center)
        for enemy in self.enemies:
            enemy_pos = np.array([enemy.position[0], enemy.position[2]])
            distance = np.linalg.norm(attack_center - enemy_pos)
            if distance <= attack_radius:
                enemy.take_damage(self.attack_damage)
                
        # Remove any enemies that have died.
        self.enemies = [enemy for enemy in self.enemies if enemy.is_alive()]

    def render(self, player_position, distance):
        """Render all spawned enemies."""
        for enemy in self.enemies:
            position = enemy.get_position()
            absolute_distance = math.sqrt((player_position[0] - position[0])**2 + (player_position[2] - position[2])**2)
            if absolute_distance <= distance:
                enemy.draw_entity_box(color=(1.0, 1.0, 1.0))

    
    
    
    
    
# if __name__ == '__main__':
#     test = Entity(
#         placement=(0, 0, 0, 0),
#         max_speed=3,
#         max_acceleration=0.1,
#         friction_coefficient=0.05,
#         jump_power=5
#     )
#     input_velocity = [1, 1]
    
#     print(test)
#     for _ in range(50):
#         test.push(input_velocity)
#         test.apply_friction()
#         test.apply_gravity()
#         test.update(0)
#         print(test)
        

