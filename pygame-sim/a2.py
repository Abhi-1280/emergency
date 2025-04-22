import pygame
import random
import math
import time
import threading
import sys
import os
import numpy as np

pygame.init()

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
FPS = 60

defaultRed = 150
defaultYellow = 5
defaultGreen = 100
defaultMinimum = 10
defaultMaximum = 60
simTime = 300

signals = []
noOfSignals = 4
currentGreen = 0
currentYellow = 0
nextGreen = (currentGreen+1)%noOfSignals
timeElapsed = 0

speeds = {'car': 2.25, 'bus': 1.8, 'truck': 3.0, 'rickshaw': 2, 'bike': 2.5}
safe_distances = {'car': 50, 'bus': 60, 'truck': 70, 'rickshaw': 50, 'bike': 40}
emergency_buffer = 100

x = {'right':[0,0,0], 'down':[755,727,697], 'left':[1400,1400,1400], 'up':[602,627,657]}    
y = {'right':[348,370,398], 'down':[0,0,0], 'left':[498,466,436], 'up':[800,800,800]}

vehicles = {
    'right': {0:[], 1:[], 2:[], 'crossed':0}, 
    'down': {0:[], 1:[], 2:[], 'crossed':0}, 
    'left': {0:[], 1:[], 2:[], 'crossed':0}, 
    'up': {0:[], 1:[], 2:[], 'crossed':0}
}

vehicleTypes = {0:'car', 1:'bus', 2:'truck', 3:'rickshaw', 4:'bike'}
directionNumbers = {0:'right', 1:'down', 2:'left', 3:'up'}

signalCoords = [(530,230),(810,230),(810,570),(530,570)]
signalTimerCoords = [(530,210),(810,210),(810,550),(530,550)]

stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
defaultStop = {'right': 580, 'down': 320, 'left': 810, 'up': 545}
stops = {'right': [580,580,580], 'down': [320,320,320], 'left': [810,810,810], 'up': [545,545,545]}

mid = {
    'right': {'x':705, 'y':445}, 
    'down': {'x':695, 'y':450}, 
    'left': {'x':695, 'y':425}, 
    'up': {'x':695, 'y':400}
}

simulation = pygame.sprite.Group()

class TrafficSignal:
    def __init__(self):
        self.red = defaultRed
        self.yellow = defaultYellow
        self.green = defaultGreen
        self.minimum = defaultMinimum
        self.maximum = defaultMaximum
        self.signalText = "30"
        self.lastGreen = 0
        self.emergencyMode = False

class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite.__init__(self)
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.direction_number = direction_number
        self.direction = direction
        self.x = x[direction][lane]
        self.y = y[direction][lane]
        self.willTurn = will_turn
        self.crossed = 0
        self.turned = 0
        self.rotateAngle = 0
        self.isEmergency = (vehicleClass == 'truck')
        self.waiting_time = 0
        self.stop_count = 0
        self.initial_speed = speeds[vehicleClass]
        self.speed = self.initial_speed
        self.moving = True
        self.safe_distance = safe_distances[vehicleClass]
        self.last_speed_update = time.time()
        
        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1
        
        path = "images/" + direction + "/" + vehicleClass + ".png"
        self.originalImage = pygame.image.load(path)
        self.currentImage = pygame.image.load(path)
        
        if direction == 'right':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop - vehicles[direction][lane][self.index-1].currentImage.get_rect().width - self.safe_distance
            else:
                self.stop = defaultStop[direction]
            x[direction][lane] -= self.currentImage.get_rect().width + self.safe_distance
            stops[direction][lane] -= self.currentImage.get_rect().width + self.safe_distance
        
        elif direction == 'left':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop + vehicles[direction][lane][self.index-1].currentImage.get_rect().width + self.safe_distance
            else:
                self.stop = defaultStop[direction]
            x[direction][lane] += self.currentImage.get_rect().width + self.safe_distance
            stops[direction][lane] += self.currentImage.get_rect().width + self.safe_distance
        
        elif direction == 'down':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop - vehicles[direction][lane][self.index-1].currentImage.get_rect().height - self.safe_distance
            else:
                self.stop = defaultStop[direction]
            y[direction][lane] -= self.currentImage.get_rect().height + self.safe_distance
            stops[direction][lane] -= self.currentImage.get_rect().height + self.safe_distance
        
        elif direction == 'up':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop + vehicles[direction][lane][self.index-1].currentImage.get_rect().height + self.safe_distance
            else:
                self.stop = defaultStop[direction]
            y[direction][lane] += self.currentImage.get_rect().height + self.safe_distance
            stops[direction][lane] += self.currentImage.get_rect().height + self.safe_distance
        
        simulation.add(self)
