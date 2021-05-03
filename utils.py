import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import glob
import os
from itertools import combinations 

dir_path = os.path.dirname(os.path.realpath(__file__))

###################
# GENERAL PURPOSE #
###################
def read_variables(grb_mod):
    '''
    Read results from a previously solved gurobi model 
    and return dictionaries for further use.

    Args:
        grb_mod (GUROBI.model): solved gurobi-model 
    Returns:
        f_vnt (dict): 1 if vehicle v is (dis-)charging 
                      at node n at time t, 0 else
        w_vnmt (dict): 1 if vehicle v is moving 
                       from n to m at time t, 0 else
        s_nt (dict): amount of stored energy 
                     at node n and time t (in kWh)
        s_vt (dict): amount of stored energy 
                     in vehicle v at time t (in kWh)
    '''

    f_vnt = {}
    w_vnmt = {}
    s_nt = {}
    s_vt = {}

    varlist = grb_mod.getVars()

    for v in varlist:
        if v.varName[:5] == 'f_vnt':
            ind = v.varName[5:].replace('[','').replace(']','').split(',')
            f_vnt[int(ind[0]), int(ind[1]), int(ind[2])] = float(v.x)
        elif v.varName[:6] == 'w_vnmt':
            ind = v.varName[6:].replace('[','').replace(']','').split(',')
            w_vnmt[int(ind[0]), int(ind[1]), int(ind[2]), int(ind[3])] = float(v.x)
        elif v.varName[:4] == 's_nt':    
            ind = v.varName[4:].replace('[','').replace(']','').split(',')
            s_nt[int(ind[0]), int(ind[1])] = float(v.x)
        elif v.varName[:4] == 's_vt':    
            ind = v.varName[4:].replace('[','').replace(']','').split(',')
            s_vt[int(ind[0]), int(ind[1])] = float(v.x)

    return f_vnt, w_vnmt, s_nt, s_vt


##############
# SMART_KRIT #
##############
def get_pd_frame(n_type, source, n_max, lat, lon):
    '''
    Find files correlating to nodes of type *n_type* 
    from *source* and return the data 
    in a pandas dataframe.  

    Args:
        n_type (str): type of nodes ['P','C','D','O']
        source (str): single CSV-file or path to folder containing CSV-files
        n_max (int): maximum number of nodes to return
        lat (tuple): range of latitude to be considered, 
                     i.e. (lat_min,lat_max)
        lon (tuple): range of longitude to be considered, 
                     i.e. (lon_min,lon_max)
    Returns:
        pd_frame (pd.DataFrame): dataframe containing the data
    '''
    if n_type in ['P','C']:
        cols = ['ID','cap[kWh]','cap_0[kWh]','peak[kW]',
                'profile','power_cdc[kW]','n_charge',
                'lat','lon']
    elif n_type in ['D','O']:
        cols = ['ID','lat','lon']
    if os.path.isdir(source):
        files = glob.glob(os.path.join(source, '*.CSV'))
    elif os.path.isfile(source) and source.endswith('.csv'):
        files = [source]
    else:
        exit(f'Cannot interpret source {source}')

    pd_frame = pd.DataFrame(columns=cols)
    for i in range(len(files)):
        frame = pd.read_csv(files[i])
        frame = frame[(frame['lat'] <= lat[1]) & 
                      (frame['lat'] >= lat[0]) &
                      (frame['lon'] <= lon[1]) & 
                      (frame['lon'] >= lon[0])]
        if set(cols).issubset(set(frame.columns)):
            pd_frame = pd_frame.append(frame)
        else:
            missing = set(cols) - set(frame.columns)
            exit('Missing columns {} in file {}'.format(missing, files[i]))
    pd_frame.insert(1,'type', n_type)

    return pd_frame[:n_max]


