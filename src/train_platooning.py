import os
from misc import *
import torch
import numpy as np
import torch.nn as nn
from argparse import ArgumentParser
import architecture
import model_platooning
from settings_platooning import get_settings

parser = ArgumentParser()
parser.add_argument("--architecture", type=str, default="default", help="architecture's name")
args = parser.parse_args()

agent_position, agent_velocity, leader_position, leader_velocity, \
            atk_arch, def_arch, train_par, test_par, \
            robustness_formula = get_settings(args.architecture, mode="train")

pg = ParametersHyperparallelepiped(agent_position, agent_velocity, 
                                    leader_position, leader_velocity)

physical_model = model_platooning.Model(pg.sample(sigma=0.05))
robustness_computer = model_platooning.RobustnessComputer(robustness_formula)

relpath = get_relpath(main_dir="platooning_"+args.architecture, train_params=train_par)

attacker = architecture.Attacker(physical_model, *atk_arch.values())
defender = architecture.Defender(physical_model, *def_arch.values())
trainer = architecture.Trainer(physical_model, robustness_computer, \
                            attacker, defender, train_par["lr"], EXP+relpath)
tester = architecture.Tester(physical_model, robustness_computer, \
                            attacker, defender, EXP+relpath)

simulation_horizon = int(train_par["horizon"] / train_par["dt"])
trainer.run(train_par["train_steps"], simulation_horizon, train_par["dt"], 
            atk_steps=train_par["atk_steps"], def_steps=train_par["def_steps"])

save_models(attacker, defender, EXP+relpath)