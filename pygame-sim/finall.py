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

# Simulation Parameters
defaultRed = 100
defaultYellow = 3
defaultGreen = 60
defaultMinimum = 20
defaultMaximum = 90

# Enhanced vehicle speeds for smoother flow
speeds = {
    'car': 5.0,
    'bus': 4.0,
    'truck': 6.0,  # Emergency vehicles
    'rickshaw': 4.5,
    'bike': 5.5
}

# Vehicle dimensions
vehicleSizes = {
    'car': (35, 50),
    'bus': (45, 65),
    'truck': (45, 65),
    'rickshaw': (30, 45),
    'bike': (25, 40)
}

# Traffic control parameters
signals = []
noOfSignals = 4
simTime = 300
timeElapsed = 0
currentGreen = 0
nextGreen = (currentGreen+1)%noOfSignals
currentYellow = 0
noOfLanes = 3
detectionTime = 2

# Vehicle timing parameters
carTime = 2
bikeTime = 1
rickshawTime = 2
busTime = 2.5
truckTime = 1.5

# Spacing parameters
minimumGap = 20
safetyGap = 25
stoppingGap = 30
turningGap = 35

# Coordinates
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

# Vehicle tracking
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

# Stop lines and turning points
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

stops = {
    'right': [580,580,580], 
    'down': [320,320,320], 
    'left': [810,810,810], 
    'up': [545,545,545]
}

mid = {
    'right': {'x':705, 'y':445, 'angle':90},
    'down': {'x':695, 'y':450, 'angle':90},
    'left': {'x':695, 'y':425, 'angle':90},
    'up': {'x':695, 'y':400, 'angle':90}
}

# Q-learning parameters
LEARNING_RATE = 0.1
DISCOUNT_FACTOR = 0.95
EPSILON = 0.1
MAX_WAITING_TIME = 120
EMERGENCY_PRIORITY = 2.0
CONGESTION_THRESHOLD = 8

pygame.init()
simulation = pygame.sprite.Group()