def check_collision(self, new_x, new_y):
    future_rect = pygame.Rect(new_x, new_y, 
                            self.currentImage.get_rect().width,
                            self.currentImage.get_rect().height)
    future_rect.inflate_ip(-15, -15)
    
    min_distance = emergency_buffer if self.isEmergency else self.safe_distance
    
    for vehicle in vehicles[self.direction][self.lane]:
        if vehicle != self:
            vehicle_rect = pygame.Rect(vehicle.x, vehicle.y,
                                     vehicle.currentImage.get_rect().width,
                                     vehicle.currentImage.get_rect().height)
            vehicle_rect.inflate_ip(-15, -15)
            
            if future_rect.colliderect(vehicle_rect):
                if self.isEmergency:
                    vehicle.speed = max(0, vehicle.speed - 1)
                    return False
                else:
                    self.speed = max(0, vehicle.speed - 0.5)
                    return True
            
            if self.direction in ['right', 'left']:
                if abs(new_x - vehicle.x) < min_distance:
                    if not self.isEmergency:
                        self.speed = max(0, vehicle.speed)
                    return True
            else:
                if abs(new_y - vehicle.y) < min_distance:
                    if not self.isEmergency:
                        self.speed = max(0, vehicle.speed)
                    return True
    return False

def update_speed(self):
    current_time = time.time()
    if current_time - self.last_speed_update > 0.3:
        if self.isEmergency:
            if self.moving:
                self.speed = min(self.initial_speed * 1.5, self.speed + 0.3)
            else:
                self.speed = max(self.initial_speed * 0.5, self.speed - 0.4)
        else:
            if self.moving:
                self.speed = min(self.initial_speed, self.speed + 0.15)
            else:
                self.speed = max(0, self.speed - 0.25)
        self.last_speed_update = current_time

Vehicle.check_collision = check_collision
Vehicle.update_speed = update_speed

def move_vehicle(vehicle):
    vehicle.update_speed()
    
    if not vehicle.moving:
        vehicle.waiting_time += 1
        if vehicle.waiting_time > 90:
            vehicle.speed = max(0, vehicle.speed - 0.2)
        return
    
    new_x, new_y = vehicle.x, vehicle.y
    
    if vehicle.direction == 'right':
        new_x = vehicle.x + vehicle.speed
    elif vehicle.direction == 'left':
        new_x = vehicle.x - vehicle.speed
    elif vehicle.direction == 'down':
        new_y = vehicle.y + vehicle.speed
    elif vehicle.direction == 'up':
        new_y = vehicle.y - vehicle.speed
    
    if vehicle.check_collision(new_x, new_y):
        vehicle.moving = False
        return
    
    if vehicle.crossed == 0:
        if ((vehicle.direction == 'right' and new_x + vehicle.currentImage.get_rect().width > stopLines[vehicle.direction]) or
            (vehicle.direction == 'down' and new_y + vehicle.currentImage.get_rect().height > stopLines[vehicle.direction]) or
            (vehicle.direction == 'left' and new_x < stopLines[vehicle.direction]) or
            (vehicle.direction == 'up' and new_y < stopLines[vehicle.direction])):
            vehicle.crossed = 1
            vehicles[vehicle.direction]['crossed'] += 1
    
    can_move = (
        vehicle.crossed == 1 or
        vehicle.isEmergency or
        (currentGreen == vehicle.direction_number and currentYellow == 0) or
        (vehicle.direction == 'right' and new_x + vehicle.currentImage.get_rect().width <= vehicle.stop) or
        (vehicle.direction == 'down' and new_y + vehicle.currentImage.get_rect().height <= vehicle.stop) or
        (vehicle.direction == 'left' and new_x >= vehicle.stop) or
        (vehicle.direction == 'up' and new_y >= vehicle.stop)
    )
    
    if can_move:
        if vehicle.willTurn and vehicle.crossed:
            if not vehicle.turned:
                vehicle.rotateAngle += 3
                vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
                if vehicle.rotateAngle >= 90:
                    vehicle.turned = 1
                if vehicle.direction == 'right':
                    new_y += 1.8
                elif vehicle.direction == 'down':
                    new_x -= 2.5
                elif vehicle.direction == 'left':
                    new_y -= 2.5
                else:
                    new_x += 1.8
            else:
                if vehicle.direction == 'right':
                    new_y = vehicle.y + vehicle.speed
                elif vehicle.direction == 'down':
                    new_x = vehicle.x - vehicle.speed
                elif vehicle.direction == 'left':
                    new_y = vehicle.y - vehicle.speed
                else:
                    new_x = vehicle.x + vehicle.speed
        
        if not vehicle.check_collision(new_x, new_y):
            vehicle.x = new_x
            vehicle.y = new_y
            vehicle.moving = True
            vehicle.waiting_time = 0
        else:
            vehicle.moving = False
    else:
        vehicle.moving = False
