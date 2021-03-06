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
    out_dir = os.path.join('output', 'paper', out_dir)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    logger = setup_logger('logger', os.path.join(out_dir, 'my_log.log'),
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
            logger.info(f'Considered time window: {t} h')
            start_time = time.time()
            # Part B: objective 0
            yaml_dict['objective'] = 0
            yaml_dict['T'] = t
            yaml_dict['TimeLimit'] = time_limit_b
            best_limit = None
            best_res = None
            for v_limit in [40, 30, 20, 15, 10, 5, 4, 3, 2, 1]:
                logger.info(f'Vehicle Limit: {v_limit}')
                yaml_dict['constrain_vehicles'] = v_limit
                sk = my_sk(yaml_dict, out_dir=out_dir)
                sk.preprocess()
                grb_mod = sk.solve()

                # Check feasibility
                if grb_mod.status == 2:
                    sk.postprocess(grb_mod)
                    best_limit = v_limit
                    best_res = os.path.join(out_dir, (sk.instance_str + '.txt'))
                    logger.info(f'Feasible after {grb_mod.runtime} s')
                elif grb_mod.status == 3:
                    logger.info(f'Infeasible  after {grb_mod.runtime} s')
                elif grb_mod.status == 9:
                    logger.info(f'Not feasible after time limit: {grb_mod.runtime}')
                else:
                    logger.info(f'grb_mod stats returned: {grb_mod.status}')

            logger.info(f'Finished part B: Best Limit: {best_limit} in file {best_res}')

            # Part C: warm-start with remaining time
            if best_res is None:
                logger.info('Could not find feasible solution, skipping warm-start...')
            else:
                yaml_dict['constrain_vehicles'] = best_limit
                yaml_dict['objective'] = 1
                time_passed = time.time() - start_time
                time_left = time_limit_total - time_passed
                yaml_dict['TimeLimit'] = time_left
                logger.info(f'Using remaining {time_left} s with warm_start')
                sk = my_sk(yaml_dict, out_dir=out_dir)
                sk.preprocess()
                w, s_n, s_v, f, z, e = read_results(best_res)
                grb_mod = sk.solve(w_start=w, s_n_start=s_n, s_v_start=s_v,
                                f_start=f, z_start=z, e_start=e)
                if hasattr(grb_mod, 'objVal'):
                    sk.postprocess(grb_mod)
                    logger.info(f'Final objective {grb_mod.objVal}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                        description='Visualize a specific file.')
    parser.add_argument('-c', '--config',
                        dest='config', default='configs', 
                        help='Config file to be used')
    parser.add_argument('-o', '--output',
                        dest='output', default='out', 
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
