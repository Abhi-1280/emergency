import random
import math
import time
import threading
import pygame
import sys
import os

# Default values of signal times
defaultRed = 40
defaultYellow = 5
defaultGreen = 20
defaultMinimum = 10
defaultMaximum = 20

signals = []
noOfSignals = 4
simTime = 300       # change this to change time of simulation
timeElapsed = 0

currentGreen = 0   # Indicates which signal is green
nextGreen = (currentGreen+1)%noOfSignals
currentYellow = 0   # Indicates whether yellow signal is on or off 

# Average times for vehicles to pass the intersection
carTime = 2
bikeTime = 1
rickshawTime = 2
busTime = 2.5
truckTime = 1.5  # Reduced time for emergency vehicles

# Count of cars at a traffic signal
noOfCars = 0
noOfBikes = 0
noOfBuses = 0
noOfTrucks = 0
noOfRickshaws = 0
noOfLanes = 2

# Red signal time at which cars will be detected at a signal
detectionTime = 5

# Modified speeds with emergency vehicles having higher priority
speeds = {
    'car': 2.25,
    'bus': 1.8,
    'truck': 4.5,  # Increased speed for emergency vehicles
    'rickshaw': 2,
    'bike': 2.5
}

# Coordinates of start points for each direction
x = {'right':[0,0,0], 'down':[755,727,697], 'left':[1400,1400,1400], 'up':[602,627,657]}    
y = {'right':[348,370,398], 'down':[0,0,0], 'left':[498,466,436], 'up':[800,800,800]}

# Vehicle tracking dictionaries
vehicles = {
    'right': {0:[], 1:[], 2:[], 'crossed':0}, 
    'down': {0:[], 1:[], 2:[], 'crossed':0}, 
    'left': {0:[], 1:[], 2:[], 'crossed':0}, 
    'up': {0:[], 1:[], 2:[], 'crossed':0}
}

vehicleTypes = {0:'car', 1:'bus', 2:'truck', 3:'rickshaw', 4:'bike'}
directionNumbers = {0:'right', 1:'down', 2:'left', 3:'up'}

# Coordinates for UI elements
signalCoods = [(530,230),(810,230),(810,570),(530,570)]
signalTimerCoods = [(530,210),(810,210),(810,550),(530,550)]
vehicleCountCoods = [(480,210),(880,210),(880,550),(480,550)]
vehicleCountTexts = ["0", "0", "0", "0"]

# Stop line coordinates
stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
defaultStop = {'right': 580, 'down': 320, 'left': 810, 'up': 545}
stops = {'right': [580,580,580], 'down': [320,320,320], 'left': [810,810,810], 'up': [545,545,545]}

# Mid-point coordinates for turning
mid = {
    'right': {'x':705, 'y':445}, 
    'down': {'x':695, 'y':450}, 
    'left': {'x':695, 'y':425}, 
    'up': {'x':695, 'y':400}
}

rotationAngle = 3

# Increased gaps to prevent collisions
gap = 25   # stopping gap
gap2 = 20   # moving gap

pygame.init()
simulation = pygame.sprite.Group()

