import pygame
from pygame.locals import *
from Entity import Player, EnemyManager
from Camera import Camera
from MeshMap import MeshMap



# Fix enemy render distances
# Couple time with spawning
# Add second attack
# Add cooldown indicators
# Make render model for Enemy class
# Add combat
# Add leveling system
# Add skill / stat upgrades
# Fix player tilting
# Set map colors




# Main Loop
def main():
    # Set up pygame to use opengl
    pygame.init()
    display = (1500, 900)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Demo")
    
    # Set basic conditions
    render_distance = 10
    chunk_width = 10
    start_placement = (0, 0, 0, 45)  # (x, y, z, r)
    
    # Make the mesh map which handles everything map related
    mesh_map = MeshMap(
        chunk_width=chunk_width,
        render_distance=render_distance,
        chunks_per_update=1,
        seed=48,
        scale=0.003,
        height_limit=1000,
        initial_target=(start_placement[0], start_placement[2])
    )
    
    # Make the player character which also takes in key controls
    player = Player(
        placement=start_placement,
        max_speed=2,
        max_acceleration=0.1,
        friction_coefficient=0.7,
        jump_power=0.7,
        gravity=0.1,
        max_fall_velocity=-1.5,
        width=0.75,
        max_attack_range=3.0,
        attack_cooldown=1.0
    )
    
    # Make the camera which also takes in key controls
    camera = Camera(player, mesh_map, display, render_distance * chunk_width * 10)
    
    # Make the enemy manager to handle enemy behavior
    enemy_manager = EnemyManager(
        mesh_map = mesh_map,
        spawn_radius=(render_distance * chunk_width),
        spawn_rate=2,
        group_spawn_size=4,
    )
    
    # Main game loop
    clock = pygame.time.Clock()
    running = True
    while running: 
        # Limit fps to 60 and get the delta of each loop
        dt = clock.tick(60) / 1000.0 
        # Quit script if pygame quits
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
                mesh_map.cleanup()
        
        # Get keys pressed this loop
        keys = pygame.key.get_pressed()
        
        # Update user control related items
        player_pos = player.get_position()
        tile_height = mesh_map.get_tile_height((player_pos[0], player_pos[2]))
        player.update(keys, tile_height, dt)
        camera.update(keys)
        
        # Update independent logic and render everything
        camera.apply()
        mesh_map.update((player_pos[0], player_pos[2]))
        mesh_map.render((player_pos[0], player_pos[2]))
        # player.draw_entity_box()
        player.render()
        
        # Manage all enemy behaviors 
        enemy_manager.update(player.get_position(), dt)
        if player.is_attacking:
            attack_center, attack_radius = player.get_attack_area()
            enemy_manager.handle_player_attacks(attack_center, attack_radius)
        # Render all enemies
        enemy_manager.render(player_pos, ((render_distance + 1) * chunk_width))
        
        # Flip the pygame buffer for the next loop
        pygame.display.flip()









        

if __name__ == '__main__':
    
    import cProfile
    cProfile.run('main()')



