import math
import heapq
import tkinter as tk
from tkinter import Canvas

def is_inside_rectangle(point, rect):
    """Checks if a point is inside a rectangle (inclusive of borders)."""
    x, y = point
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2

def line_segment_intersects_rectangle(p1, p2, rect):
    """Checks if a line segment intersects a rectangle."""
    # Check if endpoints are inside
    if is_inside_rectangle(p1, rect) or is_inside_rectangle(p2, rect):
        return True

    x1r, y1r, x2r, y2r = rect

    # Check if any of the rectangle's edges intersect the line segment
    def intersect(a, b, c, d):
        """Helper function to check if line segment (a,b) intersects (c,d)"""
        def ccw(p, q, r):
            val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
            if val == 0: return 0  # Collinear
            return 1 if val > 0 else 2 # Clockwise or Counterclockwise

        return (ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d))

    # Top edge
    if intersect(p1, p2, (x1r, y1r), (x2r, y1r)): return True
    # Bottom edge
    if intersect(p1, p2, (x1r, y2r), (x2r, y2r)): return True
    # Left edge
    if intersect(p1, p2, (x1r, y1r), (x1r, y2r)): return True
    # Right edge
    if intersect(p1, p2, (x2r, y1r), (x2r, y2r)): return True

    return False

def find_shortest_path(border, obstacles, start, target):
    """
    Finds the shortest path in a continuous 2D space avoiding rectangular obstacles.

    Args:
        border: A tuple (x1, y1, x2, y2) representing the border rectangle.
        obstacles: A list of tuples, where each tuple (x1, y1, x2, y2)
                   represents an obstacle rectangle.
        start: A tuple (x, y) representing the starting point.
        target: A tuple (x, y) representing the target point.

    Returns:
        A list of tuples representing the shortest path from start to target,
        or None if no path is found.
    """

    if not is_inside_rectangle(start, border) or not is_inside_rectangle(target, border):
        return None  # Start or target outside the border

    for obs in obstacles:
        if is_inside_rectangle(start, obs) or is_inside_rectangle(target, obs):
            return None  # Start or target inside an obstacle

    open_set = [(0, start, [])]  # (cost, current_point, path)
    visited = {start}

    while open_set:
        cost, current, path = heapq.heappop(open_set)

        if current == target:
            return path + [target]

        # Consider direct connection to the target
        can_reach_target = True
        for obs in obstacles:
            if line_segment_intersects_rectangle(current, target, obs):
                can_reach_target = False
                break
        if can_reach_target:
            return path + [target]

        # Generate potential next points (simplified - could be improved)
        # Here we consider moving towards the target and the corners of obstacles
        potential_next_points = [target]

        # Add corners of all obstacles as potential waypoints
        for x1, y1, x2, y2 in obstacles:
            potential_next_points.extend([(x1, y1), (x2, y1), (x1, y2), (x2, y2)])

        # Add some intermediate points on the line towards the target (optional, but can help)
        num_intermediate = 5
        for i in range(1, num_intermediate + 1):
            intermediate_x = current[0] + (target[0] - current[0]) * i / (num_intermediate + 1)
            intermediate_y = current[1] + (target[1] - current[1]) * i / (num_intermediate + 1)
            if is_inside_rectangle((intermediate_x, intermediate_y), border):
                potential_next_points.append((intermediate_x, intermediate_y))

        for next_point in set(potential_next_points): # Use set to avoid duplicates
            if next_point == current or next_point in visited:
                continue

            # Check if the path to the next point is valid (within border and doesn't intersect obstacles)
            is_valid = is_inside_rectangle(next_point, border)
            if is_valid:
                for obs in obstacles:
                    if line_segment_intersects_rectangle(current, next_point, obs):
                        is_valid = False
                        break

            if is_valid:
                new_cost = cost + math.sqrt((next_point[0] - current[0])**2 + (next_point[1] - current[1])**2)
                heapq.heappush(open_set, (new_cost, next_point, path + [current]))
                visited.add(next_point)

    return None

