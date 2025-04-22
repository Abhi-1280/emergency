import random
import math
import time
import threading
import pygame
import sys
import os
import numpy as np
from sklearn.preprocessing import StandardScaler
from collections import deque
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout
from tensorflow.keras.optimizers import Adam

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
gap = 25
gap2 = 20

pygame.init()
simulation = pygame.sprite.Group()
class TrafficPredictor:
    def __init__(self):
        self.model = Sequential([
            LSTM(64, input_shape=(24, 1), return_sequences=True),
            Dropout(0.2),
            LSTM(32),
            Dense(16, activation='relu'),
            Dense(4, activation='softmax')
        ])
        self.model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        self.memory = deque(maxlen=2000)
        self.batch_size = 32
        
    def remember(self, state):
        self.memory.append(state)
        
    def predict(self, state):
        if len(self.memory) < 24:
            return np.zeros(4)
        state = np.array(list(self.memory)[-24:]).reshape(1, 24, 1)
        return self.model.predict(state)[0]

class SignalOptimizer:
    def __init__(self):
        self.state_size = 24
        self.action_size = 4
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.model = self._build_model()
        
    def _build_model(self):
        model = Sequential([
            Dense(24, input_dim=self.state_size, activation='relu'),
            Dense(24, activation='relu'),
            Dense(self.action_size, activation='linear')
        ])
        model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))
        return model
        
    def act(self, state):
        if random.random() <= self.epsilon:
            return random.randrange(self.action_size)
        act_values = self.model.predict(state)
        return np.argmax(act_values[0])
        
    def train(self, state, action, reward, next_state, done):
        target = reward
        if not done:
            target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])
        target_f = self.model.predict(state)
        target_f[0][action] = target
        self.model.fit(state, target_f, epochs=1, verbose=0)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.totalGreenTime = 0
        self.predictor = TrafficPredictor()
        self.optimizer = SignalOptimizer()
        
    def optimize_time(self, state):
        prediction = self.predictor.predict(state)
        action = self.optimizer.act(state.reshape(1, -1))
        new_green = self.minimum + action * ((self.maximum - self.minimum) / 3)
        return max(min(new_green, self.maximum), self.minimum)

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
        self.start_time = timeElapsed
        
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
class TrafficManagementSystem:
    def __init__(self):
        self.state_size = 24
        self.action_size = 4
        self.memory = deque(maxlen=5000)
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.model = self._build_model()
        self.scaler = StandardScaler()
        
    def _build_model(self):
        model = Sequential([
            Dense(64, input_dim=self.state_size, activation='relu'),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dropout(0.2),
            Dense(self.action_size, activation='linear')
        ])
        model.compile(optimizer=Adam(lr=self.learning_rate), loss='mse')
        return model
        
    def get_state(self):
        state = []
        for direction in directionNumbers.values():
            direction_state = []
            vehicle_counts = {vtype: 0 for vtype in vehicleTypes.values()}
            
            for lane in range(noOfLanes):
                for vehicle in vehicles[direction][lane]:
                    if vehicle.crossed == 0:
                        vehicle_counts[vehicle.vehicleClass] += 1
                        
            direction_state.extend([
                vehicle_counts['car'],
                vehicle_counts['bus'],
                vehicle_counts['truck'],
                vehicle_counts['rickshaw'],
                vehicle_counts['bike'],
                len(vehicles[direction][lane])
            ])
            state.extend(direction_state)
            
        return np.array(state)
        
    def get_reward(self):
        total_waiting_time = 0
        total_vehicles = 0
        
        for direction in directionNumbers.values():
            for lane in range(noOfLanes):
                for vehicle in vehicles[direction][lane]:
                    if vehicle.crossed == 0:
                        total_waiting_time += timeElapsed - vehicle.start_time
                        total_vehicles += 1
                        
        if total_vehicles == 0:
            return 0
            
        avg_waiting_time = total_waiting_time / total_vehicles
        throughput = vehicles[directionNumbers[currentGreen]]['crossed']
        
        reward = throughput * 0.1 - avg_waiting_time * 0.01
        return reward
        
    def optimize_signal_timing(self):
        state = self.get_state()
        scaled_state = self.scaler.fit_transform(state.reshape(1, -1))
        action = self.model.predict(scaled_state)[0]
        
        if random.random() <= self.epsilon:
            return random.randint(defaultMinimum, defaultMaximum)
            
        optimal_time = defaultMinimum + np.argmax(action) * (
            (defaultMaximum - defaultMinimum) / self.action_size
        )
        return int(optimal_time)
        
    def update(self, state, action, reward, next_state):
        scaled_state = self.scaler.transform(state.reshape(1, -1))
        scaled_next_state = self.scaler.transform(next_state.reshape(1, -1))
        
        target = reward + self.gamma * np.amax(
            self.model.predict(scaled_next_state)[0]
        )
        target_f = self.model.predict(scaled_state)
        target_f[0][action] = target
        
        self.model.fit(scaled_state, target_f, epochs=1, verbose=0)
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
class EnhancedSimulation:
    def __init__(self):
        self.traffic_system = TrafficManagementSystem()
        self.current_state = None
        self.current_action = None
        
    def update_simulation(self):
        global currentGreen, currentYellow, nextGreen
        
        self.current_state = self.traffic_system.get_state()
        optimal_time = self.traffic_system.optimize_signal_timing()
        
        signals[currentGreen].green = optimal_time
        
        if currentYellow == 0:
            if signals[currentGreen].green > 0:
                signals[currentGreen].green -= 1
            else:
                currentYellow = 1
                vehicleCountTexts[currentGreen] = "0"
                for i in range(3):
                    stops[directionNumbers[currentGreen]][i] = defaultStop[
                        directionNumbers[currentGreen]
                    ]
        else:
            if signals[currentGreen].yellow > 0:
                signals[currentGreen].yellow -= 1
            else:
                currentYellow = 0
                signals[currentGreen].green = optimal_time
                signals[currentGreen].yellow = defaultYellow
                signals[currentGreen].red = defaultRed
                currentGreen = nextGreen
                nextGreen = (currentGreen + 1) % noOfSignals
                signals[nextGreen].red = signals[currentGreen].yellow + signals[currentGreen].green
                
        reward = self.traffic_system.get_reward()
        next_state = self.traffic_system.get_state()
        
        if self.current_state is not None:
            self.traffic_system.update(
                self.current_state,
                self.current_action,
                reward,
                next_state
            )
            
    def handle_emergency_vehicles(self):
        for direction in directionNumbers.values():
            for lane in range(noOfLanes):
                for vehicle in vehicles[direction][lane]:
                    if vehicle.vehicleClass == 'truck' and vehicle.crossed == 0:
                        if currentGreen != vehicle.direction_number:
                            currentGreen = vehicle.direction_number
                            signals[currentGreen].green = defaultGreen
                            return True
        return False
def main():
    simulation = EnhancedSimulation()
    clock = pygame.time.Clock()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
        emergency_present = simulation.handle_emergency_vehicles()
        if not emergency_present:
            simulation.update_simulation()
            
        for vehicle in simulation:
            vehicle.move()
            
        pygame.display.update()
        clock.tick(60)

if __name__ == '__main__':
    main()                                            