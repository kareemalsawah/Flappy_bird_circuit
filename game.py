import pygame
import random

pygame.init()
pygame.mixer.init()

WIDTH = 600
HEIGHT = 400
FPS = 60

#Global game variables
gravity = 0.8
jumpImpulse = -12 # Represents the impulse applied when a bird jumps
barrelSpeed = 6  # Speed by which the barrel is moving to the left
barrelWidth = 125 # Width of the opening in the barrel
barrelDepth = 80 # Depth of the barrel (along the x axis)
dist_between_barrels = 75 # number of frames between adding new barrels

screen = pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()


'''
Player class using pygame sprites

update():
    updates the current speed and current position using a simple Explicit Euler update

isDead():
    return True is the bird has died (collided with an edge of the screen, collisions with the barrels are checked in the game loop)

jump():
    Applies jump impulse to the bird's vertical speed
'''
class Player(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((30,30))
        self.image.fill((255,0,0))
        self.rect = self.image.get_rect()
        self.rect.y = HEIGHT/2
        self.rect.x = 100
        self.speed_y = 0

    def update(self):
        self.rect.y += self.speed_y
        self.speed_y += gravity

    def isDead(self):
        if self.rect.top < 0 or self.rect.bottom > HEIGHT:
            return True
        else:
            return False

    def jump(self):
        self.speed_y += jumpImpulse


'''
Obstacle class using pygame sprites
__init__():
    There are two types of obstacles:
     - top obstacle is the top part of the barrels
     - bottom obstacle is the bottom part of the barrels
    The top obstacle also has a reference to the bottom obstacle

update():
    updates the position of the obstacle according to the global variable barrelSpeed

restart():
    Used to kill the barrel when it gets off the screen
'''
class Obstacle(pygame.sprite.Sprite):
    def __init__(self,center_position,top=True,bottom_reference=None):
        pygame.sprite.Sprite.__init__(self)
        self.center_position = center_position
        self.top = top
        self.bottom_reference = bottom_reference
        if top:
            self.image = pygame.Surface((barrelDepth,self.center_position-barrelWidth/2))
            self.image.fill((0,255,0))
            self.rect = self.image.get_rect()
            self.rect.top = 0
            self.rect.left = WIDTH+1
        else:
            self.image = pygame.Surface((barrelDepth,HEIGHT-(self.center_position+barrelWidth)))
            self.image.fill((0,255,0))
            self.rect = self.image.get_rect()
            self.rect.bottom = HEIGHT
            self.rect.left = WIDTH+1

        self.speed_x = barrelSpeed

    def update(self):
        self.rect.x -= self.speed_x

    def restart(self,center_position):
        self.kill()


# A group that has all the game sprites (players, obstacles, etc.)
all_sprites = pygame.sprite.Group()

# A group that has only the top obstacles
obstacles_top = pygame.sprite.Group()

# A group that has only the bottom obstacles
obstacles_bottom = pygame.sprite.Group()

player = Player()
all_sprites.add(player)

running = True # False when player.isDead() or when player collides with an obstacle
score = -1
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.jump()

    #check collisions of player with top obstacles
    hits_top = pygame.sprite.spritecollide(player,obstacles_top,False)

    #check collisions of player with bottom obstacles
    hits_bottom = pygame.sprite.spritecollide(player,obstacles_bottom,False)
    if hits_top or hits_bottom or player.isDead():
        running = False

    all_sprites.update()

    screen.fill((0,0,0))
    all_sprites.draw(screen)
    pygame.display.flip()
    if running:
        score += 1

    if score%dist_between_barrels == 0: # add a new barrel is dist_between_barrels time frames have passed since placing the last barrel
        center_position = random.randrange(barrelWidth,HEIGHT-barrelWidth)
        obs_bottom = Obstacle(center_position,top=False)
        obs_top = Obstacle(center_position,top=True,bottom_reference = obs_bottom)

        all_sprites.add(obs_top)
        all_sprites.add(obs_bottom)
        obstacles_top.add(obs_top)
        obstacles_bottom.add(obs_bottom)
        print(len(obstacles_top.sprites()))

print(score)
pygame.quit()
