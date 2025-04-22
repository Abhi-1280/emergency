import random
import math
import time
import threading
import pygame
import sys
import os
import numpy as np
from collections import defaultdict
import traceback

# Optimized simulation parameters
defaultRed = 80
defaultYellow = 3
defaultGreen = 50
defaultMinimum = 15
defaultMaximum = 90

# Enhanced vehicle speeds for smoother flow
speeds = {
    'car': 5.5,      # Increased from 4.0
    'bus': 4.5,      # Increased from 3.5
    'truck': 7.0,    # Increased from 6.0 (Emergency vehicles)
    'rickshaw': 5.0, # Increased from 3.8
    'bike': 6.0      # Increased from 4.5
}

# Optimized vehicle dimensions
vehicleSizes = {
    'car': (35, 50),
    'bus': (45, 65),
    'truck': (45, 65),
    'rickshaw': (30, 45),
    'bike': (25, 40)
}

# Improved spacing parameters
minimumGap = 20     # Increased from 15
safetyGap = 25      # Increased from 20
stoppingGap = 30    # Increased from 25
turningGap = 35     # New parameter for turning vehicles

# Traffic control parameters
signals = []
noOfSignals = 4
simTime = 300
timeElapsed = 0
currentGreen = 0
nextGreen = (currentGreen+1)%noOfSignals
currentYellow = 0
noOfLanes = 3
detectionTime = 2   # Reduced from 3

# Improved coordinates for smoother movement
x = {
    'right': [0, 0, 0], 
    'down': [755, 727, 697], 
    'left': [1400, 1400, 1400], 
    'up': [602, 627, 657]
}    

y = {
    'right': [348, 370, 398], 
    'down': [0, 0, 0], 
    'left': [498, 466, 436], 
    'up': [800, 800, 800]
}

# Enhanced vehicle tracking system
vehicles = {
    'right': {0:[], 1:[], 2:[], 'crossed':0, 'waiting':[], 'emergency':[]}, 
    'down': {0:[], 1:[], 2:[], 'crossed':0, 'waiting':[], 'emergency':[]}, 
    'left': {0:[], 1:[], 2:[], 'crossed':0, 'waiting':[], 'emergency':[]}, 
    'up': {0:[], 1:[], 2:[], 'crossed':0, 'waiting':[], 'emergency':[]}
}

vehicleTypes = {0:'car', 1:'bus', 2:'truck', 3:'rickshaw', 4:'bike'}
directionNumbers = {0:'right', 1:'down', 2:'left', 3:'up'}

# UI coordinates
signalCoords = [(530,230), (810,230), (810,570), (530,570)]
signalTimerCoords = [(530,210), (810,210), (810,550), (530,550)]
vehicleCountCoords = [(480,210), (880,210), (880,550), (480,550)]

# Optimized stop lines and turning points
stopLines = {
    'right': 590,
    'down': 330,
    'left': 800,
    'up': 535
}

defaultStop = {
    'right': 580,
    'down': 320,
    'left': 810,
    'up': 545
}

# Improved turning coordinates
mid = {
    'right': {'x':705, 'y':445, 'angle':90, 'gap':40},
    'down': {'x':695, 'y':450, 'angle':90, 'gap':40},
    'left': {'x':695, 'y':425, 'angle':90, 'gap':40},
    'up': {'x':695, 'y':400, 'angle':90, 'gap':40}
}

# Traffic flow control parameters
MAX_WAITING_TIME = 120  # Maximum waiting time before priority increase
EMERGENCY_SPEED_MULTIPLIER = 1.5
CONGESTION_THRESHOLD = 8  # Vehicles per lane
ADAPTIVE_TIMING = True    # Enable adaptive signal timing

