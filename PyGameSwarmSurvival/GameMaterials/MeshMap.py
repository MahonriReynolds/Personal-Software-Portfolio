



import numpy as np
import pygame
from OpenGL.GL import *
import noise
import concurrent.futures
import math
import ctypes
import colorsys

class MeshMap:
    def __init__(self, chunk_width: int, render_distance: int, chunks_per_update: int, seed: int, scale: float, height_limit: int, initial_target: tuple = None):
        """
        Initialize the MeshMap.

        :param chunk_width: Number of tiles per chunk side.
        :param render_distance: Number of chunks to render in each direction from the target.
        :param chunks_per_update: Maximum number of chunks to complete (and create VBOs for) per update.
        :param seed: Seed for the noise generator.
        :param scale: Scale for noise generation.
        :param height_limit: Maximum height of the generated terrain.
        """
        self.__chunk_width = chunk_width
        self.__render_distance = render_distance
        self.__chunks_per_update = chunks_per_update
        self.__seed = seed
        self.__scale = scale
        self.__height_limit = height_limit

        # Dictionary to store generated chunks. Each key is a (chunk_x, chunk_z) tuple.
        self.__chunks = {}
        # Dictionary to store futures for chunks currently being generated.
        self.__chunk_futures = {}
        # Thread pool executor for async chunk data generation.
        self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=chunks_per_update)

        if initial_target is not None:
            self.__preload_initial(initial_target)
       
    def __preload_initial(self, target: tuple):
        """
        Preload all chunks within the render distance of the given target.
        This schedules all required chunk tasks and waits for them to complete,
        ensuring that the starting section of the map is generated as fast as possible.
        
        :param target: A tuple (x, z) representing the initial target position.
        """
        target_x, target_z = target
        current_chunk_x = math.floor(target_x / self.__chunk_width)
        current_chunk_z = math.floor(target_z / self.__chunk_width)
        # Get all required chunk coordinates.
        required_chunks = set()
        initial_distance = self.__render_distance * 2
        for dx in range(-initial_distance, initial_distance + 1):
            for dz in range(-initial_distance, initial_distance + 1):
                required_chunks.add((current_chunk_x + dx, current_chunk_z + dz))
        # Schedule tasks for any required chunk not yet generated.
        for coord in required_chunks:
            if coord not in self.__chunks and coord not in self.__chunk_futures:
                self.__chunk_futures[coord] = self.__executor.submit(
                    self.__generate_chunk_data, coord[0], coord[1]
                )
        # Wait for all tasks to complete.
        concurrent.futures.wait(list(self.__chunk_futures.values()))
        # Process all completed futures without breaking.
        for coord, future in list(self.__chunk_futures.items()):
            try:
                vertex_array, vertex_count = future.result()
                vbo = self.__create_vbo(vertex_array)
                self.__chunks[coord] = {
                    'vertices': vertex_array,
                    'vbo': vbo,
                    'vertex_count': vertex_count
                }
            except Exception as e:
                print(f"Error preloading chunk {coord}: {e}")
            del self.__chunk_futures[coord]
    
    def __generate_chunk_data(self, chunk_x: int, chunk_z: int):
        """
        Generate the vertex data for a chunk (without creating the VBO).
        The data is interleaved as [x, y, z, r, g, b] per vertex.
        In addition to the top faces of each tile, vertical walls are generated
        to connect a tile's top to its lower neighbor.
        This function is executed asynchronously.
        
        :param chunk_x: Chunk coordinate in x.
        :param chunk_z: Chunk coordinate in z.
        :return: A tuple (vertex_array, vertex_count)
        """
        grid_size = self.__chunk_width + 2
        heights = np.zeros((grid_size, grid_size), dtype=np.float32)
        
        # Compute heights for grid cells.
        # The tile at index [1,1] corresponds to the first tile in the chunk.
        start_x = chunk_x * self.__chunk_width
        start_z = chunk_z * self.__chunk_width
        
        for i in range(grid_size):
            for j in range(grid_size):
                # Compute world coordinates
                world_x = start_x + (i - 1)
                world_z = start_z + (j - 1)
                heights[i, j] = self.get_tile_height((world_x, world_z))

        vertices = []  # Holds vertex (x,y,z) and color (r,g,b)

        # Loop over each actual tile in the chunk.
        for i in range(1, self.__chunk_width+1):
            for j in range(1, self.__chunk_width+1):
                tile_height = heights[i, j]
                # World position of the tile's bottom-left corner.
                world_x = start_x + (i - 1)
                world_z = start_z + (j - 1)
                # Get top-face color.
                top_color = self.__get_color(tile_height)
                
                # Top face triangles
                p1 = (world_x,       tile_height, world_z)
                p2 = (world_x + 1,   tile_height, world_z)
                p3 = (world_x + 1,   tile_height, world_z + 1)
                p4 = (world_x,       tile_height, world_z + 1)
                # Triangle 1: p1, p2, p3
                vertices.extend(p1 + top_color)
                vertices.extend(p2 + top_color)
                vertices.extend(p3 + top_color)
                # Triangle 2: p1, p3, p4
                vertices.extend(p1 + top_color)
                vertices.extend(p3 + top_color)
                vertices.extend(p4 + top_color)

                # For each of the four sides, check the neighbor height.
                # Generate a wall if tile is higher than neighbor.
                # Define neighbor offsets and corresponding edge vertex positions.
                # (di, dj, (local top edge start), (local top edge end))
                # Local coordinates: (0,0) is bottom-left of the tile; (1,1) is top-right.
                sides = [
                    (0, 1,  ((0, 1), (1, 1))),  # North edge: top edge (p4 to p3)
                    (0, -1, ((0, 0), (1, 0))),  # South edge: bottom edge (p1 to p2)
                    (1, 0,  ((1, 0), (1, 1))),  # East edge: right edge (p2 to p3)
                    (-1, 0, ((0, 0), (0, 1)))   # West edge: left edge (p1 to p4)
                ]
                for di, dj, ((lx0, lz0), (lx1, lz1)) in sides:
                    neighbor_height = heights[i + di, j + dj]
                    # Only create a wall if there's a gap.
                    if tile_height > neighbor_height:
                        # For wall color, darken the tile's top color.
                        wall_color = tuple(c * 0.7 for c in top_color)
                        # Compute the two top edge vertices in world space.
                        # For a tile, local x and z positions: add to world_x and world_z.
                        top_edge_start = (world_x + lx0, tile_height, world_z + lz0)
                        top_edge_end   = (world_x + lx1, tile_height, world_z + lz1)
                        # The bottom edge corresponds to the neighbor's height.
                        bottom_edge_start = (world_x + lx0, neighbor_height, world_z + lz0)
                        bottom_edge_end   = (world_x + lx1, neighbor_height, world_z + lz1)
                        # Create two triangles for the vertical quad.
                        # Triangle 1: top_edge_start, bottom_edge_start, bottom_edge_end
                        vertices.extend(top_edge_start + wall_color)
                        vertices.extend(bottom_edge_start + wall_color)
                        vertices.extend(bottom_edge_end + wall_color)
                        # Triangle 2: top_edge_start, bottom_edge_end, top_edge_end
                        vertices.extend(top_edge_start + wall_color)
                        vertices.extend(bottom_edge_end + wall_color)
                        vertices.extend(top_edge_end + wall_color)

        vertex_array = np.array(vertices, dtype=np.float32)
        vertex_count = len(vertex_array) // 6  # 6 floats per vertex.
        return vertex_array, vertex_count

    def __create_vbo(self, vertices: np.ndarray):
        """
        Create an OpenGL VBO from vertex data.
        This must run on the main thread.
        
        :param vertices: A numpy array of interleaved vertex and color data.
        :return: The VBO id.
        """
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        return vbo

    def __get_color(self, height: float):
        """
        Determine a color based on the height value.
        
        :param height: The y value or height.
        :return: A tuple (r, g, b) with values in the range [0, 1].
        """
        normalized = height / self.__height_limit
        r, g, b = colorsys.hsv_to_rgb(normalized, 1, 1)
        return (r, g, b)
     
    def update(self, target):
        """
        Update the map given a target position. This method ensures that
        all chunks within the render distance are generated (or queued for generation)
        and processes a limited number of completed asynchronous tasks per update cycle.
        
        :param target: An (x, z) iterable indicating the center position.
        """
        target_x, target_z = target
        current_chunk_x = math.floor(target_x / self.__chunk_width)
        current_chunk_z = math.floor(target_z / self.__chunk_width)

        # Determine required chunk coordinates based on render_distance.
        required_chunks = set()
        for dx in range(-self.__render_distance, self.__render_distance + 1):
            for dz in range(-self.__render_distance, self.__render_distance + 1):
                chunk_coord = (current_chunk_x + dx, current_chunk_z + dz)
                required_chunks.add(chunk_coord)
                if chunk_coord not in self.__chunks and chunk_coord not in self.__chunk_futures:
                    # Queue async gen of chunk data.
                    self.__chunk_futures[chunk_coord] = self.__executor.submit(
                        self.__generate_chunk_data, chunk_coord[0], chunk_coord[1]
                    )

        # Process a limited number of async tasks.
        processed = 0
        for coord, future in list(self.__chunk_futures.items()):
            if processed >= self.__chunks_per_update:
                break
            if future.done():
                try:
                    vertex_array, vertex_count = future.result()
                    # Create the VBO on the main thread.
                    vbo = self.__create_vbo(vertex_array)
                    self.__chunks[coord] = {
                        'vertices': vertex_array,
                        'vbo': vbo,
                        'vertex_count': vertex_count
                    }
                except Exception as e:
                    print(f"Error generating chunk {coord}: {e}")
                del self.__chunk_futures[coord]
                processed += 1

    def render(self, target):
        """
        Render only the chunks that fall within the render distance of the given target.
        The method uses the target position to compute which chunks to draw, binds their VBOs,
        and issues draw calls.
        
        :param target: An (x, z) iterable indicating the center position.
        """
        target_x, target_z = target
        current_chunk_x = math.floor(target_x / self.__chunk_width)
        current_chunk_z = math.floor(target_z / self.__chunk_width)

        # Determine the set of chunk coordinates that should be rendered.
        visible_chunks = set()
        for dx in range(-self.__render_distance, self.__render_distance + 1):
            for dz in range(-self.__render_distance, self.__render_distance + 1):
                visible_chunks.add((current_chunk_x + dx, current_chunk_z + dz))

        # Render only the visible chunks using the fixed-function pipeline.
        stride = 6 * 4  # 6 floats per vertex, 4 bytes each
        for coord, chunk in self.__chunks.items():
            if coord in visible_chunks:
                glBindBuffer(GL_ARRAY_BUFFER, chunk['vbo'])
                glEnableClientState(GL_VERTEX_ARRAY)
                glVertexPointer(3, GL_FLOAT, stride, ctypes.c_void_p(0))
                glEnableClientState(GL_COLOR_ARRAY)
                glColorPointer(3, GL_FLOAT, stride, ctypes.c_void_p(12))
                
                glDrawArrays(GL_TRIANGLES, 0, chunk['vertex_count'])
                
                glDisableClientState(GL_VERTEX_ARRAY)
                glDisableClientState(GL_COLOR_ARRAY)
                glBindBuffer(GL_ARRAY_BUFFER, 0)

    def cleanup(self):
        """
        Flush all generated chunks and pending asynchronous tasks.
        This will delete all VBOs and clear the chunk dictionary.
        """
        for chunk in self.__chunks.values():
            glDeleteBuffers(1, [chunk['vbo']])
        self.__chunks.clear()
        for future in self.__chunk_futures.values():
            future.cancel()
        self.__chunk_futures.clear()

    def get_tile_height(self, pos: tuple) -> float:
        """
        Public method: Given a tuple (x, z), compute and return the height of the tile at that position.
        
        :param pos: A tuple (x, z) representing world coordinates.
        :return: The height at that tile, based on noise generation.
        """
        x, z = pos
        base_noise = noise.pnoise2(
            x * self.__scale,
            z * self.__scale,
            octaves=4,
            persistence=0.5,
            lacunarity=2.0,
            repeatx=1024,
            repeaty=1024,
            base=self.__seed
        )
        # Normalize noise to [0, 1] then scale to height_limit.
        normalized_noise = (base_noise + 1) / 2
        y = (normalized_noise **5 ) * self.__height_limit
        return y