class TrafficSignal:
    def _init_(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.totalGreenTime = 0
        self.emergencyMode = False
        
class Vehicle(pygame.sprite.Sprite):
    def _init_(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite._init_(self)
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
        
        # Initialize position based on direction
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

    def move(self):
        # Emergency vehicle logic
        if self.isEmergency:
            self.speed = speeds['truck']
            can_move = True
        else:
            # Check if any emergency vehicle is in the intersection
            emergency_present, emergency_direction = detectEmergencyVehicles()
            can_move = not emergency_present or self.direction_number == emergency_direction or self.crossed == 1

        if not can_move:
            return

        # Movement logic based on direction
        if self.direction == 'right':
            if self.crossed == 0 and self.x + self.currentImage.get_rect().width > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            
            if self.willTurn == 1:
                if self.crossed == 0 or self.x + self.currentImage.get_rect().width < mid[self.direction]['x']:
                    if (self.x + self.currentImage.get_rect().width <= self.stop or 
                        (currentGreen == 0 and currentYellow == 0) or 
                        self.crossed == 1 or 
                        self.isEmergency) and (
                        self.index == 0 or 
                        self.x + self.currentImage.get_rect().width < (
                            vehicles[self.direction][self.lane][self.index-1].x - gap2
                        ) or vehicles[self.direction][self.lane][self.index-1].turned == 1
                    ):
                        self.x += self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x += 2
                        self.y += 1.8
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if (self.index == 0 or 
                            self.y + self.currentImage.get_rect().height < (
                                vehicles[self.direction][self.lane][self.index-1].y - gap2
                            ) or self.x + self.currentImage.get_rect().width < (
                                vehicles[self.direction][self.lane][self.index-1].x - gap2
                            )):
                            self.y += self.speed
            else:
                if (self.x + self.currentImage.get_rect().width <= self.stop or 
                    self.crossed == 1 or 
                    (currentGreen == 0 and currentYellow == 0) or 
                    self.isEmergency) and (
                    self.index == 0 or 
                    self.x + self.currentImage.get_rect().width < (
                        vehicles[self.direction][self.lane][self.index-1].x - gap2
                    ) or vehicles[self.direction][self.lane][self.index-1].turned == 1
                ):
                    self.x += self.speed

        # Similar logic for other directions
        elif self.direction == 'down':
            # Movement logic for downward direction
            if self.crossed == 0 and self.y + self.currentImage.get_rect().height > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            
            if self.willTurn == 1:
                if self.crossed == 0 or self.y + self.currentImage.get_rect().height < mid[self.direction]['y']:
                    if (self.y + self.currentImage.get_rect().height <= self.stop or 
                        (currentGreen == 1 and currentYellow == 0) or 
                        self.crossed == 1 or 
                        self.isEmergency) and (
                        self.index == 0 or 
                        self.y + self.currentImage.get_rect().height < (
                            vehicles[self.direction][self.lane][self.index-1].y - gap2
                        ) or vehicles[self.direction][self.lane][self.index-1].turned == 1
                    ):
                        self.y += self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x -= 2.5
                        self.y += 2
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if (self.index == 0 or 
                            self.x > (vehicles[self.direction][self.lane][self.index-1].x + 
                                    vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap2) or 
                            self.y < (vehicles[self.direction][self.lane][self.index-1].y - gap2)):
                            self.x -= self.speed
            else:
                if (self.y + self.currentImage.get_rect().height <= self.stop or 
                    self.crossed == 1 or 
                    (currentGreen == 1 and currentYellow == 0) or 
                    self.isEmergency) and (
                    self.index == 0 or 
                    self.y + self.currentImage.get_rect().height < (
                        vehicles[self.direction][self.lane][self.index-1].y - gap2
                    ) or vehicles[self.direction][self.lane][self.index-1].turned == 1
                ):
                    self.y += self.speed

        elif self.direction == 'left':
            # Movement logic for leftward direction
            if self.crossed == 0 and self.x < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            
            if self.willTurn == 1:
                if self.crossed == 0 or self.x > mid[self.direction]['x']:
                    if (self.x >= self.stop or 
                        (currentGreen == 2 and currentYellow == 0) or 
                        self.crossed == 1 or 
                        self.isEmergency) and (
                        self.index == 0 or 
                        self.x > (vehicles[self.direction][self.lane][self.index-1].x + 
                                vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap2) or 
                        vehicles[self.direction][self.lane][self.index-1].turned == 1
                    ):
                        self.x -= self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x -= 1.8
                        self.y -= 2.5
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if (self.index == 0 or 
                            self.y > (vehicles[self.direction][self.lane][self.index-1].y + 
                                    vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height + gap2) or 
                            self.x > (vehicles[self.direction][self.lane][self.index-1].x + gap2)):
                            self.y -= self.speed
            else:
                if (self.x >= self.stop or 
                    self.crossed == 1 or 
                    (currentGreen == 2 and currentYellow == 0) or 
                    self.isEmergency) and (
                    self.index == 0 or 
                    self.x > (vehicles[self.direction][self.lane][self.index-1].x + 
                            vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap2) or 
                    vehicles[self.direction][self.lane][self.index-1].turned == 1
                ):
                    self.x -= self.speed

        elif self.direction == 'up':
            # Movement logic for upward direction
            if self.crossed == 0 and self.y < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            
            if self.willTurn == 1:
                if self.crossed == 0 or self.y > mid[self.direction]['y']:
                    if (self.y >= self.stop or 
                        (currentGreen == 3 and currentYellow == 0) or 
                        self.crossed == 1 or 
                        self.isEmergency) and (
                        self.index == 0 or 
                        self.y > (vehicles[self.direction][self.lane][self.index-1].y + 
                                vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height + gap2) or 
                        vehicles[self.direction][self.lane][self.index-1].turned == 1
                    ):
                        self.y -= self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x += 1
                        self.y -= 1
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if (self.index == 0 or 
                            self.x < (vehicles[self.direction][self.lane][self.index-1].x - 
                                    vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width - gap2) or 
                            self.y > (vehicles[self.direction][self.lane][self.index-1].y + gap2)):
                            self.x += self.speed
            else:
                if (self.y >= self.stop or 
                    self.crossed == 1 or 
                    (currentGreen == 3 and currentYellow == 0) or 
                    self.isEmergency) and (
                    self.index == 0 or 
                    self.y > (vehicles[self.direction][self.lane][self.index-1].y + 
                            vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height + gap2) or 
                    vehicles[self.direction][self.lane][self.index-1].turned == 1
                ):
                    self.y -= self.speed

def detectEmergencyVehicles():
    """Check for emergency vehicles (trucks) in any lane"""
    for direction in directionNumbers.values():
        for lane in range(3):
            for vehicle in vehicles[direction][lane]:
                if vehicle.vehicleClass == 'truck' and vehicle.crossed == 0:
                    return True, vehicle.direction_number
    return False, None

def handleEmergencyVehicle(direction_number):
    """Handle traffic signal changes for emergency vehicles"""
    global currentGreen, currentYellow, nextGreen
    
    if currentGreen != direction_number:
        # Set all signals to red except for emergency direction
        for i in range(noOfSignals):
            if i != direction_number:
                signals[i].red = defaultRed
                signals[i].yellow = 0
                signals[i].green = 0
            else:
                signals[i].green = defaultGreen
                signals[i].yellow = 0
                signals[i].red = 0
        
        currentGreen = direction_number
        nextGreen = (direction_number + 1) % noOfSignals

def initialize():
    """Initialize traffic signals"""
    ts1 = TrafficSignal(0, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts1)
    ts2 = TrafficSignal(ts1.red+ts1.yellow+ts1.green, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts2)
    ts3 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts3)
    ts4 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts4)
    repeat()