class QLearningAgent:
    def __init__(self):
        self.learning_rate = LEARNING_RATE
        self.discount_factor = DISCOUNT_FACTOR
        self.epsilon = EPSILON
        self.q_table = defaultdict(lambda: {
            'short': defaultMinimum,
            'medium': defaultGreen,
            'long': defaultMaximum
        })
        self.state_history = []
        self.reward_history = []
        
    def get_state(self):
        state_components = []
        for direction in directionNumbers.values():
            # Count waiting vehicles
            waiting_count = sum(1 for lane in range(noOfLanes)
                              for vehicle in vehicles[direction][lane]
                              if vehicle.crossed == 0)
            # Check for emergency vehicles
            emergency_present = any(vehicle.isEmergency and vehicle.crossed == 0
                                  for lane in range(noOfLanes)
                                  for vehicle in vehicles[direction][lane])
            # Calculate congestion level
            congestion = min(2, waiting_count // CONGESTION_THRESHOLD)
            
            state_components.extend([congestion, int(emergency_present)])
        
        return tuple(state_components)
    
    def get_action(self, state):
        if random.random() < self.epsilon:
            return random.choice(['short', 'medium', 'long'])
        return max(self.q_table[state].items(), key=lambda x: x[1])[0]
    
    def get_reward(self, state):
        reward = 0
        for direction in directionNumbers.values():
            # Reward for cleared vehicles
            reward += vehicles[direction]['crossed'] * 10
            
            # Penalty for waiting vehicles
            waiting_vehicles = sum(1 for lane in range(noOfLanes)
                                 for vehicle in vehicles[direction][lane]
                                 if vehicle.crossed == 0)
            reward -= waiting_vehicles * 5
            
            # Emergency vehicle handling
            emergency_waiting = sum(1 for lane in range(noOfLanes)
                                  for vehicle in vehicles[direction][lane]
                                  if vehicle.isEmergency and vehicle.crossed == 0)
            reward -= emergency_waiting * 20
        
        self.reward_history.append(reward)
        return reward
    
    def update(self, state, action, reward, next_state):
        current_q = self.q_table[state][action]
        next_max_q = max(self.q_table[next_state].values())
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max_q - current_q
        )
        self.q_table[state][action] = new_q
        self.state_history.append((state, action, reward))
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
        emergency_factor = EMERGENCY_PRIORITY if self.emergencyMode else 0.0
        return (0.4 * waiting_factor + 
                0.4 * congestion_factor + 
                0.2 * emergency_factor)

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
        vehicles[self.direction][self.lane].append(self)
        if self.isEmergency:
            vehicles[self.direction]['emergency'].append(self)
        
        self.index = len(vehicles[self.direction][self.lane]) - 1
        self.x = x[self.direction][self.lane]
        self.y = y[self.direction][self.lane]
        
        if self.index > 0:
            prev_vehicle = vehicles[self.direction][self.lane][self.index - 1]
            self.safe_distance = prev_vehicle.size[0 if self.direction in ['right', 'left'] else 1] + safetyGap
        
        self.set_initial_stop_position()

    def load_images(self):
        try:
            path = f"images/{self.direction}/{self.vehicleClass}.png"
            self.originalImage = pygame.image.load(path)
            self.currentImage = pygame.image.load(path)
            
            self.originalImage = pygame.transform.scale(self.originalImage, self.size)
            self.currentImage = pygame.transform.scale(self.currentImage, self.size)
        except pygame.error as e:
            print(f"Error loading vehicle image: {e}")
            raise

    def set_initial_stop_position(self):
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
        proposed_rect = pygame.Rect(new_x, new_y, self.size[0], self.size[1])
        
        for direction in vehicles:
            for lane in range(noOfLanes):
                for vehicle in vehicles[direction][lane]:
                    if vehicle != self:
                        other_rect = pygame.Rect(vehicle.x, vehicle.y, 
                                               vehicle.size[0], vehicle.size[1])
                        if proposed_rect.colliderect(other_rect):
                            overlap_area = (min(proposed_rect.right, other_rect.right) - 
                                          max(proposed_rect.left, other_rect.left)) * \
                                         (min(proposed_rect.bottom, other_rect.bottom) - 
                                          max(proposed_rect.top, other_rect.top))
                            if overlap_area > 50:
                                return True
        return False

    def move(self):
        self.update_position()
        
        if self.isEmergency:
            self.speed = self.max_speed * 1.5
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

    def update_position(self):
        self.last_position = (self.x, self.y)

    def check_stalled(self):
        if self.last_position:
            if (abs(self.x - self.last_position[0]) < 0.1 and 
                abs(self.y - self.last_position[1]) < 0.1):
                self.stalled_time += 1
                if self.stalled_time > 10:
                    self.handle_stall()
            else:
                self.stalled_time = 0

    def handle_stall(self):
        if self.isEmergency:
            self.speed = self.max_speed * 1.5
        else:
            self.try_alternative_movement()

    def try_alternative_movement(self):
        if self.direction in ['right', 'left']:
            new_y = self.y + (5 if random.random() > 0.5 else -5)
            if not self.check_collision(self.x, new_y):
                self.y = new_y
        else:
            new_x = self.x + (5 if random.random() > 0.5 else -5)
            if not self.check_collision(new_x, self.y):
                self.x = new_x
class VehicleMovement:
    @staticmethod
    def handle_crossing(vehicle):
        """Handle vehicle crossing the intersection"""
        vehicle.crossed = 1
        vehicles[vehicle.direction]['crossed'] += 1
        if vehicle.isEmergency:
            signals[vehicle.direction_number].emergency_vehicles_passed += 1
        signals[vehicle.direction_number].vehicles_passed += 1

    @staticmethod
    def check_turning_point(vehicle):
        """Check if vehicle is near turning point"""
        turn_point = mid[vehicle.direction]
        if vehicle.direction in ['right', 'left']:
            return abs(vehicle.x - turn_point['x']) < turningGap
        else:
            return abs(vehicle.y - turn_point['y']) < turningGap

    @staticmethod
    def execute_turn(vehicle):
        """Execute turning movement with smooth rotation"""
        turn_increment = 3
        vehicle.rotateAngle += turn_increment
        vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
        
        if vehicle.direction == 'right':
            vehicle.x += 2.5
            vehicle.y += 2.0
        elif vehicle.direction == 'down':
            vehicle.x -= 2.5
            vehicle.y += 2.0
        elif vehicle.direction == 'left':
            vehicle.x -= 2.5
            vehicle.y -= 2.0
        elif vehicle.direction == 'up':
            vehicle.x += 2.5
            vehicle.y -= 2.0
            
        if vehicle.rotateAngle >= 90:
            vehicle.turned = 1
            vehicle.rotateAngle = 90

