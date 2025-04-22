import random
import math
import time
import threading
import pygame
import sys
import os
import numpy as np
from collections import defaultdict

# Optimized default timings
defaultRed = 100
defaultYellow = 3
defaultGreen = 60
defaultMinimum = 20
defaultMaximum = 120

# Simulation parameters
signals = []
noOfSignals = 4
simTime = 300
timeElapsed = 0
currentGreen = 0
nextGreen = (currentGreen+1)%noOfSignals
currentYellow = 0

# Optimized vehicle speeds for smoother flow
speeds = {
    'car': 4.0,
    'bus': 3.5,
    'truck': 6.0,  # Emergency vehicles
    'rickshaw': 3.8,
    'bike': 4.5
}

# Optimized vehicle dimensions and spacing
vehicleSizes = {
    'car': (30, 50),
    'bus': (40, 60),
    'truck': (40, 60),
    'rickshaw': (25, 45),
    'bike': (20, 40)
}

# Optimized gaps for better traffic flow
minimumGap = 15  # Minimum gap between vehicles
safetyGap = 20   # Safety gap for lane changing
stoppingGap = 25 # Gap when stopping at signals

# Traffic count variables
noOfCars = 0
noOfBikes = 0
noOfBuses = 0
noOfTrucks = 0
noOfRickshaws = 0
noOfLanes = 3  # Increased number of lanes
detectionTime = 3

# Optimized coordinates for smoother turns
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

# Enhanced vehicle tracking with lane management
vehicles = {
    'right': {0:[], 1:[], 2:[], 'crossed':0, 'waiting':[]}, 
    'down': {0:[], 1:[], 2:[], 'crossed':0, 'waiting':[]}, 
    'left': {0:[], 1:[], 2:[], 'crossed':0, 'waiting':[]}, 
    'up': {0:[], 1:[], 2:[], 'crossed':0, 'waiting':[]}
}

vehicleTypes = {0:'car', 1:'bus', 2:'truck', 3:'rickshaw', 4:'bike'}
directionNumbers = {0:'right', 1:'down', 2:'left', 3:'up'}

# Optimized signal positions
signalCoods = [(530,230), (810,230), (810,570), (530,570)]
signalTimerCoods = [(530,210), (810,210), (810,550), (530,550)]
vehicleCountCoods = [(480,210), (880,210), (880,550), (480,550)]

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

# Improved turning coordinates for smoother turns
mid = {
    'right': {'x':705, 'y':445, 'angle':90},
    'down': {'x':695, 'y':450, 'angle':90},
    'left': {'x':695, 'y':425, 'angle':90},
    'up': {'x':695, 'y':400, 'angle':90}
}

class TrafficState:
    def __init__(self):
        self.queue_lengths = defaultdict(int)
        self.waiting_times = defaultdict(float)
        self.emergency_vehicles = defaultdict(int)
        self.congestion_level = defaultdict(float)

    def update(self, direction):
        total_vehicles = 0
        max_waiting_time = 0
        emergency_count = 0
        
        for lane in range(noOfLanes):
            for vehicle in vehicles[direction][lane]:
                if vehicle.crossed == 0:
                    total_vehicles += 1
                    max_waiting_time = max(max_waiting_time, vehicle.waiting_time)
                    if vehicle.isEmergency:
                        emergency_count += 1

        self.queue_lengths[direction] = total_vehicles
        self.waiting_times[direction] = max_waiting_time
        self.emergency_vehicles[direction] = emergency_count
        self.congestion_level[direction] = min(1.0, total_vehicles / (noOfLanes * 10))

class TrafficQLearning:
    def __init__(self):
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1
        self.q_table = defaultdict(lambda: {
            'short': 0,
            'medium': 0,
            'long': 0
        })
        self.state_history = []
        self.reward_history = []
        self.traffic_state = TrafficState()

    def get_state(self, direction):
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
class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.lastGreen = 0
        self.emergencyMode = False
        self.current_state = None
        self.current_action = None
        self.next_action = None
        self.waiting_time = 0
        self.vehicles_passed = 0
        self.emergency_vehicles_passed = 0

    def update_metrics(self):
        self.waiting_time += 1 if self.red > 0 else 0
        
    def should_extend_green(self):
        return (self.vehicles_passed < 5 and 
                self.green > self.minimum and 
                not self.emergencyMode)

    def can_switch_to_yellow(self):
        return (self.green <= self.minimum or 
                self.vehicles_passed >= 10 or 
                self.emergencyMode)

