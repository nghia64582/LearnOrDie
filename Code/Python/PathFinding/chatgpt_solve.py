import math
from heapq import heappush, heappop
import tkinter as tk
import pygame
import sys
import time
import random

def point_distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def line_intersects_rect(p1, p2, rect):
    x1, y1, x2, y2 = rect
    # Define 4 borders of the rectangle
    borders = [
        ((x1, y1), (x2, y1)),  # top
        ((x2, y1), (x2, y2)),  # right
        ((x2, y2), (x1, y2)),  # bottom
        ((x1, y2), (x1, y1))   # left
    ]
    for border in borders:
        if segments_intersect(p1, p2, border[0], border[1]):
            return True
    return False

def ccw(A, B, C):
    return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])

def segments_intersect(A, B, C, D):
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

def is_visible(p1, p2, obstacles):
    for rect in obstacles:
        if line_intersects_rect(p1, p2, rect):
            return False
    return True

def get_corners(rect):
    x1, y1, x2, y2 = rect
    return [(x1, y1), (x1, y2), (x2, y1), (x2, y2)]

def find_shortest_path(start, target, obstacles):
    startTime = time.time()
    nodes = [start, target]
    for rect in obstacles:
        nodes.extend(get_corners(rect))

    graph = {tuple(p): [] for p in nodes}
    
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            p1, p2 = nodes[i], nodes[j]
            if is_visible(p1, p2, obstacles):
                dist = point_distance(p1, p2)
                graph[tuple(p1)].append((dist, tuple(p2)))
                graph[tuple(p2)].append((dist, tuple(p1)))

    # Dijkstra's Algorithm
    start = tuple(start)
    target = tuple(target)
    queue = [(0, start, [])]
    visited = set()
    count = 0 
    while queue:
        count += 1
        cost, node, path = heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        path = path + [node]
        if node == target:
            print(f"Time taken: {time.time() - startTime:.2f} seconds")
            print(f"Path found in {count} iterations")
            return path
        for dist, neighbor in graph[node]:
            if neighbor not in visited:
                heappush(queue, (cost + dist, neighbor, path))

    return []  # No path found

def simulate_path_pygame(start, target, obstacles, path):
    SCALE = 0.6
    WIDTH, HEIGHT = 600, 600
    FPS = 6

    def scale(p): return int(p[0]*SCALE), int(p[1]*SCALE)

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Shortest Path Visualization")
    clock = pygame.time.Clock()

    running = True
    while running:
        screen.fill((255, 255, 255))  # White background

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # === Draw Filled Obstacles ===
        for i, rect in enumerate(obstacles):
            x1, y1, x2, y2 = [c * SCALE for c in rect]
            fill_color = (80, 80, 80) if i == 0 else (160, 160, 160)  # Border vs other obstacles
            border_color = (0, 0, 0)

            pygame.draw.rect(screen, fill_color, pygame.Rect(x1, y1, x2 - x1, y2 - y1))        # Fill
            pygame.draw.rect(screen, border_color, pygame.Rect(x1, y1, x2 - x1, y2 - y1), 1)    # Border

        # === Draw Path ===
        if path:
            for i in range(len(path) - 1):
                pygame.draw.line(screen, (0, 0, 255), scale(path[i]), scale(path[i+1]), 3)

        # === Draw Start & Target ===
        pygame.draw.circle(screen, (0, 200, 0), scale(start), 6)  # Green = Start
        pygame.draw.circle(screen, (200, 0, 0), scale(target), 6)  # Red = Target

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

def get_random_obstacle():
    x1 = random.randint(50, 900)
    y1 = random.randint(50, 900)
    x2 = x1 + random.randint(30, 50)
    y2 = y1 + random.randint(30, 50)
    return (x1, y1, x2, y2)

if __name__ == "__main__":
    # Define border box (used as obstacle)
    border = (0, 0, 1000, 1000)
    # Obstacles
    obstacles = [
        get_random_obstacle() for _ in range(100)
    ]
    start = (10, 10)
    target = (950, 950)
    path = find_shortest_path(start, target, obstacles)
    print("Path:", path)
    simulate_path_pygame(start, target, obstacles, path)
