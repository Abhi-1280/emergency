import random
import math
import time
import threading
import pygame
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

defaultRed = 50
defaultYellow = 5
defaultGreen = 20
defaultMinimum = 10
defaultMaximum = 60

signals = []
noOfSignals = 4
simTime = 30
timeElapsed = 0
currentGreen = 0
nextGreen = (currentGreen+1)%noOfSignals
currentYellow = 0

carTime = 2.5
bikeTime = 1
rickshawTime = 2
busTime = 2.5
truckTime = 0.5

speeds = {
    'car': 2.25,
    'bus': 1.8,
    'truck': 6.5,
    'rickshaw': 2,
    'bike': 2.5
}

x = {'right':[0,0,0], 'down':[755,727,697], 'left':[1400,1400,1400], 'up':[602,627,657]}    
y = {'right':[348,370,398], 'down':[0,0,0], 'left':[498,466,436], 'up':[800,800,800]}

vehicles = {'right': {0:[], 1:[], 2:[], 'crossed':0}, 
           'down': {0:[], 1:[], 2:[], 'crossed':0}, 
           'left': {0:[], 1:[], 2:[], 'crossed':0}, 
           'up': {0:[], 1:[], 2:[], 'crossed':0}}

vehicleTypes = {0:'car', 1:'bus', 2:'truck', 3:'rickshaw', 4:'bike'}
directionNumbers = {0:'right', 1:'down', 2:'left', 3:'up'}

signalCoords = [(530,230),(810,230),(810,570),(530,570)]
signalTimerCoords = [(530,210),(810,210),(810,550),(530,550)]
vehicleCountCoords = [(480,210),(880,210),(880,550),(480,550)]
vehicleCountTexts = ["0", "0", "0", "0"]

stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
defaultStop = {'right': 580, 'down': 320, 'left': 810, 'up': 545}
stops = {'right': [580,580,580], 'down': [320,320,320], 'left': [810,810,810], 'up': [545,545,545]}

mid = {'right': {'x':705, 'y':445}, 'down': {'x':695, 'y':450}, 
       'left': {'x':695, 'y':425}, 'up': {'x':695, 'y':400}}

rotationAngle = 3
gap = 30
gap2 = 25

pygame.init()
simulation = pygame.sprite.Group()

vehicle_count_by_type = {'car': 0, 'bus': 0, 'truck': 0, 'rickshaw': 0, 'bike': 0}
vehicle_count_by_direction = {'right': 0, 'down': 0, 'left': 0, 'up': 0}
class QLearning:
    def __init__(self):
        self.learning_rate = 0.2
        self.discount_factor = 0.95
        self.epsilon = 0.1
        self.state_size = 5
        self.action_size = 4
        self.q_table = np.zeros((self.state_size, self.action_size))
    
    def get_state(self, vehicle_count):
        if vehicle_count <= 5: return 0
        elif vehicle_count <= 10: return 1
        elif vehicle_count <= 15: return 2
        elif vehicle_count <= 20: return 3
        else: return 4
    
    def get_action(self, state):
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)
        return np.argmax(self.q_table[state])
    
    def update(self, state, action, reward, next_state):
        current_q = self.q_table[state, action]
        next_max_q = np.max(self.q_table[next_state])
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * next_max_q - current_q)
        self.q_table[state, action] = new_q

