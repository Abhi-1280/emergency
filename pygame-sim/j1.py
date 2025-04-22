import random
import math
import time
import threading
import pygame
import sys
import os
import numpy as np
from collections import deque

pygame.init()

defaultRed = 150
defaultYellow = 5
defaultGreen = 20
defaultMinimum = 10
defaultMaximum = 60
noOfSignals = 4

signals = []
currentGreen = 0
currentYellow = 0
nextGreen = (currentGreen + 1) % noOfSignals

speeds = {
    'car': 2.25,
    'bus': 1.8,
    'truck': 1.8,
    'rickshaw': 2,
    'bike': 2.5
}

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

vehicles = {
    'right': {0: [], 1: [], 2: [], 'crossed': 0},
    'down': {0: [], 1: [], 2: [], 'crossed': 0},
    'left': {0: [], 1: [], 2: [], 'crossed': 0},
    'up': {0: [], 1: [], 2: [], 'crossed': 0}
}

vehicleTypes = {0: 'car', 1: 'bus', 2: 'truck', 3: 'rickshaw', 4: 'bike'}
directionNumbers = {0: 'right', 1: 'down', 2: 'left', 3: 'up'}

signalCoords = [(530, 230), (810, 230), (810, 570), (530, 570)]
signalTimerCoords = [(530, 210), (810, 210), (810, 550), (530, 550)]
vehicleCountCoords = [(480, 210), (880, 210), (880, 550), (480, 550)]

stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
defaultStop = {'right': 580, 'down': 320, 'left': 810, 'up': 545}
stops = {'right': [580, 580, 580], 
         'down': [320, 320, 320], 
         'left': [810, 810, 810], 
         'up': [545, 545, 545]}

mid = {
    'right': {'x': 705, 'y': 445},
    'down': {'x': 695, 'y': 450},
    'left': {'x': 695, 'y': 425},
    'up': {'x': 695, 'y': 400}
}

rotationAngle = 3
gap = 40
gap2 = 15

simulation = pygame.sprite.Group()
class QLearning:
    def __init__(self):
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1
        self.state_size = 5
        self.action_size = 4
        self.q_table = np.zeros((self.state_size, self.state_size, self.action_size))
        self.memory = deque(maxlen=2000)
    
    def get_state(self, vehicle_count, emergency_count):
        traffic_state = min(4, vehicle_count // 5)
        emergency_state = min(4, emergency_count)
        return traffic_state, emergency_state
    
    def get_action(self, state):
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)
        return np.argmax(self.q_table[state[0]][state[1]])
    
    def update(self, state, action, reward, next_state):
        current_q = self.q_table[state[0]][state[1]][action]
        next_max_q = np.max(self.q_table[next_state[0]][next_state[1]])
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * next_max_q - current_q)
        self.q_table[state[0]][state[1]][action] = new_q

class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.lastGreen = 0
        self.crossed = 0
        self.current_state = [0, 0]
        self.last_action = 0
        self.reward = 0
        self.emergency_mode = False

class CollisionDetector:
    def __init__(self):
        self.safety_distance = 40
    
    def check_collision(self, vehicle1, vehicle2):
        rect1 = pygame.Rect(vehicle1.x, vehicle1.y, 
                          vehicle1.currentImage.get_rect().width,
                          vehicle1.currentImage.get_rect().height)
        rect2 = pygame.Rect(vehicle2.x, vehicle2.y,
                          vehicle2.currentImage.get_rect().width,
                          vehicle2.currentImage.get_rect().height)
        return rect1.colliderect(rect2)
    
    def is_safe_distance(self, vehicle1, vehicle2):
        distance = math.sqrt((vehicle1.x - vehicle2.x)**2 + (vehicle1.y - vehicle2.y)**2)
        return distance >= self.safety_distance

class EmergencyManager:
    def __init__(self):
        self.active_emergency = None
        self.emergency_queue = []
        self.priority_lanes = set()
        self.clearance_time = 5
        self.cooldown = 0
    
    def add_emergency(self, vehicle):
        if vehicle not in self.emergency_queue:
            self.emergency_queue.append(vehicle)
            self.update_priorities()
    
    def remove_emergency(self, vehicle):
        if vehicle in self.emergency_queue:
            self.emergency_queue.remove(vehicle)
            if vehicle == self.active_emergency:
                self.active_emergency = None
                self.cooldown = self.clearance_time
        self.update_priorities()
    
    def update_priorities(self):
        if not self.active_emergency and self.emergency_queue and self.cooldown <= 0:
            self.active_emergency = self.emergency_queue[0]
            self.priority_lanes = {self.active_emergency.direction_number}
            adjacent_lanes = [(self.active_emergency.direction_number - 1) % 4,
                            (self.active_emergency.direction_number + 1) % 4]
            self.priority_lanes.update(adjacent_lanes)
    
    def update(self):
        if self.cooldown > 0:
            self.cooldown -= 1
        self.update_priorities()
