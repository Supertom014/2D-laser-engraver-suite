# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#
#script_from_file_GUI.py


import tkinter
from tkinter import ttk, filedialog, messagebox
import time
from os.path import expanduser
from PIL import Image, ImageTk
from engraver_lib import Interpreter, Serial_Manager, Pic_To_Gcode
from threading import Thread
import queue
import multiprocessing

class Help_Window(tkinter.Toplevel):
    """Pop-up that displays information from .\\resource\\Help file.txt."""
    def __init__(self, root):
        super().__init__(root)
        tkinter.Label(self, text="Help file:").grid(column=0, row=0, sticky='w')
        try:
            help_file = open(".\\resource\\Help file.txt")
            help_text = help_file.read()
        except:
            help_text = ".\\resource\\Help file.txt not found"
        text_box = tkinter.Text(self, wrap="word")
        text_box.insert("1.0", help_text)
        text_box.grid(column=0, row=1, sticky='w')
        text_box.config(state="disabled")
        self.attributes("-topmost", 1)
        self.title("Help")
#
class Convert_Window(tkinter.Toplevel):
    """Pop-up that explains and asks for x,y max size values."""
    def __init__(self, root, filename):
        super().__init__(root)
        tkinter.Label(self, text="Enter maximum size in X or Y\nAspect ratio will be kept:").grid(column=0, row=0, sticky='w')
        ptg = Pic_To_Gcode()
        self.filename = filename
        size = ptg.image_size(filename)
        self.x_size_tkvar = tkinter.StringVar()
        self.x_size_tkvar.set(size[0])
        self.y_size_tkvar = tkinter.StringVar()
        self.y_size_tkvar.set(size[1])
        tkinter.Label(self, text="Size X: ").grid(column=0, row=1, sticky='w')
        tkinter.Entry(self, textvariable=self.x_size_tkvar).grid(column=1, row=1, sticky='w')
        tkinter.Label(self, text="Size Y: ").grid(column=0, row=2, sticky='w')
        tkinter.Entry(self, textvariable=self.y_size_tkvar).grid(column=1, row=2, sticky='w')
        tkinter.Button(self, text="Convert", command=self.__convert_btn).grid(column=0, row=3, sticky='w')
        self.attributes("-topmost", 1)
        self.title("Size")
        
    def __convert_btn(self):
        """Instantiates the file converter and writes G-code file into .\\g code ."""
        size = int(self.x_size_tkvar.get()), int(self.y_size_tkvar.get())
        try:
            ptg = Pic_To_Gcode()
            g_code = ptg.convert_file(self.filename, size)
            messagebox.showinfo("Complete", "Conversion complete\nG-code file saved in .\\g code")
            self.destroy()
        except:
            messagebox.showinfo("Error", "Conversion failed\nUnsupported file type or options.")
        
        g_code_file_name = ".\\g code\\G code - " + self.filename.split('\\')[-1].split('.')[0] + ".txt"
        g_code_file_handle = open(g_code_file_name, 'w')
        g_code_file_handle.write(g_code)
        g_code_file_handle.close()
#
class Multi_Select_Window(tkinter.Toplevel):
    """Pop-up to select a movement multiplier."""
    def __init__(self, root, multiplier):
        super().__init__(root)
        self.multiplier = multiplier
        tkinter.Label(self, text="Select expand multiplier\nChanges the spacing of points.").grid(column=0, row=0, sticky='w')
        self.multiplier_tkvar = tkinter.StringVar()
        self.multiplier_tkvar.set(multiplier)
        tkinter.Label(self, text="Multiplier: ").grid(column=0, row=1, sticky='w')
        tkinter.Entry(self, textvariable=self.multiplier_tkvar).grid(column=1, row=1, sticky='w')
        tkinter.Button(self, text="Select", command=self.__select_btn).grid(column=0, row=3, sticky='w')
        self.attributes("-topmost", 1)
        self.focus_set()
        #self.transient(perant)
        self.title("Multiplier")
        self.wait_window(self)
        
    def __select_btn(self):
        """Saves multiplier value to self.multiplier."""
        self.multiplier = int(self.multiplier_tkvar.get())
        self.destroy()