class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite.__init__(self)
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.direction_number = direction_number
        self.direction = direction
        self.x = x[direction][lane]
        self.y = y[direction][lane]
        
        # Enhanced vehicle properties
        self.speed = speeds[vehicleClass]
        self.max_speed = speeds[vehicleClass]
        self.acceleration = 0.1
        self.deceleration = 0.2
        self.crossed = 0
        self.willTurn = will_turn
        self.turned = 0
        self.rotateAngle = 0
        self.isEmergency = (vehicleClass == 'truck')
        self.waiting_time = 0
        self.stopped = False
        self.safe_distance = safetyGap
        self.size = vehicleSizes[vehicleClass]
        
        # Initialize position and image
        self.initialize_position()
        self.load_images()
        simulation.add(self)

    def initialize_position(self):
        vehicles[self.direction][self.lane].append(self)
        self.index = len(vehicles[self.direction][self.lane]) - 1
        
        if self.index > 0:
            prev_vehicle = vehicles[self.direction][self.lane][self.index - 1]
            if self.direction in ['right', 'left']:
                self.safe_distance = prev_vehicle.size[0] + safetyGap
            else:
                self.safe_distance = prev_vehicle.size[1] + safetyGap

        self.set_initial_stop_position()

    def load_images(self):
        path = f"images/{self.direction}/{self.vehicleClass}.png"
        self.originalImage = pygame.image.load(path)
        self.currentImage = pygame.image.load(path)
        
        # Scale image according to vehicle size
        self.originalImage = pygame.transform.scale(self.originalImage, self.size)
        self.currentImage = pygame.transform.scale(self.currentImage, self.size)

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

    def check_collision(self, x, y):
        rect1 = pygame.Rect(x, y, self.size[0], self.size[1])
        for direction in vehicles:
            for lane in range(noOfLanes):
                for vehicle in vehicles[direction][lane]:
                    if vehicle != self:
                        rect2 = pygame.Rect(vehicle.x, vehicle.y, vehicle.size[0], vehicle.size[1])
                        if rect1.colliderect(rect2):
                            return True
        return False

    def adjust_speed(self):
        if self.stopped:
            self.speed = max(0, self.speed - self.deceleration)
        else:
            self.speed = min(self.max_speed, self.speed + self.acceleration)

    def update_waiting_time(self):
        if self.speed < 0.1 and self.crossed == 0:
            self.waiting_time += 1
            self.stopped = True
        else:
            self.stopped = False

    def handle_turning(self):
        if self.turned == 0:
            self.rotateAngle += rotationAngle
            self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
            
            turn_data = mid[self.direction]
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
                
            if self.rotateAngle >= turn_data['angle']:
                self.turned = 1
                self.rotateAngle = turn_data['angle']

    def move(self):
        if self.isEmergency:
            self.speed = self.max_speed * 1.2
            can_move = True
        else:
            emergency_present, emergency_direction = detectEmergencyVehicles()
            can_move = not emergency_present or self.direction_number == emergency_direction or self.crossed == 1

        if not can_move:
            self.update_waiting_time()
            return

        self.adjust_speed()
        
        if self.crossed == 0 and self.check_crossing():
            self.crossed = 1
            vehicles[self.direction]['crossed'] += 1

        if self.willTurn and self.crossed == 0:
            self.handle_turn_movement()
        else:
            self.handle_straight_movement()

        self.update_waiting_time()

    def check_crossing(self):
        if self.direction == 'right':
            return self.x + self.size[0] > stopLines[self.direction]
        elif self.direction == 'down':
            return self.y + self.size[1] > stopLines[self.direction]
        elif self.direction == 'left':
            return self.x < stopLines[self.direction]
        elif self.direction == 'up':
            return self.y < stopLines[self.direction]

    def handle_turn_movement(self):
        if self.crossed == 0:
            if self.can_move_forward():
                self.move_forward()
            elif self.near_turning_point():
                self.handle_turning()
        else:
            if self.turned == 0:
                self.handle_turning()
            else:
                self.move_after_turn()

    def handle_straight_movement(self):
        if self.can_move_forward():
            self.move_forward()

    def can_move_forward(self):
        # Implementation depends on direction and traffic rules
        pass

    def move_forward(self):
        # Implementation depends on direction
        pass

    def move_after_turn(self):
        # Implementation depends on direction
        pass
