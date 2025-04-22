import random
import math
import time
import threading
import pygame
import sys
import os
import numpy as np

defaultRed = 40
defaultYellow = 5
defaultGreen = 20
defaultMinimum = 10
defaultMaximum = 20

signals = []
noOfSignals = 4
simTime = 300
timeElapsed = 0
currentGreen = 0
nextGreen = (currentGreen+1)%noOfSignals
currentYellow = 0

carTime = 2
bikeTime = 1
rickshawTime = 2
busTime = 2.5
truckTime = 1.5

noOfCars = 0
noOfBikes = 0
noOfBuses = 0
noOfTrucks = 0
noOfRickshaws = 0
noOfLanes = 2

detectionTime = 5

speeds = {
    'car': 2.25,
    'bus': 1.8,
    'truck': 4.5,
    'rickshaw': 2,
    'bike': 2.5
}

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

signalCoods = [(530,230),(810,230),(810,570),(530,570)]
signalTimerCoods = [(530,210),(810,210),(810,550),(530,550)]
vehicleCountCoods = [(480,210),(880,210),(880,550),(480,550)]
vehicleCountTexts = ["0", "0", "0", "0"]

stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
defaultStop = {'right': 580, 'down': 320, 'left': 810, 'up': 545}
stops = {'right': [580,580,580], 'down': [320,320,320], 'left': [810,810,810], 'up': [545,545,545]}

mid = {
    'right': {'x':705, 'y':445}, 
    'down': {'x':695, 'y':450}, 
    'left': {'x':695, 'y':425}, 
    'up': {'x':695, 'y':400}
}

rotationAngle = 3
gap = 35
gap2 = 30
safe_distance = 40

pygame.init()
simulation = pygame.sprite.Group()

class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.totalGreenTime = 0
        self.emergencyMode = False
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
        self.waiting_time = 0
        self.stop_count = 0
        
        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1
        path = "images/" + direction + "/" + vehicleClass + ".png"
        self.originalImage = pygame.image.load(path)
        self.currentImage = pygame.image.load(path)
        
        if direction == 'right':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:    
                self.stop = vehicles[direction][lane][self.index-1].stop - vehicles[direction][lane][self.index-1].currentImage.get_rect().width - gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().width + gap    
            x[direction][lane] -= temp
            stops[direction][lane] -= temp
        
        elif direction == 'left':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop + vehicles[direction][lane][self.index-1].currentImage.get_rect().width + gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().width + gap
            x[direction][lane] += temp
            stops[direction][lane] += temp
        
        elif direction == 'down':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop - vehicles[direction][lane][self.index-1].currentImage.get_rect().height - gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().height + gap
            y[direction][lane] -= temp
            stops[direction][lane] -= temp
        
        elif direction == 'up':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop + vehicles[direction][lane][self.index-1].currentImage.get_rect().height + gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().height + gap
            y[direction][lane] += temp
            stops[direction][lane] += temp
        simulation.add(self)

    def check_collision(self, new_x, new_y):
        future_rect = pygame.Rect(new_x, new_y, 
                                self.currentImage.get_rect().width,
                                self.currentImage.get_rect().height)
        for vehicle in simulation:
            if vehicle != self:
                vehicle_rect = pygame.Rect(vehicle.x, vehicle.y,
                                         vehicle.currentImage.get_rect().width,
                                         vehicle.currentImage.get_rect().height)
                if future_rect.colliderect(vehicle_rect):
                    return True
        return False

    def check_safe_distance(self, new_x, new_y):
        for vehicle in simulation:
            if vehicle != self and vehicle.direction == self.direction:
                dx = abs(new_x - vehicle.x)
                dy = abs(new_y - vehicle.y)
                if dx < safe_distance and dy < safe_distance:
                    return False
        return True

def handleEmergencyVehicles():
    global currentGreen, currentYellow
    for direction in directionNumbers.values():
        for lane in range(3):
            for vehicle in vehicles[direction][lane]:
                if vehicle.isEmergency and not vehicle.crossed:
                    direction_number = list(directionNumbers.keys())[list(directionNumbers.values()).index(direction)]
                    if currentGreen != direction_number:
                        currentYellow = 0
                        currentGreen = direction_number
                        signals[currentGreen].green = max(signals[currentGreen].green, defaultGreen)
                        for i in range(noOfSignals):
                            if i != currentGreen:
                                signals[i].red = signals[currentGreen].green
                    return True, direction_number
    return False, None
