from smart_krit import *
from utils import *
import pandas as pd
import time
import cProfile, pstats, io
from pstats import SortKey


class greedy2():
    def __init__(self, config):
        self.sk = my_sk(config) 
        self.logfile = os.path.join('output', 
                                    self.sk.time_str+'_hlog.txt')
        log_str = 'Instance: {}'.format(self.sk.instance_name)
        log_str += '\nProblem parameters: \n{} vehicles'.format(
                    len(range(self.sk.vehicle_data.shape[0])))
        log_str += '\n{} consumers\n{} producers'.format(
                    len(self.sk.consumers), len(self.sk.producers))
        log_str += '\n{} other nodes\n{} time intervals'.format(
                    len(self.sk.others),self.sk.t_steps-1)
        self.write_log(log_str) 
        # save old objective 
        self.__obj__ = self.sk.obj
        self.__time_limit__ = self.sk.TimeLimit
        self.write_log('Total Time Limit: {}'.format(
                       self.__time_limit__))
        # apply score function to all vehicles
        self.sk.vehicle_data = score_function(self.sk)
        self.full_data = self.sk.vehicle_data.copy()
        self.t_eff = self.full_data['theta_eff']
        self.names = self.full_data['name']
        self.costs = self.full_data['costs']
        self.stats = {'iter': 0, 
                      'inf': 0, 
                      'inf_time': 0., 
                      'feas': 0, 
                      'feas_time': 0.,
                      'feas_times': [], 
                      'tlimit': 0,
                      'tlimit_time': 0.,
                      'blacklist_found': 0}
        self.f_start = None
        self.w_start = None
        self.s_n_start = None
        self.s_v_start = None
        self.blacklist = []
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        self.feas_grb_mod = None
        self.obj_progress = []


    def quick_init(self): 
        '''
        Find a initial feasible vehicle set via a 
        Divide-and-Conquer approach.
        
        - Sort vehicles descending with respect to score
        - Find last index to include by repeatedly halving
          the search-space and testing the pivotal element
          in the middle for feasibility
        - Feasible sets provide upper bound, infeasible sets 
          provide lower bound on that index
        '''
        v_data = self.sk.vehicle_data.sort_values('score', 
                                                  ascending=False)
        v_set = v_data.index.tolist()
        self.sk.TimeLimit = self.__time_limit__
        grb_mod = self.run_model(v_set)
        if grb_mod.status == 2:
            feas_set = v_set.copy()
            ub = len(v_set)-1
            lb = 0
            self.sk.TimeLimit = self.sk.h_init_time_limit
            self.write_log('Full set feasible! ({:.2f} s)'.format(
                grb_mod.Runtime))
            ind = int(lb+(ub-lb)/2)
        else:
            self.write_log('Full set not feasible, exiting...')
            exit()
        while ind < ub and ind > lb:
            tmp_set = v_set[:ind+1].copy()
            self.write_log('Trying {}<---{}-->{}'.format(
                            lb,ind,ub))
            grb_mod = self.run_model(tmp_set)
            if grb_mod.status == 2:
                self.write_log('Feasible! ({:.2f} s)'.format(
                                grb_mod.Runtime))
                ub = len(tmp_set)-1
                feas_set = tmp_set.copy()
            else:
                self.write_log('Infeasible! ({:.2f} s)'.format(
                                grb_mod.Runtime))
                lb = len(tmp_set)-1
            ind = int(lb+(ub-lb)/2)

        self.sk.vehicle_data = self.full_data.iloc[feas_set]
        self.write_log('Initial set: {} vehicles'.format(
                        len(feas_set)))
        self.write_log('\nCosts: {}'.format(
                       self.sk.vehicle_data['costs'].sum()))
        self.v_set = feas_set


    def greedy_init(self):   
        '''
        Greedy initialization scheme to obtain a feasible set

        1. init_set provides initial estimate based on throughput
        2. this set is tested on feasibility
        3. If feasible, remove vehicles. 
           If infeasible, add vehicles. 
        '''
        v_set, log_str = init_set(self.sk)
        self.write_log(log_str)

        grb_mod = self.run_model(v_set)
        costs = self.sk.vehicle_data['costs'].sum()
        if grb_mod.status==2:
            log_str = '\nInitial set feasible! ({})'.format(costs)
            log_str += ' -> Try to remove vehicles...'
            infeasible = False
        else:
            infeasible = True
            name_list = [self.names[i] for i in v_set]
            name_list.sort()
            self.blacklist.append(name_list)
            if grb_mod.status == 3:
                log_str = '\nInitial set infeasible! ' \
                          '-> Try to add vehicles...'
            elif grb_mod.status == 9:
                log_str = '\nTime limit reached, ' \
                          'assuming infeasibility! ' \
                          '-> Try to add vehicles...'
        self.write_log(log_str)
        
        if infeasible:
            while infeasible:
                v_set, log = add_greedy(self.full_data, v_set)
                self.write_log(log)
                if v_set is None:
                    exit()
                grb_mod = self.run_model(v_set)
                if grb_mod.status==2:
                    infeasible=False
                else:
                    name_list = [self.names[i] for i in v_set]
                    name_list.sort()
                    self.blacklist.append(name_list)
                    if grb_mod.status==3:
                        self.write_log('Still infeasible!')  
                    elif grb_mod.status==9:
                        self.write_log(
                            'Time limit of {}'.format(
                            self.sk.TimeLimit) + 
                            ' seconds reached!')
        else:
            tmp_set = v_set.copy()
            while not infeasible:
                v_set, log = remove_greedy(self.full_data, v_set)
                self.write_log(log)
                grb_mod = self.run_model(v_set)
                if grb_mod.status==2:
                    tmp_set = v_set.copy()
                    costs = self.sk.vehicle_data['costs'].sum()
                    self.write_log('Still feasible') 
                    self.write_log('Vehicle costs: {}'.format(
                                   costs)) 
                    self.write_log('Keep removing...')
                else:
                    name_list = [self.names[i] for i in v_set]
                    name_list.sort()
                    self.blacklist.append(name_list)
                    infeasible = True
                    v_set = tmp_set
                    if grb_mod.status==3:
                        self.write_log('Infeasible! ' + 
                                       'Use previous set...')
                    if grb_mod.status==9:
                        self.write_log('Time limit of {}'.format(
                                       self.sk.TimeLimit) + 
                                       'seconds reached!')

        self.sk.vehicle_data = self.full_data.iloc[v_set, :]
        self.v_set = v_set 
        self.sum_costs = self.sk.vehicle_data['costs'].sum()
        self.sum_theta = self.sk.vehicle_data['theta_eff'].sum()
        
        log_str = '\nFeasible set: \n{}'.format(
                    self.sk.vehicle_data[['name','score',
                                          'theta_eff','costs']])
        log_str += '\nCombined Throughput: {}'.format(
                    self.sum_theta)
        log_str += '\nVehicle costs: {}'.format(self.sum_costs)
        self.write_log(log_str)


    def write_log(self, log_str):
        '''
        Print a log-string to console and write it 
        to the heuristics logfile simultaneously.

        Args:
            log_str (str): string to be logged
        '''
        print(log_str)
        with open(self.logfile, 'a') as hlog:
            hlog.write('\n')
            hlog.write(log_str)
        with open(self.sk.LogFile, 'a') as log:
            log.write('\n')
            log.write(log_str)


    def run_model(self, v_set):
        '''
        Run GRB-model and update statistics
        '''
        self.stats['iter'] += 1
        self.sk.vehicle_data = self.full_data.iloc[v_set, :]
        self.sk.preprocess()
        grb_mod = self.sk.solve(f_start=self.f_start, 
                                w_start=self.w_start, 
                                s_n_start=self.s_n_start, 
                                s_v_start=self.s_v_start)
        
        if grb_mod.status == 2:
            self.feas_grb_mod = grb_mod.copy()
            self.f_start, self.w_start, self.s_n_start, self.s_v_start = read_variables(grb_mod)
            self.sum_costs = self.sk.vehicle_data['costs'].sum()
            self.stats['feas'] += 1
            self.stats['feas_time'] += grb_mod.Runtime
            self.stats['feas_times'].append('{:.2f}'.format(
                                            grb_mod.Runtime))
        elif grb_mod.status == 3:
            self.stats['inf'] += 1
            self.stats['inf_time'] += grb_mod.Runtime
        elif grb_mod.status == 9:
            self.stats['tlimit'] += 1
            self.stats['tlimit_time'] += grb_mod.Runtime

        return grb_mod


    def removals(self, max_time, patience, after_feas_patience=1):
        '''
        Obtain a feasible vehicle set and try to improve it 
        by removing all but the last added one.
        Candidates are sorted ascending by costs.
        If a removal is feasible, further (=better) 
        removals will be tried until there is an infeasible one.
        If patience-many removals are infeasible, break.

        Args: 
            max_time (int): maximum time limit in seconds 
                            for removals
            patience (int): number of infeasible removals 
                            before breaking
            after_feas_patience (int): 
                    number of removals investigated 
                    after a feasible removal is found
        '''

        start = time.time()

        log_str = ('\nTry removals on intermediate set {} ({})'
                   ).format(self.v_set, self.sum_costs)
        self.write_log(log_str)
        
        curr_set = self.full_data.iloc[self.v_set].sort_values(
                                    'costs', ascending=True)
        removal_set = curr_set.index.tolist()
   
        keep_removing = True
        time_limit_reached = False
        patience_exceeded = False
        while keep_removing:
            # INITIALIZE FLAGS AND COUNTER #
            keep_removing = False          
            tb_removed = None              
            count = 0                      
            after_feas_count = 0           
            ################################
            for removed in removal_set:
                # CHECK PATIENCE/TIMELIMIT/IMPROVAL VIOLATIONS #
                if count >= patience:                          
                    patience_exceeded = True
                    break
                if (time.time() - start) >= max_time:
                    time_limit_reached = True
                    break  
                if not (tb_removed is None):
                    if (self.costs[removed] 
                        <= self.costs[tb_removed]):
                        continue
                ###################################################
                # TRY REMOVING IF NOT IN BLACKLIST #
                tmp_set = self.v_set.copy()
                tmp_set.remove(removed)
                name_list = [self.names[i] for i in tmp_set]
                name_list.sort()
                if name_list in self.blacklist:
                    self.stats['blacklist_found'] += 1
                    continue
                log_str = 'Try removing {}-{} ({})'.format(
                        removed, self.names[removed],
                        self.costs[removed])
                self.write_log(log_str)
                grb_mod = self.run_model(tmp_set)
                ###################################################
                # REMEMBER IF FEASIBLE, PROCEED IF INFEASIBLE     #
                # BREAK IF: 1. FEASIBLE WAS FOUND BEFORE          #
                #           2. AFTERFEAS-PATIENCE EXCEEDED        #
                if grb_mod.status == 2:
                    tb_removed = removed
                    after_feas_patience = 0
                    self.write_log(('Feasible! ' \
                                    '(Runtime: {:.2f})').format(
                                    grb_mod.Runtime))
                else:
                    count += 1
                    self.blacklist.append(name_list)
                    if not (tb_removed is None):
                        after_feas_count += 1
                        if (after_feas_count 
                            >= after_feas_patience):
                            break
                ###################################################
            # POSTPROCESS DEPENDING ON REASON OF FOR-LOOP EXIT    #
            if not (tb_removed is None):                            
                self.v_set.remove(tb_removed)
                removal_set.remove(tb_removed)    
                log_str = 'Removing {}\nNew set: {} ({})'.format(
                tb_removed,
                self.v_set, self.sum_costs)
                self.write_log(log_str)
                keep_removing = True
            if patience_exceeded:
                self.write_log('Patience exceeded!')
                break
            if time_limit_reached:       
                self.write_log('Time limit reached!')
                break
            #######################################################
        self.sk.vehicle_data = self.full_data.iloc[self.v_set]


    def switch_1vX(self, max_time, c_patience, 
                   after_feas_patience=1):
        '''
        Replace a vehicle with 1-3 candidates featuring lower costs

        Args: 
            max_time (int): maximum time limit in seconds 
                            for switches
            patience (int): number of infeasible switches 
                            before breaking
            after_feas_patience (int): 
                    number of further switches processed 
                    after feasible switch
        Returns:
            no_options_left (bool): True, if no switches left
        '''
        start = time.time()

        log_str = '\nTry 1vX switches on intermediate set ' 
        log_str += '{} ({})'.format(self.v_set, self.sum_costs)
        self.write_log(log_str)

        unused = [i for i in self.full_data.index.tolist() 
                 if i not in self.v_set]

        time_limit_reached = False
        no_options_left = False
        set_changed = False
        while not (time_limit_reached or no_options_left):
            df = self.full_data.iloc[self.v_set]
            unique_df = df.drop_duplicates(subset='name')
            v_candidates = unique_df.index.tolist()
            no_options_left = True
            for v in v_candidates:
                v_costs = self.costs[v]
                unused_red = [item for item in unused 
                              if self.costs[item]<v_costs]
                unused_df = self.full_data.iloc[unused]
                unique_df = unused_df.drop_duplicates(
                            subset='name')
                list_1 = [c for c in unique_df.index.tolist() 
                          if self.costs[c] < v_costs]
                list_1 = [((c,),[self.costs[c],self.t_eff[c]]) 
                          for c in list_1]
                list_2 = [[c1,c2] for c1 in unused for c2 in unused
                           if self.costs[c1] + self.costs[c2] 
                              < v_costs]
                list_2 = remove_duplicates(list_2, self.names)
                list_2 = [((c1,c2),
                           [self.costs[c1]+self.costs[c2],
                            self.t_eff[c1]+self.t_eff[c2]]) 
                           for [c1,c2] in list_2]
                list_3 = findTriplets(unused_red, self.costs, 
                                      v_costs)
                list_3 = remove_duplicates(list_3, self.names)
                list_3 = [((c1,c2,c3),
                           [self.costs[c1]+self.costs[c2]+
                            self.costs[c3],
                            self.t_eff[c1]+self.t_eff[c2]+
                            self.t_eff[c3]]) 
                          for [c1,c2,c3] in list_3]
                my_dict = dict(list_1+list_2+list_3)
                list_sorted = sorted(my_dict.items(), 
                                     key=lambda item: item[-1][1])
                list_sorted.reverse()
                tb_switched = None
                count = 0
                after_feas_count = 0
                found_costs = 1e99
                for c,[c_costs,c_t_eff] in list_sorted:
                    if not (tb_switched is None): 
                        if c_costs >= found_costs:
                            continue
                    if count >= c_patience:
                        break
                    if (time.time()-start) >= max_time:
                        time_limit_reached = True
                        break    
                    c_names = [self.names[i] for i in list(c)]
                    tmp_set = self.v_set.copy()
                    tmp_set.remove(v)
                    tmp_set += list(c)
                    name_list = [self.names[i] for i in tmp_set]
                    name_list.sort()
                    if name_list in self.blacklist:
                        self.stats['blacklist_found'] += 1
                        continue
                    no_options_left = False
                    log_str = 'Try switching {}-{}'.format(
                              v, self.names[v]) 
                    log_str += '({},{:.1f}) '.format(
                                self.costs[v], self.t_eff[v])
                    log_str += '-> {}-{} ({},{:.1f})'.format(
                                c, c_names, c_costs, c_t_eff)
                    self.write_log(log_str)
                    grb_mod = self.run_model(tmp_set)
                    if grb_mod.status==2:
                        found_costs = c_costs
                        tb_switched = [v,c]
                        log_str = 'Feasible! '
                        log_str += '(Runtime: {:.2f})'.format(
                                    grb_mod.Runtime)
                        self.write_log(log_str)
                        after_feas_count = 0
                    else:
                        count += 1
                        self.blacklist.append(name_list)
                        if not (tb_switched is None):
                            after_feas_count += 1
                            if (after_feas_count 
                                >= after_feas_patience):
                                break
                if not (tb_switched is None):
                    set_changed = True
                    [v,c] = tb_switched
                    self.v_set.remove(v)
                    self.v_set += list(c)
                    unused = [item for item in unused 
                              if item not in list(c)]
                    unused += [v]
                    log_str = 'Switching {} -> {} '.format(v, c)
                    log_str += '\nNew set: {}\n ### {} ###'.format(
                                tmp_set, self.sum_costs)
                    self.write_log(log_str)
                    break
                if time_limit_reached:
                    self.write_log('Time limit reached!')  
                    no_options_left = False
                    break  
            if no_options_left:
                self.write_log('No options left!')

        self.sk.vehicle_data = self.full_data.iloc[self.v_set]  
        
        return (no_options_left and not set_changed)


    def switch_2vX(self, max_time, c_patience, 
                   after_feas_patience=1):
        '''
        Replace two vehicle with 1-3 candidates 
        featuring lower costs.

        Args: 
            max_time (int): maximum time limit in seconds 
                            for switches
            patience (int): number of infeasible switches 
                            before breaking
            after_feas_patience (int): 
                    number of further switches processed 
                    after feasible switch
        Returns:
            no_options_left (bool): True, if no switches left
        '''
        start = time.time()

        log_str = '\nTry 2vX switches on intermediate set {} ({})'.format(
                self.v_set, self.sum_costs)
        self.write_log(log_str)

        unused = [i for i in self.full_data.index.tolist() 
                  if i not in self.v_set]

        time_limit_reached = False
        no_options_left = False
        set_changed = False
        while not (time_limit_reached or no_options_left):
            v_candidates = [(v1,v2) for v1 in self.v_set 
                                    for v2 in self.v_set]
            v_candidates = remove_duplicates(v_candidates, 
                                             self.names)
            no_options_left = True
            for (v1,v2) in v_candidates:
                v_costs = self.costs[v1] + self.costs[v2]
                unused_red = [item for item in unused 
                              if self.costs[item]<v_costs]
                v_effs = self.t_eff[v1]+self.t_eff[v2]
                df = self.full_data.iloc[unused]
                unique_df = df.drop_duplicates(subset='name')
                list_1 = [c for c in unique_df.index.tolist() 
                          if self.costs[c] < v_costs]
                list_1 = [((c,),[self.costs[c],self.t_eff[c]]) 
                          for c in list_1]
                list_2 = [[c1,c2] for c1 in unused for c2 in unused
                         if self.costs[c1] + self.costs[c2] 
                            < v_costs]
                list_2 = remove_duplicates(list_2, self.names)
                list_2 = [((c1,c2),[self.costs[c1]+self.costs[c2],
                                    self.t_eff[c1]+self.t_eff[c2]])
                                    for [c1,c2] in list_2]
                list_3 = findTriplets(unused_red, self.costs, 
                                      v_costs)
                list_3 = remove_duplicates(list_3, self.names)
                list_3 = [((c1,c2,c3),
                           [self.costs[c1]+self.costs[c2]
                            +self.costs[c3],
                            self.t_eff[c1]+self.t_eff[c2]
                            +self.t_eff[c3]]) 
                          for [c1,c2,c3] in list_3]
                my_dict = dict(list_1+list_2+list_3)
                list_sorted = sorted(my_dict.items(), 
                                     key=lambda item: item[-1][1])
                list_sorted.reverse()
                tb_switched = None
                count = 0
                after_feas_count = 0
                found_costs = 1e99
                for c,[c_costs,c_t_eff] in list_sorted:
                    if not (tb_switched is None): 
                        if c_costs >= found_costs:
                            continue
                    if count >= c_patience:
                        break
                    if (time.time()-start) >= max_time:
                        time_limit_reached = True
                        break    
                    c_names = [self.names[i] for i in list(c)]
                    tmp_set = self.v_set.copy()
                    tmp_set = [item for item in tmp_set 
                               if item not in [v1,v2]]
                    tmp_set += list(c)
                    name_list = [self.names[i] for i in tmp_set]
                    name_list.sort()
                    if name_list in self.blacklist:
                        self.stats['blacklist_found'] += 1
                        continue
                    no_options_left = False
                    log_str = 'Try switching {}-{} & {}-{}'.format(
                                v1, self.names[v1], 
                                v2, self.names[v2]) 
                    log_str += ' ({},{:.1f}) -> {}-{} '.format(
                                v_costs, v_effs, c, c_names)
                    log_str += '({},{:.1f})'.format(c_costs, 
                                                    c_t_eff)
                    self.write_log(log_str)
                    grb_mod = self.run_model(tmp_set)
                    if grb_mod.status==2:
                        found_costs = c_costs
                        tb_switched = [v1,v2,c]
                        log_str = 'Feasible! '
                        log_str += '(Runtime: {:.2f})'.format(
                                    grb_mod.Runtime)
                        self.write_log(log_str)
                        after_feas_count = 0
                    else:
                        count += 1
                        self.blacklist.append(name_list)
                        if not (tb_switched is None):
                            after_feas_count += 1
                            if (after_feas_count 
                                >= after_feas_patience):
                                break
                if not (tb_switched is None):
                    set_changed = True
                    [v1,v2,c] = tb_switched
                    self.v_set = [item for item in self.v_set 
                                  if item not in [v1,v2]]
                    self.v_set += list(c)
                    unused = [item for item in unused 
                              if item not in list(c)]
                    unused += [v1,v2]
                    log_str = 'Switching {} & {} -> {} '.format( 
                                v1, v2, c)
                    log_str += '\nNew set: {}\n ### {} ###'.format(
                                tmp_set, self.sum_costs)
                    self.write_log(log_str)
                    break
                if time_limit_reached:
                    self.write_log('Time limit reached!')
                    no_options_left = False
                    break    
            if no_options_left:
                self.write_log('No options left!')

        self.sk.vehicle_data = self.full_data.iloc[self.v_set]   
        
        return (no_options_left and not set_changed)


    def switch_3vX(self, max_time, c_patience, 
                   after_feas_patience=1):
        '''
        Replace three vehicle with 1-3 candidates 
        featuring lower costs.

        Args: 
            max_time (int): maximum time limit in seconds 
                            for switches
            patience (int): number of infeasible switches 
                            before breaking
            after_feas_patience (int): 
                    number of further switches processed 
                    after feasible switch
        Returns:
            no_options_left (bool): True, if no switches left
        '''
        start = time.time()

        log_str = '\nTry 3vX switches on intermediate set '
        log_str += '{} ({})'.format(self.v_set, self.sum_costs)
        self.write_log(log_str)

        unused = [i for i in self.full_data.index.tolist() 
                  if i not in self.v_set]

        time_limit_reached = False
        no_options_left = False 
        set_changed = False
        while not (time_limit_reached or no_options_left):
            v_candidates = [(v1,v2,v3) for v1 in self.v_set 
                                       for v2 in self.v_set 
                                       for v3 in self.v_set]
            v_candidates = remove_duplicates(v_candidates, 
                                             self.names)
            no_options_left = True
            for (v1,v2,v3) in v_candidates:
                v_costs = (self.costs[v1] + self.costs[v2] 
                          + self.costs[v3])
                unused_red = [item for item in unused 
                              if self.costs[item]<v_costs]
                v_t_effs = (self.t_eff[v1] + self.t_eff[v2] 
                            + self.t_eff[v3])
                df = self.full_data.iloc[unused]
                unique_df = df.drop_duplicates(subset='name')
                list_1 = [c for c in unique_df.index.tolist() 
                          if self.costs[c] < v_costs]
                list_1 = [((c,),[self.costs[c],self.t_eff[c]]) 
                          for c in list_1]
                list_2 = [[c1,c2] for c1 in unused 
                                  for c2 in unused 
                          if (self.costs[c1] + self.costs[c2] 
                              < v_costs)]
                list_2 = remove_duplicates(list_2, self.names)
                list_2 = [((c1,c2),[self.costs[c1]+self.costs[c2],
                                    self.t_eff[c1]+self.t_eff[c2]])
                                    for [c1,c2] in list_2]
                list_3 = findTriplets(unused_red,self.costs,
                                      v_costs)
                list_3 = remove_duplicates(list_3, self.names)
                list_3 = [((c1,c2,c3),
                          [self.costs[c1]+self.costs[c2]
                           +self.costs[c3],
                           self.t_eff[c1]+self.t_eff[c2]
                           +self.t_eff[c3]]) 
                           for [c1,c2,c3] in list_3]
                my_dict = dict(list_1+list_2+list_3)
                list_sorted = sorted(my_dict.items(), 
                                     key=lambda item: item[-1][1])
                list_sorted.reverse()
                tb_switched = None
                count = 0
                after_feas_count = 0
                found_costs = 1e99
                for c,[c_costs,c_t_eff] in list_sorted:
                    if not (tb_switched is None): 
                        if c_costs >= found_costs:
                            continue
                    if count >= c_patience:
                        break
                    if (time.time()-start) >= max_time:
                        time_limit_reached = True
                        break    
                    c_names = [self.names[i] for i in list(c)]
                    tmp_set = self.v_set.copy()
                    tmp_set = [item for item in tmp_set 
                               if item not in [v1,v2,v3]]
                    tmp_set += list(c) 
                    name_list = [self.names[i] for i in tmp_set]
                    name_list.sort()
                    if name_list in self.blacklist:
                        self.stats['blacklist_found'] += 1
                        continue
                    no_options_left = False
                    log_str = 'Try switching {}-{} & {}-{}'.format(
                               v1, self.names[v1], 
                               v2, self.names[v2])
                    log_str += ' & {}-{} ({},{:.1f}) '.format(
                                v3, self.names[v3], 
                                v_costs, v_t_effs)
                    log_str += '-> {}-{} ({},{:.1f})'.format( 
                                c, c_names, c_costs, c_t_eff)
                    self.write_log(log_str)
                    grb_mod = self.run_model(tmp_set)
                    if grb_mod.status==2:
                        found_costs = c_costs
                        tb_switched = [v1,v2,v3,c]
                        log_str = 'Feasible! '
                        log_str += '(Runtime: {:.2f})'.format(
                                    grb_mod.Runtime)
                        self.write_log(log_str)
                        after_feas_count = 0
                    else:
                        count += 1
                        self.blacklist.append(name_list)
                        if not (tb_switched is None):
                            after_feas_count += 1
                            if (after_feas_count 
                                >= after_feas_patience):
                                break
                if not (tb_switched is None):
                    set_changed = True
                    [v1,v2,v3,c] = tb_switched
                    self.v_set = [item for item in self.v_set 
                                  if item not in [v1,v2,v3]]
                    self.v_set += list(c)
                    unused = [item for item in unused 
                              if item not in list(c)]
                    unused += [v1,v2,v3]
                    log_str = 'Switching {} & {} & {} '.format(
                               v1, v2, v3) 
                    log_str += '-> {} \nNew set: {}'.format(
                                list(c), tmp_set)
                    log_str += '\n ### {} ###'.format(
                                self.sum_costs) 
                    self.write_log(log_str)
                    break
                if time_limit_reached:
                    self.write_log('Time limit reached!') 
                    no_options_left = False 
                    break
            if no_options_left:
                self.write_log('No options left!')

        self.sk.vehicle_data = self.full_data.iloc[self.v_set] 

        return (no_options_left and not set_changed)