def can_move_forward(self):
    if self.direction == 'right':
        if self.crossed == 0:
            if self.x + self.size[0] <= self.stop:
                return True
            elif (currentGreen == 0 and currentYellow == 0) or self.isEmergency:
                if self.index == 0 or self.x + self.size[0] < (vehicles[self.direction][self.lane][self.index-1].x - safetyGap):
                    return True
        else:
            return True
    
    elif self.direction == 'down':
        if self.crossed == 0:
            if self.y + self.size[1] <= self.stop:
                return True
            elif (currentGreen == 1 and currentYellow == 0) or self.isEmergency:
                if self.index == 0 or self.y + self.size[1] < (vehicles[self.direction][self.lane][self.index-1].y - safetyGap):
                    return True
        else:
            return True
    
    elif self.direction == 'left':
        if self.crossed == 0:
            if self.x >= self.stop:
                return True
            elif (currentGreen == 2 and currentYellow == 0) or self.isEmergency:
                if self.index == 0 or self.x > (vehicles[self.direction][self.lane][self.index-1].x + vehicles[self.direction][self.lane][self.index-1].size[0] + safetyGap):
                    return True
        else:
            return True
    
    elif self.direction == 'up':
        if self.crossed == 0:
            if self.y >= self.stop:
                return True
            elif (currentGreen == 3 and currentYellow == 0) or self.isEmergency:
                if self.index == 0 or self.y > (vehicles[self.direction][self.lane][self.index-1].y + vehicles[self.direction][self.lane][self.index-1].size[1] + safetyGap):
                    return True
        else:
            return True
    
    return False

def move_forward(self):
    if self.direction == 'right':
        temp_x = self.x + self.speed
        if not self.check_collision(temp_x, self.y):
            self.x = temp_x
    elif self.direction == 'down':
        temp_y = self.y + self.speed
        if not self.check_collision(self.x, temp_y):
            self.y = temp_y
    elif self.direction == 'left':
        temp_x = self.x - self.speed
        if not self.check_collision(temp_x, self.y):
            self.x = temp_x
    elif self.direction == 'up':
        temp_y = self.y - self.speed
        if not self.check_collision(self.x, temp_y):
            self.y = temp_y

def updateSignalQL(q_learning):
    global currentGreen, nextGreen
    
    current_state = q_learning.get_state(nextGreen)
    
    # Epsilon-greedy action selection
    if random.random() < q_learning.epsilon:
        action = random.choice(['short', 'medium', 'long'])
    else:
        action = max(q_learning.q_table[current_state].items(), key=lambda x: x[1])[0]
    
    # Set green time based on action and traffic conditions
    if action == 'short':
        green_time = max(defaultMinimum, 
                        min(defaultGreen, 
                            q_learning.traffic_state.queue_lengths[directionNumbers[nextGreen]] * 5))
    elif action == 'long':
        green_time = min(defaultMaximum, 
                        max(defaultGreen, 
                            q_learning.traffic_state.queue_lengths[directionNumbers[nextGreen]] * 8))
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
    for direction in directionNumbers.values():
        waiting_vehicles = 0
        max_waiting_time = 0
        
        for lane in range(noOfLanes):
            for vehicle in vehicles[direction][lane]:
                if vehicle.crossed == 0:
                    waiting_vehicles += 1
                    max_waiting_time = max(max_waiting_time, vehicle.waiting_time)
        
        vehicles[direction]['waiting'] = waiting_vehicles
        
        # Adaptive signal timing based on waiting vehicles
        if waiting_vehicles > 10 and currentGreen != directionNumbers.index(direction):
            signals[directionNumbers.index(direction)].waiting_time += 1