def move_vehicle(vehicle):
    if vehicle.isEmergency and not vehicle.crossed:
        vehicle.speed = speeds['truck'] * 1.5
    
    if vehicle.direction == 'right':
        new_x = vehicle.x + vehicle.speed
        if not vehicle.check_collision(new_x, vehicle.y) and vehicle.check_safe_distance(new_x, vehicle.y):
            if vehicle.crossed == 0 and vehicle.x + vehicle.currentImage.get_rect().width > stopLines[vehicle.direction]:
                vehicle.crossed = 1
                vehicles[vehicle.direction]['crossed'] += 1
            
            if vehicle.willTurn == 1:
                if vehicle.crossed == 0 or vehicle.x + vehicle.currentImage.get_rect().width < mid[vehicle.direction]['x']:
                    if (vehicle.x + vehicle.currentImage.get_rect().width <= vehicle.stop or 
                        (currentGreen == 0 and currentYellow == 0) or 
                        vehicle.crossed == 1 or 
                        vehicle.isEmergency):
                        vehicle.x = new_x
                else:
                    if vehicle.turned == 0:
                        vehicle.rotateAngle += rotationAngle
                        vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
                        vehicle.x += 2
                        vehicle.y += 1.8
                        if vehicle.rotateAngle == 90:
                            vehicle.turned = 1
                    else:
                        if vehicle.check_safe_distance(vehicle.x, vehicle.y + vehicle.speed):
                            vehicle.y += vehicle.speed
            else:
                if (vehicle.x + vehicle.currentImage.get_rect().width <= vehicle.stop or 
                    vehicle.crossed == 1 or 
                    (currentGreen == 0 and currentYellow == 0) or 
                    vehicle.isEmergency):
                    vehicle.x = new_x

    elif vehicle.direction == 'down':
        new_y = vehicle.y + vehicle.speed
        if not vehicle.check_collision(vehicle.x, new_y) and vehicle.check_safe_distance(vehicle.x, new_y):
            if vehicle.crossed == 0 and vehicle.y + vehicle.currentImage.get_rect().height > stopLines[vehicle.direction]:
                vehicle.crossed = 1
                vehicles[vehicle.direction]['crossed'] += 1
            
            if vehicle.willTurn == 1:
                if vehicle.crossed == 0 or vehicle.y + vehicle.currentImage.get_rect().height < mid[vehicle.direction]['y']:
                    if (vehicle.y + vehicle.currentImage.get_rect().height <= vehicle.stop or 
                        (currentGreen == 1 and currentYellow == 0) or 
                        vehicle.crossed == 1 or 
                        vehicle.isEmergency):
                        vehicle.y = new_y
                else:
                    if vehicle.turned == 0:
                        vehicle.rotateAngle += rotationAngle
                        vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
                        vehicle.x -= 2.5
                        vehicle.y += 2
                        if vehicle.rotateAngle == 90:
                            vehicle.turned = 1
                    else:
                        if vehicle.check_safe_distance(vehicle.x - vehicle.speed, vehicle.y):
                            vehicle.x -= vehicle.speed
            else:
                if (vehicle.y + vehicle.currentImage.get_rect().height <= vehicle.stop or 
                    vehicle.crossed == 1 or 
                    (currentGreen == 1 and currentYellow == 0) or 
                    vehicle.isEmergency):
                    vehicle.y = new_y

    elif vehicle.direction == 'left':
        new_x = vehicle.x - vehicle.speed
        if not vehicle.check_collision(new_x, vehicle.y) and vehicle.check_safe_distance(new_x, vehicle.y):
            if vehicle.crossed == 0 and vehicle.x < stopLines[vehicle.direction]:
                vehicle.crossed = 1
                vehicles[vehicle.direction]['crossed'] += 1
            
            if vehicle.willTurn == 1:
                if vehicle.crossed == 0 or vehicle.x > mid[vehicle.direction]['x']:
                    if (vehicle.x >= vehicle.stop or 
                        (currentGreen == 2 and currentYellow == 0) or 
                        vehicle.crossed == 1 or 
                        vehicle.isEmergency):
                        vehicle.x = new_x
                else:
                    if vehicle.turned == 0:
                        vehicle.rotateAngle += rotationAngle
                        vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
                        vehicle.x -= 1.8
                        vehicle.y -= 2.5
                        if vehicle.rotateAngle == 90:
                            vehicle.turned = 1
                    else:
                        if vehicle.check_safe_distance(vehicle.x, vehicle.y - vehicle.speed):
                            vehicle.y -= vehicle.speed
            else:
                if (vehicle.x >= vehicle.stop or 
                    vehicle.crossed == 1 or 
                    (currentGreen == 2 and currentYellow == 0) or 
                    vehicle.isEmergency):
                    vehicle.x = new_x

    elif vehicle.direction == 'up':
        new_y = vehicle.y - vehicle.speed
        if not vehicle.check_collision(vehicle.x, new_y) and vehicle.check_safe_distance(vehicle.x, new_y):
            if vehicle.crossed == 0 and vehicle.y < stopLines[vehicle.direction]:
                vehicle.crossed = 1
                vehicles[vehicle.direction]['crossed'] += 1
            
            if vehicle.willTurn == 1:
                if vehicle.crossed == 0 or vehicle.y > mid[vehicle.direction]['y']:
                    if (vehicle.y >= vehicle.stop or 
                        (currentGreen == 3 and currentYellow == 0) or 
                        vehicle.crossed == 1 or 
                        vehicle.isEmergency):
                        vehicle.y = new_y
                else:
                    if vehicle.turned == 0:
                        vehicle.rotateAngle += rotationAngle
                        vehicle.currentImage = pygame.transform.rotate(vehicle.originalImage, -vehicle.rotateAngle)
                        vehicle.x += 1
                        vehicle.y -= 1
                        if vehicle.rotateAngle == 90:
                            vehicle.turned = 1
                    else:
                        if vehicle.check_safe_distance(vehicle.x + vehicle.speed, vehicle.y):
                            vehicle.x += vehicle.speed
            else:
                if (vehicle.y >= vehicle.stop or 
                    vehicle.crossed == 1 or 
                    (currentGreen == 3 and currentYellow == 0) or 
                    vehicle.isEmergency):
                    vehicle.y = new_y        
