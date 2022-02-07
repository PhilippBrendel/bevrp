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


def main(configs, time_limit_total, time_limit_b, out_dir, approach, time_windows):
    '''
    Part B: (A is direct solution of full model)
    Solve for feasibility within *time_limit_b*
    with different configurations:
    - time windows: [2, 3, 4, 5, 10]
    - v_limit: [40, 30, 20, 15, 10, 5, 4, 3, 2, 1]

    Part C:
    Use remaining time of *time_limit_total* and previous
    warm-start to improve feasible solution from B
    '''
    # Set up logging
    out_dir = os.path.join('output', 'paper', out_dir)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    logger = setup_logger('logger', os.path.join(out_dir, 'my_log.log'),
                            formatter=['%(asctime)s:%(message)s',
                                        '%H:%M:%S'])

    logger.info(f'Total time limit per instance: {time_limit_total}')
    logger.info(f'Time Limit for finding feasible solutions: {time_limit_b}\n')

    res_frame = pd.DataFrame()

    for config in configs:
        with open(config) as config_file:
            yaml_dict = yaml.load(config_file,
                                Loader=yaml.FullLoader)
        logger.info('')
        logger.info(f'Config file: {config}')
        logger.info('--------------------------------')
        config_name = os.path.splitext(os.path.basename(config))[0]
        tmp_out = os.path.join(out_dir, config_name)
        
        for t in time_windows:
            logger.info(f'Considered time window: {t} h')
            start_time = time.time()
            # Part B: objective 0
            yaml_dict['objective'] = 0
            yaml_dict['T'] = t
            yaml_dict['TimeLimit'] = time_limit_b
            best_limit = None
            best_res = None
            if approach == 'bs':
                for v_limit in [40, 30, 20, 15, 10, 5, 4, 3, 2, 1]:
                    logger.info(f'Vehicle Limit: {v_limit}')
                    yaml_dict['constrain_vehicles'] = v_limit
                    sk = my_sk(yaml_dict, out_dir=tmp_out)
                    sk.preprocess()
                    grb_mod = sk.solve()

                    # Check feasibility
                    if grb_mod.status == 2:
                        sk.postprocess(grb_mod)
                        best_limit = v_limit
                        best_res = os.path.join(tmp_out, (sk.instance_str + '.txt'))
                        logger.info(f'Feasible after {grb_mod.runtime} s')
                        status = 'FEASIBLE'
                    elif grb_mod.status == 3:
                        logger.info(f'Infeasible after {grb_mod.runtime} s')
                        status = 'INFEASIBLE'
                    elif grb_mod.status == 9:
                        logger.info(f'Timeout after {grb_mod.runtime} s')
                        status = 'TIMEOUT'
                    else:
                        logger.info(f'grb_mod status returned: {grb_mod.status}')
                        status = grb_mod.status
                    res_frame = res_frame.append({'config': config_name,
                                                  't': t,
                                                  'v_limit': v_limit,
                                                  'status': status,
                                                  'runtime': grb_mod.runtime}, ignore_index=True)
                    res_frame.to_csv(os.path.join(out_dir, 'tmp_results.csv'))
            elif approach == 'pb':
                ub = 40
                lb = 0
                v_limit = int(lb+(ub-lb)/2)
                while v_limit < ub and v_limit > lb:
                    logger.info(f'Vehicle Limit: {v_limit}')
                    yaml_dict['constrain_vehicles'] = v_limit
                    sk = my_sk(yaml_dict, out_dir=tmp_out)
                    sk.preprocess()
                    grb_mod = sk.solve()

                    # Check feasibility
                    if grb_mod.status == 2:
                        sk.postprocess(grb_mod)
                        best_limit = v_limit
                        best_res = os.path.join(tmp_out, (sk.instance_str + '.txt'))
                        logger.info(f'Feasible after {grb_mod.runtime} s')
                        ub = v_limit
                        status = 'FEASIBLE'
                    else:
                        lb = v_limit
                        if grb_mod.status == 3:
                            logger.info(f'Infeasible  after {grb_mod.runtime} s')
                            status = 'INFEASIBLE'
                        elif grb_mod.status == 9:
                            logger.info(f'Timeout after {grb_mod.runtime} s')
                            status = 'TIMEOUT'
                        else:
                            logger.info(f'grb_mod status returned: {grb_mod.status}')
                            status = grb_mod.status
                    res_frame = res_frame.append({'config': config_name,
                                                  't': t,
                                                  'v_limit': v_limit,
                                                  'status': status,
                                                  'runtime': grb_mod.runtime}, ignore_index=True)
                    v_limit = int(lb+(ub-lb)/2)
                    res_frame.to_csv(os.path.join(out_dir, 'tmp_results.csv'))

            res_frame.to_csv(os.path.join(out_dir, 'tmp_results.csv'))
            logger.info(f'Finished part B: Best Limit: {best_limit} in file {best_res}')

            # Part C: warm-start with remaining time
            if best_res is None:
                logger.info('Could not find feasible solution, skipping warm-start...\n')
            else:
                yaml_dict['constrain_vehicles'] = best_limit
                yaml_dict['objective'] = 1
                time_passed = time.time() - start_time
                time_left = time_limit_total - time_passed
                yaml_dict['TimeLimit'] = time_left
                logger.info(f'Using remaining {time_left} s with warm_start')
                sk = my_sk(yaml_dict, out_dir=tmp_out)
                sk.preprocess()
                w, s_n, s_v, f, z, e = read_results(best_res)
                grb_mod = sk.solve(w_start=w, s_n_start=s_n, s_v_start=s_v,
                                f_start=f, z_start=z, e_start=e)
                if hasattr(grb_mod, 'objVal'):
                    sk.postprocess(grb_mod)
                    logger.info(f'Final objective {grb_mod.objVal}\n')
                    obj_val = grb_mod.obj_val
                else:
                    logger.info('No Objective value -> failed warmstart?\n')
                    obj_val = 'None'
                res_frame = res_frame.append({'config': config_name + '_warmstart',
                                                't': t,
                                                'v_limit': best_limit,
                                                'status': grb_mod.status,
                                                'runtime': grb_mod.runtime,
                                                'obj_val': obj_val}, ignore_index=True)
                res_frame.to_csv(os.path.join(out_dir, 'tmp_results.csv'))

    res_frame.to_csv(os.path.join(out_dir, 'results.csv'))


