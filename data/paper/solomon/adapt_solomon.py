import os
import pandas as pd
import matplotlib.pyplot as plt

folder = 'rc1'
instance = 'rc101.csv'
time_window = 240.


csv_file = os.path.abspath(os.path.join(folder,instance))
pd_frame = pd.read_csv(csv_file)

c_frame = pd_frame[1:]
data = {}

data['ID'] = c_frame['CUST NO.']

data['DEMAND'] = c_frame['DEMAND']
data['DUE DATE'] = c_frame['DUE DATE']


# consumer needs to run out at the same fraction of the considered time window
# cap_0 and peak such that we run out of energy at due data
# with constant consumption
due_fraction = c_frame['DUE DATE'] / time_window

data['cap_0[kWh]'] = c_frame['DEMAND'] / (1 - due_fraction) - c_frame['DEMAND']
data['cap[kWh]'] = data['cap_0[kWh]'] 

# make sure that we consume cap_0 + demand over the full time-horizon
# i.e. demand needs to be provided by vehicles
data['peak[kW]'] = (data['cap_0[kWh]'] + c_frame['DEMAND']) / (time_window / 60.)
data['profile'] = 'const.csv'

data['power_cdc[kW]'] = 100
data['n_charge'] = 10

# xcoords: [2, 67] -> lat range: [49.56, 49.61]
min_x = c_frame['XCOORD.'].min()
max_x = c_frame['XCOORD.'].max()
print(min_x, max_x)

data['lat'] = 49.56 + 0.05 * (c_frame['XCOORD.']-min_x) / (max_x-min_x)
# ycoords: [3, 77] -> lon range: [10.98, 11.03]
min_y = c_frame['YCOORD.'].min()
max_y = c_frame['YCOORD.'].max()
print(min_y, max_y)
data['lon'] = 10.98 + 0.05 * (c_frame['YCOORD.']-min_y) / (max_y-min_y)

c_frame_new = pd.DataFrame(data=data)
c_frame_new.to_csv(os.path.join(folder, 'c_'+ instance), index=False)


#########
# DEPOT #
#########
d_frame = pd_frame[:1]

data = {}
data['ID'] = d_frame['CUST NO.']
# lat range: [49.56, 49.61]
data['lat'] = 49.56 + 0.05 * (d_frame['XCOORD.']-min_x) / (max_x-min_x)
# lon range: [10.98, 11.03]
data['lon'] = 10.98 + 0.05 * (d_frame['YCOORD.']-min_y) / (max_y-min_y)

d_frame_new = pd.DataFrame(data=data)
d_frame_new.to_csv(os.path.join(folder, 'd_'+ instance), index=False)

############
# PRODUCER #
############


#x_and_y = pd_frame[['XCOORD.', 'YCOORD.']]
#plt.scatter(pd_frame['XCOORD.'], pd_frame['YCOORD.'])
#plt.show()
# data = {}
# data['ID'] = ['1']

# volume = 100.

# data['cap[kWh]'] = volume
# data['cap_0[kWh]'] = 0.1 * volume
# data['peak[kW]'] = volume / (time_window / 60.)
# data['profile'] = 'const.csv'
# data['power_cdc[kW]'] = 100
# data['n_charge'] = 10

# c_lat = 49.56 + 0.05 * d_frame['XCOORD.'] / 100.
# c_lon = 10.98 + 0.05 * d_frame['YCOORD.'] / 100.
# data['lat'] = sum(c_lat) / len(c_lat)
# data['lon'] = sum(c_lon) / len(c_lon)

# p_frame_new = pd.DataFrame(data=data)
# p_frame_new.to_csv('p_r101.csv', index=False)