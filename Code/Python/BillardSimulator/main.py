import pygame
import math
import sys

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 800, 600
BALL_RADIUS = 15
CUSHION_WIDTH = 20
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 128, 0)
BROWN = (139, 69, 19)
TARGET_TRAJECTORY = (255, 165, 0)  # Orange color for target ball trajectory
DASH_LENGTH = 10  # Length of each dash in the dashed line

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Billiard Simulation")
clock = pygame.time.Clock()

class Ball:
    def __init__(self, x, y, color, is_cue=False):
        self.x = x
        self.y = y
        self.radius = BALL_RADIUS
        self.color = color
        self.velocity_x = 0
        self.velocity_y = 0
        self.is_cue = is_cue
        self.friction = 0.99  # Friction coefficient

    def move(self):
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        # Apply friction
        self.velocity_x *= self.friction
        self.velocity_y *= self.friction
        
        # Stop the ball if velocity is very small
        if abs(self.velocity_x) < 0.1 and abs(self.velocity_y) < 0.1:
            self.velocity_x = 0
            self.velocity_y = 0

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        if self.is_cue:
            # Draw a small white dot to indicate the cue ball
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), 3)

    def check_cushion_collision(self):
        # Left cushion
        if self.x - self.radius < CUSHION_WIDTH:
            self.x = CUSHION_WIDTH + self.radius
            self.velocity_x = -self.velocity_x
        # Right cushion
        if self.x + self.radius > WIDTH - CUSHION_WIDTH:
            self.x = WIDTH - CUSHION_WIDTH - self.radius
            self.velocity_x = -self.velocity_x
        # Top cushion
        if self.y - self.radius < CUSHION_WIDTH:
            self.y = CUSHION_WIDTH + self.radius
            self.velocity_y = -self.velocity_y
        # Bottom cushion
        if self.y + self.radius > HEIGHT - CUSHION_WIDTH:
            self.y = HEIGHT - CUSHION_WIDTH - self.radius
            self.velocity_y = -self.velocity_y

def predict_cushion_collision(x, y, vx, vy):
    # Predict where the ball will hit the cushion
    while True:
        x += vx
        y += vy
        
        # Check if we hit a cushion
        if x - BALL_RADIUS < CUSHION_WIDTH:
            return (CUSHION_WIDTH + BALL_RADIUS, y - (x - CUSHION_WIDTH - BALL_RADIUS) * (vy/vx)), (-vx, vy)
        if x + BALL_RADIUS > WIDTH - CUSHION_WIDTH:
            return (WIDTH - CUSHION_WIDTH - BALL_RADIUS, y + (x + BALL_RADIUS - (WIDTH - CUSHION_WIDTH)) * (vy/vx)), (-vx, vy)
        if y - BALL_RADIUS < CUSHION_WIDTH:
            return (x - (y - CUSHION_WIDTH - BALL_RADIUS) * (vx/vy), CUSHION_WIDTH + BALL_RADIUS), (vx, -vy)
        if y + BALL_RADIUS > HEIGHT - CUSHION_WIDTH:
            return (x + (y + BALL_RADIUS - (HEIGHT - CUSHION_WIDTH)) * (vx/vy), HEIGHT - CUSHION_WIDTH - BALL_RADIUS), (vx, -vy)

def predict_ball_collision(cue_x, cue_y, target_x, target_y, vx, vy):
    # Check if the trajectory will hit the target ball
    dx = target_x - cue_x
    dy = target_y - cue_y
    distance = math.sqrt(dx**2 + dy**2)
    
    # Calculate the angle between the velocity vector and the line to the target ball
    velocity_angle = math.atan2(vy, vx)
    target_angle = math.atan2(dy, dx)
    angle_diff = abs(velocity_angle - target_angle)
    
    # Calculate the minimum distance between the trajectory and the target ball
    min_distance = distance * math.sin(angle_diff)
    
    if min_distance < 2 * BALL_RADIUS:
        # Calculate the point of collision
        collision_distance = distance * math.cos(angle_diff) - math.sqrt((2 * BALL_RADIUS)**2 - min_distance**2)
        collision_x = cue_x + collision_distance * math.cos(velocity_angle)
        collision_y = cue_y + collision_distance * math.sin(velocity_angle)
        
        # Calculate the new velocities after collision
        angle = math.atan2(dy, dx)
        sin = math.sin(angle)
        cos = math.cos(angle)
        
        # Rotate velocities
        vx1 = vx * cos + vy * sin
        vy1 = vy * cos - vx * sin
        
        # Exchange velocities (simplified collision)
        new_vx = vx1 * cos - vy1 * sin
        new_vy = vy1 * cos + vx1 * sin
        
        return (collision_x, collision_y), (new_vx, new_vy)
    
    return None, None