q_learning = QLearning()

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
        self.current_state = 0
        self.last_action = 0
        self.reward = 0

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
        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1
        path = "images/" + direction + "/" + vehicleClass + ".png"
        self.originalImage = pygame.image.load(path)
        self.currentImage = pygame.image.load(path)
        self.initialize_position()
        simulation.add(self)
        
        # Update counters
        vehicle_count_by_type[vehicleClass] += 1
        vehicle_count_by_direction[direction] += 1
    
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
    def can_move(self):
        if self.isEmergency:
            return True
        emergency_present, emergency_directions = detectEmergencyVehicles()
        if emergency_present:
            if self.direction_number in emergency_directions or self.crossed == 1:
                return True
            return False
        return True

    def move(self):
        if not self.can_move():
            return
        
        if self.direction == 'right':
            if self.crossed == 0 and self.x + self.currentImage.get_rect().width > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if self.willTurn == 1:
                if self.crossed == 0 or self.x + self.currentImage.get_rect().width < mid[self.direction]['x']:
                    if (self.x + self.currentImage.get_rect().width <= self.stop or (currentGreen == 0 and currentYellow == 0) or self.crossed == 1 or self.isEmergency) and (self.index == 0 or self.x + self.currentImage.get_rect().width < (vehicles[self.direction][self.lane][self.index-1].x - gap2)):
                        self.x += self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x += 2.5
                        self.y += 2.5
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if (self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index-1].y - gap2)):
                            self.y += self.speed
            else:
                if (self.x + self.currentImage.get_rect().width <= self.stop or self.crossed == 1 or (currentGreen == 0 and currentYellow == 0) or self.isEmergency) and (self.index == 0 or self.x + self.currentImage.get_rect().width < (vehicles[self.direction][self.lane][self.index-1].x - gap2)):
                    self.x += self.speed
        
        elif self.direction == 'down':
            if self.crossed == 0 and self.y + self.currentImage.get_rect().height > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if self.willTurn == 1:
                if self.crossed == 0 or self.y + self.currentImage.get_rect().height < mid[self.direction]['y']:
                    if (self.y + self.currentImage.get_rect().height <= self.stop or (currentGreen == 1 and currentYellow == 0) or self.crossed == 1 or self.isEmergency) and (self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index-1].y - gap2)):
                        self.y += self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x -= 2.5
                        self.y += 2.5
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if (self.index == 0 or self.x > (vehicles[self.direction][self.lane][self.index-1].x + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap2)):
                            self.x -= self.speed
            else:
                if (self.y + self.currentImage.get_rect().height <= self.stop or self.crossed == 1 or (currentGreen == 1 and currentYellow == 0) or self.isEmergency) and (self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index-1].y - gap2)):
                    self.y += self.speed

        elif self.direction == 'left':
            if self.crossed == 0 and self.x < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if self.willTurn == 1:
                if self.crossed == 0 or self.x > mid[self.direction]['x']:
                    if (self.x >= self.stop or (currentGreen == 2 and currentYellow == 0) or self.crossed == 1 or self.isEmergency) and (self.index == 0 or self.x > (vehicles[self.direction][self.lane][self.index-1].x + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap2)):
                        self.x -= self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x -= 2.5
                        self.y -= 2.5
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if (self.index == 0 or self.y > (vehicles[self.direction][self.lane][self.index-1].y + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height + gap2)):
                            self.y -= self.speed
            else:
                if (self.x >= self.stop or self.crossed == 1 or (currentGreen == 2 and currentYellow == 0) or self.isEmergency) and (self.index == 0 or self.x > (vehicles[self.direction][self.lane][self.index-1].x + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap2)):
                    self.x -= self.speed

        elif self.direction == 'up':
            if self.crossed == 0 and self.y < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if self.willTurn == 1:
                if self.crossed == 0 or self.y > mid[self.direction]['y']:
                    if (self.y >= self.stop or (currentGreen == 3 and currentYellow == 0) or self.crossed == 1 or self.isEmergency) and (self.index == 0 or self.y > (vehicles[self.direction][self.lane][self.index-1].y + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height + gap2)):
                        self.y -= self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x += 2.5
                        self.y -= 2.5
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if (self.index == 0 or self.x < (vehicles[self.direction][self.lane][self.index-1].x - vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width - gap2)):
                            self.x += self.speed
            else:
                if (self.y >= self.stop or self.crossed == 1 or (currentGreen == 3 and currentYellow == 0) or self.isEmergency) and (self.index == 0 or self.y > (vehicles[self.direction][self.lane][self.index-1].y + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height + gap2)):
                    self.y -= self.speed
def initialize():
    ts1 = TrafficSignal(0, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts1)
    ts2 = TrafficSignal(ts1.red+ts1.yellow+ts1.green, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts2)
    ts3 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts3)
    ts4 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts4)
    thread = threading.Thread(target=signalTimer)
    thread.daemon = True
    thread.start()

def signalTimer():
    global currentGreen, currentYellow, nextGreen
    while True:
        updateSignal()
        time.sleep(1)