class VehicleManager:
    def __init__(self):
        self.collision_detector = CollisionDetector()
        self.vehicles = {
            'right': {0: [], 1: [], 2: [], 'crossed': 0},
            'down': {0: [], 1: [], 2: [], 'crossed': 0},
            'left': {0: [], 1: [], 2: [], 'crossed': 0},
            'up': {0: [], 1: [], 2: [], 'crossed': 0}
        }
        self.waiting_vehicles = []
        self.safe_distance = 40
    
    def add_vehicle(self, vehicle):
        direction = vehicle.direction
        lane = vehicle.lane
        self.vehicles[direction][lane].append(vehicle)
    
    def remove_vehicle(self, vehicle):
        direction = vehicle.direction
        lane = vehicle.lane
        if vehicle in self.vehicles[direction][lane]:
            self.vehicles[direction][lane].remove(vehicle)
    
    def check_spacing(self, vehicle):
        direction = vehicle.direction
        lane = vehicle.lane
        vehicles_in_lane = self.vehicles[direction][lane]
        if vehicle not in vehicles_in_lane:
            return True
        index = vehicles_in_lane.index(vehicle)
        
        if index > 0:
            prev_vehicle = vehicles_in_lane[index - 1]
            return self.collision_detector.is_safe_distance(vehicle, prev_vehicle)
        return True
    
    def can_move(self, vehicle):
        if not self.check_spacing(vehicle):
            return False
        
        if vehicle.crossed == 1:
            return True
        
        if vehicle.isEmergency:
            return True
        
        if currentGreen == vehicle.direction_number or currentYellow == 1:
            return True
        
        return False

class MovementController:
    def __init__(self):
        self.intersection_box = pygame.Rect(590, 330, 220, 205)
        self.turning_points = {
            'right': {'x': 705, 'y': 445},
            'down': {'x': 695, 'y': 450},
            'left': {'x': 695, 'y': 425},
            'up': {'x': 695, 'y': 400}
        }
    
    def update_vehicle_position(self, vehicle):
        if not vehicle_manager.can_move(vehicle):
            return False
        
        if vehicle.direction == 'right':
            return self.move_right(vehicle)
        elif vehicle.direction == 'down':
            return self.move_down(vehicle)
        elif vehicle.direction == 'left':
            return self.move_left(vehicle)
        elif vehicle.direction == 'up':
            return self.move_up(vehicle)
    
    def move_right(self, vehicle):
        if vehicle.crossed == 0 and vehicle.x + vehicle.currentImage.get_rect().width > stopLines[vehicle.direction]:
            vehicle.crossed = 1
            if vehicle.isEmergency:
                emergency_manager.remove_emergency(vehicle)
            vehicles[vehicle.direction]['crossed'] += 1
        
        if vehicle.willTurn:
            return self.handle_right_turn(vehicle)
        else:
            return self.handle_straight_movement(vehicle, 'right')
    
    def move_down(self, vehicle):
        if vehicle.crossed == 0 and vehicle.y + vehicle.currentImage.get_rect().height > stopLines[vehicle.direction]:
            vehicle.crossed = 1
            if vehicle.isEmergency:
                emergency_manager.remove_emergency(vehicle)
            vehicles[vehicle.direction]['crossed'] += 1
        
        if vehicle.willTurn:
            return self.handle_down_turn(vehicle)
        else:
            return self.handle_straight_movement(vehicle, 'down')
    
    def move_left(self, vehicle):
        if vehicle.crossed == 0 and vehicle.x < stopLines[vehicle.direction]:
            vehicle.crossed = 1
            if vehicle.isEmergency:
                emergency_manager.remove_emergency(vehicle)
            vehicles[vehicle.direction]['crossed'] += 1
        
        if vehicle.willTurn:
            return self.handle_left_turn(vehicle)
        else:
            return self.handle_straight_movement(vehicle, 'left')
    
    def move_up(self, vehicle):
        if vehicle.crossed == 0 and vehicle.y < stopLines[vehicle.direction]:
            vehicle.crossed = 1
            if vehicle.isEmergency:
                emergency_manager.remove_emergency(vehicle)
            vehicles[vehicle.direction]['crossed'] += 1
        
        if vehicle.willTurn:
            return self.handle_up_turn(vehicle)
        else:
            return self.handle_straight_movement(vehicle, 'up')