def detectEmergencyVehicles():
    """Detect emergency vehicles in the traffic"""
    emergency_vehicles = []
    for direction in directionNumbers.values():
        for lane in range(noOfLanes):
            for vehicle in vehicles[direction][lane]:
                if vehicle.isEmergency and vehicle.crossed == 0:
                    emergency_vehicles.append((vehicle, list(directionNumbers.values()).index(direction)))
    
    if emergency_vehicles:
        # Prioritize emergency vehicle with longest waiting time
        emergency_vehicle, direction = max(emergency_vehicles, 
                                        key=lambda x: x[0].waiting_time)
        return True, direction
    return False, None

def handleEmergencyVehicle(direction_number):
    """Handle emergency vehicle priority"""
    global currentGreen, currentYellow, nextGreen
    
    if currentGreen != direction_number:
        currentYellow = 1
        signals[currentGreen].yellow = defaultYellow // 2
        
        for i in range(noOfSignals):
            if i != direction_number:
                signals[i].red = defaultRed
                signals[i].yellow = 0
                signals[i].green = 0
            else:
                signals[i].green = defaultGreen
                signals[i].yellow = 0
                signals[i].red = 0
                signals[i].emergencyMode = True
        
        currentGreen = direction_number
        nextGreen = (direction_number + 1) % noOfSignals

def initialize():
    """Initialize traffic signals"""
    global signals
    signals = []  # Clear existing signals if any
    
    # Create initial signals
    ts1 = TrafficSignal(0, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts1)
    
    ts2 = TrafficSignal(ts1.red+ts1.yellow+ts1.green, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts2)
    
    ts3 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts3)
    
    ts4 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts4)

def updateTrafficState():
    """Update traffic state and manage signal timings"""
    if not signals:  # Check if signals are initialized
        initialize()
        
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
        
        # Get signal index safely
        try:
            signal_idx = list(directionNumbers.values()).index(direction)
            if signal_idx < len(signals):
                signals[signal_idx].congestion_level = waiting_vehicles / (noOfLanes * CONGESTION_THRESHOLD)
                
                if emergency_waiting > 0 and currentGreen != signal_idx:
                    signals[signal_idx].emergencyMode = True
                    if max_waiting_time > MAX_WAITING_TIME / 2:
                        handleEmergencyVehicle(signal_idx)
        except (ValueError, IndexError) as e:
            print(f"Error updating traffic state: {e}")
            continue

class TrafficSimulation:
    def __init__(self):
        pygame.init()
        self.setup_display()
        initialize()  # Initialize signals first
        self.setup_simulation()
        self.load_images()
        self.initialize_metrics()
        self.movement_handler = VehicleMovement()

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
            try:
                self.clock.tick(self.fps * self.simulation_speed)
                self.handle_input()
                
                if not self.paused and signals:  # Check if signals are initialized
                    updateTrafficState()
                    self.update_metrics()
                
                # Draw simulation
                self.screen.fill(self.colors['white'])
                self.screen.blit(self.background, (0, 0))
                self.draw_signals()
                self.draw_vehicles()
                self.draw_stats()
                
                if self.show_debug:
                    self.draw_debug_info()
                
                pygame.display.flip()
                
                self.frame_count += 1
                if self.frame_count % 60 == 0:
                    current_time = time.time()
                    self.fps = 60 / (current_time - self.last_update)
                    self.last_update = current_time
                    
            except Exception as e:
                print(f"Error in simulation loop: {e}")
                continue



