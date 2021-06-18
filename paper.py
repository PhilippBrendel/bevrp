# execute python file

import os
import glob
import logging
from sys import platform
import yaml
import time

from utils import *
from smart_krit import my_sk
import argparse


def main(configs, time_limit_total, time_limit_b, out_dir):
    # Set up logging
    out_dir = os.path.join('output', 'paper', out_dir, "my_log.log")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    logger = setup_logger('logger', out_dir,
                            formatter=['%(asctime)s:%(message)s',
                                        '%H:%M:%S'])

    logger.info(f'Total time limit per instance: {time_limit_total}')
    logger.info(f'Time Limit for finding feasible solutions: {time_limit_b}')

    for config in configs:
        with open(config) as config_file:
            yaml_dict = yaml.load(config_file,
                                Loader=yaml.FullLoader)
        logger.info(f'Config file: {config}')

        for t in [2.0, 3.0, 4.0, 5.0, 10.0]:
            start_time = time.time()
            # Part B: objective 0
            yaml_dict['objective'] = 0
            yaml_dict['T'] = t
            yaml_dict['TimeLimit'] = time_limit_b
            best_limit = None
            best_res = None
            for v_limit in [40, 30, 20, 15, 10, 5, 4, 3, 2, 1]:
                logger.info(f'Limit: {v_limit}')
                yaml_dict['constrain_vehicles'] = v_limit
                sk = my_sk(yaml_dict)
                sk.preprocess()
                grb_mod = sk.solve()
                sk.postprocess(grb_mod)

                # Check feasibility
                if grb_mod.status == 2:
                    best_limit = v_limit
                    best_res = sk.instance_str + '.txt'
                    logger.info('Feasible')
                else:
                    logger.info('Infeasible')

            logger.info(f'Finished part B: Best Limit: {v_limit} in file {best_res}')

            # Part C: warm-start with remaining time
            yaml_dict['constrain_vehicles'] = best_limit
            yaml_dict['objective'] = 1
            time_passed = time.time - start_time
            time_left = time_limit_total - time_passed
            yaml_dict['TimeLimit'] = time_left
            logger.info(f'Using remaining {time_left} s with warm_start')
            sk = my_sk(yaml_dict)
            sk.preprocess()
            w, s_n, s_v, f, z, e = read_results(os.path.join('output', best_res))
            grb_mod = sk.solve(w_start=w, s_n_start=s_n, s_v_start=s_v,
                            f_start=f, z_start=z, e_start=e)
            sk.postprocess(grb_mod)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                        description='Visualize a specific file.')
    parser.add_argument('-c', '--config',
                        dest='config', default='configs', 
                        help='Config file to be used')
    parser.add_argument('-o', '--output',
                        dest='output', default='paper', 
                        help='Output (sub-)directory to be used')
    parser.add_argument('-t', '--timelimit', type=int,
                        dest='timelimit', default=86400, 
                        help='TimeLimit')
    args = parser.parse_args()


    if os.path.isdir(args.config):
        # read all yamls from dir
        if platform in ['linux','linux2']:
            configs = glob.glob(os.path.join('configs', '*.YAML')) +  glob.glob(os.path.join('configs', '*.yaml'))
        elif platform == 'win32':
            configs = glob.glob(os.path.join('configs', '*.YAML'))
        else:
            print('Unknown platform!')
            exit()
    elif os.path.isfile(args.config):
        # use config
        configs = [args.config]


    time_limit_b = 1800
    time_limit_total = args.timelimit

    main(configs, time_limit_total, time_limit_b, args.output)