def initialize():
    ts1 = TrafficSignal(0, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts1)
    ts2 = TrafficSignal(ts1.red+ts1.yellow+ts1.green, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts2)
    ts3 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts3)
    ts4 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts4)
    repeat()

def updateValues():
    global currentGreen, currentYellow, nextGreen
    for i in range(noOfSignals):
        if i == currentGreen:
            if currentYellow == 0:
                if signals[i].green > 0:
                    signals[i].green -= 1
            else:
                if signals[i].yellow > 0:
                    signals[i].yellow -= 1
        else:
            if signals[i].red > 0:
                signals[i].red -= 1
    
    emergency_present, emergency_direction = handleEmergencyVehicles()
    if emergency_present:
        if currentGreen != emergency_direction:
            currentGreen = emergency_direction
            currentYellow = 0
            signals[currentGreen].green = defaultGreen
            for i in range(noOfSignals):
                if i != currentGreen:
                    signals[i].red = signals[currentGreen].green

def repeat():
    global currentGreen, currentYellow, nextGreen
    while signals[currentGreen].green > 0:
        updateValues()
        time.sleep(1)
    
    currentYellow = 1
    for i in range(3):
        stops[directionNumbers[currentGreen]][i] = defaultStop[directionNumbers[currentGreen]]
        for vehicle in vehicles[directionNumbers[currentGreen]][i]:
            vehicle.stop = defaultStop[directionNumbers[currentGreen]]
    
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

