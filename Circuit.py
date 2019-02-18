import pygame
import random
import numpy as np
import pickle as pkl
import ahkab

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


render_screen = True
screen = None
clock = None

if render_screen:
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

'''
class env


step(action):
    Inputs:
        action: The action to execute (either 1 for jump or 0 for not jump)

    Actions:
        Executes one game frame (updates sprites, checks for collisions with the player, and adds new barrels)
    Returns:
        observations: The three inputs to be given to the model to decide the next action
        game_state: True is the player is alive, False otherwise
        score: The number of frames the player has been alive

    get_observations():
        Returns:
            The three input variables used in deciding an action:
                - Horizontal distance to the next nearest barrel
                - Height difference between player and center of the gap between the nearest top and bottom barrels
                - Vertical velocity of the player
    get_state():
        Returns:
            False if the player has collided with and edge of the game or with a barrel
            True otherwise
'''


class env():
    def __init__(self):
        self.all_sprites = pygame.sprite.Group()
        self.obstacles_top = pygame.sprite.Group()
        self.obstacles_bottom = pygame.sprite.Group()

        self.player = Player()
        self.all_sprites.add(self.player)
        self.score = -1

        self.alive = True

    def step(self,action):
        if action == 1:
            self.player.jump()

        self.all_sprites.update()
        game_state = self.state()

        observations = self.get_observations()

        if self.score%75 == 0:
            center_position = random.randrange(barrelWidth,HEIGHT-barrelWidth)
            obs_bottom = Obstacle(center_position,top=False)
            obs_top = Obstacle(center_position,top=True,bottom_reference = obs_bottom)

            self.all_sprites.add(obs_top)
            self.all_sprites.add(obs_bottom)
            self.obstacles_top.add(obs_top)
            self.obstacles_bottom.add(obs_bottom)
        if game_state:
            self.score += 1

        if render_screen:
            clock.tick(FPS)
            screen.fill((0,0,0))
            self.all_sprites.draw(screen)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    game_state = False
        return observations,game_state,self.score

    def get_observations(self):
        sprites_list = self.obstacles_top.sprites()
        dist_to_nearest_barrel = 200
        height_diff_nearest_barrel = 0
        for sprite in sprites_list:
            dist = sprite.rect.right - self.player.rect.x
            if dist > 0:
                dist_to_nearest_barrel = dist
                height_diff_nearest_barrel = sprite.center_position - self.player.rect.y
                break
        observations = [dist_to_nearest_barrel,height_diff_nearest_barrel,self.player.speed_y]
        return observations

    def state(self):
        game_state = True
        hits_top = pygame.sprite.spritecollide(self.player,self.obstacles_top,False)
        hits_bottom = pygame.sprite.spritecollide(self.player,self.obstacles_bottom,False)
        if hits_top or hits_bottom:
            game_state = False

        if self.player.isDead():
            game_state = False
        return game_state

'''
Given a value that is in the range (min_1,max_1) return that value if the range was mapped linearly to (min_2,max_2)
'''
def convert_value_to_range(value, min_1, max_1, min_2, max_2):
    span_1 = max_1 - min_1
    span_2 = max_2 - min_2

    scaled_value = (value - min_1) / (span_1)

    return min_2 + (scaled_value * span_2)

'''
Use convert_value_to_range to map all observations to the range 0-5 (to be used with an arduino 0-5 Volts)
'''
def normalize_observations(observations):
    observations[0] = convert_value_to_range(observations[0],0,dist_between_barrels,0,5)
    observations[1] = convert_value_to_range(observations[1],0,HEIGHT,0,5)
    observations[2] = convert_value_to_range(observations[2],-5,5,0,5)
    return observations

'''
The model that combines the paramters and observations to return a result
'''
def take_decision(observations,parameters):
    observations = normalize_observations(observations)
    weights = parameters[:3]
    bias = parameters[3]
    answer = 0
    for idx,weight in enumerate(weights):
        answer += observations[idx]*weight
    if answer > 2.5:
        return 1
    else:
        return 0

'''
Run one episode using the input paramters to the model. (run a game until the player dies or a time limit "max_frames_per_episode" is reached)
Returns:
    Final score the player achieved before the episode terminated
'''
def run_episode(parameters):
    game_env = env()
    observations = game_env.get_observations()
    total_reward = 0
    for _ in range(max_frames_per_episode):
        action = take_decision_circuit(observations,parameters) # changed to take_decision_circuit
        observations,alive,score = game_env.step(action)
        total_reward = score
        if not alive:
            break
    return total_reward

