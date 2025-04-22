import random
import math
import time
import threading
import pygame
import sys
import os
import numpy as np

pygame.init()
simulation = pygame.sprite.Group()

defaultRed = 100
defaultYellow = 3
defaultGreen = 30
defaultMinimum = 10
defaultMaximum = 60

signals = []
noOfSignals = 4
simTime = 300
timeElapsed = 0
currentGreen = 0
nextGreen = 1
currentYellow = 0

speeds = {
    'car': 3.0,
    'bus': 2.5,
    'truck': 5.0,
    'rickshaw': 2.8,
    'bike': 3.5
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

rotationAngle = 3
gap = 30
gap2 = 25

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
        self.stop_time = None
        
        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1
        path = "images/" + direction + "/" + vehicleClass + ".png"
        self.originalImage = pygame.image.load(path)
        self.currentImage = pygame.image.load(path)
        
        self.initialize_position()
        simulation.add(self)

    def initialize_position(self):
        if self.direction == 'right':
            if len(vehicles[self.direction][self.lane]) > 1 and vehicles[self.direction][self.lane][self.index-1].crossed == 0:
                self.stop = vehicles[self.direction][self.lane][self.index-1].stop - vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width - gap
            else:
                self.stop = defaultStop[self.direction]
            temp = self.currentImage.get_rect().width + gap    
            x[self.direction][self.lane] -= temp
            stops[self.direction][self.lane] -= temp
        
        elif self.direction == 'left':
            if len(vehicles[self.direction][self.lane]) > 1 and vehicles[self.direction][self.lane][self.index-1].crossed == 0:
                self.stop = vehicles[self.direction][self.lane][self.index-1].stop + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap
            else:
                self.stop = defaultStop[self.direction]
            temp = self.currentImage.get_rect().width + gap
            x[self.direction][self.lane] += temp
            stops[self.direction][self.lane] += temp
        
        elif self.direction == 'down':
            if len(vehicles[self.direction][self.lane]) > 1 and vehicles[self.direction][self.lane][self.index-1].crossed == 0:
                self.stop = vehicles[self.direction][self.lane][self.index-1].stop - vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height - gap
            else:
                self.stop = defaultStop[self.direction]
            temp = self.currentImage.get_rect().height + gap
            y[self.direction][self.lane] -= temp
            stops[self.direction][self.lane] -= temp
        
        elif self.direction == 'up':
            if len(vehicles[self.direction][self.lane]) > 1 and vehicles[self.direction][self.lane][self.index-1].crossed == 0:
                self.stop = vehicles[self.direction][self.lane][self.index-1].stop + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height + gap
            else:
                self.stop = defaultStop[self.direction]
            temp = self.currentImage.get_rect().height + gap
            y[self.direction][self.lane] += temp
            stops[self.direction][self.lane] += temp
    def move(self):
        if self.direction == 'right':
            if self.crossed == 0 and self.x + self.currentImage.get_rect().width > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            
            if self.willTurn:
                if self.crossed == 0 or self.x + self.currentImage.get_rect().width < mid[self.direction]['x']:
                    if (self.x + self.currentImage.get_rect().width <= self.stop or (currentGreen == 0 and currentYellow == 0) or self.crossed == 1 or self.isEmergency) and (self.index == 0 or self.x + self.currentImage.get_rect().width < (vehicles[self.direction][self.lane][self.index-1].x - gap2) or vehicles[self.direction][self.lane][self.index-1].turned == 1):
                        self.x += self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x += 2.5
                        self.y += 2.0
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index-1].y - gap2):
                            self.y += self.speed
            else:
                if (self.x + self.currentImage.get_rect().width <= self.stop or self.crossed == 1 or (currentGreen == 0 and currentYellow == 0) or self.isEmergency) and (self.index == 0 or self.x + self.currentImage.get_rect().width < (vehicles[self.direction][self.lane][self.index-1].x - gap2)):
                    self.x += self.speed

        elif self.direction == 'down':
            if self.crossed == 0 and self.y + self.currentImage.get_rect().height > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            
            if self.willTurn:
                if self.crossed == 0 or self.y + self.currentImage.get_rect().height < mid[self.direction]['y']:
                    if (self.y + self.currentImage.get_rect().height <= self.stop or (currentGreen == 1 and currentYellow == 0) or self.crossed == 1 or self.isEmergency) and (self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index-1].y - gap2)):
                        self.y += self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x -= 2.5
                        self.y += 2.0
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if self.index == 0 or self.x > (vehicles[self.direction][self.lane][self.index-1].x + gap2):
                            self.x -= self.speed
            else:
                if (self.y + self.currentImage.get_rect().height <= self.stop or self.crossed == 1 or (currentGreen == 1 and currentYellow == 0) or self.isEmergency) and (self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index-1].y - gap2)):
                    self.y += self.speed

        elif self.direction == 'left':
            if self.crossed == 0 and self.x < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            
            if self.willTurn:
                if self.crossed == 0 or self.x > mid[self.direction]['x']:
                    if (self.x >= self.stop or (currentGreen == 2 and currentYellow == 0) or self.crossed == 1 or self.isEmergency) and (self.index == 0 or self.x > (vehicles[self.direction][self.lane][self.index-1].x + gap2)):
                        self.x -= self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x -= 2.5
                        self.y -= 2.0
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if self.index == 0 or self.y > (vehicles[self.direction][self.lane][self.index-1].y + gap2):
                            self.y -= self.speed
            else:
                if (self.x >= self.stop or self.crossed == 1 or (currentGreen == 2 and currentYellow == 0) or self.isEmergency) and (self.index == 0 or self.x > (vehicles[self.direction][self.lane][self.index-1].x + gap2)):
                    self.x -= self.speed

        elif self.direction == 'up':
            if self.crossed == 0 and self.y < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            
            if self.willTurn:
                if self.crossed == 0 or self.y > mid[self.direction]['y']:
                    if (self.y >= self.stop or (currentGreen == 3 and currentYellow == 0) or self.crossed == 1 or self.isEmergency) and (self.index == 0 or self.y > (vehicles[self.direction][self.lane][self.index-1].y + gap2)):
                        self.y -= self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x += 2.5
                        self.y -= 2.0
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if self.index == 0 or self.x < (vehicles[self.direction][self.lane][self.index-1].x - gap2):
                            self.x += self.speed
            else:
                if (self.y >= self.stop or self.crossed == 1 or (currentGreen == 3 and currentYellow == 0) or self.isEmergency) and (self.index == 0 or self.y > (vehicles[self.direction][self.lane][self.index-1].y + gap2)):
                    self.y -= self.speed