class MovementController:  # Continuing from previous part
    def handle_right_turn(self, vehicle):
        if vehicle.crossed == 0 or vehicle.x + vehicle.currentImage.get_rect().width < self.turning_points['right']['x']:
            if self.can_move_forward(vehicle):
                vehicle.x += vehicle.speed
                return True
        else:
            if vehicle.turned == 0:
                vehicle.rotateAngle += rotationAngle
                vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
                vehicle.x += 2
                vehicle.y += 2
                if vehicle.rotateAngle == 90:
                    vehicle.turned = 1
                return True
            else:
                if self.can_move_forward(vehicle):
                    vehicle.y += vehicle.speed
                    return True
        return False

    def handle_down_turn(self, vehicle):
        if vehicle.crossed == 0 or vehicle.y + vehicle.currentImage.get_rect().height < self.turning_points['down']['y']:
            if self.can_move_forward(vehicle):
                vehicle.y += vehicle.speed
                return True
        else:
            if vehicle.turned == 0:
                vehicle.rotateAngle += rotationAngle
                vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
                vehicle.x -= 2
                vehicle.y += 2
                if vehicle.rotateAngle == 90:
                    vehicle.turned = 1
                return True
            else:
                if self.can_move_forward(vehicle):
                    vehicle.x -= vehicle.speed
                    return True
        return False

    def handle_left_turn(self, vehicle):
        if vehicle.crossed == 0 or vehicle.x > self.turning_points['left']['x']:
            if self.can_move_forward(vehicle):
                vehicle.x -= vehicle.speed
                return True
        else:
            if vehicle.turned == 0:
                vehicle.rotateAngle += rotationAngle
                vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
                vehicle.x -= 2
                vehicle.y -= 2
                if vehicle.rotateAngle == 90:
                    vehicle.turned = 1
                return True
            else:
                if self.can_move_forward(vehicle):
                    vehicle.y -= vehicle.speed
                    return True
        return False

    def handle_up_turn(self, vehicle):
        if vehicle.crossed == 0 or vehicle.y > self.turning_points['up']['y']:
            if self.can_move_forward(vehicle):
                vehicle.y -= vehicle.speed
                return True
        else:
            if vehicle.turned == 0:
                vehicle.rotateAngle += rotationAngle
                vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
                vehicle.x += 2
                vehicle.y -= 2
                if vehicle.rotateAngle == 90:
                    vehicle.turned = 1
                return True
            else:
                if self.can_move_forward(vehicle):
                    vehicle.x += vehicle.speed
                    return True
        return False

    def handle_straight_movement(self, vehicle, direction):
        if direction == 'right':
            if self.can_move_forward(vehicle):
                vehicle.x += vehicle.speed
                return True
        elif direction == 'down':
            if self.can_move_forward(vehicle):
                vehicle.y += vehicle.speed
                return True
        elif direction == 'left':
            if self.can_move_forward(vehicle):
                vehicle.x -= vehicle.speed
                return True
        elif direction == 'up':
            if self.can_move_forward(vehicle):
                vehicle.y -= vehicle.speed
                return True
        return False

    def can_move_forward(self, vehicle):
        if vehicle.crossed == 1:
            return True
        
        if vehicle.isEmergency:
            return True
        
        if currentGreen == vehicle.direction_number or currentYellow == 1:
            if not self.check_collision_ahead(vehicle):
                return True
        
        return False

    def check_collision_ahead(self, vehicle):
        direction = vehicle.direction
        lane = vehicle.lane
        vehicles_in_lane = vehicle_manager.vehicles[direction][lane]
        if vehicle not in vehicles_in_lane:
            return False
        index = vehicles_in_lane.index(vehicle)
        
        if index > 0:
            vehicle_ahead = vehicles_in_lane[index - 1]
            if direction in ['right', 'left']:
                distance = abs(vehicle.x - vehicle_ahead.x)
            else:
                distance = abs(vehicle.y - vehicle_ahead.y)
            return distance < vehicle_manager.safe_distance
        return False