def draw_dashed_line(surface, color, start_pos, end_pos, width=2):
    x1, y1 = start_pos
    x2, y2 = end_pos
    dx = x2 - x1
    dy = y2 - y1
    distance = math.sqrt(dx**2 + dy**2)
    dx = dx / distance
    dy = dy / distance
    
    for i in range(0, int(distance), DASH_LENGTH * 2):
        start = (x1 + dx * i, y1 + dy * i)
        end = (x1 + dx * (i + DASH_LENGTH), y1 + dy * (i + DASH_LENGTH))
        pygame.draw.line(surface, color, start, end, width)

def draw_trajectory(screen, cue_ball, target_ball, mouse_x, mouse_y):
    # Calculate initial velocity vector
    dx = mouse_x - cue_ball.x
    dy = mouse_y - cue_ball.y
    distance = math.sqrt(dx**2 + dy**2)
    
    if distance == 0:
        return
    
    # Calculate speed based on distance (capped at max_distance)
    max_distance = 200  # Maximum distance for full power
    speed_factor = min(distance, max_distance) / max_distance
    base_speed = 20  # Base speed multiplier
    speed = base_speed * speed_factor
    
    vx = (dx / distance) * speed
    vy = (dy / distance) * speed
    
    # Draw initial trajectory from cue ball
    start_x, start_y = cue_ball.x, cue_ball.y
    
    # Check for ball collision first
    collision_point, new_velocity = predict_ball_collision(cue_ball.x, cue_ball.y, 
                                                         target_ball.x, target_ball.y, 
                                                         vx, vy)
    
    if collision_point:
        # Draw trajectory to collision point
        pygame.draw.line(screen, WHITE, (start_x, start_y), collision_point, 2)
        
        # Calculate and draw predicted positions after collision
        # For target ball
        target_end_x = collision_point[0] + new_velocity[0] * 10
        target_end_y = collision_point[1] + new_velocity[1] * 10
        cushion_point_target, _ = predict_cushion_collision(target_end_x, target_end_y, 
                                                          new_velocity[0], new_velocity[1])
        
        # For cue ball
        cue_end_x = collision_point[0] + vx * 10
        cue_end_y = collision_point[1] + vy * 10
        cushion_point_cue, _ = predict_cushion_collision(cue_end_x, cue_end_y, vx, vy)
        
        # Draw target ball's trajectory after collision with dashed line
        draw_dashed_line(screen, TARGET_TRAJECTORY, collision_point, cushion_point_target, 3)
        # Draw predicted target ball position with a larger outline
        pygame.draw.circle(screen, TARGET_TRAJECTORY, (int(target_end_x), int(target_end_y)), BALL_RADIUS + 2, 3)
        
        # Draw cue ball's trajectory after collision
        pygame.draw.line(screen, WHITE, collision_point, cushion_point_cue, 2)
        # Draw predicted cue ball position
        pygame.draw.circle(screen, WHITE, (int(cue_end_x), int(cue_end_y)), BALL_RADIUS, 2)
        
        # Draw collision point indicator
        pygame.draw.circle(screen, (255, 255, 0), (int(collision_point[0]), int(collision_point[1])), 5)
    else:
        # No ball collision, just draw trajectory to cushion
        cushion_point, _ = predict_cushion_collision(cue_ball.x, cue_ball.y, vx, vy)
        pygame.draw.line(screen, WHITE, (start_x, start_y), cushion_point, 2)
        
        # Draw predicted cue ball position
        cue_end_x = cushion_point[0] - vx * 10
        cue_end_y = cushion_point[1] - vy * 10
        pygame.draw.circle(screen, WHITE, (int(cue_end_x), int(cue_end_y)), BALL_RADIUS, 2)

