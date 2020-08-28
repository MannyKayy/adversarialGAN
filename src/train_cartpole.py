import os

import misc
import architecture
import model_cartpole

import torch
import torch.nn as nn
import numpy as np

# Specifies the initial conditions of the setup
cart_position = 0
cart_velocity = np.linspace(0, 10, 40)
pole_angle = np.linspace(-3.1415/4, 3.1415/4, 15)
pole_velocity = np.linspace(0, 10, 40)

# Initializes the generator of initial states
pg = misc.ParametersHyperparallelepiped(cart_position, cart_velocity, pole_angle, pole_velocity)

# Instantiates the world's model
physical_model = model_cartpole.Model(pg.sample(sigma=0.05))

# Specifies the STL formula to compute the robustness
robustness_formula = 'G(theta >= -0.785 & theta <= 0.785)'
robustness_computer = model_cartpole.RobustnessComputer(robustness_formula)

# Instantiates the NN architectures
attacker = architecture.Attacker(physical_model, 2, 10, 2)
defender = architecture.Defender(physical_model, 2, 10)

working_dir = '../experiments/cartpole'

# Instantiates the traning and test environments
trainer = architecture.Trainer(physical_model, robustness_computer, \
                            attacker, defender, working_dir)
tester = architecture.Tester(physical_model, robustness_computer, \
                            attacker, defender, working_dir)

dt = 0.05 # timestep
training_steps = 100 #00 # number of episodes for training
simulation_horizon = int(5 / dt) # 5 seconds

# Starts the training
trainer.run(training_steps, simulation_horizon, dt, atk_steps=3, def_steps=5)

test_steps = 10 # number of episodes for testing
simulation_horizon = int(60 / dt) # 60 seconds

# Starts the testing
tester.run(test_steps, simulation_horizon, dt)

# Saves the trained models
misc.save_models(attacker, defender, working_dir)