def generateVehicles():
    while True:
        vehicle_type = random.randint(0, 4)
        lane_number = 0 if vehicle_type == 4 else random.randint(1, 2)
        will_turn = 1 if lane_number == 2 and random.randint(0, 4) <= 2 else 0
        direction_number = random.randint(0, 3)
        
        if len(vehicles[directionNumbers[direction_number]][lane_number]) > 0:
            last_vehicle = vehicles[directionNumbers[direction_number]][lane_number][-1]
            if (directionNumbers[direction_number] in ['right', 'down'] and 
                abs(last_vehicle.x - x[directionNumbers[direction_number]][lane_number]) > safe_distance):
                Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, 
                       directionNumbers[direction_number], will_turn)
            elif (directionNumbers[direction_number] in ['left', 'up'] and 
                  abs(last_vehicle.x - x[directionNumbers[direction_number]][lane_number]) > safe_distance):
                Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, 
                       directionNumbers[direction_number], will_turn)
        else:
            Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, 
                   directionNumbers[direction_number], will_turn)
        
        time.sleep(random.randint(1, 3))

def simulationTime():
    global timeElapsed, simTime
    while True:
        timeElapsed += 1
        time.sleep(1)
        if timeElapsed == simTime:
            print('\nSimulation completed.')
            os._exit(1)

def updateVehicleCount():
    for i in range(noOfSignals):
        vehicleCountTexts[i] = str(vehicles[directionNumbers[i]]['crossed'])
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

        screenWidth = 1400
        screenHeight = 800
        screenSize = (screenWidth, screenHeight)

        background = pygame.image.load('images/mod_int.png')
        screen = pygame.display.set_mode(screenSize)
        pygame.display.set_caption("Traffic Simulation with Emergency Vehicle Priority")

        redSignal = pygame.image.load('images/signals/red.png')
        yellowSignal = pygame.image.load('images/signals/yellow.png')
        greenSignal = pygame.image.load('images/signals/green.png')
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
                if i == currentGreen:
                    if currentYellow == 1:
                        if signals[i].yellow > 0:
                            signals[i].signalText = signals[i].yellow
                            screen.blit(yellowSignal, signalCoods[i])
                    else:
                        if signals[i].green > 0:
                            signals[i].signalText = signals[i].green
                            screen.blit(greenSignal, signalCoods[i])
                else:
                    if signals[i].red > 0:
                        signals[i].signalText = signals[i].red
                        screen.blit(redSignal, signalCoods[i])
                
                if emergency_present and i == emergency_direction:
                    emergencyText = font.render("EMERGENCY", True, red)
                    screen.blit(emergencyText, (signalCoods[i][0], signalCoods[i][1] - 30))

            for i in range(noOfSignals):
                signalText = font.render(str(max(0, signals[i].signalText)), True, white, black)
                screen.blit(signalText, signalTimerCoods[i])
                
                vehicleCount = vehicles[directionNumbers[i]]['crossed']
                vehicleCountText = font.render(str(vehicleCount), True, black, white)
                screen.blit(vehicleCountText, vehicleCountCoods[i])

            timeText = font.render(f"Time: {timeElapsed}s", True, black, white)
            screen.blit(timeText, (1100,50))
            
            if emergency_present:
                emergencyText = font.render("Emergency Vehicle Present", True, red)
                screen.blit(emergencyText, (1100,80))

            for vehicle in simulation:
                if vehicle.crossed == 0:
                    if vehicle.direction == 'right':
                        signal = signals[0]
                    elif vehicle.direction == 'down':
                        signal = signals[1]
                    elif vehicle.direction == 'left':
                        signal = signals[2]
                    elif vehicle.direction == 'up':
                        signal = signals[3]
                    
                    if signal.red > 0 and not vehicle.isEmergency:
                        vehicle.waiting_time += 1
                        if vehicle.waiting_time > 100:
                            vehicle.speed = min(vehicle.speed * 1.1, speeds[vehicle.vehicleClass] * 1.5)
                    else:
                        vehicle.waiting_time = 0
                        vehicle.speed = speeds[vehicle.vehicleClass]
                
                screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
                move_vehicle(vehicle)

            pygame.display.update()

if __name__ == '__main__':
    Main()                             