# Initialize pygame
pygame.init()
simulation = pygame.sprite.Group()
class TrafficQLearning:
    def __init__(self):
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1
        self.q_table = defaultdict(lambda: {'short': 0, 'medium': 0, 'long': 0})
        self.state_history = []
        self.reward_history = []
        self.traffic_state = TrafficState()

    def get_state(self, direction):
        """Get current state of traffic"""
        self.traffic_state.update(direction)
        
        queue_length = self.traffic_state.queue_lengths[direction]
        waiting_time = self.traffic_state.waiting_times[direction]
        emergency_present = self.traffic_state.emergency_vehicles[direction] > 0
        congestion = self.traffic_state.congestion_level[direction]

        # Discretize state space
        queue_state = min(2, queue_length // 5)
        waiting_state = min(2, int(waiting_time / 30))
        congestion_state = min(2, int(congestion * 3))

        return (queue_state, waiting_state, emergency_present, congestion_state)

    def get_action(self, state):
        """Select action using epsilon-greedy policy"""
        if random.random() < self.epsilon:
            return random.choice(['short', 'medium', 'long'])
        else:
            return max(self.q_table[state].items(), key=lambda x: x[1])[0]

    def get_reward(self, direction):
        """Calculate reward based on traffic conditions"""
        queue_length = self.traffic_state.queue_lengths[direction]
        waiting_time = self.traffic_state.waiting_times[direction]
        emergency_count = self.traffic_state.emergency_vehicles[direction]
        
        # Calculate reward components
        queue_penalty = -0.5 * queue_length
        waiting_penalty = -0.3 * waiting_time
        emergency_reward = 20 * emergency_count
        
        # Calculate total reward
        total_reward = queue_penalty + waiting_penalty + emergency_reward
        self.reward_history.append(total_reward)
        
        return total_reward

    def update(self, state, action, reward, next_state):
        """Update Q-values using Q-learning algorithm"""
        current_q = self.q_table[state][action]
        next_max_q = max(self.q_table[next_state].values())
        
        # Q-learning update formula
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max_q - current_q
        )
        
        self.q_table[state][action] = new_q
        self.state_history.append((state, action, reward))

    def get_best_action(self, state):
        """Get the best action for a given state"""
        return max(self.q_table[state].items(), key=lambda x: x[1])[0]

    def get_average_reward(self, window=10):
        """Calculate average reward over recent history"""
        if self.reward_history:
            return sum(self.reward_history[-window:]) / min(window, len(self.reward_history))
        return 0

    def adjust_learning_parameters(self):
        """Dynamically adjust learning parameters based on performance"""
        avg_reward = self.get_average_reward()
        
        # Adjust epsilon (exploration rate)
        if avg_reward > 0:
            self.epsilon = max(0.01, self.epsilon * 0.995)  # Reduce exploration
        else:
            self.epsilon = min(0.3, self.epsilon * 1.005)   # Increase exploration

        # Adjust learning rate
        if len(self.state_history) > 1000:
            self.learning_rate = max(0.01, self.learning_rate * 0.995)

class TrafficState:
    def __init__(self):
        self.queue_lengths = defaultdict(int)
        self.waiting_times = defaultdict(float)
        self.emergency_vehicles = defaultdict(int)
        self.congestion_level = defaultdict(float)
        self.lane_density = defaultdict(lambda: defaultdict(float))
        self.total_waiting_time = 0
        self.vehicles_processed = 0
        
    def update(self, direction):
        total_vehicles = 0
        max_waiting_time = 0
        emergency_count = 0
        lane_vehicles = defaultdict(int)
        
        for lane in range(noOfLanes):
            for vehicle in vehicles[direction][lane]:
                if vehicle.crossed == 0:
                    total_vehicles += 1
                    lane_vehicles[lane] += 1
                    max_waiting_time = max(max_waiting_time, vehicle.waiting_time)
                    if vehicle.isEmergency:
                        emergency_count += 1
                        
        self.queue_lengths[direction] = total_vehicles
        self.waiting_times[direction] = max_waiting_time
        self.emergency_vehicles[direction] = emergency_count
        
        # Calculate lane density
        for lane in range(noOfLanes):
            self.lane_density[direction][lane] = lane_vehicles[lane] / CONGESTION_THRESHOLD
            
        # Update congestion level using weighted average
        total_density = sum(self.lane_density[direction].values())
        self.congestion_level[direction] = total_density / noOfLanes
        
    def get_priority_score(self, direction):
        """Calculate priority score for signal timing"""
        waiting_factor = min(1.0, self.waiting_times[direction] / MAX_WAITING_TIME)
        congestion_factor = self.congestion_level[direction]
        emergency_factor = 2.0 if self.emergency_vehicles[direction] > 0 else 0.0
        
        return (0.4 * waiting_factor + 
                0.4 * congestion_factor + 
                0.2 * emergency_factor)