def handleEmergencyVehicles():
    global currentGreen, currentYellow, nextGreen
    
    emergency_vehicles = []
    for direction in directionNumbers.values():
        for lane in range(3):
            for vehicle in vehicles[direction][lane]:
                if vehicle.isEmergency and not vehicle.crossed:
                    distance_to_signal = 0
                    if direction in ['right', 'left']:
                        distance_to_signal = abs(vehicle.x - stopLines[direction])
                    else:
                        distance_to_signal = abs(vehicle.y - stopLines[direction])
                    emergency_vehicles.append((vehicle, direction, distance_to_signal))
    
    if emergency_vehicles:
        emergency_vehicles.sort(key=lambda x: x[2])
        closest_emergency = emergency_vehicles[0]
        direction = closest_emergency[1]
        direction_number = list(directionNumbers.keys())[list(directionNumbers.values()).index(direction)]
        
        if currentGreen != direction_number:
            if currentYellow == 0:
                currentYellow = 1
                signals[currentGreen].yellow = defaultYellow
            elif signals[currentGreen].yellow <= 0:
                currentYellow = 0
                currentGreen = direction_number
                nextGreen = (direction_number + 1) % noOfSignals
                for i in range(noOfSignals):
                    if i == direction_number:
                        signals[i].green = defaultGreen
                        signals[i].yellow = 0
                        signals[i].red = 0
                    else:
                        signals[i].red = defaultRed
                        signals[i].yellow = 0
                        signals[i].green = 0
        return True, direction_number
    return False, None

def generateVehicles():
    while True:
        vehicle_type = random.randint(0, 4)
        lane_number = random.randint(0, 2)
        will_turn = 1 if lane_number == 2 and random.randint(0, 4) <= 2 else 0
        direction_number = random.randint(0, 3)
        direction = directionNumbers[direction_number]
        
        min_spawn_gap = emergency_buffer if vehicleTypes[vehicle_type] == 'truck' else safe_distances[vehicleTypes[vehicle_type]] * 2
        
        can_spawn = True
        if len(vehicles[direction][lane_number]) > 0:
            last_vehicle = vehicles[direction][lane_number][-1]
            if direction in ['right', 'down']:
                if abs(last_vehicle.x - x[direction][lane_number]) < min_spawn_gap:
                    can_spawn = False
            else:
                if abs(last_vehicle.x - x[direction][lane_number]) < min_spawn_gap:
                    can_spawn = False
        
        if can_spawn:
            try:
                Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, direction, will_turn)
            except:
                pass
        
        spawn_delay = 1 if vehicleTypes[vehicle_type] == 'truck' else random.randint(1, 3)
        time.sleep(spawn_delay)

def initialize():
    for i in range(noOfSignals):
        signals.append(TrafficSignal())
    signals[0].green = defaultGreen
    repeat()

def updateValues():
    global currentGreen, currentYellow, nextGreen
    emergency_present, emergency_direction = handleEmergencyVehicles()
    
    if not emergency_present:
        for i in range(noOfSignals):
            if i == currentGreen:
                if currentYellow == 0:
                    if signals[i].green > 0:
                        signals[i].green -= 1
                    else:
                        currentYellow = 1
                        signals[i].yellow = defaultYellow
                else:
                    if signals[i].yellow > 0:
                        signals[i].yellow -= 1
                    else:
                        signals[i].red = defaultRed
                        currentYellow = 0
                        currentGreen = nextGreen
                        nextGreen = (currentGreen + 1) % noOfSignals
            else:
                if signals[i].red > 0:
                    signals[i].red -= 1