if __name__ == "__main__":
    start = time.time()
    parser = argparse.ArgumentParser(
             description='Visualize a specific file.')
    parser.add_argument('-c', '--config', 
                        dest='config', default='config.yaml', 
                        help='Config file to be used')
    args = parser.parse_args()

    heuristic = greedy2(args.config)
    heuristic.sk.min_vehicles = False
    heuristic.sk.LogToConsole = False
    heuristic.sk.obj = 0
    heuristic.sk.TimeLimit = heuristic.sk.h_init_time_limit
    heuristic.sk.MIPFocus = 1

    # PART Ia: init ###############################################
    heuristic.write_log('\n### Part Ia: Initialization ###')
    heuristic.write_log('Init time limit: {}'.format(
                        heuristic.sk.TimeLimit))
    if heuristic.sk.h_init == 'greedy':
        heuristic.write_log('Using Greedy-1 init...')
        heuristic.greedy_init()
    elif heuristic.sk.h_init == 'quick':
        heuristic.write_log('Using quick_init...')
        heuristic.quick_init()
    else:
        exit('Error on sk.h_init, exiting...')

    init_time = time.time()-start
    stats = heuristic.stats
    stats_str = '\nInit stats:\nRuntime: {}'.format(init_time) 
    stats_str += '\n{} Iterations\n{} feasible'.format(
                    stats['iter'], stats['feas'])
    stats_str += ' -> {:.2f}s {}\n{} infeasible'.format(
                    stats['feas_time'],stats['feas_times'],
                    stats['inf'])
    stats_str += ' -> {:.2f}s\n{} reached t-limit '.format(
                    stats['inf_time'],
                    stats['tlimit']) 
    stats_str += ' -> {:.2f}s'.format(stats['tlimit_time'])

    heuristic.write_log(stats_str)
    ###############################################################

    # Part Ib: improvement ########################################
    v_time_limit = 0.75*heuristic.__time_limit__   
    heuristic.sk.TimeLimit = heuristic.sk.h_time_limit
    log_str = '\n### Part Ib: vehicle set improvement ###'
    log_str += '\nTime Limit: {}\nRunTime limit: {}'.format(
                v_time_limit, heuristic.sk.TimeLimit)
    heuristic.write_log(log_str)

    heuristic.removals(120, 2)
    while (time.time()-start < v_time_limit):
        time_left = v_time_limit - (time.time()-start)
        nol_1 = heuristic.switch_1vX(0.33*time_left,1)
        nol_2 = heuristic.switch_2vX(0.33*time_left,1)
        nol_3 = heuristic.switch_3vX(0.33*time_left,1)
        if (nol_1 or nol_2 or nol_3):
            heuristic.write_log('No more options! Exiting...')
            break

    v_time = time.time() - start
    stats = heuristic.stats
    stats_str = '\n{} Iterations\n{} feasible'.format(
                stats['iter'], stats['feas'])
    stats_str += ' -> {:.2f}s {}\n{} infeasible'.format(
                    stats['feas_time'],stats['feas_times'],
                    stats['inf'])
    stats_str += ' -> {:.2f}s\n{} reached t-limit'.format(
                       stats['inf_time'],
                       stats['tlimit']) 
    stats_str += ' -> {:.2f}s'.format(stats['tlimit_time'])
    stats_str += '\n{} blacklist entries skipped'.format(
                  stats['blacklist_found'])


    log_str = '\nFinal set: \n{}'.format(
                heuristic.sk.vehicle_data[['name','score',
                                           'theta_eff','costs']])
    log_str += '\nCombined Throughput: {}'.format(
                heuristic.sk.vehicle_data['theta_eff'].sum())
    log_str += '\nVehicle costs: {}'.format(
                heuristic.sk.vehicle_data['costs'].sum())
    heuristic.write_log(log_str)
    ###############################################################
    
    # Part II: Routing ############################################
    heuristic.sk.TimeLimit = max((heuristic.__time_limit__  
                                 - (time.time()-start)), 
                                 100)
    heuristic.write_log('\n### Part II: routing ###')
    heuristic.write_log('Time Limit: {:.1f}'.format(
                        heuristic.__time_limit__ 
                        - (time.time()-start)))
    heuristic.sk.method = 2
    heuristic.sk.MIPFocus = 2
    heuristic.sk.LogToConsole = True    
    heuristic.sk.obj = heuristic.__obj__
    grb_mod = heuristic.run_model(heuristic.v_set)

    log_str = '\nObj: {:.2f}\nRuntime: {:.2f}'.format(
                grb_mod.objVal, grb_mod.Runtime)
    log_str += '\nGap: {:.1f} %'.format(100*grb_mod.MIPGap) 
    heuristic.write_log(log_str)
    heuristic.sk.postprocess(grb_mod) 
    log_str = '\nCombined objective: {:.2f}'.format(
                grb_mod.objVal 
                + heuristic.sk.vehicle_data['costs'].sum()) 
    log_str += '\nRuntime for vehicle-set: {:.2f}'.format(v_time)
    log_str += stats_str
    log_str += '\nTotal runtime: {:.2f}'.format(time.time()-start)
    heuristic.write_log(log_str)
        
    heuristic.profiler.disable()
    s = io.StringIO()
    stats = pstats.Stats(heuristic.profiler, stream=s)
    ps = stats.sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(20)
    #print(s.getvalue())
    proFile = os.path.join('output', 
                           heuristic.sk.time_str + '_profile.txt')
    

    with open(proFile, 'w+') as f:
        f.write(s.getvalue())
