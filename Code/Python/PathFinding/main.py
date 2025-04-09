import pygame
import heapq
import math
from shapely.geometry import LineString, Polygon

# Constants
WIDTH, HEIGHT = 800, 600
WHITE, BLACK, GRAY, RED, GREEN, BLUE, YELLOW = (255, 255, 255), (0, 0, 0), (180, 180, 180), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)

class Node:
    def __init__(self, pos, cost, heuristic):
        self.pos = pos
        self.cost = cost
        self.heuristic = heuristic
        self.total_cost = cost + heuristic
        self.parent = None

    def __lt__(self, other):
        return self.total_cost < other.total_cost

def heuristic(p1, p2):
    """Euclidean distance heuristic."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def is_line_clear(line, obstacles):
    """Check if a line segment is free of obstacles."""
    return all(not line.intersects(obs) for obs in obstacles)

def build_visibility_graph(border, obstacles, start, target):
    """Create a visibility graph for pathfinding."""
    nodes = [start, target]  # Start with start and target
    obstacle_polygons = [Polygon(obs) for obs in obstacles]

    for obs in obstacles:
        nodes.extend(obs)  # Add corners of obstacles

    edges = []
    print(nodes)
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            line = LineString([nodes[i], nodes[j]])
            if is_line_clear(line, obstacle_polygons):
                edges.append((nodes[i], nodes[j], heuristic(nodes[i], nodes[j])))

    return nodes, edges

def astar_visibility_graph(start, target, nodes, edges, draw_callback):
    """A* search on the visibility graph."""
    open_set = []
    start_node = Node(start, 0, heuristic(start, target))
    heapq.heappush(open_set, start_node)
    
    node_map = {start: start_node}
    came_from = {}
    print(edges)
    while open_set:
        current = heapq.heappop(open_set)
        draw_callback(current.pos, "visited")  # Animate search

        if current.pos == target:
            path = []
            while current.pos in came_from:
                path.append(current.pos)
                current = came_from[current.pos]
            path.append(start)
            print("Path found:", path[::-1])
            return path[::-1]

        for neighbor, end, cost in edges:
            if neighbor == current.pos:
                new_cost = current.cost + cost
                if end not in node_map or new_cost < node_map[end].cost:
                    new_node = Node(end, new_cost, heuristic(end, target))
                    new_node.parent = current
                    heapq.heappush(open_set, new_node)
                    node_map[end] = new_node
                    came_from[end] = current
    print("No path found")
    return None  # No path found

def visualize(border, obstacles, start, target):
    """Pygame visualization of pathfinding."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Visibility Graph A* Pathfinding")
    clock = pygame.time.Clock()
    
    def draw_callback(pos, state):
        """Draw function to visualize search progress."""
        color = GRAY if state == "visited" else YELLOW
        pygame.draw.circle(screen, color, (int(pos[0]), int(pos[1])), 3)
        pygame.display.update()
        pygame.time.delay(10)

    running = True
    screen.fill(WHITE)

    # Draw border
    pygame.draw.rect(screen, BLACK, (border[0][0], border[0][1], border[1][0] - border[0][0], border[2][1] - border[0][1]), 2)

    # Draw obstacles
    for obs in obstacles:
        pygame.draw.polygon(screen, RED, obs)

    # Draw start and target
    pygame.draw.circle(screen, GREEN, start, 8)
    pygame.draw.circle(screen, BLUE, target, 8)

    # Build visibility graph and run A*
    nodes, edges = build_visibility_graph(border, obstacles, start, target)

    # Draw visibility edges
    for n1, n2, _ in edges:
        pygame.draw.line(screen, GRAY, n1, n2, 1)

    pygame.display.update()
    path = astar_visibility_graph(start, target, nodes, edges, draw_callback)

    # Draw the final shortest path
    if path:
        for i in range(len(path) - 1):
            pygame.draw.line(screen, RED, path[i], path[i + 1], 3)

    pygame.display.update()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.quit()

# Example Usage
border = [(50, 50), (750, 50), (750, 550), (50, 550)]
obstacles = [[(200, 200), (300, 200), (300, 300), (200, 300)],
             [(400, 150), (500, 150), (500, 250), (400, 250)],
             [(600, 400), (700, 400), (700, 500), (600, 500)]]
start = (100, 100)
target = (600, 530)

visualize(border, obstacles, start, target)