def setTime():
    """Set signal timings using Q-learning"""
    global q_learning
    if not hasattr(setTime, 'q_learning'):
        setTime.q_learning = QLearningAgent()
    
    emergency_present, emergency_direction = detectEmergencyVehicles()
    if emergency_present:
        handleEmergencyVehicle(emergency_direction)
        return
    
    current_state = setTime.q_learning.get_state()
    action = setTime.q_learning.get_action(current_state)
    
    # Set green time based on action and traffic conditions
    if action == 'short':
        green_time = defaultMinimum
    elif action == 'long':
        green_time = defaultMaximum
    else:
        green_time = defaultGreen
    
    # Store state for reward calculation
    signals[nextGreen].current_state = current_state
    signals[nextGreen].current_action = action
    signals[nextGreen].green = green_time

def generateVehicles():
    """Generate vehicles with improved distribution"""
    while True:
        try:
            # Calculate total waiting vehicles
            total_waiting = 0
            for direction in directionNumbers.values():
                for lane in range(noOfLanes):
                    total_waiting += sum(1 for v in vehicles[direction][lane] if v.crossed == 0)
            
            if total_waiting < CONGESTION_THRESHOLD * noOfLanes * noOfSignals:
                # Vehicle type selection with weights
                weights = [0.4, 0.2, 0.1, 0.2, 0.1]  # car, bus, truck, rickshaw, bike
                vehicle_type = random.choices(range(5), weights=weights)[0]
                
                # Lane selection
                lane_number = 0 if vehicle_type == 4 else random.randint(1, 2)
                
                # Calculate lane occupancy
                lane_occupancy = []
                for d in directionNumbers.values():
                    for i in range(noOfLanes):
                        count = sum(1 for v in vehicles[d][i] if v.crossed == 0)
                        lane_occupancy.append(count)
                
                # Determine turning probability
                turn_probability = 0.3 if lane_number == 2 else 0.1
                will_turn = random.random() < turn_probability
                
                # Choose direction with least traffic
                direction_counts = []
                for i in range(noOfSignals):
                    count = 0
                    for lane in range(noOfLanes):
                        count += sum(1 for v in vehicles[directionNumbers[i]][lane] if v.crossed == 0)
                    direction_counts.append((i, count))
                
                direction_number = min(direction_counts, key=lambda x: x[1])[0]
                
                # Create new vehicle
                Vehicle(lane_number, vehicleTypes[vehicle_type], 
                       direction_number, directionNumbers[direction_number], 
                       will_turn)
                
                # Adaptive delay based on traffic density
                delay = max(0.5, 2 - (total_waiting / (CONGESTION_THRESHOLD * noOfLanes * noOfSignals)))
                time.sleep(delay)
            else:
                time.sleep(1)  # Wait if traffic is heavy
                
        except Exception as e:
            print(f"Error generating vehicle: {e}")
            continue

