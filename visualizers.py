import sys
import numpy as np 
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.widgets import Button
import pandas as pd
import csv
import argparse
import os
from datetime import datetime, timedelta
import pickle
from utils import *

# Print iterations progress
def get_progress_bar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', unfill = '-'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    #percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + unfill * (length - filledLength)
    bar_str = f'{prefix} |{bar}| {suffix}'
    return bar_str
    # Print New Line on Complete
    if iteration == total: 
        print()

class visuals:
    def __init__(self, model_dict, out_file):
        self.times = model_dict['times']
        self.t_0 = model_dict['t_0']
        self.delta_t = model_dict['delta_t']
        self.t_steps = model_dict['t_steps']
        self.vehicles = model_dict['vehicles']
        self.v_names = model_dict['v_names']
        self.nodes = model_dict['nodes']
        self.n_type = model_dict['n_type']
        self.n_names = model_dict['n_names']
        self.n_peak = model_dict['n_peak']
        self.x_values = model_dict['n_x']
        self.y_values = model_dict['n_y']
        self.P_vn = model_dict['P_vn']     
        self.E_nt = model_dict['E_nt']
        self.S_n_max = model_dict['S_n_max']
        self.S_v_max = model_dict['S_v_max']    
        self.s_n0 = model_dict['s_n0']
        self.s_v0 = model_dict['s_v0']    

        a,b,c,d = read_results(out_file, self.s_n0, 
                               self.s_v0, self.nodes, 
                               self.vehicles)
        self.w_vnmt = a
        self.s_nt = b 
        self.s_vt = c
        f_vnt_grb = d
        
        self.x_vnt, self.f_vnt, v_list = preprocess_vars(
                              self.w_vnmt, f_vnt_grb, 
                              self.vehicles, self.times, 
                              self.nodes)
        v_names = [self.v_names[v] for v in v_list]
        print(v_names)

        x_min = np.min(self.x_values) 
        x_max = np.max(self.x_values)
        x_range = x_max - x_min
        x_min -= 0.2*x_range
        x_max += 0.2*x_range
        x_range = x_max - x_min
        y_min = np.min(self.y_values)
        y_max = np.max(self.y_values)
        y_range = y_max - y_min
        y_min -= 0.2*y_range
        y_max += 0.2*y_range
        
        self.xlim = [x_min, x_max]
        self.ylim = [y_min, y_max]

        self.x_tick_str = []
        self.title_str = []
        t_0 = datetime.strptime(self.t_0, '%H:%M')
        for t in range(self.t_steps):
            now = t_0 + timedelta(hours=t*self.delta_t)
            self.title_str.append(now.strftime('%H:%M'))
            interval = int(self.t_steps / 10)
            if t % interval == 0:
                self.x_tick_str.append(now.strftime('%H:%M'))
            else:
                self.x_tick_str.append('')
       

        # setting for time_series_plot
        self.show_fictive_soc = True
        self.show_producers = False
        self.label_vehicles = False
        self.cummulative_E_nt = False
        # Settings for interactive_plot
        self.n_color = {'P': 'b', 
                        'C': 'r', 
                        'D': 'k',
                        'O': 'darkgrey'}
        self.circle_rad = {'D': 0.0002, 'P': 0.0002, 
                           'C': 0.0002, 'O': 0.0001}
        self.box_factor = 1.5
        self.show_vehicles = {'D': True, 'P': True, 
                              'C': True, 'O': True}
        self.show_n_name = {'D': True, 'P': False, 
                            'C': False, 'O': False}
        self.show_n_info = {'D': False, 'P': False, 
                            'C': False, 'O': False}

    def update_annot_v(self,v, n_type):
        '''
        Called when mouse hovers over vehicle and
        its annotation needs to be updated.
        '''
        self.annot.xy = (self.v_x[v], self.v_y[v])
        if n_type in ['P','C']:
            text = '{} \n{:.2f}/{} kWh ({:.2f}%)'.format(
                    self.v_names[v], self.s_vt[v, self.t_ind],
                    self.S_v_max[v],
                    100*self.s_vt[v, self.t_ind]/self.S_v_max[v])
            text += '\nc/dc: {:.2f} kWh'.format(
                     self.f_vnt[v, self.v_node[v], self.t_ind] * 
                     self.P_vn[v, self.v_node[v], self.t_ind]) 
            text += '\n({:.2f} * {} h @ {} kW)'.format( 
                    self.f_vnt[v, self.v_node[v], self.t_ind],
                    self.delta_t,
                    self.P_vn[v, self.v_node[v], self.t_ind] / 
                    self.delta_t)
        elif n_type in ['D','O']:
            text = "{} \n{:.2f}/{} kWh ({:.2f}%)".format(
                    self.v_names[v], self.s_vt[v, self.t_ind],
                    self.S_v_max[v],
                    100*self.s_vt[v, self.t_ind]/self.S_v_max[v])      
        self.annot.set_text(text)
        self.annot.get_bbox_patch().set_alpha(1.0)

    def update_annot_n(self, n, n_type):
        '''
        Called when mouse hovers over node n and
        updates its annotation.
        '''
        self.annot.xy = (self.x_values[n], self.y_values[n])
        if n_type in ['P','C']:
            text =  '{} (peak: {}kW)'.format(self.n_names[n],
                                             self.n_peak[n]) 
            text += '\nstored: {:.2f}/{} kWh ({:.2f}%)'.format(
                    self.s_nt[n, self.t_ind], self.S_n_max[n],
                    100*self.s_nt[n, self.t_ind] / self.S_n_max[n])
            text += '\nE_nt: {:.2f} kWh (@ {:.2f} kW)'.format(                                                                                                      
                    self.E_nt[n, self.t_ind],
                    self.E_nt[n, self.t_ind] / self.delta_t)
        elif n_type in ['D','O']:
            text = self.n_names[n]
        self.annot.set_text(text)
        self.annot.get_bbox_patch().set_alpha(1.0)

    def press(self, event):
        '''
        Defines some key shortcuts to toggle information 
        about vehicles and nodes.
        '''
        sys.stdout.flush()
        if event.key == 'right':
            self.next(None)
        elif event.key == 'left':
            self.prev(None)
        elif event.key == 'd':
            # hide/show vehicles and name at depots
            self.show_vehicles['D'] = not self.show_vehicles['D']
            self.show_n_name['D'] = not self.show_n_name['D'] 
            self.ax.clear()
            self.update_plot()
            plt.draw()
        elif event.key == 'i':
            # toggle info for consumer nodes
            self.show_n_info['C'] = not self.show_n_info['C']
            self.ax.clear()
            self.update_plot()
            plt.draw()
        elif event.key == 'I':
            # toggle info for both consumer and producer nodes
            self.show_n_info['C'] = not self.show_n_info['C']
            self.show_n_info['P'] = not self.show_n_info['P']
            self.ax.clear()
            self.update_plot()
            plt.draw()

    def hover(self, event):
        '''
        Called whenever mouse movement occurs.
        Calls update_annot_n() and update_annot_v() 
        when cursor hovers over node or vehicle.
        '''
        # check if annotation is currently visible
        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            for v in self.vehicles:
                node_type = self.n_type[self.v_node[v]]
                if not self.show_vehicles[node_type]:
                    cont = False
                else:
                    cont, ind = self.v_circle[v].contains(event)
                if cont:
                    self.update_annot_v(v, node_type)
                    self.annot.set_visible(True)
                    self.fig.canvas.draw_idle()
                else:
                    if vis:
                        self.annot.set_visible(False)
                        self.fig.canvas.draw_idle()
            for n in self.nodes:
                cont, ind = self.n_circle[n].contains(event)
                if cont:
                    self.update_annot_n(n, self.n_type[n])
                    self.annot.set_visible(True)
                    self.fig.canvas.draw_idle()
                else:
                    if vis:
                        self.annot.set_visible(False)
                        self.fig.canvas.draw_idle()

    def interactive_plot(self, from_gui=True):
        '''
        Initialize interactive plot with fixed elements 
        like buttons.

        Args:
            - draw_buttons(bool): optionally draw buttons
        '''
        # initialize plot with fixed elements
        self.fig, self.ax = plt.subplots()
        

        if not from_gui:
            self.fig.canvas.mpl_connect("motion_notify_event", 
                                    self.hover)
            self.fig.canvas.mpl_connect("key_press_event", self.press)
            axprev = plt.axes([0.7, 0.05, 0.1, 0.075])
            axnext = plt.axes([0.81, 0.05, 0.1, 0.075])
            bnext = Button(axnext, 'Next')
            bnext.on_clicked(self.next)
            bprev = Button(axprev, 'Previous')
            bprev.on_clicked(self.prev) 

        self.t_ind = 0
        self.update_plot(from_gui)
        return self.fig

    def next(self, event):
        '''
        Called when next button is clicked.
        '''
        if self.t_ind < self.t_steps - 1:
            self.ax.clear()
            self.t_ind += 1 
            self.update_plot()
            plt.draw()

    def prev(self, event):
        '''
        Called when prev button is clicked
        '''
        if self.t_ind >= 1:
            self.ax.clear()
            self.t_ind -= 1
            self.update_plot()
            plt.draw()

    def update_plot(self, from_gui=False, show_map=True):
        '''
        Called initially and when either next or prev is clicked.
        '''
        t = self.t_ind
        self.ax.set_xlim(self.xlim)
        self.ax.set_ylim(self.ylim)
        self.annot = self.ax.annotate("", xy=(0,0), 
                    xytext=(-20,20),textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w"),
                    arrowprops=dict(arrowstyle="->"))
        self.annot.set_visible(False)
        prog_bar = get_progress_bar(t, self.t_steps-1, prefix=self.title_str[0],
                                    suffix=self.title_str[-1], decimals=0, length=25)
        # u"\u25CF"
        self.ax.set_title('{}\n{}\n'.format(self.title_str[t], prog_bar), fontsize=15)

        if show_map:
            img = plt.imread("images/osm_KL.png")
            self.ax.imshow(img, extent=[7.6516, 7.8935, 
                                        49.4042, 49.5075])

        # dicts to save circle objects, 
        # nodes and coordinates of vehicles
        self.n_circle = {}
        self.n_rect = {}
        self.n_rect_text = {}
        self.v_circle = {}
        self.v_node = {}
        self.v_x = {}
        self.v_y = {}
        v_color = {}

        for n in self.nodes:
            # draw node with description
            n_type = self.n_type[n]
            n_color = self.n_color[n_type]
            n_rad = self.circle_rad[n_type]
            n_x = self.x_values[n]
            n_y = self.y_values[n] 
            self.ax.text(n_x-n_rad, n_y + 2*n_rad, 
                         self.n_names[n], ha='left', zorder=0, 
                        visible=self.show_n_name[n_type])

            # find vehicles at each node
            v_list = []
            for v in self.vehicles:
                if self.x_vnt[v, n, t] == 1:
                    v_list.append(v)
                    self.v_node[v] = n

            # calculate vehicle rectangles for this node
            rows = np.ceil(np.sqrt(len(v_list)))
            cols = np.ceil(np.sqrt(len(v_list)))
            box_width = self.box_factor*cols*n_rad
            box_height = self.box_factor*rows*n_rad
            # left bottom coords of rectangle
            lb_x = n_x - n_rad - box_width
            lb_y = n_y - n_rad - box_height 
            for i, v in enumerate(v_list): 
                # change color to nodes color 
                # if vehicles is (dis-)charging
                v_color[v] = 'k'
                if n_type in ['P','C']:
                    try:
                        if self.f_vnt[v, n, t] > 0:
                            v_color[v] = n_color
                    except KeyError:
                        pass      
                row_ind = i // cols
                col_ind = i % cols
                self.v_x[v] = lb_x + self.box_factor*(0.5 + 
                                            col_ind)*n_rad
                self.v_y[v] = lb_y + self.box_factor*(0.5 + 
                                            row_ind)*n_rad

            self.n_rect[n] = self.ax.add_artist(
                            plt.Rectangle((lb_x, lb_y),
                            width=box_width, 
                            height=box_height, 
                            fill=False, 
                            visible=self.show_vehicles[n_type]))
            for i,v in enumerate(v_list):
                v_rad = n_rad*self.box_factor/5
                v_soc = self.s_vt[v, t]/self.S_v_max[v]
                self.v_circle[v] = self.ax.add_artist(
                            plt.Circle((self.v_x[v],self.v_y[v]), 
                            v_rad, color=v_color[v], 
                            visible=self.show_vehicles[n_type]))

            if n_type in ['C','P']:
                soc = self.s_nt[n, t] / self.S_n_max[n]
                self.n_circle[n] = self.ax.add_artist(
                        plt.Circle((n_x, n_y), n_rad, 
                                   color=n_color, fill=False)) 
                self.ax.add_artist(
                        plt.Circle((n_x, n_y), soc*n_rad, 
                                   color=n_color))
                info_str = '{:.2f}%'.format(100*soc)
                self.n_rect_text[n] = self.ax.text(
                            n_x - 0.5*box_width, 
                            n_y, info_str, 
                            ha='right', zorder=0, 
                            visible=self.show_n_info[n_type])
            else:
                self.n_circle[n] = self.ax.add_artist(
                                   plt.Circle((n_x, n_y), n_rad, 
                                              color=n_color))
    
        if from_gui:
            return self.fig
        else:
            plt.show()

    def time_series_plots(self):
        '''
        Plot three different time series plots
        for producer, consumer and vehicles.
        '''
        if self.show_producers:
            v_ax = 2
            fig, ax = plt.subplots(3)
        else:
            v_ax = 1
            fig, ax = plt.subplots(2)

        p_color = 'b'
        p_color_2 = 'grey'
        c_color = 'g'
        c_color_2 =  'grey'

        cons = np.zeros(self.t_steps)
        prod = np.zeros(self.t_steps)
        S_p_max = []
        S_c_max = []

        for n in self.nodes:
            soc = np.zeros(self.t_steps)                 
            if self.n_type[n] == 'C':
                soc_fictive = np.zeros(self.t_steps)
                soc_fictive[0] = self.s_nt[n,0]
                for t in range(self.t_steps):
                    if t > 0 and self.show_fictive_soc:
                        soc_fictive[t] = (soc_fictive[t-1] - 
                                            self.E_nt[n,t-1])
                    soc[t] = self.s_nt[n,t] #/ self.S_n_max[n]
                    cons[t] += self.E_nt[n,t] 
                if len(S_c_max) == 0:
                    ax[0].plot(soc,'{}-'.format(c_color), 
                               label='mit SmartKrit')
                    if self.show_fictive_soc:
                        ax[0].plot(soc_fictive, '{}--'.format(
                                'r'),
                                label=('ohne SmartKrit')) 
                else:
                    ax[0].plot(soc,'{}-'.format(c_color))
                    if self.show_fictive_soc:
                        ax[0].plot(soc_fictive, '{}--'.format(
                            'r'))
                S_c_max.append(max(np.max(soc),self.S_n_max[n]))    
            elif self.n_type[n] == 'P' and self.show_producers:
                soc_fictive = np.zeros(self.t_steps)
                soc_fictive[0] = self.s_nt[n,0]
                for t in range(self.t_steps):
                    if t > 0 and self.show_fictive_soc:
                        soc_fictive[t] = (soc_fictive[t-1] + 
                                          self.E_nt[n,t-1])
                    soc[t] = self.s_nt[n,t] #/ self.S_n_max[n]
                    prod[t] += self.E_nt[n,t]
                if len(S_p_max) == 0:
                    ax[1].plot(soc, '{}-'.format(
                                        self.n_color['P']), 
                                        label='producers: s_nt')
                    if self.show_fictive_soc:
                        ax[1].plot(soc_fictive, '{}--'.format(
                                self.n_color['P']),
                                label=('s_nt without' + 
                                        '\ncharging vehicles'))  
                else:
                    ax[1].plot(soc,'{}-'.format(self.n_color['P']))
                    if self.show_fictive_soc:
                        ax[1].plot(soc_fictive, '{}--'.format(
                            self.n_color['P']))
                if self.show_fictive_soc:
                    soc_p_max = max(np.max(soc), np.max(soc_fictive))
                else:
                    soc_p_max = np.max(soc)
                S_p_max.append(max(soc_p_max,self.S_n_max[n]))

                
        

        cons = cons[:-1]#/np.max(cons)
        prod = prod[:-1]#/np.max(prod)
        x_start = np.arange(self.t_steps-1)
        x_stop = np.arange(1,self.t_steps)
        
        x_array = np.arange(1,self.t_steps-1)
        y_start_c = cons[:-1]
        y_stop_c = cons[1:]
        y_start_p = prod[:-1]
        y_stop_p = prod[1:]

        
        if self.cummulative_E_nt:
            ax_01 = ax[0].twinx()
            ax_01.hlines(cons, x_start, x_stop, c_color_2, 
                        'dashed', 
                        label='Total consumption\n(cumul. per h)')
            ax_01.vlines(x_array,y_start_c,y_stop_c,c_color_2, 
                        'dashed')
            if self.show_producers:
                ax_11 = ax[1].twinx()
                ax_11.hlines(prod,x_start,x_stop,p_color_2, 
                            'dashed', 
                            label='Total production\n(cumul. per h)')
                ax_11.vlines(x_array,y_start_p,y_stop_p,p_color_2, 
                            'dashed')

        # Plot 1: consumers
        ax[0].spines['left'].set_color(c_color)
        ax[0].yaxis.label.set_color(c_color)
        ax[0].tick_params(axis='y', colors=c_color)
        ax[0].set_xticks(np.arange(0, self.t_steps, step=1))
        ax[0].set_xticklabels(self.x_tick_str[::1])
        ax[0].set_title('Energieversorgung Konsumenten', fontsize=25)
        ax[0].set_ylim([-1.5*max(S_c_max),1.1*max(S_c_max)])
        ax[0].set_ylabel('(kWh)')
        leg_0 = ax[0].legend(loc='upper left')
        for text in leg_0.get_texts():
            text.set_color('k')
        ax[0].hlines(0, -1, self.t_steps+1, 'k', 
                    'dashed',)
        if self.cummulative_E_nt:
            ax_01.spines['right'].set_color(c_color_2)
            ax_01.yaxis.label.set_color(c_color_2)
            ax_01.tick_params(axis='y', colors=c_color_2)
            ax_01.set_ylim([-0.1*np.max(cons),1.1*np.max(cons)])
            ax_01.set_ylabel('(kWh)')
            leg_01 = ax_01.legend(loc='upper right')
            for text in leg_01.get_texts():
                text.set_color(c_color_2)

        
        # Plot 2: producers
        if self.show_producers:
            #ax[1].set_title('producer')
            ax[1].set_xticks(np.arange(0, self.t_steps))
            ax[1].set_xticklabels(self.x_tick_str)
            ax[1].spines['left'].set_color(p_color)
            ax[1].yaxis.label.set_color(p_color)
            ax[1].tick_params(axis='y', colors=p_color)
            ax[1].set_ylim([-0.1*max(S_p_max),1.1*max(S_p_max)])
            ax[1].set_ylabel('(kWh)')
            leg_1 = ax[1].legend(loc='upper left')
            for text in leg_1.get_texts():
                text.set_color(p_color)
            if self.cummulative_E_nt:
                ax_11.spines['right'].set_color(p_color_2)
                ax_11.yaxis.label.set_color(p_color_2)
                ax_11.tick_params(axis='y', colors=p_color_2)
                ax_11.set_ylim([-0.1*np.max(prod),1.1*np.max(prod)])
                ax_11.set_ylabel('(kWh)')
                leg_11 = ax_11.legend(loc='upper right')
                for text in leg_11.get_texts():
                    text.set_color(p_color_2)



        # Plot 3: vehicles
        max_soc = []
        for v in self.vehicles:
            array = np.zeros(self.t_steps)
            for t in range(self.t_steps):
                array[t] = self.s_vt[v,t] / self.S_v_max[v]
            if self.label_vehicles:
                ax[v_ax].plot(array, '--', label=self.v_names[v])
            else:
                if len(max_soc) == 0:
                    ax[v_ax].plot(array,'g-', label='Ladezustand')
                else:
                    ax[v_ax].plot(array,'g-')
            max_soc.append(np.max(array))

        y_max = max(max_soc)
        ax[v_ax].set_xticks(np.arange(0, self.t_steps))
        ax[v_ax].set_xticklabels(self.x_tick_str)
        ax[v_ax].set_title('Fahrzeuge für Energietransport', fontsize=25)
        ax[v_ax].set_ylim([-0.3*y_max,1.1*y_max])
        #ax[v_ax].set_ylabel('SOC')
        ax[v_ax].yaxis.set_major_formatter(
                    mtick.PercentFormatter(1.0))

        ax[v_ax].legend(loc='upper left')
        ax[v_ax].hlines(0, -1, self.t_steps+1, 'k', 
                    'dashed',)
        #plt.draw()     
        return fig


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        description='Visualize a specific file.')
    parser.add_argument('-n', '--name', 
                        dest='name', required=True, 
                        help=('name / time string of files' +
                              ' to be visualized'))
    args = parser.parse_args()
    '''
    base = os.path.abspath(args.name)
    txt_path = base + '.txt'
    while not os.path.exists(txt_path):
        print(f'Warning: {txt_path} does not exist',)
        if os.path.isdir(base):
            print('\nSubfolders:')
            subfolders = os.walk(base)[0][1]
            print(subfolders)
            exit()
            for item in os.walk(base):
                print(item)
                print(os.path.basename(item[0]))
            print('\nTextfiles:')
            for item in glob.glob('*.txt'):
                print(item)
            x = input('\nChoose subdirectory or file_name:')
        else:
            exit(f'{base} is not valid')
        base = os.path.join(base, x)
        txt_path = base + '.txt'
    exit()
    '''

    txt_path = args.name + '.txt'
    p_path = args.name + '.p'
    if os.path.exists(txt_path):
        pass
    else:
        exit('{} does not exist'.format(txt_path))
    if os.path.exists(p_path):
        pass
    else:
        exit('{} does not exist'.format(p_path))
    
    with open(p_path,'rb') as pickle_file:
        model_dict = pickle.load(pickle_file)
    my_vis = visuals(model_dict, txt_path)
    my_vis.time_series_plots()
    my_vis.interactive_plot()
    plt.show()

    