def simulationTime():
    global timeElapsed, simTime
    while True:
        timeElapsed += 1
        time.sleep(1)
        if timeElapsed == simTime:
            print_simulation_results()
            os._exit(1)

def print_simulation_results():
    """Print detailed simulation statistics"""
    print('\nSimulation completed.\nResults:')
    print('Direction-wise vehicle count:')
    total_vehicles = 0
    total_waiting_time = 0
    emergency_response_times = []
    
    for i in range(noOfSignals):
        direction = directionNumbers[i]
        count = vehicles[direction]['crossed']
        waiting = vehicles[direction]['waiting']
        emergency = len(vehicles[direction]['emergency'])
        
        print(f'\nDirection {i+1}:')
        print(f'  Vehicles crossed: {count}')
        print(f'  Vehicles waiting: {len(waiting)}')
        print(f'  Emergency vehicles: {emergency}')
        
        total_vehicles += count
        
        # Calculate detailed statistics
        for lane in range(noOfLanes):
            for vehicle in vehicles[direction][lane]:
                total_waiting_time += vehicle.waiting_time
                if vehicle.isEmergency:
                    emergency_response_times.append(vehicle.waiting_time)
    
    # Print overall statistics
    print('\nOverall Statistics:')
    print(f'Total vehicles processed: {total_vehicles}')
    print(f'Average waiting time: {total_waiting_time/max(1, total_vehicles):.2f} seconds')
    if emergency_response_times:
        print(f'Average emergency response time: {sum(emergency_response_times)/len(emergency_response_times):.2f} seconds')
    print(f'Throughput: {total_vehicles/simTime:.2f} vehicles/second')
class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = str(green)
        self.lastGreen = 0
        self.emergencyMode = False
        self.current_state = None
        self.current_action = None
        self.next_action = None
        self.waiting_time = 0
        self.vehicles_passed = 0
        self.emergency_vehicles_passed = 0
        self.congestion_level = 0
        self.priority_score = 0

    def update_metrics(self):
        if self.red > 0:
            self.waiting_time += 1
            self.priority_score = self.calculate_priority()
    
    def calculate_priority(self):
        waiting_factor = min(1.0, self.waiting_time / MAX_WAITING_TIME)
        congestion_factor = self.congestion_level
        emergency_factor = 2.0 if self.emergencyMode else 0.0
        return (0.4 * waiting_factor + 
                0.4 * congestion_factor + 
                0.2 * emergency_factor)

    def should_extend_green(self):
        return (self.vehicles_passed < 5 and 
                self.green > self.minimum and 
                not self.emergencyMode and
                self.congestion_level > 0.5)