def updateVehicles():
    for direction in directionNumbers.values():
        for lane in range(noOfLanes):
            for vehicle in vehicles[direction][lane]:
                vehicle.update_waiting_time()
                if vehicle.crossed == 0:
                    vehicle.move()

def generateVehicles():
    while True:
        # Check current traffic density
        total_waiting = sum(vehicles[direction]['waiting'] 
                          for direction in directionNumbers.values())
        
        if total_waiting < 40:  # Adjust threshold based on capacity
            vehicle_type = random.randint(0, 4)
            
            # Intelligent lane selection
            if vehicle_type == 4:  # Bike
                lane_number = 0
            else:
                # Choose lane based on current lane occupancy
                lane_occupancy = [len(vehicles[directionNumbers[random.randint(0, 3)]][i]) 
                                for i in range(noOfLanes)]
                lane_number = lane_occupancy.index(min(lane_occupancy))
            
            # Determine turning based on lane and traffic
            will_turn = 1 if (lane_number == 2 and random.random() < 0.4) else 0
            
            # Choose direction with least traffic
            direction_counts = [(i, vehicles[directionNumbers[i]]['waiting']) 
                              for i in range(noOfSignals)]
            direction_number = min(direction_counts, key=lambda x: x[1])[0]
            
            try:
                Vehicle(lane_number, vehicleTypes[vehicle_type], 
                       direction_number, directionNumbers[direction_number], 
                       will_turn)
            except Exception as e:
                print(f"Error generating vehicle: {e}")
            
            # Adaptive delay based on traffic density
            delay = max(0.5, 2 - (total_waiting / 50))
            time.sleep(delay)
        else:
            time.sleep(1)  # Wait if traffic is heavy
def detectEmergencyVehicles():
    emergency_vehicles = []
    for direction in directionNumbers.values():
        for lane in range(noOfLanes):
            for vehicle in vehicles[direction][lane]:
                if vehicle.isEmergency and vehicle.crossed == 0:
                    emergency_vehicles.append((vehicle, directionNumbers.index(direction)))
    
    if emergency_vehicles:
        # Prioritize emergency vehicle with longest waiting time
        emergency_vehicle, direction = max(emergency_vehicles, 
                                        key=lambda x: x[0].waiting_time)
        return True, direction
    return False, None

def handleEmergencyVehicle(direction_number):
    global currentGreen, currentYellow, nextGreen
    
    if currentGreen != direction_number:
        # Quick yellow transition
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

