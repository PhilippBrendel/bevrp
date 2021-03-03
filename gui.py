import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import PySimpleGUI as sg
import matplotlib
import os
from visualizers import visuals
import pickle

fig = matplotlib.figure.Figure(figsize=(5, 4), dpi=100)
t = np.arange(0, 3, .01)
fig.add_subplot(111).plot(t, 2 * np.sin(2 * np.pi * t))

matplotlib.use("TkAgg")

def update_canvas(canvas, filename):
    
    with open(filename,'rb') as pickle_file:
        model_dict = pickle.load(pickle_file)
        
    txt_path = os.path.splitext(filename)[0] + '.txt'
    my_vis = visuals(model_dict, txt_path)
    fig = my_vis.time_series_plots()

    figure_canvas_agg = FigureCanvasTkAgg(fig, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side="top", fill="both", expand=1)
    
    return figure_canvas_agg

def delete_figure_agg(figure_agg):
    figure_agg.get_tk_widget().forget()

# LAYOUT
file_list_column = [[sg.Text("Showroom"), 
                     sg.In(size=(25, 1), enable_events=True, key="-FOLDER-"),
                     sg.FolderBrowse(),],
                    [sg.Listbox(values=[], 
                                enable_events=True,
                                size=(40, 20),
                                key="-FILE LIST-")],
                    ]

canvas_column = [[sg.Text('Canvas', justification='center')],
                 [sg.Canvas(key="-CANVAS-")],
                 [sg.Button("PREVIOUS"), sg.Button("NEXT")]]

layout = [
    [sg.Text("My GUI")],
    [sg.Column(file_list_column), 
     sg.VSeperator(),
     sg.Column(canvas_column),
    ],
    [sg.Button("EXIT")],
]

# Create window with layout
window = sg.Window(
    "My GUI",
    layout,
    location=(0, 0),
    finalize=True,
    element_justification="center",
    font="Helvetica 18",
)


curr_agg = None

# Create an event loop
while True:
    event, values = window.read()
    # End program if user closes window or
    # presses the OK button
    
    if event == "EXIT" or event == sg.WIN_CLOSED:
        break
    if event == "-FOLDER-": # folder was chosen
        folder = values["-FOLDER-"]
        try:
            file_list = os.listdir(folder)
        except:
            file_list = []
        fnames = [f for f in file_list if os.path.isfile(os.path.join(folder, f))
                  and f.lower().endswith((".p"))]
        window["-FILE LIST-"].update(fnames)
    elif event == "-FILE LIST-":  # file was chosen from the listbox
        try:
            filename = os.path.join(
                values["-FOLDER-"], values["-FILE LIST-"][0]
            )
            # update canvas
            if curr_agg is not None:
                curr_agg.get_tk_widget().forget()
            curr_agg = update_canvas(window["-CANVAS-"].TKCanvas, filename)
        except:
            pass


window.close()