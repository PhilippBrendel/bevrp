import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import PySimpleGUI as sg
import matplotlib
import os
from visualizers import visuals
import pickle
import argparse

matplotlib.use("TkAgg")


class my_gui():
    def __init__(self, default_dir):
        self.curr_IP = None
        self.curr_TSP = None
        # LAYOUT
        file_col = [[sg.Text("Result directory:")], 
                    [sg.In(size=(25, 1), enable_events=True, key='FOLDER'), sg.FolderBrowse(),],
                    [sg.Text('Choose your result file:')],
                    [sg.Listbox(values=[], enable_events=True, size=(32, 10), key='FILE_LIST')]
                    ]

        # INTERACTIVE PLOT COLUMN
        ip_col = [[sg.Frame(layout=[[sg.Checkbox('Show Map', enable_events=True, default=False,
                                                 key='IP_SHOW_MAP')],
                                    [sg.Text('X-axis --> MIN:'), sg.InputText('', size=(6,1), 
                                                                              key='IP_X_MIN'),
                                     sg.Text('Max: '), sg.InputText('', size=(6,1), key='IP_X_MAX')],
                                    [sg.Text('Y-axis --> MIN:'), sg.InputText('', size=(6,1),
                                                                              key='IP_Y_MIN'),
                                     sg.Text('Max: '), sg.InputText('', size=(6,1), key='IP_Y_MAX')],
                                    [sg.Button("Apply Limits", enable_events=True, key='IP_APPLY_LIM')]], 
                            title='Options', title_color='black', relief=sg.RELIEF_SUNKEN,
                            tooltip='Use these to set flags')],
                  [sg.Text('Interactive Plot', justification='center')],
                  [sg.Canvas(key="IP")],
                  [sg.Button("PREVIOUS", key='IP_PREVIOUS'), sg.Button("NEXT", key='IP_NEXT')]]

        # TIME-SERIES-PLOT COLUMN
        tsp_col = [[sg.Frame(layout=[[sg.Checkbox('Show Producer', enable_events=True,
                                                  default=True, key='TSP_SHOW_PROD'), 
                                      sg.Checkbox('Label Vehicles', enable_events=True,
                                                  default=False, key='TSP_LABEL_V')],
                                     [sg.Checkbox('Show fictive SOC', enable_events=True,
                                                  default=False, key='TSP_SHOW_FICTIVE'),
                                      sg.Checkbox('Show cumm. Cons./Prod.', enable_events=True,
                                                  default=False, key='TSP_SHOW_E_NT')],
                                      [sg.Checkbox('Show Legends', enable_events=True,
                                                  default=True, key='TSP_SHOW_LEGENDS')],], 
                             title='Options', title_color='black', relief=sg.RELIEF_SUNKEN,
                             tooltip='Use these to set flags')],
                    [sg.Text('Time-Series Plot', justification='center')],
                    [sg.Canvas(key='TSP')]]

        # Connect columns
        layout = [[sg.Text("My SmartKrit")],
                  [sg.Column(file_col), sg.VSeperator(), sg.Column(ip_col),
                   sg.VSeperator(), sg.Column(tsp_col)],
                  [sg.Button("EXIT")]]

        # Create window with layout
        self.window = sg.Window("SmartKrit - GUI", layout, location=(0, 0), finalize=True,
                                element_justification="center", font="Helvetica 18",)
        # Default Folder setting
        self.window['FOLDER'].update(default_dir)
        all_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(default_dir) for f in fn]
        rel_path = [os.path.relpath(f, default_dir) for f in all_files]
        fnames = [f for f in rel_path if os.path.isfile(os.path.join(default_dir, f))
                        and f.lower().endswith((".p"))]
        self.window['FILE_LIST'].update(fnames)

    def init_figures(self, filename):
        '''
        '''
        with open(filename,'rb') as pickle_file:
            model_dict = pickle.load(pickle_file)
            
        txt_path = os.path.splitext(filename)[0] + '.txt'
        self.visuals = visuals(model_dict, txt_path)
        self.visuals.show_fictive_soc = False
        self.visuals.show_producers = True
        self.visuals.label_vehicles = False
        self.visuals.cummulative_E_nt = False
        self.ip_fig = self.visuals.interactive_plot(from_gui=True)
        self.tsp_fig = self.visuals.time_series_plots()
        # write values
        self.window['IP_X_MIN'].update('{:.3f}'.format(self.visuals.xlim[0]))
        self.window['IP_X_MAX'].update('{:.3f}'.format(self.visuals.xlim[1]))
        self.window['IP_Y_MIN'].update('{:.3f}'.format(self.visuals.ylim[0]))
        self.window['IP_Y_MAX'].update('{:.3f}'.format(self.visuals.ylim[1]))

    def draw_ip_fig(self):
        '''
        Uses the currently set Interactive Plot figure
        and draws it in the GUI
        '''
        if self.curr_IP is not None:
            self.curr_IP.get_tk_widget().forget()
        self.curr_IP = FigureCanvasTkAgg(self.ip_fig, self.window['IP'].TKCanvas)
        # reconnect canvas via mpl_connect
        self.curr_IP.mpl_connect("motion_notify_event", self.visuals.hover)
        self.curr_IP.mpl_connect("key_press_event", self.visuals.press)
        self.curr_IP.draw()
        self.curr_IP.get_tk_widget().pack(side="top", fill="both", expand=1)

    def draw_tsp_fig(self):
        '''
        Uses the currently set Time-Series Plot figure
        and draws it in the GUI
        '''
        if self.curr_TSP is not None:
            self.curr_TSP.get_tk_widget().forget()
        self.curr_TSP = FigureCanvasTkAgg(self.tsp_fig, self.window['TSP'].TKCanvas)
        self.curr_TSP.draw()
        self.curr_TSP.get_tk_widget().pack(side="top", fill="both", expand=1)

    def run(self):
        while True:
            event, values = self.window.read()
            print(event)
            #print(values['IP_SHOW_MAP'])
            if event == "EXIT" or event == sg.WIN_CLOSED:
                break
            if event == 'FOLDER': # folder was chosen
                folder = values['FOLDER']
                all_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(folder) for f in fn]
                rel_path = [os.path.relpath(f, folder) for f in all_files]
                fnames = [f for f in rel_path if os.path.isfile(os.path.join(folder, f))
                        and f.lower().endswith((".p"))]
                self.window['FILE_LIST'].update(fnames)
            elif event == 'FILE_LIST':  # file was chosen from the listbox
                try:
                    filename = os.path.join(values['FOLDER'], values['FILE_LIST'][0])
                    self.init_figures(filename)
                    self.draw_ip_fig()
                    self.draw_tsp_fig()
                except:
                    pass
            elif event.startswith('IP'):
                self.visuals.ax.clear()
                if event == 'IP_PREVIOUS':
                    if self.visuals.t_ind >= 1:
                        self.visuals.t_ind -= 1
                elif event == 'IP_NEXT':
                    if self.visuals.t_ind  < self.visuals.t_steps - 1:
                        self.visuals.t_ind += 1
                elif event == 'IP_SHOW_MAP':
                    self.visuals.show_map = values['IP_SHOW_MAP']
                elif event == 'IP_APPLY_LIM':
                    update = True
                    try:
                        xlim = [float(values['IP_X_MIN']),
                                float(values['IP_X_MAX'])]
                        ylim = [float(values['IP_Y_MIN']),
                                float(values['IP_Y_MAX'])]
                    except ValueError:
                        print('whaaat')
                        update=False
                    if update:
                        self.visuals.xlim = xlim
                        self.visuals.ylim = ylim
                # Draw IP FIG
                self.ip_fig = self.visuals.update_plot(from_gui=True)
                self.draw_ip_fig()
            elif event.startswith('TSP'):
                if event == 'TSP_SHOW_FICTIVE':
                    self.visuals.show_fictive_soc = values['TSP_SHOW_FICTIVE']
                elif event == 'TSP_SHOW_PROD':
                    self.visuals.show_producers = values['TSP_SHOW_PROD']
                elif event == 'TSP_LABEL_V':
                    self.visuals.label_vehicles = values['TSP_LABEL_V']
                elif event == 'TSP_SHOW_E_NT':
                    self.visuals.cummulative_E_nt = values['TSP_SHOW_E_NT']
                elif event == 'TSP_SHOW_LEGENDS':
                    self.visuals.show_legends = values['TSP_SHOW_LEGENDS']
                # Draw TSP fig    
                self.tsp_fig = self.visuals.time_series_plots()
                self.draw_tsp_fig()

        self.window.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        description='Visualize a specific file.')
    parser.add_argument('-d', '--directory', 
                        dest='dir', default='D:/projects/MA_YRC/bevrp/showroom/obj0', 
                        help='Default result directory')
    args = parser.parse_args()
    gui = my_gui(args.dir)
    gui.run()