class TrafficSimulation:
    def __init__(self):
        pygame.init()
        self.setup_display()
        self.setup_simulation()
        self.load_images()
        self.initialize_metrics()
        
    def setup_display(self):
        self.screenWidth = 1400
        self.screenHeight = 800
        self.screenSize = (self.screenWidth, self.screenHeight)
        self.screen = pygame.display.set_mode(self.screenSize)
        pygame.display.set_caption("Intelligent Traffic Management System")
        
        # Colors
        self.black = (0, 0, 0)
        self.white = (255, 255, 255)
        self.red = (255, 0, 0)
        self.yellow = (255, 255, 0)
        self.green = (0, 255, 0)
        self.blue = (0, 0, 255)
        
        self.font = pygame.font.Font(None, 30)
        
    def setup_simulation(self):
        self.q_learning = TrafficQLearning()
        self.frame_count = 0
        self.last_update = time.time()
        self.fps = 60
        self.clock = pygame.time.Clock()
        
    def load_images(self):
        self.background = pygame.image.load('images/mod_int.png')
        self.signals_images = {
            'red': pygame.image.load('images/signals/red.png'),
            'yellow': pygame.image.load('images/signals/yellow.png'),
            'green': pygame.image.load('images/signals/green.png')
        }
        
    def initialize_metrics(self):
        self.metrics = {
            'total_waiting_time': 0,
            'vehicles_passed': 0,
            'emergency_response_time': [],
            'average_speed': [],
            'congestion_levels': []
        }
        
    def update_metrics(self):
        total_vehicles = 0
        total_speed = 0
        
        for direction in directionNumbers.values():
            for lane in range(noOfLanes):
                for vehicle in vehicles[direction][lane]:
                    if vehicle.crossed == 0:
                        self.metrics['total_waiting_time'] += vehicle.waiting_time
                    if vehicle.isEmergency and vehicle.crossed == 1:
                        self.metrics['emergency_response_time'].append(vehicle.waiting_time)
                    total_speed += vehicle.speed
                    total_vehicles += 1
        
        if total_vehicles > 0:
            self.metrics['average_speed'].append(total_speed / total_vehicles)
            
        congestion = sum(vehicles[direction]['waiting'] for direction in directionNumbers.values())
        self.metrics['congestion_levels'].append(congestion)
        
    def draw_signals(self):
        for i in range(noOfSignals):
            if i == currentGreen:
                if currentYellow == 1:
                    self.screen.blit(self.signals_images['yellow'], signalCoods[i])
                else:
                    self.screen.blit(self.signals_images['green'], signalCoods[i])
            else:
                self.screen.blit(self.signals_images['red'], signalCoods[i])
                
            if signals[i].emergencyMode:
                text = self.font.render("EMERGENCY", True, self.red)
                self.screen.blit(text, (signalCoods[i][0], signalCoods[i][1] - 30))
                
    def draw_vehicles(self):
        for vehicle in simulation:
            self.screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
            
            # Draw indicators for emergency vehicles
            if vehicle.isEmergency and vehicle.crossed == 0:
                pygame.draw.circle(self.screen, self.red,
                                (int(vehicle.x + vehicle.size[0]/2),
                                 int(vehicle.y + vehicle.size[1]/2)), 5)
                
    def draw_stats(self):
        stats_y = 50
        stats_x = 1100
        
        # Draw simulation time
        time_text = self.font.render(f"Time: {timeElapsed}s", True, self.black)
        self.screen.blit(time_text, (stats_x, stats_y))
        
        # Draw vehicle counts
        for i in range(noOfSignals):
            direction = directionNumbers[i]
            count = vehicles[direction]['crossed']
            waiting = vehicles[direction]['waiting']
            text = self.font.render(f"Direction {i+1}: {count} (Waiting: {waiting})", 
                                  True, self.black)
            self.screen.blit(text, (stats_x, stats_y + 30 * (i+1)))
            
        # Draw performance metrics
        if self.metrics['average_speed']:
            avg_speed = sum(self.metrics['average_speed'][-10:]) / min(10, len(self.metrics['average_speed']))
            speed_text = self.font.render(f"Avg Speed: {avg_speed:.2f}", True, self.black)
            self.screen.blit(speed_text, (stats_x, stats_y + 150))
            
        if self.metrics['emergency_response_time']:
            avg_response = sum(self.metrics['emergency_response_time']) / len(self.metrics['emergency_response_time'])
            response_text = self.font.render(f"Avg Emergency Response: {avg_response:.2f}s", 
                                          True, self.black)
            self.screen.blit(response_text, (stats_x, stats_y + 180))
            
    def run(self):
        # Start simulation threads
        threads = [
            threading.Thread(target=generateVehicles, daemon=True),
            threading.Thread(target=simulationTime, daemon=True)
        ]
        for thread in threads:
            thread.start()
            
        while True:
            self.clock.tick(self.fps)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
            # Update simulation state
            updateTrafficState()
            updateVehicles()
            self.update_metrics()
            
            # Draw simulation
            self.screen.fill(self.white)
            self.screen.blit(self.background, (0, 0))
            self.draw_signals()
            self.draw_vehicles()
            self.draw_stats()
            
            pygame.display.flip()
            
            self.frame_count += 1
            if self.frame_count % 60 == 0:  # Update every second
                current_time = time.time()
                self.fps = 60 / (current_time - self.last_update)
                self.last_update = current_time

if __name__ == '__main__':
    try:
        simulation = TrafficSimulation()
        simulation.run()
    except Exception as e:
        print(f"Simulation error: {e}")
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)                    
    