class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite.__init__(self)
        # Basic properties
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.direction_number = direction_number
        self.direction = direction
        self.willTurn = will_turn
        
        # Movement properties
        self.speed = speeds[vehicleClass]
        self.max_speed = speeds[vehicleClass]
        self.acceleration = 0.2
        self.deceleration = 0.3
        self.turned = 0
        self.rotateAngle = 0
        self.crossed = 0
        
        # Status properties
        self.isEmergency = (vehicleClass == 'truck')
        self.waiting_time = 0
        self.stopped = False
        self.size = vehicleSizes[vehicleClass]
        self.safe_distance = safetyGap
        self.last_position = None
        self.stalled_time = 0
        
        # Initialize position and add to simulation
        self.initialize_position()
        self.load_images()
        simulation.add(self)

    def initialize_position(self):
        # Add vehicle to appropriate lists
        vehicles[self.direction][self.lane].append(self)
        if self.isEmergency:
            vehicles[self.direction]['emergency'].append(self)
        
        self.index = len(vehicles[self.direction][self.lane]) - 1
        
        # Set initial coordinates
        self.x = x[self.direction][self.lane]
        self.y = y[self.direction][self.lane]
        
        # Calculate safe distance based on previous vehicle
        if self.index > 0:
            prev_vehicle = vehicles[self.direction][self.lane][self.index - 1]
            self.safe_distance = prev_vehicle.size[0 if self.direction in ['right', 'left'] else 1] + safetyGap
        
        self.set_initial_stop_position()

    def load_images(self):
        try:
            path = f"images/{self.direction}/{self.vehicleClass}.png"
            self.originalImage = pygame.image.load(path)
            self.currentImage = pygame.image.load(path)
            
            # Scale images to vehicle size
            self.originalImage = pygame.transform.scale(self.originalImage, self.size)
            self.currentImage = pygame.transform.scale(self.currentImage, self.size)
        except pygame.error as e:
            print(f"Error loading vehicle image: {e}")
            raise

    def set_initial_stop_position(self):
        """Set initial stop position based on direction and previous vehicles"""
        if self.direction == 'right':
            self.stop = (defaultStop[self.direction] if self.index == 0 
                        else vehicles[self.direction][self.lane][self.index-1].stop - self.safe_distance)
            x[self.direction][self.lane] -= (self.size[0] + minimumGap)
        elif self.direction == 'left':
            self.stop = (defaultStop[self.direction] if self.index == 0 
                        else vehicles[self.direction][self.lane][self.index-1].stop + self.safe_distance)
            x[self.direction][self.lane] += (self.size[0] + minimumGap)
        elif self.direction == 'down':
            self.stop = (defaultStop[self.direction] if self.index == 0 
                        else vehicles[self.direction][self.lane][self.index-1].stop - self.safe_distance)
            y[self.direction][self.lane] -= (self.size[1] + minimumGap)
        elif self.direction == 'up':
            self.stop = (defaultStop[self.direction] if self.index == 0 
                        else vehicles[self.direction][self.lane][self.index-1].stop + self.safe_distance)
            y[self.direction][self.lane] += (self.size[1] + minimumGap)

    def check_collision(self, new_x, new_y):
        """Enhanced collision detection with predictive checking"""
        # Create rectangle for proposed position
        proposed_rect = pygame.Rect(new_x, new_y, self.size[0], self.size[1])
        
        # Check collision with other vehicles
        for direction in vehicles:
            for lane in range(noOfLanes):
                for vehicle in vehicles[direction][lane]:
                    if vehicle != self:
                        # Create rectangle for other vehicle
                        other_rect = pygame.Rect(vehicle.x, vehicle.y, 
                                               vehicle.size[0], vehicle.size[1])
                        
                        # Check if rectangles intersect
                        if proposed_rect.colliderect(other_rect):
                            # Calculate overlap area
                            overlap_area = (min(proposed_rect.right, other_rect.right) - 
                                          max(proposed_rect.left, other_rect.left)) * \
                                         (min(proposed_rect.bottom, other_rect.bottom) - 
                                          max(proposed_rect.top, other_rect.top))
                            
                            # Return True if significant overlap
                            if overlap_area > 50:  # Threshold for significant collision
                                return True
        
        return False

    def update_position(self):
        """Store current position for movement tracking"""
        self.last_position = (self.x, self.y)

    def check_stalled(self):
        """Check if vehicle is stalled and handle accordingly"""
        if self.last_position:
            if (abs(self.x - self.last_position[0]) < 0.1 and 
                abs(self.y - self.last_position[1]) < 0.1):
                self.stalled_time += 1
                if self.stalled_time > 10:  # If stalled for more than 10 frames
                    self.handle_stall()
            else:
                self.stalled_time = 0

    def handle_stall(self):
        """Handle stalled vehicle situation"""
        if self.isEmergency:
            # Give emergency vehicles more aggressive movement
            self.speed = self.max_speed * 1.5
        else:
            # Try alternative paths or slight position adjustments
            self.try_alternative_movement()

    def try_alternative_movement(self):
        """Attempt to move vehicle when stuck"""
        if self.direction in ['right', 'left']:
            # Try slight vertical adjustment
            new_y = self.y + (5 if random.random() > 0.5 else -5)
            if not self.check_collision(self.x, new_y):
                self.y = new_y
        else:
            # Try slight horizontal adjustment
            new_x = self.x + (5 if random.random() > 0.5 else -5)
            if not self.check_collision(new_x, self.y):
                self.x = new_x

    def move(self):
        """Enhanced movement logic with improved flow and collision avoidance"""
        self.update_position()
        
        if self.isEmergency:
            self.speed = self.max_speed * EMERGENCY_SPEED_MULTIPLIER
            can_move = True
        else:
            emergency_present, emergency_direction = detectEmergencyVehicles()
            can_move = not emergency_present or self.direction_number == emergency_direction or self.crossed == 1

        if not can_move:
            self.update_waiting_time()
            return

        self.adjust_speed()
        
        if self.crossed == 0 and self.check_crossing():
            self.handle_crossing()

        if self.willTurn and not self.crossed:
            self.handle_turn_movement()
        else:
            self.handle_straight_movement()

        self.check_stalled()
        self.update_waiting_time()