def repeat():
    global currentGreen, currentYellow, nextGreen
    while signals[currentGreen].green > 0:
        updateValues()
        time.sleep(1)
    currentYellow = 1
    for i in range(3):
        stops[directionNumbers[currentGreen]][i] = defaultStop[directionNumbers[currentGreen]]
    while signals[currentGreen].yellow > 0:
        updateValues()
        time.sleep(1)
    currentYellow = 0
    signals[currentGreen].green = defaultGreen
    signals[currentGreen].yellow = defaultYellow
    signals[currentGreen].red = defaultRed
    currentGreen = nextGreen
    nextGreen = (currentGreen + 1) % noOfSignals
    signals[nextGreen].red = signals[currentGreen].yellow + signals[currentGreen].green
    repeat()
def simulationTime():
    global timeElapsed
    while True:
        timeElapsed += 1
        time.sleep(1)
        if timeElapsed == simTime:
            os._exit(1)

class Main:
    def __init__(self):
        thread4 = threading.Thread(name="simulationTime", target=simulationTime, args=())
        thread4.daemon = True
        thread4.start()

        thread2 = threading.Thread(name="initialization", target=initialize, args=())
        thread2.daemon = True
        thread2.start()

        black = (0, 0, 0)
        white = (255, 255, 255)
        red = (255, 0, 0)

        screenSize = (WINDOW_WIDTH, WINDOW_HEIGHT)
        screen = pygame.display.set_mode(screenSize)
        pygame.display.set_caption("Traffic Simulation with Emergency Vehicle Priority")

        try:
            background = pygame.image.load('images/mod_int.png')
            redSignal = pygame.image.load('images/signals/red.png')
            yellowSignal = pygame.image.load('images/signals/yellow.png')
            greenSignal = pygame.image.load('images/signals/green.png')
        except:
            print("Error loading images. Make sure all required images are in the 'images' folder.")
            sys.exit()

        font = pygame.font.Font(None, 30)

        thread3 = threading.Thread(name="generateVehicles", target=generateVehicles, args=())
        thread3.daemon = True
        thread3.start()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()

            screen.blit(background, (0,0))
            emergency_present, emergency_direction = handleEmergencyVehicles()
            
            for i in range(noOfSignals):
                if emergency_present and i == emergency_direction:
                    screen.blit(greenSignal, signalCoords[i])
                    signals[i].signalText = signals[i].green
                elif i == currentGreen:
                    if currentYellow == 1:
                        screen.blit(yellowSignal, signalCoords[i])
                        signals[i].signalText = signals[i].yellow
                    else:
                        screen.blit(greenSignal, signalCoords[i])
                        signals[i].signalText = signals[i].green
                else:
                    screen.blit(redSignal, signalCoords[i])
                    signals[i].signalText = signals[i].red

                signalText = font.render(str(signals[i].signalText), True, white, black)
                screen.blit(signalText, signalTimerCoords[i])

                if emergency_present and i == emergency_direction:
                    emergencyText = font.render("EMERGENCY", True, red)
                    screen.blit(emergencyText, (signalCoords[i][0], signalCoords[i][1] - 30))

                vehicleCountText = font.render(str(vehicles[directionNumbers[i]]['crossed']), True, black, white)
                screen.blit(vehicleCountText, (signalCoords[i][0] - 60, signalCoords[i][1]))

            timeText = font.render(f"Time: {timeElapsed}s", True, black, white)
            screen.blit(timeText, (1100,50))
            
            if emergency_present:
                emergencyText = font.render("Emergency Vehicle Present", True, red)
                screen.blit(emergencyText, (1100,80))

            for direction in directionNumbers.values():
                for lane in range(3):
                    for vehicle in vehicles[direction][lane]:
                        if vehicle.crossed == 0 and vehicle.waiting_time > 90:  
                            pygame.draw.circle(screen, red, (int(vehicle.x), int(vehicle.y)), 5)

            for vehicle in simulation:
                try:
                    screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
                    if vehicle.moving:
                        move_vehicle(vehicle)
                    elif time.time() - vehicle.last_speed_update > 0.5:
                        move_vehicle(vehicle)
                except:
                    simulation.remove(vehicle)
                    
            try:
                pygame.display.update()
            except:
                pass

if __name__ == '__main__':
    try:
        Main()
    except Exception as e:
        print(f"An error occurred: {e}")
        pygame.quit()
        sys.exit()                    