def simulationTime():
    """Track simulation time and print final statistics"""
    global timeElapsed, simTime
    while True:
        timeElapsed += 1
        time.sleep(1)
        if timeElapsed == simTime:
            print('\nSimulation completed.\nResults:')
            print('Direction-wise vehicle count:')
            total_vehicles = 0
            total_waiting_time = 0
            emergency_response_times = []
            
            for i in range(noOfSignals):
                direction = directionNumbers[i]
                count = vehicles[direction]['crossed']
                waiting = len(vehicles[direction]['waiting'])
                emergency = sum(1 for lane in range(noOfLanes)
                              for v in vehicles[direction][lane]
                              if v.isEmergency)
                
                print(f'\nDirection {i+1}:')
                print(f'  Vehicles crossed: {count}')
                print(f'  Vehicles waiting: {waiting}')
                print(f'  Emergency vehicles: {emergency}')
                
                total_vehicles += count
                
                for lane in range(noOfLanes):
                    for vehicle in vehicles[direction][lane]:
                        total_waiting_time += vehicle.waiting_time
                        if vehicle.isEmergency:
                            emergency_response_times.append(vehicle.waiting_time)
            
            print('\nOverall Statistics:')
            print(f'Total vehicles processed: {total_vehicles}')
            if total_vehicles > 0:
                print(f'Average waiting time: {total_waiting_time/total_vehicles:.2f} seconds')
            if emergency_response_times:
                print(f'Average emergency response time: {sum(emergency_response_times)/len(emergency_response_times):.2f} seconds')
            print(f'Throughput: {total_vehicles/simTime:.2f} vehicles/second')
            
            os._exit(1)
    def setup_simulation(self):
        """Initialize simulation components"""
        self.q_learning = QLearningAgent()
        self.frame_count = 0
        self.last_update = time.time()
        self.fps = 60
        self.clock = pygame.time.Clock()
        self.paused = False
        self.show_debug = False
        self.show_q_values = False
        self.simulation_speed = 1.0
        
    def load_images(self):
        """Load and prepare images"""
        try:
            self.background = pygame.image.load('images/mod_int.png')
            self.signals_images = {
                'red': pygame.image.load('images/signals/red.png'),
                'yellow': pygame.image.load('images/signals/yellow.png'),
                'green': pygame.image.load('images/signals/green.png')
            }
            
            # Scale signal images
            for key in self.signals_images:
                self.signals_images[key] = pygame.transform.scale(
                    self.signals_images[key], (30, 90))
            
            # Create emergency vehicle indicator
            self.emergency_indicator = pygame.Surface((20, 20))
            self.emergency_indicator.fill(self.colors['red'])
            
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
            'lane_utilization': defaultdict(list),
            'q_learning_rewards': [],
            'learning_progress': []
        }

    def update_metrics(self):
        """Update simulation metrics"""
        total_vehicles = 0
        total_speed = 0
        current_congestion = 0
        
        for direction in directionNumbers.values():
            direction_vehicles = 0
            for lane in range(noOfLanes):
                lane_vehicles = len(vehicles[direction][lane])
                direction_vehicles += lane_vehicles
                self.metrics['lane_utilization'][direction].append(lane_vehicles)
                
                for vehicle in vehicles[direction][lane]:
                    if vehicle.crossed == 0:
                        self.metrics['total_waiting_time'] += vehicle.waiting_time
                        current_congestion += 1
                    if vehicle.isEmergency and vehicle.crossed == 1:
                        self.metrics['emergency_response_time'].append(vehicle.waiting_time)
                    total_speed += vehicle.speed
                    total_vehicles += 1
        
        if total_vehicles > 0:
            self.metrics['average_speed'].append(total_speed / total_vehicles)
        
        self.metrics['congestion_levels'].append(current_congestion)
        
        # Update Q-learning metrics
        if hasattr(self.q_learning, 'reward_history') and self.q_learning.reward_history:
            self.metrics['q_learning_rewards'].append(
                sum(self.q_learning.reward_history[-10:]) / min(10, len(self.q_learning.reward_history))
            )

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
            timer_text = self.fonts['medium'].render(str(signals[i].signalText), True, color)
            self.screen.blit(timer_text, signalTimerCoords[i])
            
            # Draw Q-learning state if enabled
            if self.show_q_values and hasattr(signals[i], 'current_state'):
                q_text = self.fonts['small'].render(
                    f"Q: {self.q_learning.q_table[signals[i].current_state][signals[i].current_action]:.2f}",
                    True, self.colors['purple']
                )
                self.screen.blit(q_text, (signalCoords[i][0]-10, signalCoords[i][1]-50))
            
            # Draw emergency mode indicator
            if signals[i].emergencyMode:
                emergency_text = self.fonts['medium'].render("EMERGENCY", True, self.colors['red'])
                self.screen.blit(emergency_text, 
                               (signalCoords[i][0]-10, signalCoords[i][1]-30))

    def draw_vehicles(self):
        """Draw vehicles with enhanced visualization"""
        for vehicle in simulation:
            # Draw vehicle
            self.screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
            
            # Draw vehicle indicators
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
            
            # Draw waiting time for stopped vehicles
            if vehicle.stopped and vehicle.waiting_time > 30:
                wait_text = self.fonts['small'].render(
                    str(vehicle.waiting_time), True, 
                    self.colors['red'] if vehicle.waiting_time > 60 else self.colors['orange']
                )
                self.screen.blit(wait_text, (vehicle.x, vehicle.y - 20))

    def draw_stats(self):
        """Draw performance statistics"""
        stats_x = 1100
        stats_y = 50
        line_height = 30
        
        # Draw simulation time and speed
        time_text = self.fonts['large'].render(
            f"Time: {timeElapsed}s (Speed: {self.simulation_speed:.1f}x)", 
            True, self.colors['black']
        )
        self.screen.blit(time_text, (stats_x, stats_y))
        
        # Draw vehicle statistics
        y_offset = stats_y + line_height * 2
        for i in range(noOfSignals):
            direction = directionNumbers[i]
            crossed = vehicles[direction]['crossed']
            waiting = len([v for lane in range(noOfLanes)
                         for v in vehicles[direction][lane]
                         if v.crossed == 0])
            emergency = len([v for lane in range(noOfLanes)
                           for v in vehicles[direction][lane]
                           if v.isEmergency and v.crossed == 0])
            
            color = self.colors['red'] if emergency > 0 else self.colors['black']
            text = self.fonts['medium'].render(
                f"Direction {i+1}: {crossed} (Waiting: {waiting}, Emergency: {emergency})",
                True, color
            )
            self.screen.blit(text, (stats_x, y_offset + line_height * i))
        
        # Draw performance metrics
        y_offset += line_height * (noOfSignals + 1)
        
        if self.metrics['average_speed']:
            avg_speed = sum(self.metrics['average_speed'][-10:]) / min(10, len(self.metrics['average_speed']))
            speed_text = self.fonts['medium'].render(
                f"Avg Speed: {avg_speed:.2f}", True, self.colors['blue']
            )
            self.screen.blit(speed_text, (stats_x, y_offset))
        
        if self.metrics['emergency_response_time']:
            avg_response = sum(self.metrics['emergency_response_time']) / len(self.metrics['emergency_response_time'])
            response_text = self.fonts['medium'].render(
                f"Avg Emergency Response: {avg_response:.2f}s",
                True, self.colors['red']
            )
            self.screen.blit(response_text, (stats_x, y_offset + line_height))
        
        # Draw Q-learning metrics
        if self.metrics['q_learning_rewards']:
            avg_reward = sum(self.metrics['q_learning_rewards'][-10:]) / min(10, len(self.metrics['q_learning_rewards']))
            reward_text = self.fonts['medium'].render(
                f"Avg Q-Learning Reward: {avg_reward:.2f}",
                True, self.colors['purple']
            )
            self.screen.blit(reward_text, (stats_x, y_offset + line_height * 2))

    def handle_input(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_d:
                    self.show_debug = not self.show_debug
                elif event.key == pygame.K_q:
                    self.show_q_values = not self.show_q_values
                elif event.key == pygame.K_UP:
                    self.simulation_speed = min(2.0, self.simulation_speed + 0.1)
                elif event.key == pygame.K_DOWN:
                    self.simulation_speed = max(0.1, self.simulation_speed - 0.1)

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
            self.clock.tick(self.fps * self.simulation_speed)
            self.handle_input()
            
            if not self.paused:
                updateTrafficState()
                self.update_metrics()
            
            # Draw simulation
            self.screen.fill(self.colors['white'])
            self.screen.blit(self.background, (0, 0))
            self.draw_signals()
            self.draw_vehicles()
            self.draw_stats()
            
            if self.show_debug:
                self.draw_debug_info()
            
            pygame.display.flip()
            
            self.frame_count += 1
            if self.frame_count % 60 == 0:
                current_time = time.time()
                self.fps = 60 / (current_time - self.last_update)
                self.last_update = current_time

def main():
    try:
        simulation = TrafficSimulation()
        simulation.run()
    except Exception as e:
        print(f"Simulation error: {e}")
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)

if __name__ == '__main__':
    main()                                    