'''
Run n episodes and return their mean score
'''
def run_episodes(n,parameters):
    total_reward = 0
    for _ in range(n):
        total_reward += run_episode(parameters)
    return total_reward/n

'''
Used in the genetic algorithm
'''
def eval_function(parameters):
    return run_episodes(sampling_number,parameters),

sampling_number = 3 # The value n using in run_episodes
max_frames_per_episode = 20000 # the max number of frames to run an episode before it is forced to terminate

best_player = None # best player weights learned using the genetic algorithm
with open('best_player.pkl','rb') as f:
    best_player = pkl.load(f)

'''
Since this is only a one layer network, we can get around using inverters to get negative
vaules by multiplying the values before sending them to the circuit.
Negative paramters will be converted to positive to compensate their corresponding observations
are multiplied by -1 before sending them to the circuit.
'''


negative_weights = []
for idx,w in enumerate(best_player):
    if w < 0:
        negative_weights.append(idx)
        best_player[idx] *= -1

mycir = ahkab.Circuit('Flappy bird Circuit')

# Custom function to create an opamp
def add_op_amp(circuit,opamp_name):
    circuit.add_resistor('input'+opamp_name, circuit.gnd, 'inverting_input'+opamp_name, value=10*1000000)
    circuit.add_vcvs('gain'+opamp_name, "opamp_internal_1"+opamp_name, circuit.gnd, circuit.gnd, 'inverting_input'+opamp_name, value=100*1000)
    circuit.add_resistor('P1'+opamp_name, "opamp_internal_1"+opamp_name, "opamp_internal_2"+opamp_name, value=1*1000)
    circuit.add_capacitor('P1'+opamp_name, "opamp_internal_2"+opamp_name, circuit.gnd, 1.5915*(10e-6))
    circuit.add_vcvs('buffer'+opamp_name, "opamp_internal_3"+opamp_name, circuit.gnd, "opamp_internal_2"+opamp_name, circuit.gnd, value=1)
    circuit.add_resistor('out'+opamp_name, "opamp_internal_3"+opamp_name, 'output'+opamp_name, value=10)

# Very slow to create the circuit each time from scratch but is fast enough for prototyping purposes
def take_decision_circuit(observations,parameters):
    observations = normalize_observations(observations)
    observations.append(1) # The bias paramter is multiplied by 1 (or -1)

    # Multiply observations that have indicies in the array negative_weights by -1 to compensate for the paramters by multiplied by -1
    for i in range(len(observations)):
        if i in negative_weights:
            observations[i] *= -1

    # Creating an opamp circuit that adds the input voltages; resistors are used as the paramters (actually 1/parameters)
    mycir = ahkab.Circuit('Simple Example Circuit')
    add_op_amp(mycir,"_opamp1")
    mycir.add_vsource("V1","v1_r1",mycir.gnd,observations[0])
    mycir.add_vsource("V2","v2_r2",mycir.gnd,observations[1])
    mycir.add_vsource("V3","v3_r3",mycir.gnd,observations[2])
    mycir.add_vsource("V4","v4_r4",mycir.gnd,observations[3])
    mycir.add_resistor("R1","inverting_input_opamp1","v1_r1",value=1/parameters[0] *1000)
    mycir.add_resistor("R2","inverting_input_opamp1","v2_r2",value=1/parameters[1] *1000)
    mycir.add_resistor("R3","inverting_input_opamp1","v3_r3",value=1/parameters[2] *1000)
    mycir.add_resistor("R4","inverting_input_opamp1","v4_r4",value=1/parameters[3] *1000)
    mycir.add_resistor("over","inverting_input_opamp1","output_opamp1",value=1000)

    opa = ahkab.new_op()
    r = ahkab.run(mycir, opa)['op']

    # output is multiplied by -1 because the opamp inverts the output signal
    jump_prob = r["VOUTPUT_OPAMP1"][0][0]*-1

    if jump_prob > 2.5:
        return 1
    else:
        return 0

evaluation = run_episode(best_player)
print("The model ran for {} frames".format(evaluation))
pygame.quit()