if __name__ == '__main__':
    import sys
    import math
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
    import numpy as np
    import noise  # pip install noise
    import concurrent.futures
    
    # Initialize pygame and create an OpenGL-enabled window.
    pygame.init()
    display = (1500, 900)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("MeshMap Demo")

    # Set up basic OpenGL state.
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.5, 0.7, 1.0, 1.0)  # light blue sky background

    # Setup perspective projection.
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (display[0] / display[1]), 0.1, 100000.0)
    glMatrixMode(GL_MODELVIEW)

    # Create an instance of MeshMap.
    max_height = 1000
    rendering = 30
    mesh_map = MeshMap(chunk_width=16, render_distance=rendering, chunks_per_update=6, seed=42, scale=0.005, height_limit=max_height, initial_target=(0, 0))

    # Starting target position (x, z). We'll update this with arrow keys.
    target = [0.0, 0.0]

    clock = pygame.time.Clock()
    running = True

    # Camera parameters.
    camera_height = max_height + 10
    camera_distance = max_height + 100

    while running:
        dt = clock.tick(60)  # Limit to 60 FPS.
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        # Get the state of all keys.
        keys = pygame.key.get_pressed()
        move_speed = 0.1 * dt  # Adjust speed based on delta time for smooth movement

        # Update target position continuously based on arrow keys.
        if keys[K_LEFT]:
            target[0] -= move_speed
        if keys[K_RIGHT]:
            target[0] += move_speed
        if keys[K_UP]:
            target[1] -= move_speed
        if keys[K_DOWN]:
            target[1] += move_speed
        
        
        
        # Clear the screen and depth buffer.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Position the camera above and behind the target using gluLookAt.
        camera_x = target[0]
        camera_y = camera_height
        camera_z = target[1] + camera_distance
        gluLookAt(camera_x, camera_y, camera_z,  # Camera position.
                  target[0], 0, target[1],       # Look-at position (target).
                  0, 1, 0)                      # Up vector.

        # Update and render the MeshMap using the current target position.
        mesh_map.update(target)
        mesh_map.render(target)

        pygame.display.flip()

    # On exit, flush all chunks and cleanup OpenGL resources.
    mesh_map.cleanup()
    pygame.quit()
    sys.exit()









