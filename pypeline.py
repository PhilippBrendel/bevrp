# execute python file

import os
import glob
import subprocess
from sys import platform 


#print(platform)

if platform in ['linux','linux2']:
    configs = glob.glob(os.path.join('configs', '*.YAML')) +  glob.glob(os.path.join('configs', '*.yaml'))
elif platform == 'win32':
    configs = glob.glob(os.path.join('configs', '*.YAML'))
else:
    print('Unknown platform!')
    exit()

#print(configs)

for i, config in enumerate(configs):
    print('\n{} of {}: {}'.format(i+1,len(configs),config))
    #proc = subprocess.Popen('python greedy2.py -c {}'.format(config), stdout=subprocess.PIPE, shell=True)
    #(out, err) = proc.communicate()
    #print "program output:", out

    #os.system('python smart_krit.py -c {}'.format(config))
    os.system('python greedy2.py -c {}'.format(config))