def handle_crossing(self):
    """Handle vehicle crossing the intersection"""
    self.crossed = 1
    vehicles[self.direction]['crossed'] += 1
    if self.isEmergency:
        signals[self.direction_number].emergency_vehicles_passed += 1
    signals[self.direction_number].vehicles_passed += 1

def handle_turn_movement(self):
    """Enhanced turning movement logic"""
    if self.near_turning_point():
        if self.turned == 0:
            self.execute_turn()
        else:
            self.complete_turn()
    else:
        self.approach_turn()

def near_turning_point(self):
    """Check if vehicle is near turning point"""
    turn_point = mid[self.direction]
    if self.direction in ['right', 'left']:
        return abs(self.x - turn_point['x']) < turn_point['gap']
    else:
        return abs(self.y - turn_point['y']) < turn_point['gap']

def execute_turn(self):
    """Execute turning movement with smooth rotation"""
    turn_increment = 3  # Smaller increment for smoother turning
    self.rotateAngle += turn_increment
    self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
    
    # Adjust position during turn based on direction
    if self.direction == 'right':
        self.x += 2.5
        self.y += 2.0
    elif self.direction == 'down':
        self.x -= 2.5
        self.y += 2.0
    elif self.direction == 'left':
        self.x -= 2.5
        self.y -= 2.0
    elif self.direction == 'up':
        self.x += 2.5
        self.y -= 2.0
        
    if self.rotateAngle >= 90:
        self.turned = 1
        self.rotateAngle = 90

def complete_turn(self):
    """Complete turning movement"""
    if self.can_move_forward():
        if self.direction in ['right', 'left']:
            self.y += self.speed if self.direction == 'right' else -self.speed
        else:
            self.x += self.speed if self.direction == 'up' else -self.speed

def approach_turn(self):
    """Approach turning point with proper speed and spacing"""
    if self.can_move_forward():
        if self.direction == 'right':
            new_x = self.x + self.speed
            if not self.check_collision(new_x, self.y):
                self.x = new_x
        elif self.direction == 'down':
            new_y = self.y + self.speed
            if not self.check_collision(self.x, new_y):
                self.y = new_y
        elif self.direction == 'left':
            new_x = self.x - self.speed
            if not self.check_collision(new_x, self.y):
                self.x = new_x
        elif self.direction == 'up':
            new_y = self.y - self.speed
            if not self.check_collision(self.x, new_y):
                self.y = new_y

