import os
import pickle

import model_cartpole
import misc
import architecture
import torch
import torch.nn as nn
import numpy as np
from argparse import ArgumentParser
from tqdm import tqdm

torch.set_default_tensor_type('torch.FloatTensor')

parser = ArgumentParser()
parser.add_argument("-d", "--dir", default="../experiments/cartpole", dest="dirname",
                    help="model's directory")
parser.add_argument("-r", "--repetitions", dest="repetitions", type=int, default=1,
                    help="simulation repetions")
parser.add_argument("--ode_idx", type=int, default=1)
parser.add_argument("--device", type=str, default="cuda")
args = parser.parse_args()

cart_position = np.linspace(0., 5., 10)
cart_velocity = np.linspace(-0.5, 0.5, 10)
pole_angle = np.linspace(-0.196, 0.196, 10)
pole_ang_velocity = np.linspace(-0.5, 0.5, 10)

pg = misc.ParametersHyperparallelepiped(cart_position, cart_velocity, pole_angle, pole_ang_velocity)

physical_model = model_cartpole.Model(pg.sample(sigma=0.05), device=args.device, ode_idx=args.ode_idx)

attacker = architecture.Attacker(physical_model, 2, 10, 3)
defender = architecture.Defender(physical_model, 3, 10)

misc.load_models(attacker, defender, args.dirname+str(args.ode_idx))

dt = 0.005 # timestep
steps = 50

def run(mode=None):
    physical_model.initialize_random()
    conf_init = {
        'x': physical_model.agent.x,
        'dot_x': physical_model.agent.dot_x,
        'theta': physical_model.agent.theta,                     
        'dot_theta': physical_model.agent.dot_theta,
    }

    sim_t = []
    sim_x = []
    sim_theta = []
    sim_dot_x = []
    sim_dot_theta = []
    sim_attack = []
    sim_defence = []

    t = 0
    for i in tqdm(range(steps)):
        with torch.no_grad():

            oa = torch.tensor(physical_model.agent.status).float()
            oe = torch.tensor(physical_model.environment.status).float()
            z = torch.rand(attacker.noise_size).float()
            
            if mode == 0:
                atk_policy = lambda x: torch.tensor(0.05) 
            elif mode == 1:
                atk_policy = lambda x: torch.tensor(0.05) if i > 10 and i < 30 else torch.tensor(-0.05)
            else:
                atk_policy = attacker(torch.cat((z, oe)))

            def_policy = defender(oa)

        atk_input = atk_policy(dt).float()
        def_input = def_policy(dt).float()

        physical_model.step(env_input=atk_input, agent_input=def_input, dt=dt)

        sim_t.append(t)
        sim_x.append(physical_model.agent.x.item())
        sim_theta.append(physical_model.agent.theta.item())
        sim_dot_x.append(physical_model.agent.dot_x.item())
        sim_dot_theta.append(physical_model.agent.dot_theta.item())
        sim_attack.append(atk_input.item())
        sim_defence.append(def_input.item())

        t += dt
        
    return {'init': conf_init,
            'sim_t': np.array(sim_t),
            'sim_x': np.array(sim_x),
            'sim_theta': np.array(sim_theta),
            'sim_dot_x': np.array(sim_dot_x),
            'sim_dot_theta': np.array(sim_dot_theta),
            'sim_attack': np.array(sim_attack),
            'sim_defence': np.array(sim_defence),
    }

records = []
for i in range(args.repetitions):
    sim = {}
    sim['const'] = run(0)
    sim['pulse'] = run(1)
    sim['atk'] = run()

    # print(sim)
    
    records.append(sim)
    
with open(os.path.join(args.dirname+str(args.ode_idx), 'sims.pkl'), 'wb') as f:
    pickle.dump(records, f)