def updateSignal():
    global currentGreen, currentYellow, nextGreen
    if currentYellow == 0:
        if signals[currentGreen].green > 0:
            signals[currentGreen].green -= 1
            if signals[currentGreen].green == 0:
                currentYellow = 1
                signals[currentGreen].yellow = defaultYellow
                signals[currentGreen].red = defaultRed
        else:
            currentYellow = 1
            signals[currentGreen].yellow = defaultYellow
    else:
        if signals[currentGreen].yellow > 0:
            signals[currentGreen].yellow -= 1
            if signals[currentGreen].yellow == 0:
                currentYellow = 0
                currentGreen = nextGreen
                nextGreen = (currentGreen + 1) % noOfSignals
                signals[currentGreen].green = defaultGreen
                signals[currentGreen].yellow = 0
                signals[nextGreen].red = defaultRed
    
    for i in range(0, noOfSignals):
        if i != currentGreen:
            if signals[i].red > 0:
                signals[i].red -= 1

def updateSignalTimer():
    for i in range(noOfSignals):
        if i == currentGreen:
            if currentYellow == 0:
                signals[i].signalText = signals[i].green
            else:
                signals[i].signalText = signals[i].yellow
        else:
            signals[i].signalText = signals[i].red

def detectEmergencyVehicles():
    emergency_directions = set()
    for direction in directionNumbers.values():
        for lane in range(3):
            for vehicle in vehicles[direction][lane]:
                if vehicle.vehicleClass == 'truck' and vehicle.crossed == 0:
                    emergency_directions.add(vehicle.direction_number)
    return len(emergency_directions) > 0, emergency_directions

def handleEmergencyVehicle():
    global currentGreen, nextGreen, currentYellow
    emergency_present, emergency_directions = detectEmergencyVehicles()
    if emergency_present:
        for direction in emergency_directions:
            if currentGreen != direction:
                currentGreen = direction
                nextGreen = (currentGreen + 1) % noOfSignals
                currentYellow = 0
                for i in range(noOfSignals):
                    if i == currentGreen:
                        signals[i].green = defaultGreen
                        signals[i].yellow = 0
                        signals[i].red = 0
                    else:
                        signals[i].red = defaultRed
                        signals[i].yellow = 0
                        signals[i].green = 0
                return True
    return False

def generateVehicles():
    while True:
        vehicle_type = random.randint(0,4)
        lane_number = random.randint(1,2) if vehicle_type != 4 else 0
        will_turn = random.randint(0,1) if lane_number == 2 else 0
        direction_number = random.randint(0,3)
        Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, directionNumbers[direction_number], will_turn)
        time.sleep(1.5)

def create_metrics_table():
    plt.figure(figsize=(8, 4))
    plt.axis('tight')
    plt.axis('off')
    
    data = [
        ['Throughput Accuracy', f"{(sum(vehicles[d]['crossed'] for d in directionNumbers.values())/120)*100:.2f}%"],
        ['Improvement Potential', f"{100-(sum(vehicles[d]['crossed'] for d in directionNumbers.values())/120)*100:.2f}%"],
        ['Total Vehicles Passed', sum(vehicles[d]['crossed'] for d in directionNumbers.values())],
        ['Simulation Duration', f"{timeElapsed} Seconds"],
        ['Average Vehicles/Seconds', f"{sum(vehicles[d]['crossed'] for d in directionNumbers.values())/timeElapsed:.2f}"]
    ]
    
    table = plt.table(cellText=data, colLabels=['METRIC', 'VALUE'], 
                     cellLoc='center', loc='center', colWidths=[0.6, 0.4])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    
    plt.title('Traffic Simulation Metrics')
    plt.savefig('metrics_table.png', bbox_inches='tight', dpi=300)
    plt.close()

def create_direction_pie_chart():
    plt.figure(figsize=(8, 6))
    directions = list(vehicle_count_by_direction.keys())
    values = list(vehicle_count_by_direction.values())
    
    plt.pie(values, labels=directions, autopct='%1.1f%%', startangle=90)
    plt.title('Vehicle Distribution by Direction')
    plt.axis('equal')
    plt.savefig('direction_distribution.png', bbox_inches='tight', dpi=300)
    plt.close()