def check_ball_collision(ball1, ball2):
    dx = ball2.x - ball1.x
    dy = ball2.y - ball1.y
    distance = math.sqrt(dx**2 + dy**2)
    
    if distance < ball1.radius + ball2.radius:
        # Calculate collision response
        angle = math.atan2(dy, dx)
        sin = math.sin(angle)
        cos = math.cos(angle)
        
        # Rotate velocities
        vx1 = ball1.velocity_x * cos + ball1.velocity_y * sin
        vy1 = ball1.velocity_y * cos - ball1.velocity_x * sin
        vx2 = ball2.velocity_x * cos + ball2.velocity_y * sin
        vy2 = ball2.velocity_y * cos - ball2.velocity_x * sin
        
        # Exchange velocities
        ball1.velocity_x = vx2 * cos - vy1 * sin
        ball1.velocity_y = vy1 * cos + vx2 * sin
        ball2.velocity_x = vx1 * cos - vy2 * sin
        ball2.velocity_y = vy2 * cos + vx1 * sin
        
        # Move balls apart to prevent sticking
        overlap = (ball1.radius + ball2.radius - distance) / 2
        ball1.x -= overlap * cos
        ball1.y -= overlap * sin
        ball2.x += overlap * cos
        ball2.y += overlap * sin

def draw_table():
    # Draw cushions
    pygame.draw.rect(screen, BROWN, (0, 0, WIDTH, CUSHION_WIDTH))  # Top
    pygame.draw.rect(screen, BROWN, (0, 0, CUSHION_WIDTH, HEIGHT))  # Left
    pygame.draw.rect(screen, BROWN, (0, HEIGHT - CUSHION_WIDTH, WIDTH, CUSHION_WIDTH))  # Bottom
    pygame.draw.rect(screen, BROWN, (WIDTH - CUSHION_WIDTH, 0, CUSHION_WIDTH, HEIGHT))  # Right
    
    # Draw table surface
    pygame.draw.rect(screen, GREEN, (CUSHION_WIDTH, CUSHION_WIDTH, 
                                    WIDTH - 2*CUSHION_WIDTH, HEIGHT - 2*CUSHION_WIDTH))

def main():
    # Create balls
    cue_ball = Ball(WIDTH//4, HEIGHT//2, WHITE, True)
    target_ball = Ball(3*WIDTH//4, HEIGHT//2, RED)
    
    # Game state
    aiming = True
    max_distance = 200  # Maximum distance for full power
    base_speed = 20  # Base speed multiplier
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN and aiming:
                # Calculate shot direction and power based on distance
                mouse_x, mouse_y = pygame.mouse.get_pos()
                dx = mouse_x - cue_ball.x
                dy = mouse_y - cue_ball.y
                distance = math.sqrt(dx**2 + dy**2)
                
                if distance > 0:
                    # Calculate speed based on distance
                    speed_factor = min(distance, max_distance) / max_distance
                    speed = base_speed * speed_factor
                    
                    cue_ball.velocity_x = (dx / distance) * speed
                    cue_ball.velocity_y = (dy / distance) * speed
                    aiming = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:  # Reset the simulation
                    cue_ball = Ball(WIDTH//4, HEIGHT//2, WHITE, True)
                    target_ball = Ball(3*WIDTH//4, HEIGHT//2, RED)
                    aiming = True
        
        # Update
        if not aiming:
            cue_ball.move()
            target_ball.move()
            
            # Check collisions
            cue_ball.check_cushion_collision()
            target_ball.check_cushion_collision()
            check_ball_collision(cue_ball, target_ball)
            
            # Check if balls have stopped
            if (cue_ball.velocity_x == 0 and cue_ball.velocity_y == 0 and 
                target_ball.velocity_x == 0 and target_ball.velocity_y == 0):
                aiming = True
        
        # Draw
        screen.fill(BLACK)
        draw_table()
        
        # Draw trajectory when aiming
        if aiming:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            draw_trajectory(screen, cue_ball, target_ball, mouse_x, mouse_y)
        
        # Draw balls
        target_ball.draw(screen)
        cue_ball.draw(screen)
        
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
