# execute python file

import os
import glob
import logging
from sys import platform
import yaml

from utils import *
from smart_krit import my_sk


# Read configs
if platform in ['linux','linux2']:
    configs = glob.glob(os.path.join('configs', '*.YAML')) +  glob.glob(os.path.join('configs', '*.yaml'))
elif platform == 'win32':
    configs = glob.glob(os.path.join('configs', '*.YAML'))
else:
    print('Unknown platform!')
    exit()

# logging
# TODO:


for config in configs:
    with open(config) as config_file:
        yaml_dict = yaml.load(config_file,
                              Loader=yaml.FullLoader)
    print(f'Config file: {config}')

    for t in [2.0, 3.0, 4.0, 5.0, 10.0]:
        # Part B: objective 0
        yaml_dict['objective'] = 0
        yaml_dict['T'] = t
        best_limit = None
        best_res = None
        for v_limit in [40, 30, 20, 15, 10, 5, 4, 3, 2, 1]:
            print(f'Limit: {v_limit}')
            yaml_dict['constrain_vehicles'] = v_limit
            sk = my_sk(yaml_dict)
            sk.preprocess()
            grb_mod = sk.solve()
            sk.postprocess(grb_mod)

            # Check feasibility
            if grb_mod.status == 2:
                best_limit = v_limit
                best_res = sk.instance_str + '.txt'
                print('Feasible')
            else:
                print('Infeasible')
        
        print(f'Finished part B: Best Limit: {v_limit} in file {best_res}')
        #exit()

        # Part C: warm-start with remaining time
        yaml_dict['constrain_vehicles'] = best_limit
        yaml_dict['objective'] = 1
        sk = my_sk(yaml_dict)
        sk.preprocess()
        w, s_n, s_v, f, z, e = read_results(os.path.join('output', best_res))
        grb_mod = sk.solve(w_start=w, s_n_start=s_n, s_v_start=s_v,
                           f_start=f, z_start=z, e_start=e)
        sk.postprocess(grb_mod)

    exit()