def detectEmergencyVehicles():
    for direction in directionNumbers.values():
        for lane in range(3):
            for vehicle in vehicles[direction][lane]:
                if vehicle.vehicleClass == 'truck' and vehicle.crossed == 0:
                    return True, vehicle.direction_number
    return False, None

def handleEmergencyVehicle(direction_number):
    global currentGreen, currentYellow, nextGreen
    if currentGreen != direction_number:
        currentYellow = 0
        currentGreen = direction_number
        nextGreen = (direction_number + 1) % noOfSignals
        for i in range(noOfSignals):
            if i == direction_number:
                signals[i].green = defaultGreen
                signals[i].yellow = 0
                signals[i].red = 0
                signals[i].emergencyMode = True
            else:
                signals[i].red = defaultRed
                signals[i].yellow = 0
                signals[i].green = 0
                signals[i].emergencyMode = False

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

def updateSignals():
    global currentGreen, currentYellow, nextGreen
    emergency_present, emergency_direction = detectEmergencyVehicles()
    
    if emergency_present:
        handleEmergencyVehicle(emergency_direction)
    else:
        if signals[currentGreen].green > 0:
            signals[currentGreen].green -= 1
        elif currentYellow == 1:
            signals[currentGreen].yellow -= 1
        if signals[currentGreen].yellow == 0 and currentYellow == 1:
            currentYellow = 0
            signals[currentGreen].green = defaultGreen
            signals[currentGreen].yellow = defaultYellow
            signals[currentGreen].emergencyMode = False
            currentGreen = nextGreen
            nextGreen = (currentGreen + 1) % noOfSignals
        for i in range(noOfSignals):
            if i != currentGreen:
                signals[i].red -= 1

def repeat():
    global currentGreen, currentYellow, nextGreen
    while True:
        updateSignals()
        time.sleep(1)
        if signals[currentGreen].green == 0:
            currentYellow = 1
            for i in range(3):
                stops[directionNumbers[currentGreen]][i] = defaultStop[directionNumbers[currentGreen]]

def generateVehicles():
    while True:
        vehicle_type = random.randint(0,4)
        lane_number = 0 if vehicle_type == 4 else random.randint(1,2)
        will_turn = 1 if lane_number == 2 and random.randint(0,4) <= 2 else 0
        direction_number = random.randint(0,3)
        
        Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, 
               directionNumbers[direction_number], will_turn)
        time.sleep(random.randint(1,3))

def simulationTime():
    global timeElapsed, simTime
    while True:
        timeElapsed += 1
        time.sleep(1)
        if timeElapsed == simTime:
            print('Simulation completed.')
            os._exit(1)
class Main:
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
    pygame.display.set_caption("Traffic Signal Simulation with Emergency Vehicle Priority")

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

        screen.blit(background,(0,0))
        
        emergency_present, emergency_direction = detectEmergencyVehicles()
        
        for i in range(0,noOfSignals):
            if i == currentGreen:
                if currentYellow == 1:
                    signals[i].signalText = signals[i].yellow
                    screen.blit(yellowSignal, signalCoords[i])
                else:
                    signals[i].signalText = signals[i].green
                    screen.blit(greenSignal, signalCoords[i])
            else:
                signals[i].signalText = signals[i].red
                screen.blit(redSignal, signalCoords[i])
            
            signalText = font.render(str(signals[i].signalText), True, white, black)
            screen.blit(signalText, signalTimerCoords[i])
            
            if signals[i].emergencyMode:
                emergencyText = font.render("EMERGENCY", True, red)
                screen.blit(emergencyText, (signalCoords[i][0], signalCoords[i][1] - 30))

        for vehicle in simulation:
            if vehicle.isEmergency and not vehicle.crossed:
                pygame.draw.circle(screen, red, (int(vehicle.x + vehicle.currentImage.get_rect().width/2), 
                                              int(vehicle.y + vehicle.currentImage.get_rect().height/2)), 
                                 20, 2)
            screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
            vehicle.move()

        timeText = font.render(f"Time: {timeElapsed}s", True, black)
        screen.blit(timeText, (1100,50))

        if emergency_present:
            emergencyText = font.render("Emergency Vehicle Present!", True, red)
            screen.blit(emergencyText, (1100,80))

        vehicleCountTexts = []
        for direction in directionNumbers.values():
            count = vehicles[direction]['crossed']
            vehicleCountTexts.append(str(count))

        y_offset = 120
        for i, count in enumerate(vehicleCountTexts):
            countText = font.render(f"Lane {i+1}: {count}", True, black)
            screen.blit(countText, (1100, y_offset))
            y_offset += 30

        pygame.display.update()

if __name__ == '__main__':
    Main()                                                    