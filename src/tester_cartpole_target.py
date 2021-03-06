import os
import pickle
import model_cartpole_target
from misc import *
import architecture
import torch
import torch.nn as nn
import numpy as np
from argparse import ArgumentParser
from tqdm import tqdm
from settings_cartpole_target import get_settings

parser = ArgumentParser()
parser.add_argument("-r", "--repetitions", type=int, default=1, help="simulation repetions")
parser.add_argument("--architecture", type=str, default="default", help="architecture's name")
args = parser.parse_args()

cart_position, cart_velocity, pole_angle, pole_ang_velocity, x_target, \
        atk_arch, def_arch, train_par, test_par, \
        robustness_formula = get_settings(args.architecture, mode="test")

pg = ParametersHyperparallelepiped(cart_position, cart_velocity, 
                                        pole_angle, pole_ang_velocity, x_target)

physical_model = model_cartpole_target.Model(pg.sample(sigma=0.05))

attacker = architecture.Attacker(physical_model, *atk_arch.values())
defender = architecture.Defender(physical_model, *def_arch.values())

relpath = get_relpath(main_dir="cartpole_target_"+args.architecture, train_params=train_par)

load_models(attacker, defender, EXP+relpath)

def run(mode=None):
    physical_model.initialize_random()
    conf_init = {
        'x': physical_model.agent.x,
        'dot_x': physical_model.agent.dot_x,
        'theta': physical_model.agent.theta,                     
        'dot_theta': physical_model.agent.dot_theta,
        'dist': physical_model.agent.dist
    }

    sim_t = []
    sim_x = []
    sim_theta = []
    sim_dot_x = []
    sim_ddot_x = []
    sim_dot_theta = []
    sim_x_target = []
    sim_attack_mu = []
    sim_attack_nu = []
    sim_def_acc = []
    sim_dist = []

    t = 0
    dt = test_par["dt"]
    for i in range(test_par["test_steps"]):
        with torch.no_grad():

            oa = torch.tensor(physical_model.agent.status)
            oe = torch.tensor(physical_model.environment.status)
            z = torch.rand(attacker.noise_size)
            
            if mode == 0:
                atk_policy = lambda x: (torch.tensor(0.0), torch.tensor(0.0), torch.tensor(0.0))

            else:

                # atk_policy = attacker(torch.cat((z, oe)))

                def atk_policy(x):
                    dot_eps, mu, nu = attacker(torch.cat((z, oe)))(x)
                    
                    update_mu = 1 if i==0 else np.random.binomial(n=1, p=0.2)

                    if update_mu==1:
                        return dot_eps, mu, nu
                    else:
                        return dot_eps, torch.tensor(sim_attack_mu[i-1]), nu

            def_policy = defender(oa)

        atk_input = atk_policy(dt)
        def_input = def_policy(dt)

        physical_model.step(env_input=atk_input, agent_input=def_input, dt=dt)

        sim_t.append(t)
        sim_x.append(physical_model.agent.x.item())
        sim_theta.append(physical_model.agent.theta.item())
        sim_dot_x.append(physical_model.agent.dot_x.item())
        sim_ddot_x.append(physical_model.agent.ddot_x.item())
        sim_dot_theta.append(physical_model.agent.dot_theta.item())
        sim_x_target.append(physical_model.agent.x_target.item())
        sim_dist.append(physical_model.agent.dist.item())
        sim_attack_mu.append(atk_input[1].item())
        sim_attack_nu.append(atk_input[2].item())
        sim_def_acc.append(def_input.item())

        t += dt
        
    return {'init': conf_init,
            'sim_t': np.array(sim_t),
            'sim_x': np.array(sim_x),
            'sim_theta': np.array(sim_theta),
            'sim_dot_x': np.array(sim_dot_x),
            'sim_ddot_x': np.array(sim_dot_x),
            'sim_dot_theta': np.array(sim_dot_theta),
            'sim_x_target': np.array(sim_x_target),
            'sim_dist': np.array(sim_dist),
            'sim_attack_mu': np.array(sim_attack_mu),
            'sim_attack_nu': np.array(sim_attack_nu),
            'sim_def_acc': np.array(sim_def_acc),
    }

records = []
for i in tqdm(range(args.repetitions)):
    sim = {}
    sim['const'] = run(0)
    sim['pulse'] = run(1)
    sim['atk'] = run()
    records.append(sim)
    
filename = get_sims_filename(repetitions=args.repetitions, test_params=test_par)
           
with open(os.path.join(EXP+relpath, filename), 'wb') as f:
    pickle.dump(records, f)