class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite.__init__(self)
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.speed = speeds[vehicleClass]
        self.direction_number = direction_number
        self.direction = direction
        self.x = x[direction][lane]
        self.y = y[direction][lane]
        self.crossed = 0
        self.willTurn = will_turn
        self.turned = 0
        self.rotateAngle = 0
        self.isEmergency = (vehicleClass == 'truck')
        
        if self.isEmergency:
            emergency_manager.add_emergency(self)
        
        path = "images/" + direction + "/" + vehicleClass + ".png"
        self.originalImage = pygame.image.load(path)
        self.currentImage = pygame.image.load(path)
        
        self.initialize_position()
        simulation.add(self)
        vehicle_manager.add_vehicle(self)
    
    def initialize_position(self):
        if self.direction == 'right':
            if len(vehicles[self.direction][self.lane]) > 1:
                self.stop = vehicles[self.direction][self.lane][-1].stop - vehicles[self.direction][self.lane][-1].currentImage.get_rect().width - gap
            else:
                self.stop = defaultStop[self.direction]
            temp = self.currentImage.get_rect().width + gap    
            x[self.direction][self.lane] -= temp
            stops[self.direction][self.lane] -= temp
        
        elif self.direction == 'down':
            if len(vehicles[self.direction][self.lane]) > 1:
                self.stop = vehicles[self.direction][self.lane][-1].stop - vehicles[self.direction][self.lane][-1].currentImage.get_rect().height - gap
            else:
                self.stop = defaultStop[self.direction]
            temp = self.currentImage.get_rect().height + gap
            y[self.direction][self.lane] -= temp
            stops[self.direction][self.lane] -= temp
        
        elif self.direction == 'left':
            if len(vehicles[self.direction][self.lane]) > 1:
                self.stop = vehicles[self.direction][self.lane][-1].stop + vehicles[self.direction][self.lane][-1].currentImage.get_rect().width + gap
            else:
                self.stop = defaultStop[self.direction]
            temp = self.currentImage.get_rect().width + gap
            x[self.direction][self.lane] += temp
            stops[self.direction][self.lane] += temp
        
        elif self.direction == 'up':
            if len(vehicles[self.direction][self.lane]) > 1:
                self.stop = vehicles[self.direction][self.lane][-1].stop + vehicles[self.direction][self.lane][-1].currentImage.get_rect().height + gap
            else:
                self.stop = defaultStop[self.direction]
            temp = self.currentImage.get_rect().height + gap
            y[self.direction][self.lane] += temp
            stops[self.direction][self.lane] += temp

class TrafficSimulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1400, 800))
        pygame.display.set_caption("Traffic Simulation with Emergency Vehicle Priority")
        self.clock = pygame.time.Clock()
        self.start_time = time.time()
        self.vehicle_generate_time = time.time()
        
        self.simulation_time = 0
        self.stats = {
            'total_vehicles': 0,
            'emergency_vehicles': 0,
            'average_wait_time': 0
        }
        
        self.running = True
        self.load_images()

    def load_images(self):
        try:
            self.background = pygame.image.load('images/mod_int.png')
            self.signals = {
                'red': pygame.image.load('images/signals/red.png'),
                'yellow': pygame.image.load('images/signals/yellow.png'),
                'green': pygame.image.load('images/signals/green.png')
            }
            self.font = pygame.font.Font(None, 30)
        except pygame.error as e:
            print(f"Couldn't load images: {e}")
            self.running = False
