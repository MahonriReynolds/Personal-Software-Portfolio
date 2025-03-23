# Overview

This project was written to explore working with a game engine and I chose PyGame because I enjoy working with Python. The purpose of this was to learn how to use a technology I hadn't used before and have some fun doing it. 

The game takes place on a procedurally generated world, where the map is divided into chunks with each chunk being a grid of tiles. The map is generated using perlin noise and chunks are generated in async to keep it running smoothly. 
The camera can be controlled with w (look up), s (look down), a (look right), d (look left), q (zoom in), and e (zoom out). The a and d keys are actually player movements to rotate the player and the camera just follows. The camera automatically zooms in when it collides with the map and automatically zooms back out when it no longer collides. The player can be moved with the arrow keys which operate in relation to the player's position. The m key can be used for a melee attack which deals damage to enemies within range. 
Enemies spawn regularly and track towards the player. The goal was for their collision with the player to deal damage and the player would fend them off. 

As of now, the game is incomplete and has no actual gameplay aside from enemy bounding boxes that spawn and track towards the player. The player can attack them but that is all. 

[Software Demo Video](https://youtu.be/gxcTTxbzFYQ)

# Development Environment

- Python 3.12
    - noise 1.2.2
    - pygame 2.6.1
    - PyOpenGL 3.1.9
    - numpy 2.1.3
- VSCode 1.98.2

# Useful Websites

{Make a list of websites that you found helpful in this project}
* [PIP PyOpenGL Docs](https://pypi.org/project/PyOpenGL/)
* [Geeks For Geeks on PyGame](https://www.geeksforgeeks.org/pygame-tutorial/)
* [Kronos Thread On glDrawArrays() With VBO](https://community.khronos.org/t/how-to-use-gldrawarrays-with-vbo-vertex-buffer-object-to-display-stl-geometry/71155)

# Future Work
* Add second attack
* Add cooldown indicators
* Make render model for Enemy class
* Add full combat
* Add leveling system
* Add skill / stat upgrades
* Set new map colors