def setTime():
    """Set signal times based on traffic density and emergency vehicles"""
    global noOfCars, noOfBikes, noOfBuses, noOfTrucks, noOfRickshaws, noOfLanes
    global carTime, busTime, truckTime, rickshawTime, bikeTime
    
    # Check for emergency vehicles
    emergency_present, emergency_direction = detectEmergencyVehicles()
    if emergency_present:
        handleEmergencyVehicle(emergency_direction)
        return

    # Normal traffic flow calculation
    noOfCars, noOfBuses, noOfTrucks, noOfRickshaws, noOfBikes = 0, 0, 0, 0, 0
    for lane in range(3):
        for vehicle in vehicles[directionNumbers[nextGreen]][lane]:
            if vehicle.crossed == 0:
                if vehicle.vehicleClass == 'car':
                    noOfCars += 1
                elif vehicle.vehicleClass == 'bus':
                    noOfBuses += 1
                elif vehicle.vehicleClass == 'truck':
                    noOfTrucks += 1
                elif vehicle.vehicleClass == 'rickshaw':
                    noOfRickshaws += 1
                elif vehicle.vehicleClass == 'bike':
                    noOfBikes += 1
    
    # Calculate green time based on vehicle density
    greenTime = math.ceil(((noOfCars*carTime) + (noOfRickshaws*rickshawTime) + 
                          (noOfBuses*busTime) + (noOfTrucks*truckTime) + 
                          (noOfBikes*bikeTime))/(noOfLanes+1))
    
    # Constrain green time within limits
    greenTime = max(min(greenTime, defaultMaximum), defaultMinimum)
    signals[nextGreen].green = greenTime

def repeat():
    """Main traffic signal control loop"""
    global currentGreen, currentYellow, nextGreen
    
    while signals[currentGreen].green > 0:
        updateValues()
        # Check for emergency vehicles
        emergency_present, emergency_direction = detectEmergencyVehicles()
        if emergency_present:
            handleEmergencyVehicle(emergency_direction)
        
        if signals[nextGreen].red == detectionTime:
            thread = threading.Thread(name="detection", target=setTime, args=())
            thread.daemon = True
            thread.start()
        time.sleep(1)
    
    currentYellow = 1
    vehicleCountTexts[currentGreen] = "0"
    # Reset stops
    for i in range(3):
        stops[directionNumbers[currentGreen]][i] = defaultStop[directionNumbers[currentGreen]]
        for vehicle in vehicles[directionNumbers[currentGreen]][i]:
            vehicle.stop = defaultStop[directionNumbers[currentGreen]]
    
    while signals[currentGreen].yellow > 0:
        updateValues()
        time.sleep(1)
    
    currentYellow = 0   
    
    # Reset signal timings
    signals[currentGreen].green = defaultGreen
    signals[currentGreen].yellow = defaultYellow
    signals[currentGreen].red = defaultRed
    
    currentGreen = nextGreen
    nextGreen = (currentGreen + 1) % noOfSignals
    signals[nextGreen].red = signals[currentGreen].yellow + signals[currentGreen].green
    repeat()