#
class Parse_Com_Thread(Thread):
    """Thread that handles parsing the G-code script and sending commands through serial."""
    def __init__(self, out_queue, in_queue, script, port=0, multiplier=1):
        super().__init__()
        self.out_queue = out_queue
        self.in_queue = in_queue
        self.port = port
        self.script = script
        self.interp = Interpreter(multiplier)
        self.serial_man = Serial_Manager()
        if port != 0:
            self.serial_man.connect("//./COM" + port)
    
    def run(self):
        exit = False
        script_len = len(self.script)
        while True:
            line_num=1
            for line in self.script:
                x_y = self.interp.decode_string_line(line, line_num)
                if x_y == False:
                    exit = True
                    break
                if self.port != 0:
                    not_error = self.serial_man.send_positions(x_y)
                else:
                    time.sleep(0.1)
                    not_error = True
                x_y = int(x_y[0]/self.interp.multiplier), int(x_y[1]/self.interp.multiplier)
                self.in_queue.put((not_error, line_num/script_len*100, x_y))
                if line_num == script_len:
                    exit = True
                    break
                line_num+=1
                try:
                    out = self.out_queue.get(False)
                    if out == "exit":
                        exit = True
                        break
                except queue.Empty:
                    pass
            if exit:
                break
#
class Instant_Preview(tkinter.Frame):
    """Frame, housing an image built from a G-code script."""
    def __init__(self, root, size):
        super().__init__(root)
        tkinter.Label(self, text="Preview").pack(side="top")
        self.label_pic = tkinter.Label(self)
        self.im = Image.new("L", (size[0], size[1]), "white")
        self.photo = ImageTk.PhotoImage(self.im)
        self.label_pic.configure(image=self.photo)
        self.label_pic.pack(side="top")
        
    def load_gcode(self, script, size):
        """Creates new image and populates with pixels from given G-code script"""
        self.script = script
        self.im = Image.new("L", (size[0], size[1]), "white")
        self.im_pixmap = self.im.load()
        self.photo = ImageTk.PhotoImage(self.im)
        self.label_pic.configure(image=self.photo)
        self.__populate_image()
    
    def __populate_image(self):
        """Populates the blank image with pixels from G-code script"""
        interp = Interpreter(1)
        line_num = 0
        for line in self.script:
            x_y = interp.decode_string_line(line, line_num)
            if x_y != False:
                x, y = x_y
                self.im_pixmap[x, y] = 0
            line_num += 1
        
        self.photo = ImageTk.PhotoImage(self.im.transpose(Image.FLIP_TOP_BOTTOM))
        self.label_pic.image = self.photo
        self.label_pic.configure(image=self.photo)
        self.label_pic.update()
#
class Progressive_Preview(tkinter.Frame):
    """Frame, housing an image progressively built from add_point() calls."""
    def __init__(self, root, size):
        super().__init__(root)
        tkinter.Label(self, text="Instant View").pack(side="top")
        self.im = Image.new("L", (size[0], size[1]), "white")
        self.photo = ImageTk.PhotoImage(self.im)
        self.label_pic = tkinter.Label(self)
        self.label_pic.configure(image=self.photo)
        self.label_pic.pack(side="top")
        self.size = size
    
    def load_gcode(self, script, size=None):
        """Creates new blank image."""
        if size == None:
            size = self.size
        self.size = size
        self.im = Image.new("L", (size[0], size[1]), "white")
        self.im_pixmap = self.im.load()
        self.photo = ImageTk.PhotoImage(self.im)
        self.label_pic.configure(image=self.photo)
    
    def add_point(self, x_y_cords):
        """Adds a black pixel at the x,y point specified."""
        if x_y_cords != False:
            x, y = x_y_cords
            self.im_pixmap[x, y] = 0
        
        self.photo = ImageTk.PhotoImage(self.im.transpose(Image.FLIP_TOP_BOTTOM))
        self.label_pic.image = self.photo
        self.label_pic.configure(image=self.photo)
        self.label_pic.update()
        
    def reset_picture(self):
        """Alternative to create new blank image, Using same size as previous."""
        self.im = Image.new("L", (self.size[0], self.size[1]), "white")
        self.im_pixmap = self.im.load()
        self.photo = ImageTk.PhotoImage(self.im)
        self.label_pic.configure(image=self.photo)
#
class Info_Running_Frame(tkinter.Frame):
    """Information frame displayed at the bottom of the main window. Shows percent and time estimation."""
    def __init__(self, root):
        super().__init__(root)
        tkinter.Label(self, text="Percent complete: ").pack(side="left")
        self.percent_done_val = tkinter.StringVar()
        self.percent_done_val.set("0%")
        tkinter.Label(self, textvariable=self.percent_done_val).pack(side="left")
        tkinter.Label(self, text="Time estimate: ").pack(side="left")
        self.time_estimation = tkinter.StringVar()
        self.time_estimation.set("00:00:00")
        tkinter.Label(self, textvariable=self.time_estimation).pack(side="left")
        