def get_vehicle_data(yaml_dict):
    '''
    Find vehicle files in the specified directory 
    and return a single pandas-dataframe containing 
    all vehicle data.

    Args:
        yaml_dict (dict): dictionary from the config file, 
                          containing directory of vehicle files 
    Returns:
        v_data (pd.DataFrame): Dataframe containing all data
    '''
    v_max = yaml_dict['v_max']
    vehicle_dir = os.path.join(dir_path, 
                               yaml_dict['vehicle_dir'])
    cols = ['ID','cap[kWh]','cap_0[kWh]','node_0',
            'consumption[kWh/km]','power_cdc[kW]',
            'speed[km/h]','name','costs']
    vehicle_files = glob.glob(os.path.join(vehicle_dir,'*.CSV'))
    vehicle_data = pd.DataFrame(columns=cols)
    for i in range(len(vehicle_files)):
        frame = pd.read_csv(vehicle_files[i])
        if list(frame.columns) == cols:
            vehicle_data = vehicle_data.append(frame[:v_max])
        else:
            print('Wrong columns in file {}'.format(
                  vehicle_files[i]))

    v_data = vehicle_data[:v_max]

    return v_data


def get_gc_distance(lat_1, lon_1, lat_2, lon_2):
    '''
    calculates direct great circle distance 
    between two points using haversine formula
    '''
    R = 6373.0

    lat_1 = math.radians(lat_1)
    lon_1 = math.radians(lon_1)
    lat_2 = math.radians(lat_2)
    lon_2 = math.radians(lon_2)

    d_lon = lon_2 - lon_1
    d_lat = lat_2 - lat_1

    a = math.sin(d_lat / 2)**2 + math.cos(lat_1) * math.cos(lat_2) * math.sin(d_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance


def get_distance(node_data, type):
    '''
    calculate all distances between nodes depending on type

    Args: 
        node_data (pd.DataFrame): DataFrame of considered nodes
        type (str): Type of distance calculation, e.g. 'air' for
                    direct distance 
    '''
    n_nodes = node_data.shape[0]
    lon = node_data['lon'].values
    lat = node_data['lat'].values

    dist = np.empty((n_nodes,n_nodes)) 
    for n in range(n_nodes):
        for m in range(n_nodes):
            if type == 'air':
                dist[n,m] = get_gc_distance(lat[n], lon[n], 
                                            lat[m], lon[m])
            else:
                exit('type of distance calculation not supported')

    return dist


def get_profiles(nodes, peak, profiles, t_0, delta_t, t_steps):
    '''
    Read profiles and return it in granularity as specified.
    This function expects data to be defined in 0.25h steps
    and delta_t to be a multiple of 0.25h as well.

    Args:
        nodes (list): index-list of nodes featuring a profile
        peak (list): list of floats, containing peak 
                     production/consumption values for all nodes
        profiles (list): list of strings, containing the names 
                         of CSV-files specifying the profile 
                         of this node
        t_0 (str): string of initial time instance, e.g. '10:30'
        delta_t (float): length of time-step (in h)
        t_steps (int): amount of time instances to be considered     
    Returns:
        E_nt (dict): consumed or produced energy by node n during 
                     interval [t,t+delta_t]
    '''
    if not ((delta_t % 0.25)==0 or delta_t==0.05):
        exit('Bad delta_t: {}'.format(delta_t)) 

    E_nt = {}
    t_0_dt = datetime.strptime(t_0, '%H:%M')

    for n in nodes:
        profile = pd.read_csv(os.path.join('data','profiles',
                              profiles[n]))
        times = profile['time'].values
        # energy that is produced/consumed in each 15 min interval
        energy = profile['peak_percentage'].values * peak[n] * 0.25
        for t in range(t_steps):
            # set E to zero when charging is not possible
            #if t in [0, t_steps-2, t_steps-1]:
            if t in [t_steps-1]:
                E_nt[n,t] = 0
                continue
            t_dt = t_0_dt + timedelta(hours=t*delta_t)
            t_str = t_dt.strftime('%H:%M')

            if (delta_t % 0.25)==0:
                t_dt_next = t_0_dt + timedelta(hours=(t+1)*delta_t)
                t_str_next = t_dt_next.strftime('%H:%M')
                first_ind = np.where(times==t_str)[0][0]
                last_ind = np.where(times==t_str_next)[0][0] - 1 
                E_nt[n, t] = sum(energy[first_ind:(last_ind+1)])
            else:
                ind = np.where(times>t_str)[0][0] - 1 
                E_nt[n, t] = energy[ind] / 5. 

    return E_nt


#############
# HEURISTIC #
#############
def score_function(mod):
    '''
    Calculate scores and add as column to vehicle data.
    
    Args:
        mod (smart_krit.my_sk object): underlying smart krit model,
                                       see smart_krit.py
    Returns:
        vehicle_data (pd.Dataframe): vehicle data for which 
                                     the score is calculated
    '''

    v_data = mod.vehicle_data
    node_data = mod.node_data
    E_nt = mod.E_nt
    times = mod.times

    node_data = node_data[node_data['type'].isin(['C','P'])].copy()
    nodes = node_data.index.tolist()

    # calc average E_nt of node, 
    E_list = []
    for n in nodes:
        sum_n = 0
        for t in times[1:-2]:
            sum_n += E_nt[n,t]
        E_list.append(sum_n/len(times))

    cap_E = E_list + node_data['cap[kWh]'].values
    node_data['cap+E'] = cap_E
    node_data['through'] = pd.concat([node_data['power_cdc[kW]']*
                                      mod.delta_t,
                                      node_data['cap+E']], 
                                      axis=1).min(axis=1) 
    v_data['through'] = pd.concat([v_data['power_cdc[kW]']*
                                   mod.delta_t,v_data['cap[kWh]']],
                                   axis=1).min(axis=1)
    
    theta_eff_list = []
    for index, row in v_data.iterrows():
        theta_vn = [min(n_through, row['through']) 
                    for n_through in node_data['through'].values]
        N_vn = [max(1,row['cap[kWh]'] / t_vn ) 
                for t_vn in theta_vn]
        f_vn = [min(N / (N+2+1),(len(times)-3-2)/(len(times)-3)) 
                for N in N_vn]
        theta_avg = [f*theta for f,theta in zip(f_vn,theta_vn)]
        theta_eff = sum(theta_avg)/len(theta_avg)            
        theta_eff_list.append(theta_eff)

    v_data['theta_eff'] = theta_eff_list    
    v_data['score'] = v_data['theta_eff'].div(v_data['costs'])

    return v_data


def init_set(mod):
    '''
    Find a good initial set as a baseline for the heuristic.
    This set does not have to be feasible yet,
    but serves as a initial guess. 

    I. Find approximation for required throughput per timestep 
    II. Add vehicles until the required throughput is met

    Args:
        mod (smart_krit.my_sk object): underlying smart krit model, 
                                       see smart_krit.py
    
    Returns:
        v_set (list): index list of vehicles that provide 
                      the required approximated throughput
        log_str (str): logging string containing information 
    '''
    v_data = mod.vehicle_data
    node_data = mod.node_data
    E_nt = mod.E_nt
    s_n_0 = mod.s_n0
    times = mod.times

    log_str = 'Finding initial set...'

    consumers = node_data.index[node_data['type'] == 'C'].tolist()
    producers = node_data.index[node_data['type'] == 'P'].tolist()

    # calculate cumulative energies of consumer and producer 
    # for all times 
    energy_c = []
    energy_p = []
    energy_cp = []
    for t in times[1:-2]:
        sum_energy_cp = 0
        sum_energy_c = 0
        for c in consumers:
            sum_energy_c += E_nt[c,t]
            sum_energy_cp += E_nt[c,t]
        sum_energy_p = 0
        for p in producers:
            sum_energy_p += E_nt[p,t]
            sum_energy_cp += E_nt[p,t]
        energy_c.append(sum_energy_c) 
        energy_p.append(sum_energy_p)
        energy_cp.append(sum_energy_cp)
    
    init_energy_p = 0
    for p in producers:
        init_energy_p += s_n_0[p]
    init_energy_c = 0
    for c in consumers:
        init_energy_c += s_n_0[c]

    req_energy = sum(energy_c)-init_energy_c
    av_energy = sum(energy_p)+init_energy_p

    log_str += '\nInitial Energy in producers: {:.2f}'.format(
                init_energy_p)
    log_str += '\nEnergy produced: {:.2f}'.format(sum(energy_p))
    log_str += '\nInitial Energy in consumers: {:.2f}'.format(
                init_energy_c)
    log_str += '\nEnergy consumed: {:.2f}'.format(sum(energy_c))
    log_str += '\nAVAILABLE: {:.2f}\nREQUIRED: {:.2f}'.format(
                av_energy, req_energy)
    if av_energy < req_energy:     #+ vehicle_energy
        log_str += '\nWarning! Cumulative available energy' 
        log_str += 'less than required amount'
    
    avg_throughput = 2*req_energy/len(energy_c)
    log_str += '\nRequired avg throughput: {}'.format(
                avg_throughput)

    # add vehicles greedy until threshold is met
    threshold = avg_throughput
    v_set = []
    sum_theta = 0
    while sum_theta < threshold:
        old_set = v_set
        v_set, log = add_greedy(v_data, v_set)
        if v_set is None:
            log_str += '\nRequired throughput exceeds all vehicles'
            log_str += ' using full set...'
            v_set = old_set
            break
        log_str += log
        last_added = v_set[-1]
        sum_theta += v_data['theta_eff'].values[last_added]
    
    log_str += '\nInitial set: {}'.format(v_set)
    log_str += '\nCombined throughput: {}'.format(sum_theta)

    return v_set, log_str


def add_greedy(v_data, v_set):
    '''
    Adds the vehicle with the highest score 
    to the current vehicle set
    
    Args:
        v_data (pd.Dataframe): dataframe containing 
                               all vehicle data
        v_set (list): list of indices for vehicles 
                      included in the current set
    Returns:
        v_set (list): new list including the added vehicle
        log_str (str): logging string containing information 
    '''
    unused = v_data.drop(v_set)
    if unused.shape[0] == 0:
        log_str = 'No vehicles left to add, problem is infeasible!'        
        return None, log_str
 
    unused['score'] = pd.to_numeric(unused['score'])
    max_index = unused['score'].idxmax()

    log_str = '\nAdding {} ({}) to {}...'.format(max_index, 
                v_data['name'].values[max_index], v_set)
    v_set.append(max_index)

    return v_set, log_str


def remove_greedy(v_data, v_set):
    '''
    Removes the vehicle with the lowest score from a vehicle set.

    Args:
        v_data (pd.Dataframe): dataframe containing 
                               all vehicle data
        v_set (list): list of indices for vehicles 
                      included in the current set
    Returns:
        v_set (list): new list without the removed vehicle
        log_str (str): logging string containing information
    '''
    used = v_data.iloc[v_set,:]
    score = pd.to_numeric(used['score'])
    min_index = score.idxmin()

    log_str = '\nRemoving {} ({}) from {}...'.format(min_index, 
                v_data['name'].values[min_index], v_set)

    v_set.remove(min_index)

    return v_set, log_str


def remove_duplicates(tuple_list,names):
    '''
    Remove duplicate index-tuples from a list 
    depending on their value in list names.
    E.g., (1,3,4) is a duplicate of (5,6,7), if
    set(names[1],names[3],names[4]) == 
    set(names[5],names[6],names[7]) 
    
    Args:
        tuple_list (list): list of tuples to be edited
        names (list): list of strings
    Returns:
        result (list): new list of tuples without duplicates
    '''
    # remove trivial duplicates first
    duplicate_free = list(set([tuple(sorted(i)) 
                               for i in tuple_list]))

    # remove additional duplicates due to correlating entries in names
    result = []
    result_names = [] 
    for item in duplicate_free:
        # no index is allowed more than once
        if len(item) != len(set(item)):
            continue
        item_names = [names[i] for i in item]
        item_names.sort()
        if item_names not in result_names:
            result_names.append(item_names)
            result.append(item)
        else:
            continue

    return result


def findTriplets(lst, costs, key):
    '''
    Find all triplet-combinations in list 
    whose costs are smaller than some key

    Args:
        lst (list): list of indices
        costs (list): list of corresponding costs
        key (float): bound for costs of triplet-combinations
    Returns:
        triplets (list): list of triplets featuring 
                         lower costs than key
    '''   
    def valid(val): 
        cost_list = [costs[i] for i in val] 
        return sum(cost_list) < key 

    triplets = list(filter(valid, list(combinations(lst, 3)))) 

    return triplets


###########
# VISUALS #
###########
def read_results(out_file, s_n0=None, s_v0=None, nodes=None, vehicles=None):
    '''
    Read results obtained by gurobi and 
    return them as dictionaries for further use.

    Args:
        out_file (str): path of txt-file containing results
        s_n0 (list): list of initial storage values for nodes
        s_v0 (list): list of initial storage values for vehicles
        nodes (list): index-list for nodes
        vehicles (list): index-list for vehicles
        
    Returns:
        s_nt (dict): stored energy at all locations and times
        s_vt (dict): stored energy in vehicle v at time t
        f_vnt (dict): 1 if vehicle v is (dis-)charging 
                      at node n at time t, 0 else
        w_vnmt (dict): 1 if vehicle v is moving 
                       from n to m at time t, 0 else
    '''

    s_nt = {}  
    s_vt = {}
    f_vnt = {}
    w_vnmt = {}
    z_v = {}
    e_nt = {}

    with open(out_file, 'r') as my_file:
        lines = my_file.readlines()

    counter = 0
    for line in lines:
        var, val = line.split(' ')
        val = float(val)
        if var[:3] == 'z_v':
            counter += 1
            ind = var[3:].replace('[','').replace(']',
                                                  '').split(',')
            z_v[int(ind[0])] = val
        if var[:4] == 'e_nt':
            counter += 1
            ind = var[4:].replace('[','').replace(']',
                                                  '').split(',')
            e_nt[int(ind[0]),int(ind[1])] = val
        elif var[:4] == 's_nt':
            counter += 1
            ind = var[4:].replace('[','').replace(']',
                                                  '').split(',')
            s_nt[int(ind[0]),int(ind[1])] = val
        elif var[:4] == 's_vt':
            counter += 1
            ind = var[4:].replace('[','').replace(']',
                                                  '').split(',')
            s_vt[int(ind[0]),int(ind[1])] = val
        elif var[:5] == 'f_vnt':
            counter += 1
            ind = var[5:].replace('[','').replace(']',
                                                  '').split(',')
            f_vnt[int(ind[0]), int(ind[1]), int(ind[2])] = val
        elif var[:6] == 'w_vnmt':
            counter += 1
            ind = var[6:].replace('[','').replace(']',
                                                  '').split(',')
            w_vnmt[int(ind[0]), int(ind[1]), 
                   int(ind[2]), int(ind[3])] = val

    print(f'\nRead {counter} values from {out_file}...\n')

    if nodes is not None:
        for n in nodes:
            if s_n0 is not None:
                s_nt[n,0] = s_n0[n]
    if vehicles is not None:
        for v in vehicles:
            if s_v0 is not None:
                s_vt[v,0] = s_v0[v]
    
    return w_vnmt, s_nt, s_vt, f_vnt, z_v, e_nt


def preprocess_vars(w, f_grb, vehicles, times, nodes):
    '''
    Preprocess variables from gurobi for further use in
    visualisation functions.
    Some variables are not implemented as actual variables,
    e.g., because their value is fixed a-priori.
    This function recovers such values in order to visualize
    the solution seamless.

    Args:
        w (dict): arc-based variables w_vnmt
        f_grb (dict): f_variables from gurobi 
                      (not all indices exist)
        vehicles (list): index-list for vehicles
        times (list): index-list for time-instances
        nodes (list): index-list for nodes

    Return:
        x (dict): node-based variables x_vnt
        f (dict): complete f_vnt variables for visualisation
        v_list (list): index-list of used vehicle  
    '''
    x = {}
    f = {}
    v_list = []
    for v in vehicles:
        for t in times:
            for n in nodes:
                x[v,n,t] = 0
                f[v,n,t] = 0
    for v in vehicles:
        for t in times:
            for n in nodes:
                try:
                    if f_grb[v,n,t] > 0:
                        f[v,n,t] = f_grb[v,n,t]
                        if v not in v_list:
                            v_list.append(v)
                except KeyError:
                    pass 
                for m in nodes:
                    try:
                        if w[v,n,m,t] == 1:
                            x[v,n,t] = 1
                            if t == times[-2]:
                                x[v,m,times[-1]] = 1
                    except KeyError:
                        pass
    return x,f,v_list