class TrafficSimulation:  # Continuing TrafficSimulation class
    def generate_vehicle(self):
        if time.time() - self.vehicle_generate_time >= 2.5:
            vehicle_type = random.randint(0, 4)
            lane_number = random.randint(1, 2) if vehicle_type != 4 else 0
            will_turn = random.randint(0, 1) if lane_number == 2 else 0
            direction_number = random.randint(0, 3)
            direction = directionNumbers[direction_number]
            
            if len(vehicle_manager.vehicles[direction][lane_number]) == 0 or \
               self.check_spawn_position(direction, lane_number):
                Vehicle(lane_number, vehicleTypes[vehicle_type], 
                       direction_number, direction, will_turn)
                self.vehicle_generate_time = time.time()

    def check_spawn_position(self, direction, lane):
        vehicles_in_lane = vehicle_manager.vehicles[direction][lane]
        if not vehicles_in_lane:
            return True
        last_vehicle = vehicles_in_lane[-1]
        if direction in ['right', 'left']:
            return abs(last_vehicle.x - x[direction][lane]) > 70
        else:
            return abs(last_vehicle.y - y[direction][lane]) > 70

    def update_signal_timings(self):
        global currentGreen, currentYellow, nextGreen
        if emergency_manager.active_emergency:
            self.handle_emergency_signal()
        else:
            self.handle_normal_signal()

    def handle_emergency_signal(self):
        global currentGreen, currentYellow, nextGreen
        emergency_direction = emergency_manager.active_emergency.direction_number
        if currentGreen != emergency_direction:
            currentYellow = 1
            signals[currentGreen].yellow = defaultYellow
            nextGreen = emergency_direction

    def handle_normal_signal(self):
        global currentGreen, currentYellow, nextGreen
        if currentYellow == 0:
            if signals[currentGreen].green > 0:
                signals[currentGreen].green -= 1
            else:
                currentYellow = 1
                signals[currentGreen].yellow = defaultYellow
        else:
            if signals[currentGreen].yellow > 0:
                signals[currentGreen].yellow -= 1
            else:
                currentYellow = 0
                currentGreen = nextGreen
                nextGreen = (currentGreen + 1) % noOfSignals
                signals[currentGreen].green = defaultGreen

    def update(self):
        self.simulation_time = int(time.time() - self.start_time)
        self.generate_vehicle()
        self.update_signal_timings()
        
        for vehicle in list(simulation):
            if not movement_controller.update_vehicle_position(vehicle):
                if vehicle in simulation:
                    simulation.remove(vehicle)
                    vehicle_manager.remove_vehicle(vehicle)
        
        emergency_manager.update()
        self.update_statistics()

    def update_statistics(self):
        self.stats['total_vehicles'] = sum(vehicles[d]['crossed'] for d in directionNumbers.values())
        self.stats['emergency_vehicles'] = len([v for v in simulation if v.isEmergency])

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        
        for i in range(noOfSignals):
            if i == currentGreen:
                if currentYellow == 1:
                    self.screen.blit(self.signals['yellow'], signalCoords[i])
                else:
                    self.screen.blit(self.signals['green'], signalCoords[i])
            else:
                self.screen.blit(self.signals['red'], signalCoords[i])
            
            if i == currentGreen:
                timer = signals[i].yellow if currentYellow == 1 else signals[i].green
            else:
                timer = signals[i].red
            timer_text = self.font.render(str(timer), True, (255, 255, 255), (0, 0, 0))
            self.screen.blit(timer_text, signalTimerCoords[i])
            
            vehicles_crossed = vehicles[directionNumbers[i]]['crossed']
            count_text = self.font.render(str(vehicles_crossed), True, (0, 0, 0), (255, 255, 255))
            self.screen.blit(count_text, vehicleCountCoords[i])
        
        for vehicle in simulation:
            self.screen.blit(vehicle.currentImage, (vehicle.x, vehicle.y))
        
        self.draw_statistics()

    def draw_statistics(self):
        stats_texts = [
            f"Simulation Time: {self.simulation_time}",
            f"Total Vehicles: {self.stats['total_vehicles']}",
            f"Emergency Vehicles: {self.stats['emergency_vehicles']}",
            f"Avg Wait Time: {self.stats['average_wait_time']:.2f}s"
        ]
        
        for i, text in enumerate(stats_texts):
            text_surface = self.font.render(text, True, (0, 0, 0))
            self.screen.blit(text_surface, (1000, 50 + i * 30))
        
        if emergency_manager.active_emergency:
            emergency_text = self.font.render(
                f"EMERGENCY VEHICLE IN LANE {emergency_manager.active_emergency.direction_number + 1}", 
                True, (255, 0, 0))
            self.screen.blit(emergency_text, (1000, 170))

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

def initialize():
    global currentGreen, currentYellow, nextGreen, signals
    global vehicle_manager, emergency_manager, movement_controller, q_learning
    
    currentGreen = 0
    currentYellow = 0
    nextGreen = (currentGreen + 1) % noOfSignals
    
    for i in range(noOfSignals):
        if i == 0:
            signals.append(TrafficSignal(0, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum))
        else:
            signals.append(TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum))
    
    vehicle_manager = VehicleManager()
    emergency_manager = EmergencyManager()
    movement_controller = MovementController()
    q_learning = QLearning()

def main():
    global simulation
    simulation = pygame.sprite.Group()
    
    initialize()
    traffic_sim = TrafficSimulation()
    
    try:
        traffic_sim.run()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pygame.quit()

if __name__ == '__main__':
    main()                                