def create_vehicle_type_bar_chart():
    plt.figure(figsize=(10, 6))
    types = list(vehicle_count_by_type.keys())
    counts = list(vehicle_count_by_type.values())
    
    plt.bar(types, counts)
    plt.title('Vehicle Type Distribution')
    plt.xlabel('Vehicle Type')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('vehicle_type_distribution.png', bbox_inches='tight', dpi=300)
    plt.close()
def simulationTime():
    global timeElapsed, simTime
    while True:
        timeElapsed += 1
        time.sleep(1)
        if timeElapsed == simTime:
            totalVehicles = 0
            print('\nSimulation Statistics:')
            print('-' * 50)
            
            for i in range(0, 4):
                direction = directionNumbers[i]
                vehicles_crossed = vehicles[direction]['crossed']
                totalVehicles += vehicles_crossed
                print(f'{direction.capitalize()} direction vehicles crossed: {vehicles_crossed}')
            
            print(f'\nTotal vehicles passed: {totalVehicles}')
            print(f'Total time: {timeElapsed} seconds')
            print(f'Average vehicles per second: {totalVehicles/timeElapsed:.2f}')
            
            # Create and save visualizations
            create_metrics_table()
            create_direction_pie_chart()
            create_vehicle_type_bar_chart()
            
            # Display the visualizations
            metrics_img = plt.imread('metrics_table.png')
            plt.figure(figsize=(12, 8))
            plt.subplot(2, 2, 1)
            plt.imshow(metrics_img)
            plt.axis('off')
            
            pie_img = plt.imread('direction_distribution.png')
            plt.subplot(2, 2, 2)
            plt.imshow(pie_img)
            plt.axis('off')
            
            bar_img = plt.imread('vehicle_type_distribution.png')
            plt.subplot(2, 2, (3, 4))
            plt.imshow(bar_img)
            plt.axis('off')
            
            plt.tight_layout()
            plt.show()
            
            os._exit(1)

class Main:
    def __init__(self):
        thread4 = threading.Thread(name="simulationTime", target=simulationTime, args=())
        thread4.daemon = True
        thread4.start()

        thread2 = threading.Thread(name="initialization", target=initialize, args=())
        thread2.daemon = True
        thread2.start()

        self.screen = pygame.display.set_mode((1400,800))
        pygame.display.set_caption("Traffic Simulation with Emergency Vehicle Priority")

        self.background = pygame.image.load('images/mod_int.png')
        self.redSignal = pygame.image.load('images/signals/red.png')
        self.yellowSignal = pygame.image.load('images/signals/yellow.png')
        self.greenSignal = pygame.image.load('images/signals/green.png')
        self.font = pygame.font.Font(None, 30)

        thread3 = threading.Thread(name="generateVehicles", target=generateVehicles, args=())
        thread3.daemon = True
        thread3.start()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()

            self.screen.blit(self.background,(0,0))
            handleEmergencyVehicle()
            
            emergency_present, emergency_directions = detectEmergencyVehicles()
            
            for i in range(0,noOfSignals):
                if i == currentGreen:
                    if currentYellow == 1:
                        signals[i].signalText = signals[i].yellow
                        self.screen.blit(self.yellowSignal, signalCoords[i])
                    else:
                        signals[i].signalText = signals[i].green
                        self.screen.blit(self.greenSignal, signalCoords[i])
                else:
                    signals[i].signalText = signals[i].red
                    self.screen.blit(self.redSignal, signalCoords[i])

                signalText = self.font.render(str(signals[i].signalText), True, (255,255,255), (0,0,0))
                self.screen.blit(signalText, signalTimerCoords[i])

                vehicleCount = vehicles[directionNumbers[i]]['crossed']
                vehicleCountText = self.font.render(str(vehicleCount), True, (0,0,0), (255,255,255))
                self.screen.blit(vehicleCountText, vehicleCountCoords[i])

            timeText = self.font.render("Time: " + str(timeElapsed), True, (0,0,0), (255,255,255))
            self.screen.blit(timeText, (1100,50))

            if emergency_present:
                emergencyText = self.font.render("EMERGENCY VEHICLE PRESENT", True, (255,0,0), (255,255,255))
                self.screen.blit(emergencyText, (1100,100))

            for vehicle in simulation:
                self.screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
                vehicle.move()

            pygame.display.update()

if __name__ == '__main__':
    Main()                                    