def main_naive(configs, time_limit, out_dir, time_windows):
    '''
    Naive solution of instances
    '''
    # Set up logging
    out_dir = os.path.join('output', 'paper', out_dir)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    logger = setup_logger('logger', os.path.join(out_dir, 'my_log.log'),
                            formatter=['%(asctime)s:%(message)s',
                                        '%H:%M:%S'])

    res_frame = pd.DataFrame()

    for config in configs:
        logger.info(f'Config file: {config}')
        with open(config) as config_file:
            yaml_dict = yaml.load(config_file,
                                  Loader=yaml.FullLoader)
        config_name = os.path.splitext(os.path.basename(config))[0]
        tmp_out = os.path.join(out_dir, config_name)

        for t in time_windows:
            logger.info(f'Considered time window: {t} h')
            yaml_dict['objective'] = 1
            yaml_dict['TimeLimit'] = time_limit
            yaml_dict['T'] = t

            logger.info(f'Using {time_limit} s for naive optimization')
            sk = my_sk(yaml_dict, out_dir=tmp_out)
            sk.preprocess()
            grb_mod = sk.solve()
            if grb_mod.status == 2:
                status = 'FEASIBLE'
                sk.postprocess(grb_mod)
                logger.info(f'Feasible after {grb_mod.runtime} s')
                logger.info(f'Final objective {grb_mod.objVal}')
                obj_val = grb_mod.objVal
            elif grb_mod.status == 3:
                status = 'INFEASIBLE'
                logger.info(f'Infeasible  after {grb_mod.runtime} s')
                obj_val = 'None'
            elif grb_mod.status == 9:
                status = 'TIMEOUT'
                logger.info(f'Timeout after {grb_mod.runtime} s')
                if hasattr(grb_mod, 'objVal'):
                    logger.info(f'Objective: {grb_mod.objVal}')
                    obj_val = grb_mod.objVal
                else:
                    obj_val = None

            res_frame = res_frame.append({'config': config_name,
                                          't': t,
                                          'status': status,
                                          'runtime': grb_mod.runtime,
                                          'obj_val': obj_val},
                                          ignore_index=True)
            res_frame.to_csv(os.path.join(out_dir, 'tmp_results.csv'))

    res_frame.to_csv(os.path.join(out_dir, 'results.csv'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                        description='Visualize a specific file.')
    required = parser.add_argument_group('required named arguments')
    required.add_argument('-a', '--approach', type=str,
                        dest='approach',
                        help='Algorithmic approach', required=True)
    parser.add_argument('-c', '--config',
                        dest='config', default='configs', 
                        help='Config file(s) to be used')
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
            configs = glob.glob(os.path.join(args.config, '*.YAML')) +  glob.glob(os.path.join(args.config, '*.yaml'))
        elif platform == 'win32':
            configs = glob.glob(os.path.join(args.config, '*.YAML'))
        else:
            print('Unknown platform!')
            exit()
    elif os.path.isfile(args.config):
        # use config
        configs = [args.config]

    time_windows = [4.0] # 2.0, 3.0 , 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    time_limit_b = 1800
    time_limit_total = args.timelimit

    if args.approach == 'naive':
        main_naive(configs, time_limit_total, args.output, time_windows)
    else:
        main(configs, time_limit_total, time_limit_b, args.output, args.approach, time_windows)