def simulate_path(border, obstacles, path, start, target):
    """
    Simulates the path using Tkinter.

    Args:
        border: A tuple (x1, y1, x2, y2) representing the border rectangle.
        obstacles: A list of tuples, where each tuple (x1, y1, x2, y2)
                   represents an obstacle rectangle.
        path: A list of tuples representing the path.
        start: A tuple (x, y) representing the starting point.
        target: A tuple (x, y) representing the target point.
    """
    if not path:
        print("No path to simulate.")
        return

    master = tk.Tk()
    master.title("Shortest Path Simulation")

    min_x = min(border[0], min(obs[0] for obs in obstacles) if obstacles else border[0], start[0], target[0], min(p[0] for p in path) if path else border[0])
    min_y = min(border[1], min(obs[1] for obs in obstacles) if obstacles else border[1], start[1], target[1], min(p[1] for p in path) if path else border[1])
    max_x = max(border[2], max(obs[2] for obs in obstacles) if obstacles else border[2], start[0], target[0], max(p[0] for p in path) if path else border[2])
    max_y = max(border[3], max(obs[3] for obs in obstacles) if obstacles else border[3], start[1], target[1], max(p[1] for p in path) if path else border[3])

    canvas_width = 800
    canvas_height = 600
    canvas = Canvas(master, width=canvas_width, height=canvas_height, bg="white")
    canvas.pack()

    def scale_coords(x, y):
        scaled_x = canvas_width * (x - min_x) / (max_x - min_x) if (max_x - min_x) != 0 else canvas_width / 2
        scaled_y = canvas_height * (y - min_y) / (max_y - min_y) if (max_y - min_y) != 0 else canvas_height / 2
        return scaled_x, canvas_height - scaled_y  # Flip y for Tkinter

    # Draw border
    bx1, by1, bx2, by2 = border
    sc_bx1, sc_by1 = scale_coords(bx1, by1)
    sc_bx2, sc_by2 = scale_coords(bx2, by2)
    canvas.create_rectangle(sc_bx1, sc_by1, sc_bx2, sc_by2, outline="black")

    # Draw obstacles
    for ox1, oy1, ox2, oy2 in obstacles:
        sc_ox1, sc_oy1 = scale_coords(ox1, oy1)
        sc_ox2, sc_oy2 = scale_coords(ox2, oy2)
        canvas.create_rectangle(sc_ox1, sc_oy1, sc_ox2, sc_oy2, fill="red")

    # Draw start and target
    sc_start_x, sc_start_y = scale_coords(start[0], start[1])
    sc_target_x, sc_target_y = scale_coords(target[0], target[1])
    canvas.create_oval(sc_start_x - 5, sc_start_y - 5, sc_start_x + 5, sc_start_y + 5, fill="green")
    canvas.create_oval(sc_target_x - 5, sc_target_y - 5, sc_target_x + 5, sc_target_y + 5, fill="blue")

    # Draw path
    if path:
        scaled_path = [scale_coords(p[0], p[1]) for p in path]
        for i in range(len(scaled_path) - 1):
            canvas.create_line(scaled_path[i], scaled_path[i+1], fill="purple", width=2)

    master.mainloop()

if __name__ == "__main__":
    border = (0, 0, 10, 10)
    obstacles = [(2, 2, 4, 4), (6, 6, 8, 8)]
    start_point = (1, 1)
    target_point = (9, 9)

    path = find_shortest_path(border, obstacles, start_point, target_point)

    if path:
        print("Shortest Path:", path)
        simulate_path(border, obstacles, path, start_point, target_point)
    else:
        print("No path found.")

    print("\n--- Another Example ---")
    border2 = (0, 0, 20, 15)
    obstacles2 = [(3, 2, 7, 5), (10, 8, 15, 12), (1, 10, 5, 14)]
    start_point2 = (2, 1)
    target_point2 = (18, 13)

    path2 = find_shortest_path(border2, obstacles2, start_point2, target_point2)

    if path2:
        print("Shortest Path:", path2)
        simulate_path(border2, obstacles2, path2, start_point2, target_point2)
    else:
        print("No path found.")

    print("\n--- Example with no path ---")
    border3 = (0, 0, 10, 10)
    obstacles3 = [(0, 5, 10, 6)]
    start_point3 = (1, 1)
    target_point3 = (9, 9)

    path3 = find_shortest_path(border3, obstacles3, start_point3, target_point3)

    if path3:
        print("Shortest Path:", path3)
        simulate_path(border3, obstacles3, path3, start_point3, target_point3)
    else:
        print("No path found.")