#
class Info_Eval_Frame(tkinter.Frame):
    """Information frame displayed at the bottom of the main window. Shows size and time estimations."""
    def __init__(self, root):
        super().__init__(root)
        tkinter.Label(self, text="Time estimate: ").pack(side="left")
        self.time_estimation = tkinter.StringVar()
        self.time_estimation.set("00:00:00")
        tkinter.Label(self, textvariable=self.time_estimation).pack(side="left")
        tkinter.Label(self, text="Size estimate: ").pack(side="left")
        self.size_estimation = tkinter.StringVar()
        self.size_estimation.set("0mm by 0mm")
        tkinter.Label(self, textvariable=self.size_estimation).pack(side="left")
        
#
class Window(tkinter.Frame):
    """Main application window."""
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.instant = Instant_Preview(self, (300, 300))
        self.instant.grid(column=0, row=0)
        self.progressive = Progressive_Preview(self, (300, 300))
        self.progressive.grid(column=1, row=0)
        self.info_eval_frame = Info_Eval_Frame(self)
        self.info_eval_frame.grid(column=0, row=1, columnspan=2, sticky='w')
        self.info_running_frame = Info_Running_Frame(self)
        self.__gen_menu()
        root.config(menu=self.menu)
        self.parse_com_handle = True
        self.multiplier = 1
        self.lase_time = 100
        self.exit = False
        self.script = []
        
    def __gen_menu(self):
        """Generates the main window menu."""
        self.menu = tkinter.Menu(self.root)
        #File menu
        submenu = tkinter.Menu(self.menu, tearoff=0)
        submenu.add_command(label = 'Open Gcode', command=self.__menu_open_gcode)
        #submenu.add_command(label = 'Save', command=self.save_file)
        #submenu.add_command(label = 'Save as...', command=self.save_as_file)
        submenu.add_separator()
        submenu.add_command(label = 'Quit', command=self.menu_quit)
        self.menu.add_cascade(label='File', menu=submenu)
        #Run menu
        self.submenu = tkinter.Menu(self.menu, tearoff=0)
        self.submenu.add_command(label = 'Run', command=self.__menu_run)
        self.submenu.entryconfig(0, state=tkinter.DISABLED)
        self.submenu.add_command(label = 'Reset', command=self.__menu___reset_system)
        self.submenu.entryconfig(1, state=tkinter.DISABLED)
        self.submenu.add_separator()
        self.submenu.add_command(label = 'Multiplier', command=self.__menu_select_multiplier)
        self.submenu.add_separator()
        self.serial_port = tkinter.IntVar()
        ports = Serial_Manager.list_serial_ports()
        if len(ports) < 2:
            self.submenu.add_command(label = 'No ports')
        for serial_port in ports:
            self.submenu.add_checkbutton(label = "COM: "+str(serial_port), variable=self.serial_port, onvalue=serial_port)
        self.menu.add_cascade(label='Run', menu=self.submenu)
        #Convert menu
        submenu = tkinter.Menu(self.menu, tearoff=0)
        submenu.add_command(label = 'Convert picture...', command=self.__menu_convert)
        self.menu.add_cascade(label='Conversion', menu=submenu)
        #Help menu
        submenu = tkinter.Menu(self.menu, tearoff=0)
        submenu.add_command(label = 'Help', command=self.__menu_help_window)
        self.menu.add_cascade(label='About', menu=submenu)
        
    def __menu_help_window(self):
        """Displays the help window by instantiating Help_Window."""
        Help_Window(self.root)
        
    def __menu_select_multiplier(self):
        """Displays the movement multiplier selection window by instantiating Multi_Select_Window. Updates UI information on window close."""
        #Get multiplier from dialogue
        x = Multi_Select_Window(self.root, self.multiplier)
        self.multiplier = x.multiplier
        #Estimate new UI values
        points, steps, size = Interpreter.estimator(self.script)
        time_ms = (points*(self.lase_time+12)+steps*self.multiplier)/1000
        min, sec = divmod(time_ms, 60)
        hour, min = divmod(min, 60)
        time_str = "%02d:%02d:%02d" % (hour, min, sec)
        #Set new UI values
        self.info_eval_frame.time_estimation.set(time_str)
        self.info_eval_frame.size_estimation.set(str(round(self.multiplier*size[0]*(0.15/8), 3))+"mm by "+str(round(self.multiplier*size[1]*(0.15/8), 3))+"mm")
        self.info_running_frame.time_estimation.set(time_str)
    
    def __menu_convert(self):
        """Show File dialogue then instantiate Convert_Window."""
        pic_folder = expanduser("~")+"\\Pictures"
        filename = filedialog.askopenfilename(initialdir=pic_folder).replace('/', '\\')
        if filename:
            Convert_Window(self.root, filename)
    
    def menu_quit(self):
        """Stop Parse_Com_Thread and periodic self.__check_queue() ."""
        self.exit = True
        self.out_queue.put("exit")
        self.root.destroy()
    
    def __menu_open_gcode(self):
        """Show File dialogue then parse file and update UI."""
        self.filename = filedialog.askopenfilename(defaultextension=".txt", initialdir=".\g code")
        if self.filename:
            #Open file with exception safeguards
            try:
                file = open(self.filename, 'r', encoding='utf-8')
                temp = file.read()
                file.close()
            except:
                messagebox.showinfo("Error", "Encoding error.\nFile->Open G-code\nIs for UTF-8 encoded G-code files")
                return
            #Split file into line by line script
            temp = temp.split('\n')
            self.script = []
            for line in temp:
                if len(line) >0 and line[0] != '#':
                    self.script.append(line)
            if len(self.script) < 2:
                return
            #Calculate UI values
            points, steps, size = Interpreter.estimator(self.script)
            time_ms = (points*(self.lase_time+12)+steps*self.multiplier)/1000
            min, sec = divmod(time_ms, 60)
            hour, min = divmod(min, 60)
            time_str = "%02d:%02d:%02d" % (hour, min, sec)
            #Set UI values, visibility and states
            self.info_eval_frame.time_estimation.set(time_str)
            self.info_eval_frame.size_estimation.set(str(round(self.multiplier*size[0]*(0.15/8), 3))+"mm by "+str(round(self.multiplier*size[1]*(0.15/8), 3))+"mm")
            self.info_eval_frame.grid(column=0, row=1, columnspan=2, sticky='w')
            self.info_running_frame.time_estimation.set(time_str)
            self.info_running_frame.grid_remove()
            self.instant.load_gcode(self.script, size)
            self.progressive.load_gcode(self.script, size)
            self.submenu.entryconfig(0, state=tkinter.NORMAL)
            #Change window size if too small
            if int(self.root.geometry().split('+')[0].split('x')[0]) < 400:
                self.root.geometry('{}x{}'.format(400, int(self.root.geometry().split('+')[0].split('x')[1])))
    
    def __menu_run(self):
        """Launch Parse_Com_Thread to begin executing loaded G-code script."""
        self.exit = False
        if self.parse_com_handle or (not self.parse_com_handle.is_alive()):
            self.out_queue = queue.Queue()
            self.in_queue = queue.Queue()
            self.parse_com_handle = Parse_Com_Thread(self.out_queue, self.in_queue, self.script, self.serial_port.get(), self.multiplier)
            self.parse_com_handle.deamon = True
            self.parse_com_handle.start()
            #Swap info frame
            self.info_eval_frame.grid_remove()
            self.info_running_frame.grid(column=0, row=1, columnspan=2, sticky='w')
            #Change menu
            self.submenu.entryconfig(1, state=tkinter.NORMAL)
            #Begin updating UI
            self.__check_queue()
    
    def __menu___reset_system(self):
        """Wrapper function to call reset functions."""
        self.__reset_system()
        self.__reset_UI()
    
    def __reset_UI(self):
        """Resets UI components: changes visibility of information frames and button states."""
        #Swap info frame
        self.info_running_frame.grid_remove()
        self.info_eval_frame.grid(column=0, row=1, columnspan=2, sticky='w')
        #Change menu
        self.submenu.entryconfig(1, state=tkinter.DISABLED)
        #Change progressive view
        self.progressive.reset_picture()
        #Stop UI queue checks
        self.exit = True
        
    def __reset_system(self):
        """Resets non UI systems: Exits Parse_Com_Thread."""
        self.out_queue.put("exit")
            
    def __check_queue(self):
        """Checks incoming queue to UI. Updates Info_Running_Frame percent and adds points to Progressive_Preview."""
        if not self.exit:
            try:
                not_error, percent_done, x_y = self.in_queue.get(False)
                self.progressive.add_point(x_y)
                self.info_running_frame.percent_done_val.set(str(round(percent_done, 3))+'%')
            except queue.Empty:
                pass
            self.root.after(100, self.__check_queue)
#


if __name__=="__main__":
    multiprocessing.freeze_support()
    root = tkinter.Tk()
    x = Window(root)
    x.pack()
    root.title("2D Laser engraver")
    root.iconbitmap(default=r"resource/icon.ico")
    root.protocol('WM_DELETE_WINDOW', x.menu_quit)
    root.resizable(width=False, height=False)
    root.mainloop()
    raise SystemExit