def updateValues():
    """Update signal timers"""
    for i in range(noOfSignals):
        if i == currentGreen:
            if currentYellow == 0:
                signals[i].green -= 1
            else:
                signals[i].yellow -= 1
        else:
            signals[i].red -= 1

def generateVehicles():
    """Generate vehicles with random properties"""
    while True:
        vehicle_type = random.randint(0, 4)
        if vehicle_type == 4:  # Bike
            lane_number = 0
        else:
            lane_number = random.randint(1, 2)
        
        will_turn = 0
        if lane_number == 2:
            will_turn = 1 if random.randint(0, 4) <= 2 else 0
        
        # Distribute vehicles across directions
        direction_number = random.randint(0, 3)
        
        # Create new vehicle
        Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, 
                directionNumbers[direction_number], will_turn)
        
        # Wait before generating next vehicle
        time.sleep(1)

def simulationTime():
    """Track simulation time and print statistics"""
    global timeElapsed, simTime
    while True:
        timeElapsed += 1
        time.sleep(1)
        if timeElapsed == simTime:
            totalVehicles = 0
            print('\nSimulation completed.\nResults:')
            print('Direction-wise vehicle count:')
            for i in range(noOfSignals):
                count = vehicles[directionNumbers[i]]['crossed']
                print(f'Direction {i+1}: {count}')
                totalVehicles += count
            print(f'\nTotal vehicles passed: {totalVehicles}')
            print(f'Total time: {timeElapsed} seconds')
            print(f'Average vehicles per second: {(float(totalVehicles)/float(timeElapsed)):.2f}')
            os._exit(1)

class Main:
    """Main simulation class"""
    thread4 = threading.Thread(name="simulationTime", target=simulationTime, args=())
    thread4.daemon = True
    thread4.start()

    thread2 = threading.Thread(name="initialization", target=initialize, args=())
    thread2.daemon = True
    thread2.start()

    # Colors
    black = (0, 0, 0)
    white = (255, 255, 255)
    red = (255, 0, 0)

    # Initialize display
    screenWidth = 1400
    screenHeight = 800
    screenSize = (screenWidth, screenHeight)

    # Load images
    background = pygame.image.load('images/mod_int.png')
    screen = pygame.display.set_mode(screenSize)
    pygame.display.set_caption("TRAFFIC SIMULATION WITH EMERGENCY VEHICLE PRIORITY")

    redSignal = pygame.image.load('images/signals/red.png')
    yellowSignal = pygame.image.load('images/signals/yellow.png')
    greenSignal = pygame.image.load('images/signals/green.png')
    font = pygame.font.Font(None, 30)

    # Start vehicle generation
    thread3 = threading.Thread(name="generateVehicles", target=generateVehicles, args=())
    thread3.daemon = True
    thread3.start()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        screen.blit(background, (0,0))
        
        # Check for emergency vehicles
        emergency_present, emergency_direction = detectEmergencyVehicles()
        
        # Update signal displays
        for i in range(noOfSignals):
            if i == currentGreen:
                if currentYellow == 1:
                    signals[i].signalText = signals[i].yellow
                    screen.blit(yellowSignal, signalCoods[i])
                else:
                    signals[i].signalText = signals[i].green
                    screen.blit(greenSignal, signalCoods[i])
            else:
                signals[i].signalText = signals[i].red
                screen.blit(redSignal, signalCoods[i])
            
            if signals[i].emergencyMode:
                emergencyText = font.render("EMERGENCY", True, red)
                screen.blit(emergencyText, (signalCoods[i][0], signalCoods[i][1] - 30))

        # Update UI elements
        for i in range(noOfSignals):
            signalText = font.render(str(signals[i].signalText), True, white, black)
            screen.blit(signalText, signalTimerCoods[i])
            
            vehicleCount = vehicles[directionNumbers[i]]['crossed']
            vehicleCountText = font.render(str(vehicleCount), True, black, white)
            screen.blit(vehicleCountText, vehicleCountCoods[i])

        # Display time elapsed
        timeText = font.render(f"Time: {timeElapsed}s", True, black, white)
        screen.blit(timeText, (1100,50))
        
        # Display emergency vehicle status
        if emergency_present:
            emergencyText = font.render("Emergency Vehicle Present", True, red)
            screen.blit(emergencyText, (1100,80))

        # Update vehicle positions
        for vehicle in simulation:
            screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
            vehicle.move()

        pygame.display.update()

if _name_ == "_main_":
    Main()