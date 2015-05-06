# Copyright (C) 2015  Thomas Wilson, email:supertwilson@Sourceforge.net
#
#    This module is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License Version 3 as published by
#    the Free Software Foundation see <http://www.gnu.org/licenses/>.
#


version_num = input('Version number X.Y.Z: ')
if version_num == '':
    version_num = 'Test build'

import os
import shutil
if os.path.isdir(r'.\dist\build'):
    shutil.rmtree(r'.\dist\build')

import sys
sys.argv.append('build')


from cx_Freeze import setup, Executable
build_exe_options = {"includes": ["serial"], "packages": ["serial"],
                    "include_files": ["resource", "pictures", "G code"],
                    "icon": r"resource\icon.ico",
                    "build_exe": r".\dist\build",
                    "compressed": True}
setup(
    name = "2D laser engraver",
    version = str(version_num),
    description = "2D laser engraver.",
    options = {"build_exe": build_exe_options},
    executables = [Executable("script_from_file_GUI.py", base = "Win32GUI", targetName="2D software.exe")])