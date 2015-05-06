# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#
#2D engraver library


class Table_State(object):
    """Used by Interpreter to retain state information."""
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        self.laser = False
        
class Interpreter(object):
    """Used to convert strings to x,y tuples, saves state to allow single axis updates."""
    def __init__(self, multiplier):
        self.multiplier = multiplier
        self.state = Table_State(0,0)
        
    def decode_string_line(self, line, line_num):
        """Parses x,y tuple from string containing one or pair of (xn or Xn and yn or Yn). E.g. 'x0 Y42'."""
        if line == '' or line[0] == '#':
            return False
        line = line.split()
        positions = [None, None]
        for n in range(0, len(line)):
            num = int(line[n][1:])*self.multiplier
            if 0 > num > 3328:
                raise Exception("Invalid range on line: ", line_num)
                break
            if line[n][0] in ('x', 'X'):
                positions[0] = num
                self.state.x = num
            elif line[n][0] in ('y', 'Y'):
                positions[1] = num
                self.state.y = num
        if positions[0] == None:
            positions[0] = self.state.x
        if positions[1] == None:
            positions[1] = self.state.y
        return positions
        
    def estimator(script, multiplier=1):
        """Calculates properties of a given G-code script."""
        max_x = 0
        max_y = 0
        min_x = 0
        min_y = 0
        line_num=0
        steps = 0
        points = 0
        x_0 = 0
        y_0 = 0
        interp = Interpreter(multiplier)
        for line in script:
            temp = interp.decode_string_line(line, line_num)
            line_num+=1
            if temp == False:
                break
            x_1 = temp[0]
            y_1 = temp[1]
            if x_1 < min_x:
                min_x = x_1
            elif x_1 > max_x:
                max_x = x_1
            if y_1 < min_y:
                min_y = y_1
            elif y_1 > max_y:
                max_y = y_1
            deltax = abs(x_1 - x_0)
            deltay = abs(y_1 - y_0)
            if deltax > deltay:
                steps += deltax
            else:
                steps += deltay
            x_0 = x_1
            y_0 = y_1
            points += 1
        return points, steps, (max_x-min_x+1, max_y-min_y+1)
#

import platform
import glob
import serial
import struct
class Serial_Manager(object):
    """Coordinates communication with Thomas Wilson's 2D laser engraver firmware."""
    def __init__(self, serial_port=False):
        if serial_port:
            self.connect(serial_port)
    
    def connect(self, serial_port):
        self.ser = serial.Serial(serial_port, 9600, timeout=5)
        
    def list_serial_ports():
        """Lists available serial ports. Praise Stack-Overflow."""
        system_name = platform.system()
        if system_name == "Windows":
            # Scan for available ports.
            available = []
            for i in range(0, 256):
                try:
                    s = serial.Serial(i)
                    available.append(i+1)
                    s.close()
                except serial.SerialException:
                    pass
            return available
        elif system_name == "Darwin":
            # Mac
            return glob.glob('/dev/tty*') + glob.glob('/dev/cu*')
        else:
            # Assume Linux or something else
            return  glob.glob('/dev/ttyUSB*')# + glob.glob('/dev/ttyS*')
        
    def close_connection(self):
        """Closes serial port connection."""
        self.ser.close()
    
    def int_to_3hex(self, value):
        """2D laser engraver firmware takes 3 char hex values."""
        hex_num = hex(value)[2:]
        while len(hex_num) < 3:
            hex_num = '0' + hex_num
        return hex_num
        
    def send_positions(self, positions):
        """Transmits given x,y cord to the 2D laser engraver."""
        if positions == False:
            return
        sent=''
        hex = self.int_to_3hex(positions[0])
        sent+='x'
        self.ser.write(struct.pack('B', ord('x')))
        for char in hex:
            sent+=char
            self.ser.write(struct.pack('B', ord(char)))
        hex = self.int_to_3hex(positions[1])
        sent+='y'
        self.ser.write(struct.pack('B', ord('y')))
        for char in hex:
            sent+=char
            self.ser.write(struct.pack('B', ord(char)))
        #print(sent)  # Debug string
        self.ser.flushInput()
        if self.ser.readline() == b'OK\r\n':
            self.ser.flushInput()
            return True
        else:
            return False
#

from PIL import Image
class Pic_To_Gcode(object):
    """Collection of functions for conditioning and converting PIL Image's into G-code."""
    def convert_file(self, filename, size):
        """Loads image at filename and returns G-code string containing all x,y cords."""
        im = Image.open(filename).convert('RGBA')
        im = self.condition_image(im, size)
        im.save(".\pictures\B&W - " + filename.split('\\')[-1])
        return self.convert_PIL_image(im)
    
    def condition_image(self, image, size):
        """Conditions image for further processing."""
        image.thumbnail(size, Image.ANTIALIAS)
        #White all transparent areas
        pixel_map = image.load()
        for x in range(0, image.size[0]):
            for y in range(0, image.size[1]):
                if pixel_map[x, y][3] < 10:
                    image.putpixel((x, y), (255, 255, 255, 0))
        return image.convert('1')
    
    def image_size(self, filename):
        """Finds size of image at filename."""
        im = Image.open(filename)
        return im.size
    
    def convert_file_save_in_folder(self, filename, size, save_dir):
        """Load, convert and save G-code from image file."""
        g_code = self.convert_file(filename, size)
        g_code_file_name = save_dir+"G code - " + filename.split('\\')[-1].split('.')[0] + ".txt"
        g_code_file_handle = open(g_code_file_name, 'w')
        g_code_file_handle.write(g_code)
        g_code_file_handle.close()
    
    def convert_PIL_image(self, im):
        """Returns a G-code string containing all x,y cords."""
        #Record pixel locations
        pixel_map = im.load()
        script = []
        for y in range(0, im.size[1]):
            y_val = im.size[1] - y - 1
            if y%2==0:
                for x in range(0, im.size[0]):
                    if pixel_map[x, y_val] < 10:
                        script.append([x, y])
            else:
                for x in range(im.size[0]-1, -1, -1):
                    if pixel_map[x, y_val] < 10:
                        script.append([x, y])
        #Find minimum values
        min_x = im.size[0]
        min_y = im.size[1]
        for cords in script:
            x, y = cords
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
        #Move all values by minimum
        for cords in script:
            cords[0] = cords[0] - min_x
            cords[1] = cords[1] - min_y
        #Create text representation
        g_code = ""
        for cords in script:
            g_code += 'x'+str(cords[0])+" y"+str(cords[1])+'\n'
        return g_code
    