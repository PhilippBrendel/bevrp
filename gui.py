import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import PySimpleGUI as sg
import matplotlib
import os
from visualizers import visuals
import pickle

matplotlib.use("TkAgg")


class my_gui():
    def __init__(self):
        self.curr_IP = None
        self.curr_TSP = None
        # LAYOUT
        file_col = [[sg.Text("Result directory:")], 
                    [sg.In(size=(25, 1), enable_events=True, key='FOLDER'), sg.FolderBrowse(),],
                    [sg.Text('Choose your result file:')],
                    [sg.Listbox(values=[], enable_events=True, size=(32, 10), key='FILE_LIST')]
                    ]

        ip_col = [[sg.Text('Interactive Plot', justification='center')],
                  [sg.Canvas(key="IP")],
                  [sg.Button("PREVIOUS"), sg.Button("NEXT")]]

        tsp_col = [[sg.Text('Time-Series Plot', justification='center')],
                     [sg.Canvas(key='TSP')]]

        layout = [[sg.Text("My SmartKrit")],
                  [sg.Column(file_col), sg.VSeperator(), sg.Column(ip_col),
                   sg.VSeperator(), sg.Column(tsp_col)],
                  [sg.Button("EXIT")]]

        # Create window with layout
        self.window = sg.Window("SmartKrit - GUI", layout, location=(0, 0), finalize=True,
                                element_justification="center", font="Helvetica 18",)
        self.run()

    def init_figures(self, filename):
        '''
        '''
        with open(filename,'rb') as pickle_file:
            model_dict = pickle.load(pickle_file)
            
        txt_path = os.path.splitext(filename)[0] + '.txt'
        self.visuals = visuals(model_dict, txt_path)
        self.ip_fig = self.visuals.interactive_plot(from_gui=True)
        self.tsp_fig = self.visuals.time_series_plots()

    def draw_ip_fig(self):
        '''
        Uses the currently set Interactive Plot figure
        and draws it in the GUI
        '''
        if self.curr_IP is not None:
            self.curr_IP.get_tk_widget().forget()
        self.curr_IP = FigureCanvasTkAgg(self.ip_fig, self.window['IP'].TKCanvas)
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
            if event == "EXIT" or event == sg.WIN_CLOSED:
                break
            if event == 'FOLDER': # folder was chosen
                folder = values['FOLDER']
                try:
                    file_list = os.listdir(folder)
                except:
                    file_list = []
                fnames = [f for f in file_list if os.path.isfile(os.path.join(folder, f))
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
            elif event == 'PREVIOUS':
                if self.visuals.t_ind >= 1:
                    self.visuals.ax.clear()
                    self.visuals.t_ind -= 1
                    self.ip_fig = self.visuals.update_plot(from_gui=True)
                    self.draw_ip_fig()
            elif event == 'NEXT':
                if self.visuals.t_ind  < self.visuals.t_steps - 1:
                    self.visuals.ax.clear()
                    self.visuals.t_ind += 1
                    self.ip_fig = self.visuals.update_plot(from_gui=True)
                    self.draw_ip_fig()
        self.window.close()

if __name__ == "__main__":
    gui = my_gui()