def updateSignalQL(q_learning):
    """Update traffic signals using Q-learning"""
    global currentGreen, nextGreen
    
    # Get current state and calculate priorities
    current_state = q_learning.get_state(nextGreen)
    priorities = []
    
    for i in range(noOfSignals):
        direction = directionNumbers[i]
        priority = q_learning.traffic_state.get_priority_score(direction)
        priorities.append((i, priority))
    
    # Sort directions by priority
    priorities.sort(key=lambda x: x[1], reverse=True)
    
    # Select action based on highest priority direction
    if priorities[0][0] == nextGreen:
        if priorities[0][1] > 0.7:  # High congestion
            action = 'long'
        elif priorities[0][1] > 0.4:  # Medium congestion
            action = 'medium'
        else:  # Low congestion
            action = 'short'
    else:
        # Switch to higher priority direction
        nextGreen = priorities[0][0]
        action = 'medium'
    
    # Set green time based on action and conditions
    if action == 'short':
        green_time = max(defaultMinimum, 
                        min(defaultGreen, 
                            q_learning.traffic_state.queue_lengths[directionNumbers[nextGreen]] * 4))
    elif action == 'long':
        green_time = min(defaultMaximum, 
                        max(defaultGreen, 
                            q_learning.traffic_state.queue_lengths[directionNumbers[nextGreen]] * 6))
    else:
        green_time = defaultGreen
    
    # Adjust for emergency vehicles
    if q_learning.traffic_state.emergency_vehicles[directionNumbers[nextGreen]] > 0:
        green_time = max(green_time, defaultMaximum // 2)
    
    signals[nextGreen].current_state = current_state
    signals[nextGreen].current_action = action
    signals[nextGreen].green = green_time
    
    return current_state, action

def updateTrafficState():
    """Update traffic state and manage signal timings"""
    for direction in directionNumbers.values():
        waiting_vehicles = 0
        max_waiting_time = 0
        emergency_waiting = 0
        
        for lane in range(noOfLanes):
            for vehicle in vehicles[direction][lane]:
                if vehicle.crossed == 0:
                    waiting_vehicles += 1
                    max_waiting_time = max(max_waiting_time, vehicle.waiting_time)
                    if vehicle.isEmergency:
                        emergency_waiting += 1
        
        vehicles[direction]['waiting'] = waiting_vehicles
        
        # Update signal priorities
        signal_idx = directionNumbers.index(direction)
        signals[signal_idx].congestion_level = waiting_vehicles / (noOfLanes * CONGESTION_THRESHOLD)
        
        # Handle emergency situations
        if emergency_waiting > 0 and currentGreen != signal_idx:
            signals[signal_idx].emergencyMode = True
            if max_waiting_time > MAX_WAITING_TIME / 2:
                handleEmergencyVehicle(signal_idx)

def generateVehicles():
    """Generate vehicles with improved distribution"""
    while True:
        # Check current traffic density
        total_waiting = sum(vehicles[direction]['waiting'] 
                          for direction in directionNumbers.values())
        
        if total_waiting < CONGESTION_THRESHOLD * noOfLanes * noOfSignals:
            # Select vehicle type with weighted probability
            weights = [0.4, 0.2, 0.1, 0.2, 0.1]  # car, bus, truck, rickshaw, bike
            vehicle_type = random.choices(range(5), weights=weights)[0]
            
            # Intelligent lane selection
            if vehicle_type == 4:  # Bike
                lane_number = 0
            else:
                # Choose lane based on current occupancy
                lane_occupancy = [len(vehicles[directionNumbers[random.randint(0, 3)]][i]) 
                                for i in range(noOfLanes)]
                lane_number = lane_occupancy.index(min(lane_occupancy))
            
            # Determine turning probability based on lane and traffic
            turn_probability = 0.3 if lane_number == 2 else 0.1
            will_turn = random.random() < turn_probability
            
            # Choose direction with least traffic
            direction_counts = [(i, len(vehicles[directionNumbers[i]]['waiting'])) 
                              for i in range(noOfSignals)]
            direction_number = min(direction_counts, key=lambda x: x[1])[0]
            
            try:
                Vehicle(lane_number, vehicleTypes[vehicle_type], 
                       direction_number, directionNumbers[direction_number], 
                       will_turn)
            except Exception as e:
                print(f"Error generating vehicle: {e}")
            
            # Adaptive delay based on traffic density
            delay = max(0.5, 2 - (total_waiting / (CONGESTION_THRESHOLD * noOfLanes * noOfSignals)))
            time.sleep(delay)
        else:
            time.sleep(1)  # Wait if traffic is heavy
class TrafficSimulation:
    def __init__(self):
        pygame.init()
        self.setup_display()
        self.setup_simulation()
        self.load_images()
        self.initialize_metrics()
        
    def setup_display(self):
        """Initialize display settings"""
        self.screenWidth = 1400
        self.screenHeight = 800
        self.screenSize = (self.screenWidth, self.screenHeight)
        self.screen = pygame.display.set_mode(self.screenSize)
        pygame.display.set_caption("Advanced Traffic Management System")
        
        # Colors
        self.colors = {
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'red': (255, 0, 0),
            'yellow': (255, 255, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'gray': (128, 128, 128),
            'orange': (255, 165, 0)
        }
        
        self.font = pygame.font.Font(None, 30)
        self.large_font = pygame.font.Font(None, 40)
        
    def setup_simulation(self):
        """Initialize simulation parameters"""
        self.q_learning = TrafficQLearning()
        self.frame_count = 0
        self.last_update = time.time()
        self.fps = 60
        self.clock = pygame.time.Clock()
        self.paused = False
        self.show_debug = False
        
    def load_images(self):
        """Load and prepare images"""
        try:
            self.background = pygame.image.load('images/mod_int.png')
            self.signals_images = {
                'red': pygame.image.load('images/signals/red.png'),
                'yellow': pygame.image.load('images/signals/yellow.png'),
                'green': pygame.image.load('images/signals/green.png')
            }
            
            # Scale signal images for better visibility
            for key in self.signals_images:
                self.signals_images[key] = pygame.transform.scale(
                    self.signals_images[key], (30, 90))
                
        except pygame.error as e:
            print(f"Error loading images: {e}")
            raise
        
    def initialize_metrics(self):
        """Initialize performance metrics"""
        self.metrics = {
            'total_waiting_time': 0,
            'vehicles_passed': 0,
            'emergency_response_time': [],
            'average_speed': [],
            'congestion_levels': [],
            'signal_efficiency': [],
            'lane_utilization': defaultdict(list)
        }

    def update_metrics(self):
        """Update simulation metrics"""
        total_vehicles = 0
        total_speed = 0
        
        for direction in directionNumbers.values():
            direction_vehicles = 0
            for lane in range(noOfLanes):
                lane_vehicles = len(vehicles[direction][lane])
                direction_vehicles += lane_vehicles
                self.metrics['lane_utilization'][direction].append(lane_vehicles)
                
                for vehicle in vehicles[direction][lane]:
                    if vehicle.crossed == 0:
                        self.metrics['total_waiting_time'] += vehicle.waiting_time
                    if vehicle.isEmergency and vehicle.crossed == 1:
                        self.metrics['emergency_response_time'].append(vehicle.waiting_time)
                    total_speed += vehicle.speed
                    total_vehicles += 1
        
        if total_vehicles > 0:
            self.metrics['average_speed'].append(total_speed / total_vehicles)
            
        congestion = sum(vehicles[direction]['waiting'] 
                        for direction in directionNumbers.values())
        self.metrics['congestion_levels'].append(congestion)

    def draw_signals(self):
        """Draw traffic signals with enhanced visualization"""
        for i in range(noOfSignals):
            # Draw signal background
            pygame.draw.rect(self.screen, self.colors['gray'],
                           (signalCoords[i][0]-5, signalCoords[i][1]-5, 40, 100))
            
            # Draw signal light
            if i == currentGreen:
                if currentYellow == 1:
                    self.screen.blit(self.signals_images['yellow'], signalCoords[i])
                    color = self.colors['yellow']
                else:
                    self.screen.blit(self.signals_images['green'], signalCoords[i])
                    color = self.colors['green']
            else:
                self.screen.blit(self.signals_images['red'], signalCoords[i])
                color = self.colors['red']
            
            # Draw signal timer
            timer_text = self.font.render(str(signals[i].signalText), True, color)
            self.screen.blit(timer_text, signalTimerCoords[i])
            
            # Draw emergency mode indicator
            if signals[i].emergencyMode:
                emergency_text = self.font.render("EMERGENCY", True, self.colors['red'])
                self.screen.blit(emergency_text, 
                               (signalCoords[i][0]-10, signalCoords[i][1]-30))

    def draw_vehicles(self):
        """Draw vehicles with enhanced visualization"""
        for vehicle in simulation:
            # Draw vehicle
            self.screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
            
            # Draw indicators for special conditions
            if vehicle.isEmergency:
                # Emergency vehicle indicator
                pygame.draw.circle(self.screen, self.colors['red'],
                                (int(vehicle.x + vehicle.size[0]/2),
                                 int(vehicle.y + vehicle.size[1]/2)), 5)
                
                # Emergency vehicle path
                if not vehicle.crossed:
                    pygame.draw.line(self.screen, self.colors['red'],
                                   (vehicle.x + vehicle.size[0]/2, vehicle.y + vehicle.size[1]/2),
                                   (stopLines[vehicle.direction], vehicle.y + vehicle.size[1]/2),
                                   2)
            
            # Draw waiting time indicator for stopped vehicles
            if vehicle.stopped and vehicle.waiting_time > 30:
                wait_text = self.font.render(str(vehicle.waiting_time), True, self.colors['red'])
                self.screen.blit(wait_text, (vehicle.x, vehicle.y - 20))

    def draw_stats(self):
        """Draw performance statistics"""
        stats_x = 1100
        stats_y = 50
        line_height = 30
        
        # Draw simulation time
        time_text = self.large_font.render(f"Time: {timeElapsed}s", True, self.colors['black'])
        self.screen.blit(time_text, (stats_x, stats_y))
        
        # Draw vehicle counts
        for i in range(noOfSignals):
            direction = directionNumbers[i]
            crossed = vehicles[direction]['crossed']
            waiting = len(vehicles[direction]['waiting'])
            emergency = len(vehicles[direction]['emergency'])
            
            text = self.font.render(
                f"Direction {i+1}: {crossed} (Waiting: {waiting}, Emergency: {emergency})",
                True, self.colors['black']
            )
            self.screen.blit(text, (stats_x, stats_y + line_height * (i+1)))
        
        # Draw performance metrics
        y_offset = stats_y + line_height * (noOfSignals + 1)
        
        if self.metrics['average_speed']:
            avg_speed = sum(self.metrics['average_speed'][-10:]) / min(10, len(self.metrics['average_speed']))
            speed_text = self.font.render(f"Avg Speed: {avg_speed:.2f}", True, self.colors['blue'])
            self.screen.blit(speed_text, (stats_x, y_offset))
        
        if self.metrics['emergency_response_time']:
            avg_response = sum(self.metrics['emergency_response_time']) / len(self.metrics['emergency_response_time'])
            response_text = self.font.render(
                f"Avg Emergency Response: {avg_response:.2f}s",
                True, self.colors['red']
            )
            self.screen.blit(response_text, (stats_x, y_offset + line_height))
        
        # Draw congestion level
        congestion = sum(vehicles[d]['waiting'] for d in directionNumbers.values())
        congestion_text = self.font.render(
            f"Congestion Level: {congestion//(noOfLanes*noOfSignals)}",
            True, self.colors['orange'] if congestion > CONGESTION_THRESHOLD else self.colors['green']
        )
        self.screen.blit(congestion_text, (stats_x, y_offset + line_height * 2))

    def handle_events(self):
        """Handle user input and events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_d:
                    self.show_debug = not self.show_debug

    def update_simulation(self):
        """Update simulation state"""
        if not self.paused:
            updateTrafficState()
            updateVehicles()
            self.update_metrics()

    def run(self):
        """Main simulation loop"""
        # Start simulation threads
        threads = [
            threading.Thread(target=generateVehicles, daemon=True),
            threading.Thread(target=simulationTime, daemon=True)
        ]
        for thread in threads:
            thread.start()

        while True:
            self.clock.tick(self.fps)
            self.handle_events()
            
            if not self.paused:
                self.update_simulation()
            
            # Draw simulation
            self.screen.fill(self.colors['white'])
            self.screen.blit(self.background, (0, 0))
            self.draw_signals()
            self.draw_vehicles()
            self.draw_stats()
            
            if self.show_debug:
                self.draw_debug_info()
            
            pygame.display.flip()
            
            # Update performance metrics
            self.frame_count += 1
            if self.frame_count % 60 == 0:
                current_time = time.time()
                self.fps = 60 / (current_time - self.last_update)
                self.last_update = current_time

    def draw_debug_info(self):
        """Draw debug information"""
        debug_x = 10
        debug_y = 10
        line_height = 20
        
        debug_info = [
            f"FPS: {self.fps:.1f}",
            f"Active Vehicles: {len(simulation)}",
            f"Current Green: {currentGreen}",
            f"Yellow: {currentYellow}",
            f"Q-table size: {len(self.q_learning.q_table)}"
        ]
        
        for i, info in enumerate(debug_info):
            text = self.font.render(info, True, self.colors['blue'])
            self.screen.blit(text, (debug_x, debug_y + i * line_height))

if __name__ == '__main__':
    try:
        simulation = TrafficSimulation()
        simulation.run()
    except Exception as e:
        print(f"Simulation error: {e}")
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)                        