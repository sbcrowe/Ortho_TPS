#=====================================================================================
#=====================================IMPORTS=========================================
#=====================================================================================
#Dash modules
import dash
from dash import dash_table
from dash.dependencies import Input, Output, State
from dash import dcc
from dash import html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

#Plotly modules
import plotly.graph_objs as go
from plotly.graph_objs import *

#Windows modules
import webbrowser
from win32com.shell import shell
import win32ui, win32con
from shutil import copyfile
import sys
import os

#Math modules
import numpy as np
import copy
from skimage import measure
from skimage.draw import polygon

#Extra modules
import pandas as pd
import pydicom as dcm
import threading

#=====================================================================================
#======================CONSTANTS - TO BE CHANGED BY BT USERS==========================
#=====================================================================================

#DOSXYZnrc doesn't compile with total number of voxels greater than this value
#This value is displayed in the Region of Interest tab of OrthoPlan
max_DOSXYZ_voxels = 48200000 

#PHSP files will be recycled appropriately to match this number of histories
simulation_histories = 20000000 

#CT ramp used by RBWH
global HU, Den
HU = [-1024, -969, -701, -512, -91, -45, -3, 0, 24, 67, 196, 209, 422, 767, 1158, 3071]
Den = [0.001, 0.001, 0.3, 0.5, 0.943, 0.979, 1.00, 1.018, 1.053, 1.09, 1.14, 1.152, 1.335, 1.559, 1.823, 3.115]

#Default HU value ranges for different tissue presents in Tissue Segmentation tab of OrthoPlan
PEGS_HN = {'Name':['AIR', 'ADIPOSE', 'MUSCLE', 'CARTILLAGE', 'C4CART', 'C4NOCART', 'CRANIUM', 'MANDIBLE', 'LEAD', 'GOLD'],
            'MinCT':[-1005, -500, 0, 100, 250, 650, 900, 1000, 2000, 8500],
            'MaxCT':[-500, 0, 100, 250, 650, 900, 1000, 2000, 8500, 15000],
            'Colour':[
                        '#bdf2ff',
                        '#ffbf00',
                        '#ff0000',
                        '#ffdbfe',
                        '#ccabcb',
                        '#cfcfcf',
                        '#a1a1a1',
                        '#707070',
                        '#640082',
                        '#e3ce32',
                    ],
            'Number':[0,0,0,0,0,0,0,0,0,0]}

PEGS_T = {'Name':['AIR', 'LUNG', 'ADIPOSE', 'MUSCLE', 'STERNUM', 'VERTEBRAE', 'SCAPULA', 'RIBS10', 'CORTICAL', 'LEAD', 'GOLD'],
            'MinCT':[-1005, -900, -200, 0, 150, 400, 650, 900, 1300, 2000, 8500],
            'MaxCT':[-900, -200, 0, 150, 400, 650, 900, 1300, 2000, 8500, 15000],
            'Colour':[
                        '#bdf2ff',
                        '#9999FF',
                        '#ffbf00',
                        '#ff0000',
                        '#ccabcb',
                        '#f2f2f2',
                        '#cfcfcf',
                        '#a1a1a1',
                        '#707070',
                        '#640082',
                        '#e3ce32',
                    ],
            'Number':[0,0,0,0,0,0,0,0,0,0,0]}

PEGS_A = {'Name':['AIR', 'ADIPOSE', 'MARROW', 'MUSCLE', 'HUMERUS_HEAD', 'HUMERUS_SHAFT', 'FEMUR_SHAFT', 'LEAD', 'GOLD'],
            'MinCT':[-1005, -500, -80, 0, 250, 700, 1500, 2000, 8500],
            'MaxCT':[-500, -80, 0, 250, 700, 1500, 2000, 8500, 15000],
            'Colour':[
                        '#bdf2ff',
                        '#ffbf00',
                        '#f5c2ff',
                        '#ff0000',
                        '#cfcfcf',
                        '#a1a1a1',
                        '#707070',
                        '#640082',
                        '#e3ce32',
                    ],
            'Number':[0,0,0,0,0,0,0,0,0]}

PEGS_CIRS = {'Name':['AIR', 'CIRS_LUNG', 'CIRS_ADIPOSE', 'CIRS_WATER', 'CIRS_MUSCLE', 'CIRS_BONE', 'LEAD', 'GOLD'],
            'MinCT':[-1005, -900, -200, -50, 50, 200, 2000, 8500],
            'MaxCT':[-900, -200, -50, 50, 200, 2000, 8500, 15000],
            'Colour':[
                        '#bdf2ff',
                        '#9999FF',
                        '#ffbf00',
                        '#083BF9',
                        '#ff0000',
                        '#707070',
                        '#640082',
                        '#e3ce32',
                    ],
            'Number':[0,0,0,0,0,0,0,0]}


#Applicator labels
low_energy_applicators = [
    {'label': '2cm diameter, 30cm SSD', 'value': 'd2'},
    {'label': '3cm diameter, 30cm SSD', 'value': 'd3'},
    {'label': '5cm diameter, 30cm SSD', 'value': 'd5'},
    {'label': '10cm diameter, 30cm SSD', 'value': 'd10'}
]
high_energy_applicators = [
    {'label': '5x7cm, 50cm SSD', 'value': '5x7'},
    {'label': '8x8cm, 50cm SSD', 'value': '8x8'},
    {'label': '10x10cm, 50cm SSD', 'value': '10x10'},
    {'label': '10x20cm, 50cm SSD', 'value': '10x20'},
    {'label': '15x15cm, 50cm SSD', 'value': '15x15'},
    {'label': '20x20cm, 50cm SSD', 'value': '20x20'}
]

dbs_parameters = {'d2': [4,31.5],
                  'd3': [4,31.5], 
                  'd5': [6,31.5], 
                  'd10': [8,31.5], 
                  '5x7': [9,51.5], 
                  '8x8': [12,51.5], 
                  '10x10': [14,51.5], 
                  '10x20': [23,51.5], 
                  '15x15': [21,51.5], 
                  '20x20': [29,51.5]}

def generate_original_phsp(field_size):
    #Creating a PHSP plane
    if field_size.starts_with('d'):
        dimension = int(field_size.replace('d',''))
        original_phsp = genCIRC(dimension,0)
    else:
        dimensions = field_size.split('x')
        original_phsp = genRECT(dimensions[0],dimensions[1],0)

    return original_phsp


#=====================================================================================
#======================================FUNCTIONS======================================
#=====================================================================================

def orientation_label(X, Y, T):
    '''
    Used to generate letters indicating CT right/left/ant/post/sup/inf in all 
    appropriate plots.
    '''
    L = dict(x=X, y=Y, text=T, showarrow=False, font=dict(family='"Segoe UI",Arial,sans-serif', size=20, color="#ffffff"), bordercolor="#000000", borderwidth=2, borderpad=3, bgcolor="#f25504", opacity=1)

    return L

def resource_path(relative_path):
    '''
    Gets absolute path to resources/assets folder used by dash app.
    '''
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def gui_select_dir():
    '''
    Opens a folder browser and returns the path to the selected directory.
    '''
    try:
        pidl, display_name, _ = shell.SHBrowseForFolder()
        fname = shell.SHGetPathFromIDList(pidl)

        loc = str(fname).split("'")

        path = str(loc[1])

    except:
        print('Failed to get directory!')
        return None

    return path 

def gui_save_file(title, savetype):
    '''
    Opens a save-file dialog.
    
    '''
    flags = win32con.OFN_OVERWRITEPROMPT
    fd = win32ui.CreateFileDialog(0, None, None, flags, savetype)

    fd.SetOFNTitle(title)

    if fd.DoModal()==win32con.IDCANCEL:
        sys.exit(1)
        
    #if fd.DoModal()==win32con.IDOK:
    n = fd.GetPathName()

    return n

def gui_select_file(title,start_dir=None):
    '''
    Opens a file browser and returns the path to the selected file.
    '''
    fd = win32ui.CreateFileDialog(1)

    fd.SetOFNTitle(title)

    if fd.DoModal()==win32con.IDCANCEL:
        sys.exit(1)
        
    filepath = fd.GetPathName()
    
    return filepath

def createFolder(directory):
    '''
    Creates a folder in the specified directory. If the folder already exists,
    a number is added to the folder name and another attempt is made.
    '''
    try:            
        if not os.path.exists(directory):
            os.makedirs(directory)
            my_dir=directory
        else:
            fail=1
            i=1
            while fail==1:
                new_directory = directory + str(i)
                
                if not os.path.exists(new_directory):
                    os.makedirs(new_directory)
                    my_dir=new_directory
                    fail=0
                else:
                    i+=1
                
        return my_dir
    except OSError:
        print('Error: Creating directory.' + directory)


def copy_rename_DICOM(old_path, new_path):
    '''
    Copies *.dcm files from old path to new path and renames them in the process,
    to their InstanceUID. This is useful when working with contour files.
    '''     
            
    for f in os.listdir(old_path):
        
        try:
            my_slice = dcm.read_file(old_path + '/' + f, force=True)
            #print('Read: ', f, ' as a DICOM file!')
        except:
            print('Can\'t read', f, 'file as a DICOM!')
            
        try:
            #Does not copy contour file - only CT files
            if my_slice.SOPClassUID == '1.2.840.10008.5.1.4.1.1.2':
                src = old_path + '/' + f
                dst = new_path + '/' + str(dcm.read_file(src, force=True).SOPInstanceUID) + '.dcm'

                copyfile(src, dst)

            else:
                pass
        except:
            print('File: ', s, ' does not have SOPInstanceUID')
            pass


# CT object generation and functions

class scan:
    '''
    CT cube class which stores all the useful information from the
    DICOM files uploaded.
    '''
    
    def __init__(self, slices):
        
        self.phantom_created = False
        self.progress = 0
        self.stage = 1 #1=imported, 2=structures added, 3=HU updated, 4=accepted for ROI, 5=ROI cropped/accepted
        
        #Raw files
        self.slices = slices
        
        #Basic information to display
        try:
            self.patient_name = str(self.slices[0].PatientName)
        except:
            self.patient_name = 'Nobody'
            
        try:
            self.patient_id = str(self.slices[0].PatientID)
        except:
            self.patient_id = 'JamesBond007'
            
        try:
            self.patient_dob = str(self.slices[0].PatientBirthDate)
        except:
            self.patient_dob = '--/--/--'
            
        try:
            self.orientation = str(self.slices[0].PatientPosition)
        except:
            self.orientation = 'Unknown'
            
        try:
            aq_date = str(self.slices[0].AcquisitionDate)
            self.acquisition_date = aq_date[6:] + '/' + aq_date[4:6] + '/' + aq_date[:4] 
        except:
            self.acquisition_date = '--/--/--'
        
        
        #Resolution in x, y, z directions
        self.x_step = self.slices[0].PixelSpacing[0]
        self.y_step = self.slices[0].PixelSpacing[1]
        self.z_step = self.slices[0].SliceThickness
        
        self.resolution = str(round(self.x_step,2)) + ',' + str(round(self.y_step,2)) + ',' + str(round(self.z_step,2))
        
        #Number of voxels in x, y, z directions
        self.rows = self.slices[0].Rows
        self.cols = self.slices[0].Columns
        self.stack = len(self.slices)
        
        #Geometrical positions of each voxel
        self.x_positions, self.y_positions = get_xy_coordinates(self.slices[0])
        self.z_positions = np.asarray([s.ImagePositionPatient[2] for s in self.slices])
        
        #Forcing the transfer syntax for CT files from Monaco
        try:
            temp = list([s.file_meta.TransferSyntaxUID for s in self.slices])
        except:
            print('Error finding TransferSyntaxUID! Going to force it to be ImplicitVRLittleEndian')
            for s in self.slices:
                s.file_meta.TransferSyntaxUID = dcm.uid.ImplicitVRLittleEndian
            
        #Extracting 3D pixel array
        image = np.stack([s.pixel_array for s in self.slices])
        image = image.astype(np.int16)
        image[image == -2000] = 0
        
        self.intercept = self.slices[0].RescaleIntercept
        self.slope = self.slices[0].RescaleSlope
        
        if self.slope != 1:
            image = self.slope * image.astype(np.float64)
            image = image.astype(np.int16)
        image += np.int16(self.intercept)
        
        #Saving the original cube orientation for overwriting data later
        self.original_cube = np.array(image, dtype = np.int16)
        
        #Rotating the cube if its in decubitus position
        if self.slices[0].ImageOrientationPatient[1] == -1:
            self.original_cube = np.rot90(self.original_cube, k=1, axes=(1,2))
        elif self.slices[0].ImageOrientationPatient[1] == 1:
            self.original_cube = np.rot90(self.original_cube, k=-1, axes=(1,2))
        
        #Flipping the cube and x,y,z positions to be in HFS orientation for display purposes
        self.HFS_cube = np.copy(self.original_cube)    
        
        self.HFS_xs = self.x_positions
        self.HFS_ys = self.y_positions
        self.HFS_zs = self.z_positions
        
        #Tag used for plotting updated HU values later
        self.updated = False     

    def crop_cube(self, rangex, rangey, rangez):
        '''
        Cropping the outer regions of the CT cube and voxel coordinate
        arrays with x,y,z min/max values based on the user selected ranges.
        This is used to remove outer voxels which are of no interest
        in the Monte Carlo simulation. Minimising the number of voxels 
        improves the simulation times.
        '''
        xmin = find_index(self.HFS_xs, rangex[0])
        xmax = find_index(self.HFS_xs, rangex[1])
        
        ymin = find_index(self.HFS_ys, rangey[0])
        ymax = find_index(self.HFS_ys, rangey[1])
        
        zmin = find_index(self.HFS_zs, rangez[0])
        zmax = find_index(self.HFS_zs, rangez[1])

        #If the x,y,z coordinate arrays start from positive and end with negative value - cropping indices must be flipped
        if xmin>xmax:
            self.cropped_xs = self.HFS_xs[xmax:xmin]
            self.cropped_cube = self.HFS_cube[:,:,xmax:xmin]
        else:
            self.cropped_xs = self.HFS_xs[xmin:xmax]
            self.cropped_cube = self.HFS_cube[:,:,xmin:xmax]
        
        if ymin>ymax:
            self.cropped_ys = self.HFS_ys[ymax:ymin]
            self.cropped_cube = self.cropped_cube[:,ymax:ymin,:]
        else:
            self.cropped_ys = self.HFS_ys[ymin:ymax]
            self.cropped_cube = self.cropped_cube[:,ymin:ymax,:]
        
        if zmin>zmax:
            self.cropped_zs = self.HFS_zs[zmax:zmin]
            self.cropped_cube = self.cropped_cube[zmax:zmin,:,:]
        else:
            self.cropped_zs = self.HFS_zs[zmin:zmax]
            self.cropped_cube = self.cropped_cube[zmin:zmax,:,:]
        
    def create_mini_cubes(self, rangex, rangey, rangez):
        '''
        Prepares CT array and coordinate arrays for phantom file writing.
        Uses cropped CT cube and cropped x,y,z coordinates as starting point
        and flips each accordingly if they are in decreasing order of coordinates.
        '''
        start_cube = self.cropped_cube
        start_xs = self.cropped_xs
        start_ys = self.cropped_ys
        start_zs = self.cropped_zs

        if start_xs[0]>start_xs[-1]:
            start_xs = start_xs[::-1]
            start_cube = np.flip(start_cube,2)

        if start_ys[0]>start_ys[-1]:
            start_ys = start_ys[::-1]
            start_cube = np.flip(start_cube,1)

        if start_zs[0]>start_zs[-1]:
            start_zs = start_zs[::-1]
            start_cube = np.flip(start_cube,0)

        self.final_cube = start_cube

        xvoxboundaries = start_xs
        xvoxboundaries = np.append(xvoxboundaries, xvoxboundaries[-1] + self.x_step)

        yvoxboundaries = start_ys
        yvoxboundaries = np.append(yvoxboundaries, yvoxboundaries[-1] + self.y_step)

        zvoxboundaries = start_zs
        zvoxboundaries = np.append(zvoxboundaries, zvoxboundaries[-1] + self.z_step)

        return self.final_cube, xvoxboundaries, yvoxboundaries, zvoxboundaries



def find_index(array, value):
    index = (np.abs(array - value)).argmin()
    
    return index


def load_dicom_files(path):
    '''
    Loads all *.dcm files from the given path and sorts the list 
    of files by the z coordinate of each file.
    '''
    slices=[]
    
    #For each file in the directory
    for s in os.listdir(path):

        #Try read file in DICOM format
        try:
            my_slice = dcm.read_file(path + '/' + s, force=True)
            print('Read: ', s, ' as a DICOM file!')
        except:
            print('Can\'t read', s, 'file as a DICOM!')
           
        try:
            #Check if the file is a DICOM CT file 
            if my_slice.SOPClassUID == '1.2.840.10008.5.1.4.1.1.2':
                slices.append(my_slice)
            else:
                pass
        except:
            print('File: ', s, ' is not a CT slice file!')
        
    if slices != []:
       
        #Sorting all slices by z position of each slice
        slices.sort(key = lambda x: x.ImagePositionPatient[2])  

        #Checking that all slices are continuous and no slices are missing
        instance_list = list(s.InstanceNumber for s in slices)
        expected_instances = list(range(min(instance_list), max(instance_list)+1))

        if instance_list == expected_instances or instance_list == expected_instances[::-1]:
            message = 'CT data imported successfully!'
        else:
            message = 'CT data imported but there are CT slices missing! Going to stretch CT slices to fill the gaps...'

        #Ensuring the same slice thickness for all slices
        try:
            slice_thickness = np.abs(slices[0].ImagePositionPatient[2] - slices[1].ImagePositionPatient[2])  
        except:
            slice_thickness = np.abs(slices[0].SliceLocation - slices[1].SliceLocation)  

        for s in slices:
            s.SliceThickness = slice_thickness
        
        return slices, message
    else:
        return False, None


def get_xy_coordinates(axial_slice):
    '''
    Reads ImageOrientationPatient tag to figure out which direction 
    x,y,z axes of the patient are facing in CT space, and hence generate
    an array of x,y,z voxel coordinates and correctly assign them.
    
    In typical DICOM CT files the:
        x-axis increases to the LHS of the patient,
        y-axis increases to the posterior of the patient
        z-axis increases to the head of the patient
        
    ImagePositionPatient tag always gives the coordinates of the (0,0)
    voxel of the raw PixelArray i.e. if I was to imshow raw pixel data, 
    the 0,0 array index has coordinates ImagePositionPatient.
    
    This first voxel can fall on the max or min coordinate of x,y,z axes and
    hence the remaining voxel coordinates have to increase or decrease depending
    on the orientation of the patient.
    
    The actual values [1,0,0,1,0,0] are the direction cosines of the first row 
    and the first column with respect to the patient x,y,z axes. 
    Value of 1 means 0 angle (Cos(0) = 1) and value of 0 means 90 angle (Cos(90) = 0).
    [1,0,0,1,0,0] means x is aligned with rows and y is aligned with columns and both are 
    increasing from voxel (0,0,0).
    [-1,0,0,1,0,0] means x is reverse aligned with rows and y is aligned with columns, hence
    x coordinates are decreasing with each voxel in the rows and y coordinates are 
    increasing with each voxel in the columns.
    
    In decubitus orientation the 2D slices need to be rotated 90 deg before being plotted
    and hence the ImagePositionPatient now defined the coordinates of the (0,512) or (512,0)
    vaxel depending on the rotation direction. This is the reason x and y arrays below have
    to be reversed.
    
    E.g. HFS here x nd y are increasing from -325 to 325 and allocated to array as they are
         []        []
                []
    [-325,-325]    []
    
    E.g. HFP here x and y are decreasing from 325 to -325 and when alocated to array the array gets flipped in x and y
    to have x and y axes in increasing order
         []        []
                []
     [325,325]     []
     
     E.g. HFDR here x and y are decreasing from 325 to -325 and when alocated to array the array gets flipped in x and y
    to have x and y axes in increasing order
         []        []
                []
     [325,-325]    []
     
      becomes array below after 90 deg rotation so now x's should increase TO the value of 325 and y should increase
      FROM the value -325. Hence if x's are generated as [325,...,-325] they need to be flipped
      
     []        []
         []
     []     [325,-325]
     
    
    '''

    print('Patient orientation DICOM tag: ',axial_slice.ImageOrientationPatient)
    print('Patient position DICOM tag: ',axial_slice.ImagePositionPatient)
    
    if axial_slice.ImageOrientationPatient[0] == 1:
        x_start = axial_slice.ImagePositionPatient[0]
        x_end = x_start + (axial_slice.Columns-1)*axial_slice.PixelSpacing[0] #x coordinates increasing with each voxel
        x_coordinates = np.linspace(x_start,x_end,axial_slice.Columns)

    elif axial_slice.ImageOrientationPatient[0] == -1:
        x_start = axial_slice.ImagePositionPatient[0]
        x_end = x_start - (axial_slice.Columns-1)*axial_slice.PixelSpacing[0] #x coordinates decreasing with each voxel
        x_coordinates = np.linspace(x_start,x_end,axial_slice.Columns)
    
    elif axial_slice.ImageOrientationPatient[3] == -1: ########
        x_start = axial_slice.ImagePositionPatient[0]
        x_end = x_start - (axial_slice.Columns-1)*axial_slice.PixelSpacing[0] #x coordinates decreasing with each voxel
        x_coordinates = np.linspace(x_start,x_end,axial_slice.Columns)
        x_coordinates = x_coordinates[::-1]
        
    elif axial_slice.ImageOrientationPatient[3] == 1:
        x_start = axial_slice.ImagePositionPatient[0]
        x_end = x_start + (axial_slice.Columns-1)*axial_slice.PixelSpacing[0] #x coordinates increasing with each voxel
        x_coordinates = np.linspace(x_start,x_end,axial_slice.Columns)
        
    else:
        print('Unknown X - ImageOrientationPatient information')
        x_coordinates = np.linspace(0,axial_slice.Columns-1,axial_slice.Columns)


    if axial_slice.ImageOrientationPatient[4] == 1:
        y_start = axial_slice.ImagePositionPatient[1]
        y_end = y_start + (axial_slice.Rows-1)*axial_slice.PixelSpacing[1] #y coordinates increasing with each voxel
        y_coordinates = np.linspace(y_start,y_end,axial_slice.Rows)

    elif axial_slice.ImageOrientationPatient[4] == -1:
        y_start = axial_slice.ImagePositionPatient[1]
        y_end = y_start - (axial_slice.Rows-1)*axial_slice.PixelSpacing[1] #y coordinates decreasing with each voxel
        y_coordinates = np.linspace(y_start,y_end,axial_slice.Rows)
        
    elif axial_slice.ImageOrientationPatient[1] == -1:
        y_start = axial_slice.ImagePositionPatient[1]
        y_end = y_start - (axial_slice.Rows-1)*axial_slice.PixelSpacing[1] #y coordinates decreasing with each voxel
        y_coordinates = np.linspace(y_start,y_end,axial_slice.Rows)
        y_coordinates = y_coordinates[::-1]
        
    elif axial_slice.ImageOrientationPatient[1] == 1: #######
        y_start = axial_slice.ImagePositionPatient[1]
        y_end = y_start + (axial_slice.Rows-1)*axial_slice.PixelSpacing[1] #y coordinates increasing with each voxel
        y_coordinates = np.linspace(y_start,y_end,axial_slice.Rows)
        
    else:
        print('Unknown Y - ImageOrientationPatient information')
        y_coordinates = np.linspace(0,axial_slice.Rows-1,axial_slice.Rows)
        
    #print('X coordinates range:', x_coordinates[0], '->', x_coordinates[-1])
    #print('Y coordinates range:', y_coordinates[0], '->', y_coordinates[-1])

    return x_coordinates, y_coordinates


class structure:
    
    def __init__(self, number, name, color, cube, sequence):
        self.number = number
        self.name = name
        self.color = color
        self.cube = cube
        self.sequence = sequence


# Plotting functions

def PLOT_CT(cube, xs, ys, zs, View, Slice, width, PEGS):
    '''
    Displays a selected slice of the CT cube in the required view
    (Axial, Saggital, Coronal). 
    '''
    #Create a copy of the CT cube to avoid modifying original
    CT_cube_copy = np.copy(cube)
    k=int(Slice)
    
    axial_xs = np.around(xs,2)
    axial_ys = np.around(ys,2)
    
    saggital_xs = np.around(ys,2)
    saggital_ys = np.around(zs,2)
    
    coronal_xs = np.around(xs,2)
    coronal_ys = np.around(zs,2)

    
    if View == 'A':
        xpos1 = axial_xs
        ypos1 = axial_ys
        img1 = CT_cube_copy[k,:,:]

        #Plotting middle slices of the other two views for reference
        half_sub1 = int(CT_cube_copy.shape[1]/2)
        half_sub2 = int(CT_cube_copy.shape[2]/2)

        xpos2 = coronal_xs
        ypos2 = coronal_ys
        img2 = CT_cube_copy[:,half_sub1,:]
        
        xpos3 = saggital_xs
        ypos3 = saggital_ys
        img3 = CT_cube_copy[:,:,half_sub2]

        #Plottig red reference line on sub views
        shape_sub1 = [{
            'type' : 'line',
            'x0':coronal_xs[0],
            'y0':coronal_ys[k],
            'x1':coronal_xs[-1],
            'y1':coronal_ys[k],
            'line': {
                'color':'#FF0000',
                'width': 2,
            }
        }]

        shape_sub2 = [{
            'type' : 'line',
            'x0':saggital_xs[0],
            'y0':saggital_ys[k],
            'x1':saggital_xs[-1],
            'y1':saggital_ys[k],
            'line': {
                'color':'#FF0000',
                'width': 2,
            }
        }]
        
        if PEGS != None:
            ht = 'Tissue: %{customdata}, <br> x: %{x}, <br> y: %{y}'
            ht1 = 'Tissue: %{customdata}, <br> x: %{x}, <br> z: %{y}'
            ht2 = 'Tissue: %{customdata}, <br> y: %{x}, <br> z: %{y}'
        else:
            ht = 'HU: %{z}, <br> x: %{x}, <br> y: %{y}'
            ht1 = 'HU: %{z}, <br> x: %{x}, <br> z: %{y}'
            ht2 = 'HU: %{z}, <br> y: %{x}, <br> z: %{y}'

    elif View == 'S':
        xpos1 = saggital_xs
        ypos1 = saggital_ys
        img1 = CT_cube_copy[:,:,k]

        #Plotting middle slices of the other two views for reference
        half_sub1 = int(CT_cube_copy.shape[0]/2)
        half_sub2 = int(CT_cube_copy.shape[1]/2)

        xpos2 = axial_xs
        ypos2 = axial_ys
        img2 = CT_cube_copy[half_sub1,:,:]
        
        xpos3 = coronal_xs
        ypos3 = coronal_ys
        img3 = CT_cube_copy[:,half_sub2,:]

        #Plottig red reference line on sub views
        shape_sub1 = [{
            'type' : 'line',
            'x0':axial_xs[k],
            'y0':axial_ys[0],
            'x1':axial_xs[k],
            'y1':axial_ys[-1],
            'line': {
                'color':'#FF0000',
                'width': 2,
            }
        }]

        shape_sub2 = [{
            'type' : 'line',
            'x0':coronal_xs[k],
            'y0':coronal_ys[0],
            'x1':coronal_xs[k],
            'y1':coronal_ys[-1],
            'line': {
                'color':'#FF0000',
                'width': 2,
            }
        }]
        
        if PEGS != None:
            ht = 'Tissue: %{customdata}, <br> x: %{x}, <br> y: %{y}'
            ht1 = 'Tissue: %{customdata}, <br> x: %{x}, <br> z: %{y}'
            ht2 = 'Tissue: %{customdata}, <br> y: %{x}, <br> z: %{y}'
        else:
            ht = 'HU: %{z}, <br> y: %{x}, <br> z: %{y}'
            ht1 = 'HU: %{z}, <br> x: %{x}, <br> y: %{y}'
            ht2 = 'HU: %{z}, <br> x: %{x}, <br> z: %{y}'

    elif View == 'C':
        xpos1 = coronal_xs
        ypos1 = coronal_ys
        img1 = CT_cube_copy[:,k,:]

        #Plotting middle slices of the other two views for reference
        half_sub1 = int(CT_cube_copy.shape[2]/2)
        half_sub2 = int(CT_cube_copy.shape[0]/2)

        xpos2 = saggital_xs
        ypos2 = saggital_ys
        img2 = CT_cube_copy[:,:,half_sub1]
        
        xpos3 = axial_xs
        ypos3 = axial_ys
        img3 = CT_cube_copy[half_sub2,:,:]

        #Plottig red reference line on sub views
        shape_sub1 = [{
            'type' : 'line',
            'x0':saggital_xs[k],
            'y0':saggital_ys[0],
            'x1':saggital_xs[k],
            'y1':saggital_ys[-1],
            'line': {
                'color':'#FF0000',
                'width': 2,
            }
        }]

        shape_sub2 = [{
            'type' : 'line',
            'x0':axial_xs[0],
            'y0':axial_ys[k],
            'x1':axial_xs[-1],
            'y1':axial_ys[k],
            'line': {
                'color':'#FF0000',
                'width': 2,
            }
        }]
        
        if PEGS != None:
            ht = 'Tissue: %{customdata}, <br> x: %{x}, <br> y: %{y}'
            ht1 = 'Tissue: %{customdata}, <br> x: %{x}, <br> z: %{y}'
            ht2 = 'Tissue: %{customdata}, <br> y: %{x}, <br> z: %{y}'
        else:
            ht = 'HU: %{z}, <br> x: %{x}, <br> z: %{y}'
            ht1 = 'HU: %{z}, <br> y: %{x}, <br> z: %{y}'
            ht2 = 'HU: %{z}, <br> x: %{x}, <br> y: %{y}'

    else:
        print('Invalid view selected! Please try A/S/C!')
        return
    
    
    if PEGS != None:
        #color coding tissue types in plots for tissue segmentation tab
        mat1 = np.empty(img1.shape, dtype='<U15')
        mat2 = np.empty(img2.shape, dtype='<U15')
        mat3 = np.empty(img3.shape, dtype='<U15')

        for i in range(len(PEGS['Name'])):
            mat1[(PEGS['MinCT'][i]<=img1) & (img1<PEGS['MaxCT'][i])] = PEGS['Name'][i]
            mat2[(PEGS['MinCT'][i]<=img2) & (img2<PEGS['MaxCT'][i])] = PEGS['Name'][i]
            mat3[(PEGS['MinCT'][i]<=img3) & (img3<PEGS['MaxCT'][i])] = PEGS['Name'][i]
    else:
        mat1 = None
        mat2 = None
        mat3 = None

    #Adjusting window level and width
    HU_min = width[0]
    HU_max = width[1]
    
    img1[img1<HU_min] = HU_min
    img1[img1>HU_max] = HU_max
    
    img2[img2<HU_min] = HU_min
    img2[img2>HU_max] = HU_max
    
    img3[img3<HU_min] = HU_min
    img3[img3>HU_max] = HU_max
    
    
    main_heatmap = go.Heatmap(
        x=xpos1,
        y=ypos1,        
        z=img1,
        showscale=False,
        name='CT',
        hoverlabel=dict(bgcolor='black'),
        colorscale='Greys',
        hovertemplate = ht,
        customdata=mat1,
        reversescale=True
    )
    
    data_main = [main_heatmap]
    layout_main = {'autosize':True,
                   'paper_bgcolor':'rgba(0,0,0,0)',
                    'plot_bgcolor':'rgba(0,0,0,0)',
                   'margin':{
                       't':1,
                       'l':1,
                       'r':1,
                       'b':1
                   },
                   'xaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },
                   'yaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },}

   
    #-----------------------------SUB1----------------------------------------
    CT_sub1_heatmap = go.Heatmap(
        z=img2,
        x=xpos2,
        y=ypos2,
        name='CT',
        showscale=False, 
        colorscale='Greys',
        reversescale=True,
        hovertemplate = ht1,
        customdata=mat2
    )
    
    
    data_sub1 = [CT_sub1_heatmap]
    layout_sub1 = {'shapes': shape_sub1,
                  'autosize':True,
                   'paper_bgcolor':'rgba(0,0,0,0)',
                    'plot_bgcolor':'rgba(0,0,0,0)',
                   'margin':{
                       't':1,
                       'l':1,
                       'r':1,
                       'b':1
                   },
                   'xaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },
                   'yaxis': {
                       #'scaleanchor':'x',
                       #'constrain':'domain',
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },} 
    figure_sub1=go.Figure(data=data_sub1, layout = layout_sub1)
    
    
    #-----------------------------SUB2----------------------------------------
    CT_sub2_heatmap = go.Heatmap(
        z=img3,
        x=xpos3,
        y=ypos3,
        name='CT',
        showscale=False, 
        colorscale='Greys',
        reversescale=True,
        hovertemplate = ht2,
        customdata=mat3
    )
    
            
    data_sub2 = [CT_sub2_heatmap]
    layout_sub2 = {'shapes': shape_sub2,
                  'autosize':True,
                   'paper_bgcolor':'rgba(0,0,0,0)',
                    'plot_bgcolor':'rgba(0,0,0,0)',
                   'margin':{
                       't':1,
                       'l':1,
                       'r':1,
                       'b':1
                   },
                   'xaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },
                   'yaxis': {
                       #'scaleanchor':'x',
                       #'constrain':'domain',
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },} 
    figure_sub2=go.Figure(data=data_sub2, layout = layout_sub2)

    return data_main, layout_main, figure_sub1, figure_sub2


def plot_ROI(cube,rangex,slicex,rangey,slicey,rangez,slicez,window):

    #Create a copy of the CT cube to avoid modifying original
    CT_cube_copy = np.copy(cube.HFS_cube)
    
    axial_xs = np.around(cube.HFS_xs,2)
    axial_ys = np.around(cube.HFS_ys,2)
    
    saggital_xs = np.around(cube.HFS_ys,2)
    saggital_ys = np.around(cube.HFS_zs,2)
    
    coronal_xs = np.around(cube.HFS_xs,2)
    coronal_ys = np.around(cube.HFS_zs,2)

    axial_slice_idx = (np.abs(cube.HFS_zs - slicez)).argmin()
    coronal_slice_idx = (np.abs(cube.HFS_ys - slicey)).argmin()
    saggital_slice_idx = (np.abs(cube.HFS_xs - slicex)).argmin()
    
    axial_img = CT_cube_copy[axial_slice_idx,:,:]
    saggital_img = CT_cube_copy[:,:,saggital_slice_idx]
    coronal_img = CT_cube_copy[:,coronal_slice_idx,:]
    
    #Adjusting window level and width
    HU_min = window[0]
    HU_max = window[1]
    
    axial_img[axial_img<HU_min] = HU_min
    axial_img[axial_img>HU_max] = HU_max
    
    saggital_img[saggital_img<HU_min] = HU_min
    saggital_img[saggital_img>HU_max] = HU_max
    
    coronal_img[coronal_img<HU_min] = HU_min
    coronal_img[coronal_img>HU_max] = HU_max

    hover_axial = 'HU: %{z}, <br> x: %{x}, <br> y: %{y}'
    hover_saggital = 'HU: %{z}, <br> y: %{x}, <br> z: %{y}'
    hover_coronal = 'HU: %{z}, <br> x: %{x}, <br> z: %{y}'
    
    axial_heatmap = go.Heatmap(
        x=axial_xs,
        y=axial_ys,        
        z=axial_img,
        showscale=False,
        name='CT',
        hoverlabel=dict(bgcolor='black'),
        colorscale='Greys',
        hovertemplate = hover_axial,
        reversescale=True
    )
    
    coronal_heatmap = go.Heatmap(
        x=coronal_xs,
        y=coronal_ys,        
        z=coronal_img,
        showscale=False,
        name='CT',
        hoverlabel=dict(bgcolor='black'),
        colorscale='Greys',
        hovertemplate = hover_coronal,
        reversescale=True
    )
    
    saggital_heatmap = go.Heatmap(
        x=saggital_xs,
        y=saggital_ys,        
        z=saggital_img,
        showscale=False,
        name='CT',
        hoverlabel=dict(bgcolor='black'),
        colorscale='Greys',
        hovertemplate = hover_saggital,
        reversescale=True
    )

    axial_line_on_saggital = {
            'type' : 'line',
            'x0':cube.HFS_ys[0],
            'y0':slicez,
            'x1':cube.HFS_ys[-1],
            'y1':slicez,
            'line': {
                'color':'#CC0000',
                'width': 2,
            }
        }
    axial_line_on_coronal = {
            'type' : 'line',
            'x0':cube.HFS_xs[0],
            'y0':slicez,
            'x1':cube.HFS_xs[-1],
            'y1':slicez,
            'line': {
                'color':'#CC0000',
                'width': 2,
            }
        }
    coronal_line_on_saggital = {
            'type' : 'line',
            'x0':slicey,
            'y0':cube.HFS_zs[0],
            'x1':slicey,
            'y1':cube.HFS_zs[-1],
            'line': {
                'color':'#00CC00',
                'width': 2,
            }
        }
    coronal_line_on_axial = {
            'type' : 'line',
            'x0':cube.HFS_xs[0],
            'y0':slicey,
            'x1':cube.HFS_xs[-1],
            'y1':slicey,
            'line': {
                'color':'#00CC00',
                'width': 2,
            }
        }
    saggital_line_on_axial = {
            'type' : 'line',
            'x0':slicex,
            'y0':cube.HFS_ys[0],
            'x1':slicex,
            'y1':cube.HFS_ys[-1],
            'line': {
                'color':'#0000CC',
                'width': 2,
            }
        }
    saggital_line_on_coronal = {
            'type' : 'line',
            'x0':slicex,
            'y0':cube.HFS_zs[0],
            'x1':slicex,
            'y1':cube.HFS_zs[-1],
            'line': {
                'color':'#0000CC',
                'width': 2,
            }
        }
    
    
    axial_outline_top = {
            'type' : 'line',
            'x0':cube.HFS_ys[0],
            'y0':cube.HFS_xs[-1],
            'x1':cube.HFS_ys[-1],
            'y1':cube.HFS_xs[-1],
            'line': {
                'color':'#CC0000',
                'width': 2,
            }
        }
    axial_outline_bottom = {
            'type' : 'line',
            'x0':cube.HFS_ys[0],
            'y0':cube.HFS_xs[0],
            'x1':cube.HFS_ys[-1],
            'y1':cube.HFS_xs[0],
            'line': {
                'color':'#CC0000',
                'width': 2,
            }
        }
    axial_outline_left = {
            'type' : 'line',
            'x0':cube.HFS_xs[0],
            'y0':cube.HFS_ys[0],
            'x1':cube.HFS_xs[0],
            'y1':cube.HFS_ys[-1],
            'line': {
                'color':'#CC0000',
                'width': 2,
            }
        }
    axial_outline_right = {
            'type' : 'line',
            'x0':cube.HFS_xs[-1],
            'y0':cube.HFS_ys[0],
            'x1':cube.HFS_xs[-1],
            'y1':cube.HFS_ys[-1],
            'line': {
                'color':'#CC0000',
                'width': 2,
            }
        }
    
    saggital_outline_top = {
            'type' : 'line',
            'x0':cube.HFS_ys[0],
            'y0':cube.HFS_zs[-1],
            'x1':cube.HFS_ys[-1],
            'y1':cube.HFS_zs[-1],
            'line': {
                'color':'#0000CC',
                'width': 2,
            }
        }
    saggital_outline_bottom = {
            'type' : 'line',
            'x0':cube.HFS_ys[0],
            'y0':cube.HFS_zs[0],
            'x1':cube.HFS_ys[-1],
            'y1':cube.HFS_zs[0],
            'line': {
                'color':'#0000CC',
                'width': 2,
            }
        }
    saggital_outline_left = {
            'type' : 'line',
            'x0':cube.HFS_ys[0],
            'y0':cube.HFS_zs[0],
            'x1':cube.HFS_ys[0],
            'y1':cube.HFS_zs[-1],
            'line': {
                'color':'#0000CC',
                'width': 2,
            }
        }
    saggital_outline_right = {
            'type' : 'line',
            'x0':cube.HFS_ys[-1],
            'y0':cube.HFS_zs[0],
            'x1':cube.HFS_ys[-1],
            'y1':cube.HFS_zs[-1],
            'line': {
                'color':'#0000CC',
                'width': 2,
            }
        }
    
    coronal_outline_top = {
            'type' : 'line',
            'x0':cube.HFS_xs[0],
            'y0':cube.HFS_zs[-1],
            'x1':cube.HFS_xs[-1],
            'y1':cube.HFS_zs[-1],
            'line': {
                'color':'#00CC00',
                'width': 2,
            }
        }
    coronal_outline_bottom = {
            'type' : 'line',
            'x0':cube.HFS_xs[0],
            'y0':cube.HFS_zs[0],
            'x1':cube.HFS_xs[-1],
            'y1':cube.HFS_zs[0],
            'line': {
                'color':'#00CC00',
                'width': 2,
            }
        }
    coronal_outline_left = {
            'type' : 'line',
            'x0':cube.HFS_xs[0],
            'y0':cube.HFS_zs[0],
            'x1':cube.HFS_xs[0],
            'y1':cube.HFS_zs[-1],
            'line': {
                'color':'#00CC00',
                'width': 2,
            }
        }
    coronal_outline_right = {
            'type' : 'line',
            'x0':cube.HFS_xs[-1],
            'y0':cube.HFS_zs[0],
            'x1':cube.HFS_xs[-1],
            'y1':cube.HFS_zs[-1],
            'line': {
                'color':'#00CC00',
                'width': 2,
            }
        }

    xcrop1_axial = shade(min(cube.HFS_xs), rangex[0], min(cube.HFS_ys), max(cube.HFS_ys), 'blue')
    xcrop2_axial = shade(rangex[1], max(cube.HFS_xs), min(cube.HFS_ys), max(cube.HFS_ys), 'blue')
    ycrop1_axial = shade(min(cube.HFS_xs), max(cube.HFS_xs), min(cube.HFS_ys), rangey[0], 'green')
    ycrop2_axial = shade(min(cube.HFS_xs), max(cube.HFS_xs), rangey[1], max(cube.HFS_ys), 'green')
    
    xcrop1_saggital = shade(min(cube.HFS_ys), rangey[0], min(cube.HFS_zs), max(cube.HFS_zs), 'green')
    xcrop2_saggital = shade(rangey[1], max(cube.HFS_ys), min(cube.HFS_zs), max(cube.HFS_zs), 'green')
    ycrop1_saggital = shade(min(cube.HFS_ys), max(cube.HFS_ys), min(cube.HFS_zs), rangez[0], '#CC0000')
    ycrop2_saggital = shade(min(cube.HFS_ys), max(cube.HFS_ys), rangez[1], max(cube.HFS_zs), '#CC0000')
    
    xcrop1_coronal = shade(min(cube.HFS_xs), rangex[0], min(cube.HFS_zs), max(cube.HFS_zs), 'blue')
    xcrop2_coronal = shade(rangex[1], max(cube.HFS_xs), min(cube.HFS_zs), max(cube.HFS_zs), 'blue')
    ycrop1_coronal = shade(min(cube.HFS_xs), max(cube.HFS_xs), min(cube.HFS_zs), rangez[0], '#CC0000')
    ycrop2_coronal = shade(min(cube.HFS_xs), max(cube.HFS_xs), rangez[1], max(cube.HFS_zs), '#CC0000')
    
    
    layout_axial = {'autosize':True,
              'shapes': [saggital_line_on_axial,coronal_line_on_axial,
                        axial_outline_bottom, axial_outline_top, axial_outline_right, axial_outline_left,
                        xcrop1_axial, xcrop2_axial, ycrop1_axial, ycrop2_axial],
                   'paper_bgcolor':'rgba(0,0,0,0)',
                    'plot_bgcolor':'rgba(0,0,0,0)',
                   'margin':{
                       't':1,
                       'l':1,
                       'r':1,
                       'b':1
                   },
                   'xaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },
                   'yaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },}
    
    layout_saggital = {'autosize':True,
              'shapes': [axial_line_on_saggital, coronal_line_on_saggital,
                        saggital_outline_bottom, saggital_outline_top, saggital_outline_right, saggital_outline_left,
                        xcrop1_saggital, xcrop2_saggital, ycrop1_saggital, ycrop2_saggital],
                   'paper_bgcolor':'rgba(0,0,0,0)',
                    'plot_bgcolor':'rgba(0,0,0,0)',
                   'margin':{
                       't':1,
                       'l':1,
                       'r':1,
                       'b':1
                   },
                   'xaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },
                   'yaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },}
    
    layout_coronal = {'autosize':True,
              'shapes': [saggital_line_on_coronal,axial_line_on_coronal,
                        coronal_outline_bottom, coronal_outline_top, coronal_outline_right, coronal_outline_left,
                        xcrop1_coronal, xcrop2_coronal, ycrop1_coronal, ycrop2_coronal],
                   'paper_bgcolor':'rgba(0,0,0,0)',
                    'plot_bgcolor':'rgba(0,0,0,0)',
                   'margin':{
                       't':1,
                       'l':1,
                       'r':1,
                       'b':1
                   },
                   'xaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },
                   'yaxis': {
                        'showgrid': False, # thin lines in the background
                        'zeroline': False, # thick line at x=0
                        'visible': False,  # numbers below
                    },}
    saggital_fig = go.Figure(saggital_heatmap, layout_saggital)
    coronal_fig = go.Figure(coronal_heatmap, layout_coronal)
    axial_fig = go.Figure(axial_heatmap, layout_axial)
    
    return saggital_fig, coronal_fig, axial_fig


def contour_structures(selected_structures, view, idx):
    
    contour_plots = []
    
    for i in SCAN.structures:
        if i.number in selected_structures:

            if view == 'A':
                a_masked = i.cube[idx,:,:].astype(np.float16)
                a_masked[a_masked==0] = None

                contour_i_plot = go.Heatmap(
                                    x=SCAN.HFS_xs,
                                    y=SCAN.HFS_ys,
                                    z=a_masked,
                                    showscale=False,
                                    hoverinfo='skip',
                                    #name=i.name,
                                    colorscale = [
                                        [0, 'rgb(255,255,255)'],
                                        [1, 'rgba(%d,%d,%d,0.1)'%(i.color[0],i.color[1],i.color[2])]
                                    ]
                                )
                
            elif view == 'S':
                s_masked = i.cube[:,:,idx].astype(np.float16)
                s_masked[s_masked==0] = None

                contour_i_plot = go.Heatmap(
                                    x=SCAN.HFS_ys,
                                    y=SCAN.HFS_zs,
                                    z=s_masked,
                                    showscale=False,
                                    hoverinfo='skip',
                                    #name=i.name,
                                    colorscale = [
                                        [0, 'rgb(255,255,255)'],
                                        [1, 'rgba(%d,%d,%d,0.1)'%(i.color[0],i.color[1],i.color[2])]
                                    ]
                                )
                
            elif view == 'C':
                c_masked = i.cube[:,idx,:].astype(np.float16)
                c_masked[c_masked==0] = None

                contour_i_plot = go.Heatmap(
                                    x=SCAN.HFS_xs,
                                    y=SCAN.HFS_zs,
                                    z=c_masked,
                                    showscale=False,
                                    hoverinfo='skip',
                                    #name=i.name,
                                    colorscale = [
                                        [0, 'rgb(255,255,255)'],
                                        [1, 'rgba(%d,%d,%d,0.1)'%(i.color[0],i.color[1],i.color[2])]
                                    ]
                                )
            
            contour_plots.append(contour_i_plot)
            
    return contour_plots

def update_slice_slider(view):
    #Update Slice slider values
    if view == 'A':
        Sstep = SCAN.z_step
        Smin = np.min(SCAN.HFS_zs)
        Smax = np.max(SCAN.HFS_zs)
        Svalue = SCAN.HFS_zs[int(len(SCAN.HFS_zs)/2)]
        
        if SCAN.HFS_zs[0]<SCAN.HFS_zs[-1]:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.HFS_zs[::20]}
        else:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.HFS_zs[::-1][::20]}
        
    elif view == 'S':
        Sstep = SCAN.x_step
        Smin = np.min(SCAN.HFS_xs)
        Smax = np.max(SCAN.HFS_xs)
        Svalue = SCAN.HFS_xs[int(len(SCAN.HFS_xs)/2)]
        
        if SCAN.HFS_xs[0]<SCAN.HFS_xs[-1]:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.HFS_xs[::35]}
        else:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.HFS_xs[::-1][::35]}
        
    elif view == 'C':
        Sstep = SCAN.y_step
        Smin = np.min(SCAN.HFS_ys)
        Smax = np.max(SCAN.HFS_ys)
        Svalue = SCAN.HFS_ys[int(len(SCAN.HFS_ys)/2)]
        
        if SCAN.HFS_ys[0]<SCAN.HFS_ys[-1]:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.HFS_ys[::35]}
        else:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.HFS_ys[::-1][::35]}
        
    return Sstep, Smin, Smax, Svalue, Smarks 


def update_slice_slider_cropped(view):
    #Update Slice slider values
    
    if view == 'A':
        Sstep = SCAN.z_step
        Smin = np.min(SCAN.cropped_zs)
        Smax = np.max(SCAN.cropped_zs)
        Svalue = SCAN.cropped_zs[int(len(SCAN.cropped_zs)/2)]
        
        num_slices = len(SCAN.cropped_zs)
        
        if SCAN.cropped_zs[0]<SCAN.cropped_zs[-1]:        
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.cropped_zs[::int(num_slices/6)]}
        else:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.cropped_zs[::-1][::int(num_slices/6)]}
        
    elif view == 'S':
        Sstep = SCAN.x_step
        Smin = np.min(SCAN.cropped_xs)
        Smax = np.max(SCAN.cropped_xs)
        Svalue = SCAN.cropped_xs[int(len(SCAN.cropped_xs)/2)]
        
        num_slices = len(SCAN.cropped_xs)
        
        if SCAN.cropped_xs[0]<SCAN.cropped_xs[-1]:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.cropped_xs[::int(num_slices/6)]}
        else:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.cropped_xs[::-1][::int(num_slices/6)]}
        
    elif view == 'C':
        Sstep = SCAN.y_step
        Smin = np.min(SCAN.cropped_ys)
        Smax = np.max(SCAN.cropped_ys)
        Svalue = SCAN.cropped_ys[int(len(SCAN.cropped_ys)/2)]
        
        num_slices = len(SCAN.cropped_ys)
        
        if SCAN.cropped_ys[0]<SCAN.cropped_ys[-1]:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.cropped_ys[::int(num_slices/6)]}
        else:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'2rem'}} for i in SCAN.cropped_ys[::-1][::int(num_slices/6)]}
        
    return Sstep, Smin, Smax, Svalue, Smarks 


def create_dcc_graph(fig):
    G = dcc.Graph(
        figure=fig,
        config={
            'displayModeBar':False,
            'autosizable':True,
            'responsive':True
        }, 
        style={
            'height':'100%'
        }
    )
    return G


def shade(x0, x1, y0, y1, colour):
    '''
    Generates a translucent rectangle to shade in areas of CT that are
    not of interest to the user.
    '''
    rect = {'type':'rect',
            'x0':x0,
            'y0':y0,
            'x1':x1,
            'y1':y1,
            'fillcolor':colour,
            'opacity': 0.5,
            'line': {'width': 0}}
    
    return rect


def hd(x0, x1, y0, y1, colour):
    '''
    Generates a translucent rectangle to shade in the HD area of CT.
    '''
    rect = {'type':'rect',
            'x0':x0,
            'y0':y0,
            'x1':x1,
            'y1':y1,
            'fillcolor':colour,
            'opacity': 0.2,
            'line': {'width': 0}}
    
    return rect


# HU Overwriting Functions
def Overwrite(num, value):
    '''
    This function overwrites pixel values of the CT images that are inside
    a selected contour region.
    '''    

    for s in SCAN.structures:
        if num == s.number:
            cont_cube = s.cube
            
    #mean = value
    #std = 10
    #noisy_cube = np.random.normal(mean, std, SCAN.HFS_cube.shape)

    ones_cube = np.ones(SCAN.HFS_cube.shape)
    noisy_cube = ones_cube * value #new_HU_cube
            
    SCAN.HFS_cube[cont_cube==1] = noisy_cube[cont_cube==1]
    
    SCAN.cube_tobesaved = np.copy(SCAN.HFS_cube)

    #FLIP THE CUBE BACK TO ORIGINAL ORIENTATION TO SAVE IT
    #if SCAN.x_positions[0]>SCAN.x_positions[-1]:
    #    SCAN.cube_tobesaved = np.flip(SCAN.cube_tobesaved, 2)
        
    #if SCAN.y_positions[0]>SCAN.y_positions[-1]:
    #    SCAN.cube_tobesaved = np.flip(SCAN.cube_tobesaved, 1)

    #if SCAN.z_positions[0]>SCAN.z_positions[-1]:
    #    SCAN.cube_tobesaved = np.flip(SCAN.cube_tobesaved, 0)

    #Updating copied files
    SCAN.cube_tobesaved = (SCAN.cube_tobesaved - SCAN.intercept)/SCAN.slope
    SCAN.cube_tobesaved = SCAN.cube_tobesaved.astype(np.uint16)
    
    
    for i, slice_i in enumerate(SCAN.slices):
        slice_i.PixelData = SCAN.cube_tobesaved[i].tobytes()

        name = SCAN.updated_ct_folder_path + '/' + str(slice_i.SOPInstanceUID) + '.dcm'
        slice_i.save_as(name)
        
    return 


# CT HU Table Generation and functions

def ramp_up(table):
    '''
    Plots the CT ramp using HU and Density values. 
    Adds shaded rectangles to the plot for given HU value ranges.
    
    '''
    global HU
    global Den

    ramp_trace = go.Scatter(
                x=HU,
                y=Den,
                mode='lines+markers',
                name='CT Ramp',
               line=dict(color='#EF3405', width=4)
            )
    ramp_data = [ramp_trace]
    
    
    rect_list = []
    
    for rect in table:
        shape = {
            'type': 'rect',
            # x-reference is assigned to the x-values
            'xref': 'x',
            # y-reference is assigned to the plot paper [0,1]
            'yref': 'paper',
            'x0': rect.MinCT,
            'y0': 0,
            'x1': rect.MaxCT,
            'y1': 1,
            'fillcolor': rect.Colour,
            'opacity': 0.9,
            'layer':'below',
            'line': {
                'width': 0,
            }
        }
        
        rect_list.append(shape)
    
    
    
    ramp_layout = {#'title': 'CT ramp with shaded material cross section region',
                   'xaxis':dict(
                                title='HU number',
                                tickmode='linear',
                                ticks='outside',
                                tickangle=45,
                                dtick=400,
                                ticklen=8,
                                tickwidth=1,
                                tickcolor='white',
                               color='white'
                            ),
                   'yaxis':dict(
                                title='Density (g/cm^3)',
                                tickmode='linear',
                                ticks='outside',
                                dtick=1,
                                ticklen=8,
                                tickwidth=1,
                                tickcolor='white',
                               color='white'
                            ),
                   'shapes': rect_list,
                   'autosize':True,
                   'paper_bgcolor':colors['background'],
                    #'plot_bgcolor':'rgba(0,0,0,0)',
        'plot_bgcolor':'#C0C0C0',
        'margin':{'l':20, 'r':20, 't':10, 'b':35}
    }

    CT_ramp_fig = go.Figure(data=ramp_data, layout=ramp_layout)
    
    return CT_ramp_fig


def colour_rows(d):
    '''
    Used to apply a style to rows of a table, namely the colour-coding.
    '''
    c_style=[{'if': {'column_id': 'Name'}, 'textAlign': 'left'},]
    
    for i in range(len(d)):
        row = d[i]
        name = row['Name']
        colour = row['Colour']
        c_style.append({'if': {'row_index':i}, 'backgroundColor': str(colour)})

    return c_style


def stretch_CT(table):
    '''
    Used to stretch the shaded material rectangles in the CT ramp plot
    to cover the whole range of HU values. 
    Lower CT value of the first material changes to lowest HU value in the range.
    Upper CT value of the last material changes to highest HU value in the range.
    Lower CT value of each material serves as the start of each shaded region
    for materials in between the first and last material.
    '''
    
    global HU
    CTL = min(HU)
    CTH = max(HU)
    
    mat = [i.Name for i in table]
    try:
        low_bound = [int(i.MinCT) for i in table]
    except:
        raise PreventUpdate
    
    
    if len(mat) == 1 or len(mat) == 0:
        s_low, s_mat = low_bound, mat
    else:
        s_low, s_mat = zip(*sorted(zip(low_bound, mat)))

    
    for item in table:
        if item.Name == s_mat[0]:
            item.MinCT = int(CTL)
        if item.Name == s_mat[-1]:
            item.MaxCT = int(CTH)
    
    for item in table:
        indx = s_mat.index(item.Name)
        
        item.Number = indx+1
        
        try:
            item.MaxCT = int(s_low[indx+1])
        except:
            pass
        
        
    return table

def write_input_file(phantom_file_path, applicator, x, y, z, theta, phi, col, phsp_file_path):

    dosinputfilepath = gui_save_file('Save DOSXYZnrc input file as', "DOSXYZnrc input files (*.egsinp)|*.egsinp||")
    dosinputfilepath += '.egsinp'
    f = open(dosinputfilepath, 'w')

    print('Writing dosxyznrc input file...')
    #Line 1 = Number of media in the phantom
    #f.write(' {}\n' .format(dosinputfilepath))
    f.write('CT_phantom_input \n')
    f.write('0 \n')
    f.write('/home/physics/Desktop/KV_Phantoms/{} \n' .format(phantom_file_path))
    f.write('0.521, 0.001, 0 \n')
    f.write('1, 0, 0, \n')
    f.write('0, 2, {}, {}, {}, {}, {}, 0, {}, 1, {}, {}, {}, 0 \n' .format(round(x/10,2),round(y/10,2),round(z/10,2),round(theta,2),round(phi,2),round(col,2),dbs_parameters[applicator][0],dbs_parameters[applicator][1],dbs_parameters[applicator][1]))
    f.write('2, 0, 0, 0, 0, 0, 0, 0 \n')
    f.write('/home/physics/EGSnrc/egs_home/kv_phsp/' + phsp_file_path + ' \n')
    f.write('{}, 0, 999, 33, 97, 100, 0, 0, 0, 0, , 0, 0, 0, 200, 0, 0 \n' .format(simulation_histories))
    f.write(' ######################### \n')
    f.write(' :Start MC Transport Parameter: \n')
    f.write(' \n')
    f.write(' Global ECUT= 0.521 \n')
    f.write(' Global PCUT= 0.001 \n')
    f.write(' Global SMAX= 5 \n')
    f.write(' ESTEPE= 0.25 \n')
    f.write(' XIMAX= 0.5 \n')
    f.write(' Boundary crossing algorithm= EXACT \n')
    f.write(' Skin depth for BCA= 1e10 \n')
    f.write(' Electron-step algorithm= PRESTA-II \n')
    f.write(' Spin effects= On \n')
    f.write(' Brems angular sampling= KM \n')
    f.write(' Brems cross sections= NIST \n')
    f.write(' Bound Compton scattering= On \n')
    f.write(' Compton cross sections= default \n')
    f.write(' Pair angular sampling= Off \n')
    f.write(' Pair cross sections= NRC \n')
    f.write(' Photoelectron angular sampling= On \n')
    f.write(' Rayleigh scattering= On \n')
    f.write(' Atomic relaxations= On \n')
    f.write(' Electron impact ionization= On \n')
    f.write(' Photon cross sections= mcdf-xcom \n')
    f.write(' Photon cross-sections output= Off \n')
    f.write(' \n')
    f.write(' :Stop MC Transport Parameter: \n')
    f.write(' ######################### \n')

    f.close()

    print('Finished writing dosxyznrc input file!')

# 3D Plotting Functions

def make_mesh(image, threshold=-300, step_size=1):
    '''
    This function creates a mesh which can be used to 3D plot the CT cube
    with a threshold (minimum) HU value.
    '''
 
    if SCAN.cropped_zs[0]>SCAN.cropped_zs[-1]:
        image = np.flip(image,0)
        
    if SCAN.cropped_ys[0]>SCAN.cropped_ys[-1]:
        image = np.flip(image,1)
        
    if SCAN.cropped_xs[0]>SCAN.cropped_xs[-1]:
        image = np.flip(image,2)
    
    print('Calculating 3D surface...')
    verts, faces, norm, val = measure.marching_cubes(
                                                        image,
                                                        threshold,
                                                        spacing=(SCAN.z_step, SCAN.y_step, SCAN.x_step),
                                                        step_size=step_size,
                                                        allow_degenerate=True)
    
    #Original verts are positioned in the positive quadrant in x,y,z starting at the origin (0,0,0)
    #These verts need to be shifted in order to position CT cube isocentre onto the 3D plot origin
    for v in verts:
        v[0] += min(SCAN.cropped_zs) 
        v[1] += min(SCAN.cropped_ys) 
        v[2] += min(SCAN.cropped_xs) 
    
    x,y,z = zip(*verts)
    
    colormap=['rgb(211, 211, 211)','rgb(200, 200, 200)'] 
    
    vertices = np.vstack((x,y,z)).T
    faces = np.asarray(faces)
    I, J, K = faces.T

    CT3D_figure = go.Mesh3d(x=z,
                     y=y,
                     z=x,
                     colorscale=colormap, 
                     intensity=z,
                     i=I,
                     j=J,
                     k=K,
                     name='',
                     showscale=False
                    )

    layout = {'scene':{'aspectmode':'data',
                      'bgcolor':'#272b30',
                         'xaxis' : {'tickfont':{
                                    'color':'white',
                                    'size':15},
                                    'backgroundcolor':"rgb(230, 230,200)",
                                    'gridcolor':"white",
                                    'showbackground':False,
                                    'zerolinecolor':"#01bf01",},
                            'yaxis' : {'tickfont':{
                                    'color':'white',
                                    'size':15},
                                    'backgroundcolor':"rgb(230, 230,200)",
                                    'gridcolor':"white",
                                    'showbackground':False,
                                    'zerolinecolor':"#01bf01",},
                            'zaxis' : {'tickfont':{
                                        'color':'white',
                                        'size':15
                                        },
                                    'backgroundcolor':"rgb(230, 230,200)",
                                    'gridcolor':"white",
                                    'showbackground':False,
                                    'zerolinecolor':"#01bf01",
                                    },
                         'xaxis_title':{'font':{'color':'white',
                                    'size':30}},
                         'yaxis_title':{'font':{'color':'white',
                                    'size':30}},
                         'zaxis_title':{'font':{'color':'white',
                                    'size':30}},},
             'margin':{'l':5, 'r':5, 't':5, 'b':5},
             'hoverlabel':{'bgcolor':'orange'}}

    
    fig1 = go.Figure(data=CT3D_figure, layout=layout)
    
    SCAN.threeD_figure = fig1
    print('3D CT surface calculated!')

    return fig1


def genRECT(length, width, height):
    '''
    Used to generate a rectangular plane representing the PHSP file.
    '''
    #Creating x, y, z coordinates of initial plane
    xx = np.linspace(-length*10/2, length*10/2, int((length/2)+1), endpoint=True)
    yy = np.linspace(-width*10/2, width*10/2, int((width/2)+1), endpoint=True)
    zz = 0 #height

    #Creating a set of points for transformations
    start_plane = [(i,j,height) for i in xx for j in yy]    
    
    return start_plane


def genCIRC(diameter, height):
    '''
    Used to generate a circular plane representing the PHSP file.
    '''
    #Creating x, y, z coordinates of initial plane
    theta = np.linspace(0, 2*np.pi)

    d = diameter*10/2
    
    start_plane = [(d*np.cos(angle), d*np.sin(angle), height) for angle in theta]
    
    return start_plane


def move_plane(plane, spin, theta, phi):
    '''
    Used to move the PHSP plane in spherical polar space
    after rotating it through the given angles.
    Order of rotations matters (I think)
    '''
    spinned_plane = []

    for point in plane:
        new_point = rotateSPIN(point, spin)
        spinned_plane.append(new_point)
        
    theta_plane = []

    for point in spinned_plane:
        new_point = rotateTHETA(point, theta)
        theta_plane.append(new_point)
        
    phi_plane = []

    for point in theta_plane:
        new_point = rotatePHI(point, phi)
        phi_plane.append(new_point)
    
    return phi_plane


def EXT_pts(plane):
    '''
    Used to extract x, y, z values from points of the plane.
    '''
    x = [point[0] for point in plane]
    y = [point[1] for point in plane]
    z = [point[2] for point in plane]
    
    return x,y,z


def rotateSPIN(point,alpha):
    '''
    Used to rotate the plane in its own plane (clockwise).
    '''
    #Spin the plane (0-360)
    x = point[0]
    y = point[1]
    x_prime = x*np.cos(np.deg2rad(-alpha)) - y*np.sin(np.deg2rad(-alpha))
    y_prime = y*np.cos(np.deg2rad(-alpha)) + x*np.sin(np.deg2rad(-alpha))
    
    return [round(x_prime,2), round(y_prime,2), point[2]]
    
def rotateTHETA(point,alpha):
    '''
    Used to rotate the plane by the angle theta in
    spherical polar coordinates.
    
    '''
    #Theta rotation (0-180)
    x = point[0]
    z = point[2]
    x_prime = x*np.cos(np.deg2rad(-alpha)) - z*np.sin(np.deg2rad(-alpha))
    z_prime = z*np.cos(np.deg2rad(-alpha)) + x*np.sin(np.deg2rad(-alpha))
    
    return [round(x_prime,2), point[1], round(z_prime,2)]
    
def rotatePHI(point,alpha):
    '''
    Used to rotate the plane by the angle phi in
    spherical polar coordinates.
    
    '''
    #Spin the plane (0-360)
    x = point[0]
    y = point[1]
    x_prime = x*np.cos(np.deg2rad(alpha)) - y*np.sin(np.deg2rad(alpha))
    y_prime = y*np.cos(np.deg2rad(alpha)) + x*np.sin(np.deg2rad(alpha))
    
    return [round(x_prime,2), round(y_prime,2), point[2]]
    


# Phantom Creation

def write_phantom_file(imgs, b_x, b_y, b_z, folder, table):
    '''
    This funtion creates a text document with .egsphant extension
    which is used to interpret the phantom by BEAMnrc simulations.
    The extra spacing in the strings is required for correct 
    formatting of the egsphant file. In newer versions of DOSXYZnrc
    (2018+) the formatting may be different!
    '''
    SCAN.phantom_created == False
    SCAN.progress = 0
    
    global HU, Den
    f = open(folder + '.egsphant', 'w')

    print('Writing media...')
    #Line 1 = Number of media in the phantom
    f.write(' {}\n' .format(len(table)))

    #Sorting the list of materials by material number which is dependent on min CT value
    sorted_table = [0] * len(table)
    for item in table:
        sorted_table[item.Number-1] = item.Name
        
    #Line 2 = Names of the media (each on new line)
    for item in sorted_table:
        f.write(str(item) + '      \n')


    #Line 3 = Dummy ESTEPE = 1.00000000 for each medium
    f.write('   ')
    for item in table:
        f.write('1.00000000       ')
    f.write('\n')

    print('Finished writing media...')


    print('Writing boundaries...')

    #Line 4 = Number of x, y, z voxels
    f.write('  ' + str(imgs.shape[2]) + '  ' + str(imgs.shape[1]) + '  ' + str(imgs.shape[0]) + '\n')


    #Line 5 = Voxel boundaries in x
    f.write('   ')
    for boundary in b_x:
        f.write(str(round(boundary/10,8)) + '      ')
    f.write('\n')

    print('Finished x boundaries!')

    #Line 6 = Voxel boundaties in y
    f.write('   ')
    for boundary in b_y:
        f.write(str(round(boundary/10,8)) + '      ')
    f.write('\n')

    print('Finished y boundaries!')

    #Line 7 = Voxel boundaries in z
    f.write('   ')
    for boundary in b_z:
        f.write(str(round(boundary/10,8)) + '      ')
    f.write('\n')

    print('Finished z boundaries!')

    print('Finished writing boundaries!')



    print('Writing material numbers...')


    #Line 8 = XY array with medium number in each voxel for each z slice

    #=====ASSIGNING MATERIALS TO VOXELS=====
    minimumCT = min([int(item.MinCT) for item in table])
    maximumCT = max([int(item.MaxCT) for item in table])
    
    mat_number_cube = np.copy(imgs)
    for material in table:
        minct = material.MinCT
        maxct = material.MaxCT

        #if len(str(material.Number))==2:
        #    num = str(material.Number)
        #elif len(str(material.Number))==1:
        #    num = '0' + str(material.Number)

        mat_number_cube[(imgs<maxct)*(imgs>=minct)]=material.Number

        if minct==minimumCT: #If the current material has the lowest HU value range:
            mat_number_cube[imgs<=minct]=material.Number
        elif maxct==maximumCT: #If the current material has the highest HU value range:
            mat_number_cube[imgs>=maxct]=material.Number

    i=0
    for z in mat_number_cube:
        for y in z:
            for x in y:

                f.write("{:02d}".format(x))

            f.write('\n')
        f.write('\n')
        print('Material slice {}/{} completed!'.format(i+1, len(mat_number_cube)))
        
        
        # update completion percentage so it's available from front-end###########################
        SCAN.progress = 50 * (i + 1) / len(mat_number_cube)
        #job.meta["progress"] = 
        #job.save_meta()
        ###############################################################
        
        
        i+=1

    print('Finished writing material numbers!')


    print('Writing densities...')

    #Line 9 = XY array with densities in each voxel for each z slice

    #=====ASSIGNING DENSITIES TO VOXELS=====
    j=0
    for z in imgs:
        for y in z:
            f.write(' ')
            for x in y:

                #Anything outside of CT ramp to the right will be 20 g/cm3 = Gold
                x_den = np.interp(x, HU, Den, right=20)

                f.write(str(round(x_den,9)) + '      ')

            f.write('\n')
        f.write('\n')
        print('Density slice {}/{} completed!'.format(j+1, len(imgs)))
        
        SCAN.progress = 50 + (50 * (j + 1) / len(imgs))
        
        j+=1

    print('Finished writing densities!')

    print('EGSphant file created!')
    SCAN.phantom_created = True

    f.close()


#CSS colour + styling
colors = {
    'background':'#1c1e22',
    'text': '#FF8000',
    'borders': '#FF8000',
    'purple':'#6600CC'
}

tabs_styles = {
    'height': '5vh',
    'font-size': '3vh',
    'fontWeight': 'bold',
    'marginLeft':'1.5vh',
    'marginRight':'1.5vh',
    'marginBottom':'1.5vh',
    'marginTop':'1.5vh',
}
tab_style = {
    'borderTop': '1px solid white',
    'borderBottom': '1px solid white',
    'borderRight': '1px solid white',
    'borderLeft': '1px solid white',
    'backgroundColor': '#3a3f44',
    'color': 'white',
    'padding': '0',
}

tab_selected_style = {
    'borderColor': colors['text'],
    'borderTop': '3px solid ',    
    'borderBottom': '3px solid ',
    'borderRight': '3px solid ',
    'borderLeft': '3px solid ',
    'backgroundColor': colors['background'],
    'color': colors['text'],
    'padding': '0',
}

#=====================================================================================
#======================================APPLICATION====================================
#=====================================================================================

app = dash.Dash(__name__)

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.config.suppress_callback_exceptions = True

app.title = 'OrthoPlan'
app._favicon='favicon_p.ico'

SCAN = 1
del SCAN

#=====================================================================================
#============================APPLICATION LAYOUT=======================================
#=====================================================================================

app.layout = html.Div(
    style={'backgroundColor': colors['background'],
           'borderTop': '0.5vh solid #FF8000',
           'borderBottom': '0.5vh solid #FF8000',
           'borderLeft': '0.3vw solid #FF8000',
           'borderRight': '0.3vw solid #FF8000',
           'height':'100vh'
          },
    children=[
        html.Div(
            style={
                'height':'6vh',#'5vh',
                'width':'100%',
                'backgroundColor':colors['background'],
                'borderBottom':'0.5vh solid #FF8000',
                #'paddingBottom': '5vh',
                
            },
            children=[
                html.H1(
                    children=app.title,
                    style={
                        'height':'100%',
                        'textAlign': 'center',
                        'font-family': 'Arial, Helvetica, sans-serif',
                        #'paddingBottom': '1%',
                        #'marginTop': '0.7vh',
                        #'marginBottom': '0.7vh',
                        'font-size':'5vh',
                        #'background-image': 'linear-gradient(#f79800,#EF3405)',#'linear-gradient(#1c1e22, #000000)'
                        #'background': '-webkit-linear-gradient(#f79800,#EF3405)',
                        #'background-clip': 'text',
                        #'-webkit-text-fill-color': '-webkit-linear-gradient(#f79800,#EF3405)',#'transparent',
                        #'color':'linear-gradient(#f79800,#EF3405)',#'transparent',
                        'letter-spacing':'0.5vw',
                        'font-weight':'bold',
                        'background-image': '-webkit-linear-gradient(#f79800,#EF3405)',
                          '-webkit-background-clip': 'text',
                          '-webkit-text-fill-color': 'transparent',
                    }
                ),
            ]
        ),
        
        html.Div(
            style={
                'height':'93vh',
                'width':'100%',
                'backgroundColor':colors['background'],
            },
            children=[
                dcc.ConfirmDialog(
                    id='imported_CT',
                    message='',
                ),
                
                dcc.ConfirmDialog(
                    id='imported_structs',
                    message='',
                ),
                dcc.ConfirmDialog(
                    id='update_hu_message',
                    message='',
                ),
                dcc.ConfirmDialog(
                    id='accept_ct_message',
                    message='',
                ),
                
                dcc.Tabs(
                    style=tabs_styles,
                    children=[

                        dcc.Tab(
                            label='Import',
                            style=tab_style,
                            selected_style=tab_selected_style,
                            children=[
                                html.Div(
                                    children=[
                                        html.Div(
                                            style={
                                                'backgroundColor': '#272b30',
                                                'height':'100%',
                                                'width':'20%',
                                                'display':'inline-block'
                                            },
                                            children=[
                                                                                                
                                                html.Button(
                                                    'Import CT Folder',
                                                    id = 'B_import_ct',
                                                    n_clicks = None,
                                                    title='Select a folder containing DICOM CT files',
                                                    style={'marginTop':'1vh', 'marginBottom':'1vh', 'width':'90%','height':'5.5vh',
                                                          'marginLeft':'5%', 'marginRight':'5%',}
                                                ),
                                                
                                                html.Div(
                                                    id='scan_info_table',
                                                    style={
                                                    'min-height':'3vh',
                                                        'backgroundColor': colors['background'],
                                                        'width':'96%',
                                                        'height':'26vh',
                                                        'maxWidth':'96%',
                                                        'margin':'auto',
                                                        'padding':'1%',
                                                        'overflow-x': 'auto'
                                                    },
                                                    children=[          
                                                    ]
                                                ),

                                                html.Button(
                                                    'Import Structure Set',
                                                    id = 'B_import_struct',
                                                    n_clicks = None,
                                                    title='Select a DICOM structure set file',
                                                    style={'marginTop':'1vh', 'marginBottom':'1vh', 'width':'90%', 'height':'5.5vh',
                                                          'marginLeft':'5%', 'marginRight':'5%',}
                                                ),

                                                html.Div(
                                                    id='structures_checkboxes',
                                                    style={
                                                    'min-height':'3vh',
                                                        'backgroundColor': colors['background'],
                                                        'width':'96%',
                                                        'margin':'auto',
                                                        'padding':'1%',
                                                        'height': '42vh', 
                                                        'overflow-y': 'auto'
                                                    },
                                                    children=[

                                                        dcc.Checklist(
                                                            id='structures_checklist',
                                                            options=[],
                                                            value=[],
                                                            style={'color': 'white',
                                                                    'font-size': '3vh'
                                                            },
                                                            labelStyle={'color':'white'},
                                                            inputStyle={'height':'2vh',
                                                                    'width':'2vw',
                                                                    'margin-right': '0.2vw'}
                                                        )
                                                    ]
                                                ), 
                                            ]
                                        ),
                                        
                                        html.Div(
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'100%',
                                                'width':'60%',
                                                'display':'inline-block',
                                                'vertical-align':'top'
                                            },
                                            children=[
                                                html.Div(
                                                    id='main_plot',
                                                    style={
                                                        'backgroundColor': '#272b30',
                                                        'height':'70vh',
                                                        'width':'33vw',
                                                        'marginLeft':'1vw',
                                                        'marginTop':'1vh',
                                                        'display':'inline-block'
                                                    },
                                                    children=[

                                                    ]
                                                ),
                                                
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'70vh',
                                                        'width':'17vw',
                                                        'marginLeft':'1vw',
                                                        'marginTop':'1vh',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        
                                                        html.Div(
                                                            id='sub1_plot',
                                                            style={
                                                                'backgroundColor': '#272b30',
                                                                'height':'34.5vh',
                                                                'width':'100%',
                                                                'display':'block'
                                                            },
                                                            children=[

                                                            ]
                                                        ),  
                                                        
                                                        html.Div(
                                                            id='sub2_plot',
                                                            style={
                                                                'backgroundColor': '#272b30',
                                                                'height':'34.5vh',
                                                                'width':'100%',
                                                                'marginTop':'1vh',
                                                                'display':'block'
                                                            },
                                                            children=[

                                                            ]
                                                        ),  
                                                    ]
                                                ),                                                
                                                
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'70vh',
                                                        'width':'1vw',
                                                        'marginLeft':'1vw',
                                                        'marginTop':'1vh',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        dcc.RangeSlider(
                                                            id='WLCT',
                                                            min=-1000,
                                                            max=1000,
                                                            marks=None,
                                                            #value=[-1000, 1000],
                                                            allowCross=False,
                                                            included=True,
                                                            step=1,
                                                            vertical=True,
                                                            className='slider',
                                                            tooltip={'always visible':True,
                                                                     'placement':'left'}
                                                        ),
                                                    ]
                                                ),
                                                
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'7vh',
                                                        'width':'100%',
                                                        'marginTop':'2vh'                                                        
                                                    },
                                                    children=[
                                                        
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'100%',
                                                                'width':'33vw',
                                                                'marginLeft':'1vw',
                                                                'display':'inline-block'
                                                            },
                                                            children=[
                                                                dcc.Slider(
                                                                    id='slider_CT',
                                                                    min=0,
                                                                    max=1,
                                                                    value=1,
                                                                    marks=[],
                                                                    tooltip={'always visible':True,
                                                                            'placement':'top'}
                                                                )
                                                            ]
                                                        ),
                                                        
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'100%',
                                                                'width':'22vw',
                                                                'marginLeft':'1vw',
                                                                'display':'inline-block',
                                                                'vertical-align':'top'
                                                            },
                                                            children=[
                                                                dcc.RadioItems(
                                                                    id='tab1_view_CT',
                                                                    options=[
                                                                        {'label': 'Axial', 'value': 'A'},
                                                                        {'label': 'Saggital', 'value': 'S'},
                                                                        {'label': 'Coronal', 'value': 'C'}
                                                                    ],
                                                                    value='A',
                                                                    labelStyle={'display':'inline-block',
                                                                               'font-size':'1.5vw',
                                                                               'color':'white'},
                                                                    inputStyle={'height':'2.5vh',
                                                                               'margin-left': '1vw',
                                                                               'margin-right': '0.5vw'}
                                                                )
                                                            ]
                                                        ),
                                                    ]
                                                ),
                                            ]
                                        ),
                                        
                                        html.Div(
                                            style={
                                                'backgroundColor': '#272b30',
                                                'height':'100%',
                                                'width':'20%',
                                                'display':'inline-block',
                                                'vertical-align':'top'
                                            },
                                            children=[
                                                html.H3(
                                                    children='HU Changer',
                                                    style={
                                                        'textAlign': 'center',
                                                        'color': colors['text'],
                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                        'padding': '0',
                                                        'marginTop': '1vh',
                                                        'paddingBottom':'2%',
                                                        'borderBottom':'0.1vh solid #FF8000'
                                                    }
                                                ),
                                                
                                                html.H4(
                                                    children='Select a structure:',
                                                    style={
                                                        'textAlign': 'left',
                                                        'color': colors['text'],
                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                        'padding': '0',
                                                        'marginTop': '2vh',
                                                        'marginLeft':'2%'
                                                    }
                                                ),
                                                
                                                dcc.Dropdown(
                                                    id='HU_ch_dropdown',
                                                    options=[
                                                    ],
                                                    value=None,
                                                    style={
                                                        'width':'90%',
                                                        'marginLeft':'5%',
                                                        'marginRight':'5%',
                                                        'height':'4vh',
                                                    }
                                                ),
                                                
                                                html.H4(
                                                    children='Enter new HU:',
                                                    style={
                                                        'textAlign': 'left',
                                                        'color': colors['text'],
                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                        'padding': '0',
                                                        'marginTop': '3vh',
                                                        'marginLeft':'2%'
                                                    }
                                                ),
                                                
                                                dcc.Input(
                                                    id='new_HU',
                                                    type='number',
                                                    placeholder='Enter new HU',
                                                    value=None,
                                                    debounce=True,
                                                    inputMode='numeric',
                                                    step=1,
                                                    style={
                                                        'width':'90%',
                                                        'marginLeft':'5%',
                                                        'marginRight':'5%'
                                                    }
                                                ),
                                                
                                                html.Button(
                                                    'Change HU value',
                                                    id = 'B_change_hu',
                                                    n_clicks = None,
                                                    title='Change HU value of the selected structure',
                                                    style={'marginTop':'3vh', 'marginBottom':'1vh', 'width':'90%', 'height':'5.5vh',
                                                          'marginLeft':'5%', 'marginRight':'5%',}
                                                ),
                                                
                                                html.Button(
                                                    'Accept CT images',
                                                    id = 'B_accept',
                                                    n_clicks = None,
                                                    title='Accept currently displayed data',
                                                    style={'marginTop':'10%', 'width':'90%', 'height':'5.5vh',
                                                          'marginLeft':'5%', 'marginRight':'5%',}
                                                           #'color':'black','backgroundColor':'#009900'}
                                                ),
                                            ]
                                        )
                                    ],
                                    style={
                                        'backgroundColor': 'green',
                                        'height':'84vh',
                                        'marginLeft':'1.5vh',
                                        'marginRight':'1.5vh'
                                    }
                                ),
                            ]
                        ),

                        dcc.Tab(
                            label='Region of Interest',
                            style=tab_style,
                            selected_style=tab_selected_style,
                            children=[
                                html.Div(
                                    children=[
                                                
                                        html.Div(
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'70%',
                                                'width':'100%',
                                                'display':'inline-block',
                                                'vertical-align':'bottom'
                                            },
                                            children=[
                                                dcc.ConfirmDialog(
                                                    id='accept_roi_message',
                                                    message='',
                                                ),
                                                html.Div(
                                                    id='ROI_plot1',
                                                    style={
                                                        'backgroundColor': '#272b30',
                                                        'height':'95%',
                                                        'width':'30%',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[

                                                    ]
                                                ),

                                                html.Div(
                                                    id='ROI_plot2',
                                                    style={
                                                        'backgroundColor': '#272b30',
                                                        'height':'95%',
                                                        'width':'30%',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[

                                                    ]
                                                ),

                                                html.Div(
                                                    id='ROI_plot3',
                                                    style={
                                                        'backgroundColor': '#272b30',
                                                        'height':'95%',
                                                        'width':'30%',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[

                                                    ]
                                                ),
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'95%',
                                                        'width':'5%',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        dcc.RangeSlider(
                                                            id='ROI_CT_window',
                                                            min=-1000,
                                                            max=1000,
                                                            marks=None,
                                                            value=[-1000, 1000],
                                                            allowCross=False,
                                                            included=True,
                                                            step=1,
                                                            vertical=True,
                                                            className='slider',
                                                            tooltip={'always visible':True,
                                                                     'placement':'left'}
                                                        ),
                                                    ]
                                                )
                                            ]
                                        ),

                                        html.Div(
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'6%',
                                                'width':'100%',
                                                'display':'inline-block'
                                            },
                                            children=[
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'100%',
                                                        'width':'30%',
                                                        'marginLeft':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        dcc.Slider(
                                                            id='ROI_slider1',
                                                            min=0,
                                                            max=1,
                                                            value=1,
                                                            marks=[],
                                                            tooltip={'always visible':True,
                                                                    'placement':'top'}
                                                        )
                                                    ]
                                                ),

                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'100%',
                                                        'width':'30%',
                                                        'marginLeft':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        dcc.Slider(
                                                            id='ROI_slider2',
                                                            min=0,
                                                            max=1,
                                                            value=1,
                                                            marks=[],
                                                            tooltip={'always visible':True,
                                                                    'placement':'top'}
                                                        )
                                                    ]
                                                ),
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'100%',
                                                        'width':'30%',
                                                        'marginLeft':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        dcc.Slider(
                                                            id='ROI_slider3',
                                                            min=0,
                                                            max=1,
                                                            value=1,
                                                            marks=[],
                                                            tooltip={'always visible':True,
                                                                    'placement':'top'}
                                                        )
                                                    ]
                                                ),

                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'100%',
                                                        'width':'5%',
                                                        'marginLeft':'1%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    },
                                                    children=[
                                                        html.H3(
                                                            children='Slicer',
                                                            style={
                                                                'textAlign': 'center',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'marginTop':'0',
                                                                'padding':'0'
                                                            }
                                                        ),
                                                    ]
                                                ),     
                                            ]
                                        ),

                                        html.Div(
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'6%',
                                                'width':'100%',
                                                'display':'inline-block'
                                            },
                                            children=[
                                                html.Div(
                                                    style={
                                                        'backgroundColor': '#CC0000',
                                                        'borderRadius':'5px',
                                                        'height':'100%',
                                                        'width':'30%',
                                                        'marginLeft':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        dcc.RangeSlider(
                                                            id='ROI_rangez',
                                                            min=-1000,
                                                            max=1000,
                                                            marks=None,
                                                            value=[-1000, 1000],
                                                            allowCross=False,
                                                            included=True,
                                                            step=1,
                                                            className='rangeslider',
                                                            tooltip={'always visible':True,
                                                                     'placement':'left'}
                                                        ),
                                                    ]
                                                ),
                                                html.Div(
                                                    style={
                                                        'backgroundColor': '#0000CC',
                                                        'borderRadius':'5px',
                                                        'height':'100%',
                                                        'width':'30%',
                                                        'marginLeft':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        dcc.RangeSlider(
                                                            id='ROI_rangex',
                                                            min=-1000,
                                                            max=1000,
                                                            marks=None,
                                                            value=[-1000, 1000],
                                                            allowCross=False,
                                                            included=True,
                                                            step=1,
                                                            className='rangeslider',
                                                            tooltip={'always visible':True,
                                                                     'placement':'left'}
                                                        ),
                                                    ]
                                                ),

                                                html.Div(
                                                    style={
                                                        'backgroundColor': '#00CC00',
                                                        'borderRadius':'5px',
                                                        'height':'100%',
                                                        'width':'30%',
                                                        'marginLeft':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        dcc.RangeSlider(
                                                            id='ROI_rangey',
                                                            min=-1000,
                                                            max=1000,
                                                            marks=None,
                                                            value=[-1000, 1000],
                                                            allowCross=False,
                                                            included=True,
                                                            step=1,
                                                            className='rangeslider',
                                                            tooltip={'always visible':True,
                                                                     'placement':'left'}
                                                        ),
                                                    ]
                                                ),

                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'100%',
                                                        'width':'5%',
                                                        'marginLeft':'1%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    },
                                                    children=[
                                                        html.H3(
                                                            children='Cropper',
                                                            style={
                                                                'textAlign': 'center',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'marginTop':'0',
                                                                'padding':'0'
                                                            }
                                                        ),
                                                    ]
                                                ),
                                            ]
                                        ),

                                        html.Div(
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'17%',
                                                'width':'100%',
                                                'display':'inline-block'
                                            },
                                            children=[
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'100%',
                                                        'width':'50%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    },
                                                    children=[
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'33%',
                                                                'width':'100%',
                                                                'marginLeft':'1%',
                                                                'display':'inline-block',
                                                                'vertical-align':'top'
                                                            },
                                                            children=[
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'30%',
                                                                        'marginLeft':'10%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            children='# X voxels = ',
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'5%',
                                                                                'marginTop':'0',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                ),
                                                                
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'30%',
                                                                        'marginLeft':'1%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            id='xvoxnum',
                                                                            children=0,
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'5%',
                                                                                'marginTop':'0',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                )         
                                                            ]
                                                        ),

                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'33%',
                                                                'width':'100%',
                                                                'marginLeft':'1%',
                                                                'display':'inline-block'
                                                            },
                                                            children=[
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'30%',
                                                                        'marginLeft':'10%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            children='# Y voxels = ',
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'5%',
                                                                                'marginTop':'0',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                ),
                                                                
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'30%',
                                                                        'marginLeft':'1%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            id='yvoxnum',
                                                                            children=0,
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'5%',
                                                                                'marginTop':'0',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                )
                                                            ]
                                                        ),

                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'33%',
                                                                'width':'100%',
                                                                'marginLeft':'1%',
                                                                'display':'inline-block'
                                                            },
                                                            children=[
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'30%',
                                                                        'marginLeft':'10%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            children='# Z voxels = ',
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'5%',
                                                                                'marginTop':'0',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                ),
                                                                
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'30%',
                                                                        'marginLeft':'1%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            id='zvoxnum',
                                                                            children=0,
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'5%',
                                                                                'marginTop':'0',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                )
                                                            ]
                                                        ),
                                                    ]
                                                ),

                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'100%',
                                                        'width':'43%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    },
                                                    children=[
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'50%',
                                                                'width':'100%',
                                                                'display':'inline-block'
                                                            },
                                                            children=[
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'35%',
                                                                        'marginLeft':'0%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            children='# Total voxels = ',
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'5%',
                                                                                'marginTop':'8%',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                ),
                                                                
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'35%',
                                                                        'marginLeft':'10%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            id='totvoxnum',
                                                                            children=0,
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'1%',
                                                                                'marginTop':'8%',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                )
                                                            ]
                                                        ),

                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'50%',
                                                                'width':'100%',
                                                                'display':'inline-block'
                                                            },
                                                            children=[
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'35%',
                                                                        'marginLeft':'0%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            children='Max allowed voxels = ',
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'5%',
                                                                                'marginTop':'0',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                ),
                                                                
                                                                html.Div(
                                                                    style={
                                                                        'backgroundColor': colors['background'],
                                                                        'height':'100%',
                                                                        'width':'35%',
                                                                        'marginLeft':'10%',
                                                                        'display':'inline-block',
                                                                        'vertical-align':'top'
                                                                    },
                                                                    children=[
                                                                        html.H4(
                                                                            children=max_DOSXYZ_voxels,
                                                                            style={
                                                                                #'textAlign': 'center',
                                                                                'color': colors['text'],
                                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                                'marginLeft':'1%',
                                                                                'marginTop':'0',
                                                                                'padding':'0'
                                                                            }
                                                                        ),
                                                                        
                                                                    ]
                                                                )
                                                            ]
                                                        ),
                                                    ]
                                                ),

                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'100%',
                                                        'width':'7%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    },
                                                    children=[
                                                        html.Button(
                                                            'Accept',
                                                            id = 'B_OK',
                                                            n_clicks = None,
                                                            title='Accept displayed ROI',
                                                            style={'width':'100%',
                                                                  'marginTop':'20%', 'height':'5.5vh',
                                                                  'font-size':'0.8vw'} 
                                                                   #'color':'black','backgroundColor':'#009900'}
                                                        ),
                                                    ]
                                                ), 

                                            ]
                                        ),
                                    ],
                                    style={
                                        'backgroundColor': colors['background'],
                                        'height':'84vh',
                                        'marginLeft':'1.5vh',
                                        'marginRight':'1.5vh'
                                    }
                                ),
                            ]
                        ),

                        dcc.Tab(
                            label='Tissue Segmentation',
                            style=tab_style,
                            selected_style=tab_selected_style,
                            children=[
                                html.Div(
                                    children=[
                                        html.Div(
                                            children=[
                                                html.Div(
                                                    id='CT_map',
                                                    style={
                                                        'backgroundColor': '#272b30',
                                                        'height':'45%',
                                                        'width':'95%',
                                                        'marginLeft':'2.5%',
                                                        'marginTop':'1%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    },
                                                    children=[

                                                    ]
                                                ),
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'48%',
                                                        'width':'25%',
                                                        'marginLeft':'1%',
                                                        'marginTop':'2%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    },
                                                    children=[
                                                        html.H2(
                                                            children='Preset',
                                                            style={
                                                                #'textAlign': 'center',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'marginLeft':'5%',
                                                                'marginTop':'1%',
                                                                'paddingBottom':'2%',
                                                                'borderBottom':'0.1vh solid #FF8000'
                                                            }
                                                        ),
                                                        
                                                        dcc.RadioItems(
                                                            id='tissue_preset',
                                                            options=[
                                                                {'label': 'Head and Neck', 'value': 'HN'},
                                                                {'label': 'Torso', 'value': 'T'},
                                                                {'label': 'Extremities', 'value': 'A'},
                                                                {'label': 'CIRS Phantom', 'value': 'CIRS'}
                                                            ],
                                                            value='',
                                                            labelStyle={#'display':'inline-block',
                                                                       'font-size':'1.5vw',
                                                                       'color':'white'},
                                                            inputStyle={'height':'20px',
                                                                       'margin-left': '2px',
                                                                       'margin-right': '5px'}
                                                        )
                                                    ]
                                                ),
                                                                                                
                                                html.Div(
                                                    id='table_container',
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'44%',
                                                        'width':'72%',
                                                        'marginLeft':'1%',
                                                        'marginTop':'5%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    },
                                                    children=[
                                                        
                                                    ]
                                                ),
                                            ],
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'100%',
                                                'width':'50%',
                                                'display':'inline-block',                                                
                                            }
                                        ),
                                        
                                        html.Div(
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'100%',
                                                'width':'50%',
                                                'display':'inline-block',
                                                'vertical-align':'top'
                                            },
                                            children=[
                                                html.Div(
                                                    id='main_plot_tissue',
                                                    style={
                                                        'backgroundColor': '#272b30',
                                                        'height':'74%',
                                                        'width':'60%',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[

                                                    ]
                                                ),
                                                
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'74%',
                                                        'width':'37%',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        
                                                        html.Div(
                                                            id='sub1_plot_tissue',
                                                            style={
                                                                'backgroundColor': '#272b30',
                                                                'height':'49%',
                                                                'width':'100%',
                                                                'display':'block'
                                                            },
                                                            children=[

                                                            ]
                                                        ),  
                                                        
                                                        html.Div(
                                                            id='sub2_plot_tissue',
                                                            style={
                                                                'backgroundColor': '#272b30',
                                                                'height':'49%',
                                                                'width':'100%',
                                                                'marginTop':'2%',
                                                                'display':'block'
                                                            },
                                                            children=[

                                                            ]
                                                        ),  
                                                    ]
                                                ),                                                
                        
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'7%',
                                                        'width':'100%',
                                                        'marginTop':'1%'                                                        
                                                    },
                                                    children=[
                                                        
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'100%',
                                                                'width':'60%',
                                                                'marginLeft':'1%',
                                                                'display':'inline-block'
                                                            },
                                                            children=[
                                                                dcc.Slider(
                                                                    id='slider_CT_tissue',
                                                                    min=0,
                                                                    max=1,
                                                                    value=1,
                                                                    marks=[],
                                                                    tooltip={'always visible':True,
                                                                            'placement':'top'}
                                                                )
                                                            ]
                                                        ),
                                                        
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'100%',
                                                                'width':'37%',
                                                                'marginLeft':'1%',
                                                                'display':'inline-block',
                                                                'vertical-align':'top'
                                                            },
                                                            children=[
                                                                dcc.RadioItems(
                                                                    id='tab3_view_CT',
                                                                    options=[
                                                                        {'label': 'Axial', 'value': 'A'},
                                                                        {'label': 'Saggital', 'value': 'S'},
                                                                        {'label': 'Coronal', 'value': 'C'}
                                                                    ],
                                                                    value='A',
                                                                    labelStyle={'display':'inline-block',
                                                                               'font-size':'1vw',
                                                                               'color':'white'},
                                                                    inputStyle={'height':'20px',
                                                                               'margin-left': '10px',
                                                                               'margin-right': '5px'}
                                                                )
                                                            ]
                                                        ),                                                        
                                                    ]
                                                ),
                                                
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'7%',
                                                        'width':'100%',
                                                        'marginTop':'1%'                                                        
                                                    },
                                                    children=[
                                                        
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'100%',
                                                                'width':'60%',
                                                                'marginLeft':'1%',
                                                                'display':'inline-block'
                                                            },
                                                            children=[
                                                                dcc.RangeSlider(
                                                                    id='window_tissue',
                                                                    min=-1000,
                                                                    max=1000,
                                                                    marks=None,
                                                                    value=[-1000, 1000],
                                                                    allowCross=False,
                                                                    included=True,
                                                                    step=1,
                                                                    vertical=False,
                                                                    className='rangeslider',
                                                                    tooltip={'always visible':True,
                                                                             'placement':'left'}
                                                                ),
                                                                
                                                            ]
                                                        ),
                                                        
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'100%',
                                                                'width':'37%',
                                                                'marginLeft':'1%',
                                                                'display':'inline-block',
                                                                'vertical-align':'top'
                                                            },
                                                            children=[
                                                                html.Button(
                                                                    'Create Phantom',
                                                                    id = 'B_phantom',
                                                                    n_clicks = None,
                                                                    title='Create MC phantom file',
                                                                    style={
                                                                        'width':'80%', 'height':'5.5vh',
                                                                        'marginTop':'1%',
                                                                        'marginLeft':'10%'}
                                                                        #'color':'black',
                                                                        #'backgroundColor':'#009900'
                                                                ),
                                                                
                                                                dcc.ConfirmDialog(
                                                                    id='preset_message',
                                                                    message='',
                                                                ),
                                                                dcc.ConfirmDialog(
                                                                    id='phantom_message_1',
                                                                    message='',
                                                                ),
                                                                dcc.ConfirmDialog(
                                                                    id='phantom_message',
                                                                    message='',
                                                                ),
                                                            ]
                                                        ),
                                                    ]
                                                ),
                                                 html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'display':'inline-block',
                                                        'vertical-align':'top',
                                                        'height':'5%',
                                                        'width':'100%',
                                                        'marginTop':'1%'
                                                    },
                                                    children=[
                                                        dcc.Interval(id="interval", interval=2000, disabled=True),
                                                        dbc.Progress( id="progress", label='0%',
                                                                     value=0, max=100, striped=True,
                                                                     style={"height": "100%",
                                                                            'width':'95%',
                                                                            'marginLeft':'2.5%',
                                                                           'font-size': '30px',
                                                                           'background-color': '#3a3f44',
                                                                            'border-radius': '1rem'}
                                                                    )
                                                                
                                                    ]
                                                )
                                                
                                            ]
                                        ),

                                    ],
                                    style={
                                        'backgroundColor': colors['background'],
                                        'height':'84vh',
                                        'marginLeft':'1.5vh',
                                        'marginRight':'1.5vh'
                                    }
                                ),
                            ]
                        ),

                        dcc.Tab(
                            label='Treatment Planning',
                            style=tab_style,
                            selected_style=tab_selected_style,
                            children=[
                                html.Div(
                                    children=[
                                        
                                        html.Div(
                                            children=[
                                                html.Div(
                                                    children=[
                                                        html.H2(
                                                            children='Surface calculator',
                                                            style={
                                                                #'textAlign': 'center',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'marginLeft':'2%',
                                                                'marginTop':'1%',
                                                                'paddingBottom':'2%',
                                                                'borderBottom':'0.1vh solid #FF8000'
                                                            }
                                                        ),

                                                        html.H4(
                                                            children='Minimum HU',
                                                            style={
                                                                'textAlign': 'left',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'padding': '0',
                                                                'marginTop': '3%',
                                                                'marginLeft':'2%',
                                                                
                                                            }
                                                        ),

                                                        dcc.Input(
                                                            id='min_HU',
                                                            type='number',
                                                            placeholder='Enter min HU value...',
                                                            value=int(-250),
                                                            debounce=True,
                                                            inputMode='numeric',
                                                            step=1,
                                                            min=int(-999),
                                                            style={
                                                                'width':'50%',
                                                                'height':'4.5vh',
                                                                'marginLeft':'3%',
                                                                'marginRight':'5%'
                                                            }
                                                        ),
                                                        
                                                         html.H4(
                                                            children='Smoothness (1-10)',
                                                            style={
                                                                'textAlign': 'left',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'padding': '0',
                                                                'marginTop': '3%',
                                                                'marginLeft':'2%'
                                                            }
                                                        ),

                                                        dcc.Input(
                                                            id='triangles',
                                                            type='number',
                                                            placeholder='Enter smoothness...',
                                                            value=int(1),
                                                            debounce=True,
                                                            inputMode='numeric',
                                                            step=1,
                                                            min=1,
                                                            max=10,
                                                            style={
                                                                'width':'50%',
                                                                'height':'4.5vh',
                                                                'marginLeft':'3%',
                                                                'marginRight':'5%'
                                                            }
                                                        ),

                                                        html.Button(
                                                            'Calculate 3D Surface',
                                                            id = 'button_surface',
                                                            n_clicks = None,
                                                            title='Turn CT slices into a 3D surface with a threshold HU value',
                                                            style={'marginTop':'5%', 'marginBottom':'1vh', 'width':'80%', 'height':'5.5vh',
                                                                  'marginLeft':'10%', 'marginRight':'10%',}
                                                        ),
                                                        dcc.ConfirmDialog(
                                                            id='calc_surface_message',
                                                            message='',
                                                        ),
                                                    ],
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'50%',
                                                        'width':'100%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    }
                                                ),
                                                
                                                html.Div(
                                                    children=[
                                                        html.H2(
                                                            children='Applicator',
                                                            style={
                                                                #'textAlign': 'center',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'marginLeft':'2%',
                                                                'marginTop':'1%',
                                                                'paddingBottom':'2%',
                                                                'borderBottom':'0.1vh solid #FF8000'
                                                            }
                                                        ),

                                                        html.Div(
                                                            children=[
                                                                html.H4(
                                                                    children='kV Energy',
                                                                    style={
                                                                        'textAlign': 'left',
                                                                        'color': colors['text'],
                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                        'padding': '0',
                                                                        'marginTop': '0vh',
                                                                        'marginLeft':'2%',
                                                                        'width':'40%'
                                                                    }
                                                                ),
                                                                dcc.Dropdown(
                                                                    id='kv_energy',
                                                                    placeholder='Select energy...',
                                                                    options=[
                                                                        {'label': '70 kV 1.20 mm Al', 'value': 'beam1'},
                                                                        {'label': '100 kV 2.90 mm Al ', 'value': 'beam2'},
                                                                        {'label': '100 kV 4.13 mm Al ', 'value': 'beam3'},
                                                                        {'label': '100 kV 6.28 mm Al ', 'value': 'beam4'},
                                                                        {'label': '300 kV 2.44 mm Cu ', 'value': 'beam5'},
                                                                        {'label': '300 kV 2.97 mm Cu ', 'value': 'beam6'},
                                                                        {'label': '300 kV 3.88 mm Cu ', 'value': 'beam7'}
                                                                    ],
                                                                    value=None,
                                                                    style={
                                                                        #'width':'80%',
                                                                        #'height':'4vh',
                                                                        'marginLeft':'3%',
                                                                        'marginRight':'5%',
                                                                        'display':'inline-block',
                                                                        'width': '80%',
                                                                        'height':'4.5vh',
                                                                        'vertical-align':'top',
                                                                        'marginTop':'0vh'
                                                                    }
                                                                ),

                                                                html.H4(
                                                                    children='Field Size',
                                                                    style={
                                                                        'textAlign': 'left',
                                                                        'color': colors['text'],
                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                        'padding': '0',
                                                                        'marginTop': '1vh',
                                                                        'marginLeft':'2%'
                                                                    }
                                                                ),
                                                                
                                                                dcc.Dropdown(
                                                                    id='kv_fields',
                                                                    placeholder='Select field size...',
                                                                    options=[
                                                                    ],
                                                                    value=None,
                                                                    style={
                                                                        #'width':'80%',
                                                                        #'height':'4.5vh',
                                                                        'marginLeft':'3%',
                                                                        'marginRight':'5%',
                                                                        'display':'inline-block',
                                                                        'width': '80%',
                                                                        'height':'4.5vh',
                                                                        'vertical-align':'top',
                                                                        'marginTop':'0vh',
                                                                        'line-height':'40px'
                                                                    }
                                                                ),

                                                                html.Button(
                                                                    'Accept kV applicator',
                                                                    id = 'Update_3d',
                                                                    n_clicks = None,
                                                                    title='Accept the selected applicator',
                                                                    style={'marginTop':'7%', 'width':'80%', 'height':'5.5vh',
                                                                        'marginLeft':'10%', 'marginRight':'10%',}
                                                                ), 
                                                            ],
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'10%',
                                                                'width':'100%',
                                                                'marginTop':'1%',
                                                                'marginBottom':'3%',
                                                                'display':'inline-block',
                                                                'vertical-align':'top'
                                                            }
                                                        ),   

                                                              
                                                    ],
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'50%',
                                                        'width':'100%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top',
                                                    }
                                                ),

                                            ],
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'100%',
                                                'width':'25%',
                                                'display':'inline-block',
                                                'vertical-align':'top'
                                            }
                                        ),
                                        
                                        html.Div(
                                            id = '3d_container',
                                            children=[

                                            ],
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'100%',
                                                'width':'50%',
                                                'display':'inline-block',
                                                'vertical-align':'top'
                                            }
                                        ),
                                        html.Div(
                                            children=[
                                                
                                                html.Div(
                                                    children=[
                                                        html.H2(
                                                            children='Beam Direction',
                                                            style={
                                                                #'textAlign': 'center',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'marginLeft':'5%',
                                                                'marginTop':'2%',
                                                                'paddingBottom':'2%',
                                                                'borderBottom':'0.1vh solid #FF8000'
                                                            }
                                                        ),
                                                        
                                                        html.H4(
                                                            children='X coordinate:',
                                                            style={
                                                                'textAlign': 'left',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'padding': '0',
                                                                'marginTop': '1%',
                                                                'marginLeft':'2%',
                                                                'display':'inline-block',
                                                                'width':'100%'
                                                            }
                                                        ),

                                                        html.Div(
                                                            children=[
                                                                dcc.Slider(
                                                                    id='x_applicator',
                                                                    min=0,
                                                                    max=1,
                                                                    value=1,
                                                                    step=1,
                                                                    marks=[],
                                                                    tooltip={'always visible':True,
                                                                            'placement':'top'}
                                                                )
                                                                
                                                            ],
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'7%',
                                                                'width':'90%',
                                                                'marginLeft':'5%',
                                                                'marginTop':'1%',
                                                                'display':'inline-block',
                                                                'vertical-align':'top'
                                                            }
                                                        ),
                                                                

                                                        html.H4(
                                                            children='Y coordinate:',
                                                            style={
                                                                'textAlign': 'left',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'padding': '0',
                                                                'marginTop': '1%',
                                                                'marginLeft':'2%',
                                                                'display':'inline-block',
                                                                'width':'100%'
                                                            }
                                                        ),
                                                        
                                                        html.Div(
                                                            children=[
                                                                dcc.Slider(
                                                                    id='y_applicator',
                                                                    min=0,
                                                                    max=1,
                                                                    value=1,
                                                                    step=1,
                                                                    marks=[],
                                                                    tooltip={'always visible':True,
                                                                            'placement':'top'}
                                                                )
                                                            ],
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'7%',
                                                                'width':'90%',
                                                                'marginLeft':'5%',
                                                                'marginTop':'1%',
                                                                'display':'inline-block',
                                                                'vertical-align':'top'
                                                            }
                                                        ),
                                                                

                                                        html.H4(
                                                            children='Z coordinate:',
                                                            style={
                                                                'textAlign': 'left',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'padding': '0',
                                                                'marginTop': '1%',
                                                                'marginLeft':'2%',
                                                                'display':'inline-block',
                                                                'width':'100%'
                                                            }
                                                        ),
                                                        html.Div(
                                                            children=[
                                                                dcc.Slider(
                                                                    id='z_applicator',
                                                                    min=0,
                                                                    max=1,
                                                                    value=1,
                                                                    step=1,
                                                                    marks=[],
                                                                    tooltip={'always visible':True,
                                                                            'placement':'top'}
                                                                )
                                                            ],
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'7%',
                                                                'width':'90%',
                                                                'marginLeft':'5%',
                                                                'marginTop':'1%',
                                                                'display':'inline-block',
                                                                'vertical-align':'top'
                                                            }
                                                        ),
                                                                
                                                        html.H4(
                                                            children='Theta (0-180):',
                                                            style={
                                                                'textAlign': 'left',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'padding': '0',
                                                                'marginTop': '1%',
                                                                'marginLeft':'2%',
                                                                'display':'inline-block',
                                                                'width':'100%'
                                                            }
                                                        ),
                                                        html.Div(
                                                            children=[
                                                                dcc.Slider(
                                                                    id='theta_applicator',
                                                                    min=0,
                                                                    max=180,
                                                                    value=30,
                                                                    step=1,
                                                                    marks={0 : {'label': '0', 'style': {'color':'white','font-size':'2rem'}},
                                                                         180 : {'label': '180', 'style': {'color':'white','font-size':'2rem'}},},
                                                                    tooltip={'always visible':True,
                                                                            'placement':'top'}
                                                                )
                                                            ],
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'7%',
                                                                'width':'90%',
                                                                'marginLeft':'5%',
                                                                #'marginTop':'1%',
                                                                #'display':'inline-block',
                                                                'vertical-align':'top'
                                                            }
                                                        ),
                                                                

                                                        html.H4(
                                                            children='Phi (0-360):',
                                                            style={
                                                                'textAlign': 'left',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'padding': '0',
                                                                'marginTop': '1%',
                                                                'marginLeft':'2%',
                                                                'display':'inline-block',
                                                                'width':'100%'
                                                            }
                                                        ),
                                                        html.Div(
                                                            children=[
                                                                dcc.Slider(
                                                                    id='phi_applicator',
                                                                    min=0,
                                                                    max=360,
                                                                    value=0,
                                                                    step=1,
                                                                    marks={0 : {'label': '0', 'style': {'color':'white','font-size':'2rem'}},
                                                                         360 : {'label': '360', 'style': {'color':'white','font-size':'2rem'}},},
                                                                    tooltip={'always visible':True,
                                                                            'placement':'top'}
                                                                )
                                                            ],
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'7%',
                                                                'width':'90%',
                                                                'marginLeft':'5%',
                                                                #'marginTop':'1%',
                                                                #'display':'inline-block',
                                                                'vertical-align':'top'
                                                            }
                                                        ),

                                                        html.H4(
                                                            children='Colimator (0-180):',
                                                            style={
                                                                'textAlign': 'left',
                                                                'color': colors['text'],
                                                                'font-family': 'Arial, Helvetica, sans-serif',
                                                                'padding': '0',
                                                                'marginTop': '1%',
                                                                'marginLeft':'2%',
                                                                'display':'inline-block',
                                                                'width':'100%'
                                                            }
                                                        ),
                                                        html.Div(
                                                            children=[
                                                                dcc.Slider(
                                                                    id='app_rot',
                                                                    min=0,
                                                                    max=180,
                                                                    value=0,
                                                                    step=1,
                                                                    marks={0 : {'label': '0', 'style': {'color':'white','font-size':'2rem'}},
                                                                         180 : {'label': '180', 'style': {'color':'white','font-size':'2rem'}},},
                                                                    tooltip={'always visible':True,
                                                                            'placement':'top'}
                                                                )
                                                            ],
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'7%',
                                                                'width':'90%',
                                                                'marginLeft':'5%',
                                                                #'marginTop':'1%',
                                                                #'display':'inline-block',
                                                                'vertical-align':'top'
                                                            }
                                                        ),
                                                        
                                                        html.Button(
                                                            'Export Setup File',
                                                            id = 'export_setup',
                                                            n_clicks = None,
                                                            title='Export the current setup DOSXYZnrc file',
                                                            style={'marginTop':'7%', 'width':'80%', 'height':'5.5vh',
                                                                'marginLeft':'10%', 'marginRight':'10%',}
                                                        ), 
                                                        dcc.ConfirmDialog(
                                                            id='export_dialog',
                                                            message='',
                                                        ),
                                                        
                                                        dcc.ConfirmDialog(
                                                            id='plot_3d_surface_message',
                                                            message='',
                                                        ),

                                                    ],
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'70%',
                                                        'width':'100%',
                                                        'display':'inline-block',
                                                        'vertical-align':'top'
                                                    }
                                                ),
                                                
                                            ],
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'100%',
                                                'width':'25%',
                                                'display':'inline-block',
                                            }
                                        ),

                                    ],
                                    style={
                                        'backgroundColor': 'green',
                                        'height':'82vh',
                                        'marginLeft':'1.5vh',
                                        'marginRight':'1.5vh'
                                    }
                                ),
                            ]
                        )                        
                    ]
                )   
            ]
        )  
    ]
)

#################################################################################
################################ CALLBACKS ######################################
#################################################################################

@app.callback([Output('scan_info_table','children'),
               Output('tab1_view_CT','value'),
              Output('B_import_ct','className'),
              Output('imported_CT', 'message'),
            Output('imported_CT', 'displayed'),
              Output('structures_checklist','options'),
              Output('HU_ch_dropdown','options'),
              Output('B_import_struct','className')],
              [Input('B_import_ct','n_clicks'),
               Input('B_import_struct','n_clicks')]
)
def upload_dicom_ct(click_ct, click_struct):
    global SCAN
    
    if click_ct == None and click_struct == None:
        raise PreventUpdate
    else:
        changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
        
        if 'B_import_ct' in changed_id:
        
            try:
                ct_folder_path = gui_select_dir()
                ct_files, mess = load_dicom_files(ct_folder_path)

                if ct_files == False:
                    error_message = 'Failed to find DICOM files in: ' + ct_folder_path
                    return [], [], 'button', error_message, True, [], [], 'button'
                    raise PreventUpdate

                else:
                    print('Compiling DICOM information...')
                    SCAN = scan(ct_files)

                    SCAN.ct_folder_path = ct_folder_path

                    SCAN.updated = False

                    ct_properties_dict = {
                        'Patient ID': SCAN.patient_id,
                        'Patient Name': SCAN.patient_name,
                        'Patient DOB': SCAN.patient_dob,
                        'Acquisition Date': SCAN.acquisition_date,
                        'Scan Orientation': SCAN.orientation,
                        'Scan Resolution': SCAN.resolution
                    }

                    ct_properties_df = pd.DataFrame(list(ct_properties_dict.items()))

                    table = dash_table.DataTable(
                                columns = [{"name": i, "id": i} for i in ct_properties_df.columns],
                                data = ct_properties_df.to_dict('records'),
                                style_cell = {
                                    'font_family': '"Segoe UI",Arial,sans-serif',
                                    'font_size': '20px',
                                    'text_align': 'left',
                                    'color':'black',
                                    'backgroundColor':'#A0A0A0'
                                },
                                style_header = {'display': 'none','height':'0px'},
                                css=[
                                {
                                    'selector': 'tr:first-child',
                                    'rule': 'display: none',
                                },
                                ],
                            )
                    SCAN.stage = 1
                    SCAN.structures = []
                    return table, 'A', 'button-pressed', mess, False, [], [], 'button'
            except:
                error_message = 'Failed reading CT files!'
                return [], [], 'button', error_message, True, [], [], 'button'
                #raise #PreventUpdate
        
        elif 'B_import_struct' in changed_id:
            try:
                SCAN
            except NameError:
                return [],[],'button','Please import CT files first!',True,[],[],'button'
                raise PreventUpdate        

                
            ct_properties_dict = {
                'Patient ID': SCAN.patient_id,
                'Patient Name': SCAN.patient_name,
                'Patient DOB': SCAN.patient_dob,
                'Acquisition Date': SCAN.acquisition_date,
                'Scan Orientation': SCAN.orientation,
                'Scan Resolution': SCAN.resolution
            }

            ct_properties_df = pd.DataFrame(list(ct_properties_dict.items()))

            table = dash_table.DataTable(
                        columns = [{"name": i, "id": i} for i in ct_properties_df.columns],
                        data = ct_properties_df.to_dict('records'),
                        style_cell = {
                            'font_family': '"Segoe UI",Arial,sans-serif',
                            'font_size': '20px',
                            'text_align': 'left',
                            'color':'black',
                            'backgroundColor':'#A0A0A0'
                        },
                        style_header = {'display': 'none', 'height':'0px'},
                        css=[
                            {
                                'selector': 'tr:first-child',
                                'rule': 'display: none',
                            },
                        ],
                    )
            SCAN.stage = 1
                    
            structure_file_path = gui_select_file('Please select DICOM structure file')
            structure_file = dcm.read_file(structure_file_path, force=True)

            try:
                if structure_file.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.3':
                    print('Structure file successfully read!')

                    SCAN.structures = []

                    for i, j in enumerate(structure_file.StructureSetROISequence):
                        number = j.ROINumber
                        name = j.ROIName

                        print('Looking for contour sequence:', name)

                        for m in structure_file.ROIContourSequence:
                            if m.ReferencedROINumber == number:
                                print('Found sequence:', name)
                                color = m.ROIDisplayColor

                                #Commented to save memory
                                #sequence = m.ContourSequence
                                sequence = 1
                                dummy_cube = np.zeros((SCAN.HFS_cube.shape[0], SCAN.HFS_cube.shape[1], SCAN.HFS_cube.shape[2]),dtype=np.int8)

                                try:
                                    for seq in m.ContourSequence:
                                        xs = seq.ContourData[::3]
                                        ys = seq.ContourData[1::3]
                                        zs = seq.ContourData[2::3]

                                        xs_idx = list(map(lambda a: (np.abs(SCAN.HFS_xs - a)).argmin(), xs))
                                        ys_idx = list(map(lambda a: (np.abs(SCAN.HFS_ys - a)).argmin(), ys))
                                        zs_idx = list(map(lambda a: (np.abs(SCAN.HFS_zs - a)).argmin(), zs))

                                        xx, yy = polygon(xs_idx, ys_idx)
                                        dummy_cube[zs_idx[0],yy,xx] = 1

                                    #dummy_cube[dummy_cube==0] = None
                                    print('Structure volume created!')
                                    s = structure(number, name, color, dummy_cube, sequence)
                                    SCAN.structures.append(s)
                                except:
                                    print('Structure:', name, ' has no ContourSequence')


                    checklist_options = []
                    for i in SCAN.structures:
                        checklist_options.append({'label':i.name, 'value':i.number})

                    SCAN.stage = 2
                    return table, 'A', 'button-pressed', 'Successfully imported DICOM structures!', True, checklist_options, checklist_options, 'button-pressed',
                else:
                    return table, 'A', 'button-pressed', 'Selected file is not a DICOM structure set!', True, [],[],'button'
                    raise PreventUpdate

            except:
                return table, 'A', 'button-pressed','Error reading the DICOM structure set!', True, [],[],'button'
                raise PreventUpdate        
            
            
@app.callback(
    [Output('slider_CT', 'step'),
     Output('slider_CT', 'min'),
    Output('slider_CT', 'max'),
     Output('slider_CT', 'value'),
     Output('slider_CT', 'marks'),
    Output('WLCT', 'min'),
    Output('WLCT', 'max'),
    Output('WLCT', 'marks'),
    Output('WLCT', 'value')],
    [Input('tab1_view_CT', 'value')])
def update_sliders(view):
    try:
        SCAN
    except NameError:
        raise PreventUpdate
        
    try:
        #Update WINDOW slider values
        steps = int((np.max(SCAN.HFS_cube)-np.min(SCAN.HFS_cube))/15)
        Wm = {i : {'label': '{}HU'.format(round(i,1)), 
                   'style': {'color':'white',
                            'font-size':'2rem'}} for i in range(int(np.min(SCAN.HFS_cube)), np.max(SCAN.HFS_cube), steps)}
        
        Wmin=np.min(SCAN.HFS_cube)
        Wmax=np.max(SCAN.HFS_cube)

        Sstep, Smin, Smax, Svalue, Smarks = update_slice_slider(view)

        return Sstep, Smin, Smax, Svalue, Smarks, Wmin, Wmax, Wm, [-1024,2000]
    except:
        raise PreventUpdate

#Plotting the graph    
@app.callback(
    [Output('main_plot', 'children'),
    Output('sub1_plot', 'children'),
    Output('sub2_plot', 'children')],
    [Input('WLCT', 'value'),
    Input('slider_CT', 'value'),
    Input('structures_checklist', 'value')], 
    [State('tab1_view_CT', 'value')])
def update_graph_CT(my_width, my_slice, selected_structures, my_view):
    
    try:
        SCAN
    except NameError:
        raise PreventUpdate
        
    if my_view == 'A':
        idx = find_index(SCAN.HFS_zs, my_slice)
        main_annotation_1 = orientation_label(np.min(SCAN.HFS_xs), 0, "R")
        main_annotation_2 = orientation_label(np.max(SCAN.HFS_xs), 0, "L")
        main_annotation_3 = orientation_label(0, np.min(SCAN.HFS_ys), "A")
        main_annotation_4 = orientation_label(0, np.max(SCAN.HFS_ys), "P")
        
    elif my_view == 'S':
        idx = find_index(SCAN.HFS_xs, my_slice)
        main_annotation_1 = orientation_label(np.min(SCAN.HFS_ys), 0, "A")
        main_annotation_2 = orientation_label(np.max(SCAN.HFS_ys), 0, "P")
        main_annotation_3 = orientation_label(0, np.min(SCAN.HFS_zs), "I")
        main_annotation_4 = orientation_label(0, np.max(SCAN.HFS_zs), "S")
        
    elif my_view == 'C':
        idx = find_index(SCAN.HFS_ys, my_slice)
        main_annotation_1 = orientation_label(np.min(SCAN.HFS_xs), 0, "R")
        main_annotation_2 = orientation_label(np.max(SCAN.HFS_xs), 0, "L")
        main_annotation_3 = orientation_label(0, np.min(SCAN.HFS_zs), "I")
        main_annotation_4 = orientation_label(0, np.max(SCAN.HFS_zs), "S")
        
    data_main, layout_main, F_sub1, F_sub2 = PLOT_CT(SCAN.HFS_cube, SCAN.HFS_xs, SCAN.HFS_ys, SCAN.HFS_zs, View=my_view, Slice=idx, width=my_width, PEGS=None)
    
    #if hasattr(SCAN, 'structures'):
    contour_plots = contour_structures(selected_structures, my_view, idx)
    F_main = go.Figure(data_main+contour_plots, layout_main)
    F_main.add_annotation(main_annotation_1)
    F_main.add_annotation(main_annotation_2)
    F_main.add_annotation(main_annotation_3)
    F_main.add_annotation(main_annotation_4)
        
    #else:
        #F_main = go.Figure(data_main, layout_main)

    F_m = create_dcc_graph(F_main)
    F_s1 = create_dcc_graph(F_sub1)
    F_s2 = create_dcc_graph(F_sub2)
        
    return F_m, F_s1, F_s2

#Updating pixel values    
@app.callback(
    [Output('update_hu_message', 'message'),
    Output('update_hu_message', 'displayed'),
    Output('B_change_hu', 'className')],
    [Input('B_change_hu', 'n_clicks')], 
    [State('new_HU', 'value'),
    State('HU_ch_dropdown', 'value')],) 
def update_pixels(n_clicks, value_HU, contour_number):
    global SCAN 
    
    if n_clicks == None:
        return '...', False, 'button'
    
    elif n_clicks >= 1:
        
        try:
            SCAN
        except NameError:
            return 'Please import CT files first!', True, 'button' 
        
        if hasattr(SCAN, 'structures'):
            pass
        else:
            return 'Please import a structure set!', True, 'button'

        if contour_number == None:
            return 'Please select a contour!', True, 'button'
        
        if value_HU == None:
            return 'Please enter a new HU value!', True, 'button'

        if contour_number != None and value_HU != None:
            
            structures_holder = SCAN.structures
            
            if SCAN.updated == False:
                print('Copying the DICOM files...')
                attempt_DICOM_folder = SCAN.ct_folder_path + '_new_HU'

                updated_ct_folder_path = createFolder(attempt_DICOM_folder)
                
                copy_rename_DICOM(SCAN.ct_folder_path, updated_ct_folder_path)

                updated_ct_files, mess = load_dicom_files(updated_ct_folder_path)

                SCAN = scan(updated_ct_files)
                
                SCAN.updated_ct_folder_path = updated_ct_folder_path
                SCAN.structures = structures_holder
                SCAN.updated = True
                
            try: 
                Overwrite(contour_number, value_HU)
                SCAN.stage = 3
                return 'HU Updated!', True, 'button-pressed'

            except:
                raise
                return 'Error updating HU value!', True, 'button'
                #raise PreventUpdate 
                
            
        else:
            return 'Please select a structure contour and enter a new HU value!', True, 'button'

    
@app.callback(
    [Output('accept_ct_message', 'message'),
    Output('accept_ct_message', 'displayed'),
    Output('ROI_rangex', 'min'),
     Output('ROI_rangex', 'max'),
    Output('ROI_rangex', 'step'),
     Output('ROI_rangex', 'marks'),
     Output('ROI_rangex', 'value'),
     Output('ROI_rangey', 'min'),
     Output('ROI_rangey', 'max'),
    Output('ROI_rangey', 'step'),
     Output('ROI_rangey', 'marks'),
     Output('ROI_rangey', 'value'),
     Output('ROI_rangez', 'min'),
     Output('ROI_rangez', 'max'),
    Output('ROI_rangez', 'step'),
    Output('ROI_rangez', 'marks'),
    Output('ROI_rangez', 'value'),
    Output('ROI_CT_window', 'min'),
    Output('ROI_CT_window', 'max'),
    Output('ROI_CT_window', 'marks'),
    Output('B_accept', 'className')],
    [Input('B_accept', 'n_clicks')])
def update_sliders(n_clicks):
    if n_clicks == None:
        raise PreventUpdate
    else:
        try:
            SCAN
            
            #Update WINDOW slider values
            steps = int((np.max(SCAN.HFS_cube)-np.min(SCAN.HFS_cube))/15)
            Wm = {i : {'label': '{}HU'.format(round(i,1)), 
                       'style': {'color':'white',
                                'font-size':'2rem'}} for i in range(int(np.min(SCAN.HFS_cube)), np.max(SCAN.HFS_cube), steps)}

            Wmin=np.min(SCAN.HFS_cube)
            Wmax=np.max(SCAN.HFS_cube)
            
            xs = SCAN.HFS_xs
            ys = SCAN.HFS_ys
            zs = SCAN.HFS_zs
            
            x_step = SCAN.x_step
            y_step = SCAN.y_step
            z_step = SCAN.z_step
            
            x_marks = {i : {'label': '{}'.format(float(round(i,1))), 
                   'style': {'color':'white',
                            'font-size':'15px'}} for i in np.linspace(float(min(xs)),float(max(xs)),8,endpoint=True)} 
            y_marks = {i : {'label': '{}'.format(float(round(i,1))), 
                   'style': {'color':'white',
                            'font-size':'15px'}} for i in np.linspace(float(min(ys)),float(max(ys)),8,endpoint=True)}
            z_marks = {i : {'label': '{}'.format(float(round(i,1))), 
                   'style': {'color':'white',
                            'font-size':'15px'}} for i in np.linspace(float(min(zs)),float(max(zs)),8,endpoint=True)}


            SCAN.stage = 4
            return ['CT data accepted!', True,
                    min(xs),max(xs),x_step,x_marks,[min(xs),max(xs)],
                    min(ys),max(ys),y_step,y_marks,[min(ys),max(ys)],
                    min(zs),max(zs),z_step,z_marks,[min(zs),max(zs)],
                   Wmin, Wmax, Wm,
                   'button-pressed']
            
        except NameError:
            return ['Please import CT files first!', True,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0, 'button']
            raise PreventUpdate
            
    
@app.callback(
    [Output('ROI_slider1','min'),
    Output('ROI_slider1','max'),
    Output('ROI_slider1','marks'),
    Output('ROI_slider1','value'),
    Output('ROI_slider1','step'),
    Output('ROI_slider2','min'),
    Output('ROI_slider2','max'),
    Output('ROI_slider2','marks'),
     Output('ROI_slider2','value'),
    Output('ROI_slider2','step'),
    Output('ROI_slider3','min'),
    Output('ROI_slider3','max'),
    Output('ROI_slider3','marks'),
     Output('ROI_slider3','value'),
    Output('ROI_slider3','step'),
    Output('xvoxnum','children'),
    Output('yvoxnum','children'),
    Output('zvoxnum','children'),
    Output('totvoxnum','children'),
    Output('totvoxnum', 'style')],
    [Input('ROI_rangex', 'value'),
     Input('ROI_rangey', 'value'),
     Input('ROI_rangez', 'value')])
def update_sliders(xvals, yvals, zvals):
    try: 
        SCAN
        
        xmin,xmax = xvals[0],xvals[1]
        ymin,ymax = yvals[0],yvals[1]
        zmin,zmax = zvals[0],zvals[1]    
        
        x_marks = {i : {'label': '{}'.format(float(round(i,1))), 
               'style': {'color':'white',
                        'font-size':'15px'}} for i in np.linspace(float(xmin),float(xmax),8,endpoint=True)} 
        y_marks = {i : {'label': '{}'.format(float(round(i,1))), 
               'style': {'color':'white',
                        'font-size':'15px'}} for i in np.linspace(float(ymin),float(ymax),8,endpoint=True)}
        z_marks = {i : {'label': '{}'.format(float(round(i,1))), 
               'style': {'color':'white',
                        'font-size':'15px'}} for i in np.linspace(float(zmin),float(zmax),8,endpoint=True)}
        
        x_step = SCAN.x_step
        y_step = SCAN.y_step
        z_step = SCAN.z_step

        xnumv = int((xmax-xmin)/x_step)
        ynumv = int((ymax-ymin)/y_step)
        znumv = int((zmax-zmin)/z_step)

        Sstep1 = SCAN.z_step
        Smin1 = zmin
        Smax1 = zmax
        Svalue1 = zmin+((zmax-zmin)/2)
        Smarks1 = z_marks
            
        Sstep2 = SCAN.x_step
        Smin2 = xmin
        Smax2 = xmax
        Svalue2 = xmin+((xmax-xmin)/2)
        Smarks2 = x_marks
            
        Sstep3 = SCAN.y_step
        Smin3 = ymin
        Smax3 = ymax
        Svalue3 = ymin+((ymax-ymin)/2)
        Smarks3 = y_marks

        if xnumv*ynumv*znumv < max_DOSXYZ_voxels:
            style={
                #'textAlign': 'center',
                'color': 'green',
                'font-family': 'Arial, Helvetica, sans-serif',
                'marginLeft':'1%',
                'marginTop':'8%',
                'padding':'0'
            }
        else:
            style={
                #'textAlign': 'center',
                'color': 'red',
                'font-family': 'Arial, Helvetica, sans-serif',
                'marginLeft':'1%',
                'marginTop':'8%',
                'padding':'0'
            }

        return [Smin1,Smax1,Smarks1,Svalue1,Sstep1,
                Smin2,Smax2,Smarks2,Svalue2,Sstep2,
                Smin3,Smax3,Smarks3,Svalue3,Sstep3,
                xnumv, ynumv, znumv, xnumv*ynumv*znumv, style]

    except NameError:
        raise PreventUpdate


@app.callback(
    [Output('ROI_plot1','children'),
    Output('ROI_plot2','children'),
    Output('ROI_plot3','children')],
    [Input('ROI_rangex', 'value'),
     Input('ROI_rangey', 'value'),
     Input('ROI_rangez', 'value'),
    Input('ROI_slider1','value'),
    Input('ROI_slider2','value'),
    Input('ROI_slider3','value'),
    Input('ROI_CT_window', 'value')])
def update_sliders(rangex, rangey, rangez, slicez, slicex, slicey, window):

    try:
        SCAN
    except NameError:
        raise PreventUpdate
        
    try:
        ps, pc, pa = plot_ROI(SCAN,rangex,slicex,rangey,slicey,rangez,slicez,window)
        
        a_annotation_1 = orientation_label(np.min(SCAN.HFS_xs), 0, "R")
        a_annotation_2 = orientation_label(np.max(SCAN.HFS_xs), 0, "L")
        a_annotation_3 = orientation_label(0, np.min(SCAN.HFS_ys), "A")
        a_annotation_4 = orientation_label(0, np.max(SCAN.HFS_ys), "P")

        s_annotation_1 = orientation_label(np.min(SCAN.HFS_ys), 0, "A")
        s_annotation_2 = orientation_label(np.max(SCAN.HFS_ys), 0, "P")
        s_annotation_3 = orientation_label(0, np.min(SCAN.HFS_zs), "I")
        s_annotation_4 = orientation_label(0, np.max(SCAN.HFS_zs), "S")

        c_annotation_1 = orientation_label(np.min(SCAN.HFS_xs), 0, "R")
        c_annotation_2 = orientation_label(np.max(SCAN.HFS_xs), 0, "L")
        c_annotation_3 = orientation_label(0, np.min(SCAN.HFS_zs), "I")
        c_annotation_4 = orientation_label(0, np.max(SCAN.HFS_zs), "S")

        ps.add_annotation(s_annotation_1)
        ps.add_annotation(s_annotation_2)
        ps.add_annotation(s_annotation_3)
        ps.add_annotation(s_annotation_4)

        pc.add_annotation(c_annotation_1)
        pc.add_annotation(c_annotation_2)
        pc.add_annotation(c_annotation_3)
        pc.add_annotation(c_annotation_4)

        pa.add_annotation(a_annotation_1)
        pa.add_annotation(a_annotation_2)
        pa.add_annotation(a_annotation_3)
        pa.add_annotation(a_annotation_4)

        PS = create_dcc_graph(ps)
        PC = create_dcc_graph(pc)
        PA = create_dcc_graph(pa)
        
        return PA,PS,PC
    except:
        raise 
    

@app.callback(
    [Output('tab3_view_CT', 'value'),
    Output('B_OK','className'),
    Output('accept_roi_message', 'message'),
    Output('accept_roi_message', 'displayed'),],
    [Input('B_OK', 'n_clicks')],
    [State('ROI_rangex', 'value'),
     State('ROI_rangey', 'value'),
     State('ROI_rangez', 'value')])
def update_sliders(n_clicks, rangex, rangey, rangez):

    if n_clicks == None:
        raise PreventUpdate
    else: 
        try:
            SCAN
            
            if SCAN.stage >= 4:
                try:
                    SCAN.crop_cube(rangex, rangey, rangez)
                    SCAN.stage = 5                   

                    return ['A','button-pressed', 'ROI accepted!', True]
                except:
                    return ['','button', 'Error cropping the cube!', True]
            else:
                return ['','button', 'Please accept CT images first!', True]
                raise PreventUpdate
            
        except:
            return ['','button', 'Please import and accept CT images first!', True]
            raise PreventUpdate
            
        
@app.callback(
    [Output('slider_CT_tissue', 'step'),
     Output('slider_CT_tissue', 'min'),
    Output('slider_CT_tissue', 'max'),
     Output('slider_CT_tissue', 'value'),
     Output('slider_CT_tissue', 'marks'),
    Output('window_tissue', 'min'),
    Output('window_tissue', 'max'),
    Output('window_tissue', 'marks')],
    [Input('tab3_view_CT', 'value')])
def update_sliders(view):
    try:
        SCAN
    except:
        raise PreventUpdate
        
    if hasattr(SCAN, 'cropped_cube'):
        try:
            #Update WINDOW slider values
            steps = int((np.max(SCAN.cropped_cube)-np.min(SCAN.cropped_cube))/8)
            Wm = {i : {'label': '{}HU'.format(round(i,1)), 
                       'style': {'color':'white',
                                'font-size':'15px'}} for i in range(int(np.min(SCAN.cropped_cube)), np.max(SCAN.cropped_cube), steps)}

            Wmin=np.min(SCAN.cropped_cube)
            Wmax=np.max(SCAN.cropped_cube)

            Sstep, Smin, Smax, Svalue, Smarks = update_slice_slider_cropped(view)

            return Sstep, Smin, Smax, Svalue, Smarks, Wmin, Wmax, Wm
        except:
            raise PreventUpdate
    else:
        raise PreventUpdate
        
@app.callback(
    [Output('main_plot_tissue', 'children'),
    Output('sub1_plot_tissue', 'children'),
    Output('sub2_plot_tissue', 'children')],
    [Input('window_tissue', 'value'),
    Input('slider_CT_tissue', 'value'),
    Input('tissue_preset', 'value')], 
    [State('tab3_view_CT', 'value')])
def update_graph_CT(my_width, my_slice, tissue_preset, my_view):

    try:
        SCAN
    except NameError:
        raise PreventUpdate
        
    if my_view == 'A':
        idx = (np.abs(SCAN.cropped_zs - my_slice)).argmin()
        main_annotation_1 = orientation_label(np.min(SCAN.HFS_xs), 0, "R")
        main_annotation_2 = orientation_label(np.max(SCAN.HFS_xs), 0, "L")
        main_annotation_3 = orientation_label(0, np.min(SCAN.HFS_ys), "A")
        main_annotation_4 = orientation_label(0, np.max(SCAN.HFS_ys), "P")

    elif my_view == 'S':
        idx = (np.abs(SCAN.cropped_xs - my_slice)).argmin()
        main_annotation_1 = orientation_label(np.min(SCAN.HFS_ys), 0, "A")
        main_annotation_2 = orientation_label(np.max(SCAN.HFS_ys), 0, "P")
        main_annotation_3 = orientation_label(0, np.min(SCAN.HFS_zs), "I")
        main_annotation_4 = orientation_label(0, np.max(SCAN.HFS_zs), "S")

    elif my_view == 'C':
        idx = (np.abs(SCAN.cropped_ys - my_slice)).argmin()
        main_annotation_1 = orientation_label(np.min(SCAN.HFS_xs), 0, "R")
        main_annotation_2 = orientation_label(np.max(SCAN.HFS_xs), 0, "L")
        main_annotation_3 = orientation_label(0, np.min(SCAN.HFS_zs), "I")
        main_annotation_4 = orientation_label(0, np.max(SCAN.HFS_zs), "S")


    if tissue_preset == 'HN':
        P = PEGS_HN
    elif tissue_preset == 'T':
        P = PEGS_T
    elif tissue_preset == 'A':
        P = PEGS_A
    elif tissue_preset == 'CIRS':
        P = PEGS_CIRS
    else:
        raise PreventUpdate
        
    data_main, layout_main, F_sub1, F_sub2 = PLOT_CT(SCAN.cropped_cube, SCAN.cropped_xs, SCAN.cropped_ys, SCAN.cropped_zs, View=my_view, Slice=idx, width=my_width, PEGS=P)

    F_main = go.Figure(data_main, layout_main)
    F_main.add_annotation(main_annotation_1)
    F_main.add_annotation(main_annotation_2)
    F_main.add_annotation(main_annotation_3)
    F_main.add_annotation(main_annotation_4)

    F_m = create_dcc_graph(F_main)
    F_s1 = create_dcc_graph(F_sub1)
    F_s2 = create_dcc_graph(F_sub2)
        
    return F_m, F_s1, F_s2


@app.callback(
    [Output('table_container', 'children'),
    Output('preset_message', 'message'),
    Output('preset_message', 'displayed')],
    [Input('tissue_preset', 'value')])
def select_anatomy(location):
    
    try:
        SCAN
    except NameError:
        raise PreventUpdate
    else:
        if hasattr(SCAN, 'cropped_cube'):
            
            if location == 'HN':
                PEGS = pd.DataFrame(PEGS_HN)
            elif location == 'T':
                PEGS = pd.DataFrame(PEGS_T)
            elif location == 'A':
                PEGS = pd.DataFrame(PEGS_A)
            elif location == 'CIRS':
                PEGS = pd.DataFrame(PEGS_CIRS)
            else:
                raise PreventUpdate

            PEGS_data_table = dash_table.DataTable(
                                    id='table',
                                    data=PEGS.to_dict('records'),
                                    columns=[{'id': c, 'name': c} for c in PEGS.columns[:-2]],
                                    style_cell_conditional=colour_rows(PEGS.to_dict('records')),
                                    row_selectable="multi",
                                    editable=True,
                                    sort_mode="multi",
                                    style_header={
                                        'backgroundColor': '#696969',
                                        'color': 'white',
                                        'fontWeight': 'bold'
                                    },
                                    style_cell = {
                                        'font_family': '"Segoe UI",Arial,sans-serif',
                                        'font_weight':'500',
                                        'font_size': '15px',
                                        'text_align': 'left',
                                        'minWidth': '30%',
                                        'color':'black',
                                    },
                                    selected_rows=[i for i in range(len(PEGS.Name))]
                                )

            return PEGS_data_table, '', False
        else:
            return [], 'Please click "Accept" in ROI tab!', True
            raise PreventUpdate

#Materials table generation
@app.callback(
    [Output('table', 'style_cell_conditional'),
    Output('CT_map', 'children')],
    [Input('table', "derived_virtual_data"),
     Input('table', "derived_virtual_selected_rows")])
def gen_material_table(rows, derived_virtual_selected_rows):
    # When the table is first rendered, `derived_virtual_data` and
    # `derived_virtual_selected_rows` will be `None`. This is due to an
    # idiosyncracy in Dash (unsupplied properties are always None and Dash
    # calls the dependent callbacks when the component is first rendered).
    # So, if `rows` is `None`, then the component was just rendered
    # and its value will be the same as the component's dataframe.
    # Instead of setting `None` in here, you could also set
    # `derived_virtual_data=df.to_rows('dict')` when you initialize
    # the component.    
    if derived_virtual_selected_rows is None:
        derived_virtual_selected_rows = []
        
    if rows is None:
        try:
            dff = PEGS
        except:
            raise PreventUpdate
    else:
        dff = pd.DataFrame(rows)
    
    st = colour_rows(dff.to_dict('records'))
    
    selected = [dff.iloc[i] for i in derived_virtual_selected_rows]
    
    try:
        SCAN
        SCAN.selected_materials = stretch_CT(selected)
    except:
        
        raise PreventUpdate
    
    plot = dcc.Graph(id='CTR', figure=ramp_up(SCAN.selected_materials), style={
            'height':'100%'
        },config={
        'displayModeBar': False
    })
    
    return st, plot

#Creating phantom    
@app.callback(
    [Output("interval", "disabled"),
    Output('phantom_message_1', 'message'),
    Output('phantom_message_1', 'displayed')
    ],
    [Input('B_phantom', 'n_clicks')],
    [State('ROI_rangex', 'value'),
    State('ROI_rangey', 'value'),
    State('ROI_rangez', 'value')],) 
def create_phtm(n_clicks, range_x, range_y, range_z):
    
    if n_clicks == None:
        raise PreventUpdate
    
    elif n_clicks >= 1:
    
        try:
            SCAN
        except:
            message = 'Please import CT images first!'
            return True, message, True
            raise PreventUpdate
            
        if not hasattr(SCAN, 'cropped_cube'):
            message = 'Please select Region of Interest first!'
            return True, message, True
            raise PreventUpdate
            
            
        if hasattr(SCAN, 'selected_materials'):
            if SCAN.selected_materials == []:
                
                message = 'Please select materials first!'
                return True, message, True
                raise PreventUpdate
            else:
                
                try:
                    for item in SCAN.selected_materials:
                        int(item.MinCT)
                        int(item.MaxCT)
                except:
                    message = 'Min/Max CT values are not integers!'
                    return True, message, True
                    raise PreventUpdate

                
                ready_cube, b_x, b_y, b_z = SCAN.create_mini_cubes(range_x, range_y, range_z)

                savefile = np.array([ready_cube, b_x, b_y, b_z])

                xyz = [ready_cube.shape[0], ready_cube.shape[1], ready_cube.shape[2]]
                tot_vox = ready_cube.shape[0] * ready_cube.shape[1] * ready_cube.shape[2]


                if tot_vox >= max_DOSXYZ_voxels:
                    message = 'Too many voxels:' + str(tot_vox) + '/' + str(max_DOSXYZ_voxels) + '. Please select a smaller ROI!'
                    return True, message, True
                    raise PreventUpdate
                    
                if hasattr(SCAN, 'updated_ct_folder_path'):
                    folder = SCAN.updated_ct_folder_path
                else:
                    folder = SCAN.ct_folder_path
                    
                folder = gui_save_file('Save CT phantom file as', "DOSXYZnrc phantom files (*.egsphant)|*.egsphant||")
                print('Creating the phantom...')
                global worker_process
                
                worker_process = threading.Thread(target=write_phantom_file, args=(ready_cube, b_x, b_y, b_z, folder, SCAN.selected_materials,))
                worker_process.start()                

                message = 'Please note phantom voxels:z=' + str(xyz[0]) + ', y=' + str(xyz[1]) + ', x=' + str(xyz[2]) + '. Please click OK and wait for the phantom file to be created!'
                return False, message, True
            
        else:
            message = 'Please select materials!'
            return True, message, True
            raise PreventUpdate

#PROGRESS BAR STUFF###########################
@app.callback(
    [   Output("progress", "value"),
        Output("progress", "label"),
        Output("interval", "max_intervals"),
        Output('B_phantom','className'),
        Output('phantom_message', 'message'),
        Output('phantom_message', 'displayed')
    ],
    [Input("interval", "n_intervals")]
)
def retrieve_output(n):
    """
    Periodically check the most recently submitted job to see if it has
    completed.
    """
    try:
        SCAN
    except NameError:
        raise PreventUpdate
    else:
        if hasattr(SCAN, 'progress'):
            if n:
                if SCAN.phantom_created == True:
                    return 100, '100%', 0, 'button-pressed', 'Phantom successfully created!', True

                # job is still running, get progress and update progress bar
                progress = round(SCAN.progress,0)
                return progress, str(progress)+'%', -1, [], 'No phantom', False

        raise PreventUpdate


@app.callback(
    [Output('x_applicator', 'min'),
    Output('x_applicator', 'max'),
    Output('x_applicator', 'marks'),
    Output('x_applicator', 'value'),
    Output('y_applicator', 'min'),
    Output('y_applicator', 'max'),
    Output('y_applicator', 'marks'),
    Output('y_applicator', 'value'),
    Output('z_applicator', 'min'),
    Output('z_applicator', 'max'),
    Output('z_applicator', 'marks'),
    Output('z_applicator', 'value'),
    Output('calc_surface_message', 'message'),
    Output('calc_surface_message', 'displayed'),
    Output('button_surface', 'className')],
    [Input('button_surface', 'n_clicks')],
    [State('min_HU', 'value'),
     State('triangles', 'value')])
def update_sliders(n_clicks, minhu, triangles):

    if n_clicks == None:
        raise PreventUpdate
    else: 
        
        try: 
            SCAN
        except NameError:
            message = 'Please import CT images first!'
            return 0,1,[],1,0,1,[],1,0,1,[],1, message, True, 'button'
            raise PreventUpdate
            
        if minhu == None:
            message = 'Please enter minimum surface HU value!'
            return 0,1,[],1,0,1,[],1,0,1,[],1, message, True, 'button'
            raise PreventUpdate
        if triangles == None:
            message = 'Please enter the smoothness value!'
            return 0,1,[],1,0,1,[],1,0,1,[],1, message, True, 'button'
            raise PreventUpdate
            
        if triangles < 1:
            message = 'Please enter the smoothness value >0!'
            return 0,1,[],1,0,1,[],1,0,1,[],1, message, True, 'button'
            raise PreventUpdate
            
            
        if hasattr(SCAN, 'cropped_cube'):
            xmin = min(SCAN.cropped_xs) - 20
            xmax = max(SCAN.cropped_xs) + 20

            ymin = min(SCAN.cropped_ys) - 20
            ymax = max(SCAN.cropped_ys) + 20

            zmin = min(SCAN.cropped_zs) - 20
            zmax = max(SCAN.cropped_zs) + 20

            xmarks = {xmin : {'label': '{}'.format(float(round(xmin,1))), 'style': {'color':'white','font-size':'15px'}},
                     xmax : {'label': '{}'.format(float(round(xmax,1))), 'style': {'color':'white','font-size':'15px'}},}
            ymarks = {ymin : {'label': '{}'.format(float(round(ymin,1))), 'style': {'color':'white','font-size':'15px'}},
                     ymax : {'label': '{}'.format(float(round(ymax,1))), 'style': {'color':'white','font-size':'15px'}},}
            zmarks = {zmin : {'label': '{}'.format(float(round(zmin,1))), 'style': {'color':'white','font-size':'15px'}},
                     zmax : {'label': '{}'.format(float(round(zmax,1))), 'style': {'color':'white','font-size':'15px'}},}

            make_mesh(SCAN.cropped_cube, minhu, triangles)
            
            return [xmin, xmax, xmarks, (xmin+xmax/2),
                    ymin, ymax, ymarks, (ymin+ymax/2),
                    zmin, zmax, zmarks, (zmin+zmax/2), '3D surface calculated!', True, 'button-pressed']
        else:
            message = 'No ROI selected! Please accept cropped cube in ROI tab!'

            return 0,1,[],1,0,1,[],1,0,1,[],1, message, True, 'button'
            raise PreventUpdate

@app.callback(
    [Output('3d_container', 'children'),
    Output('plot_3d_surface_message', 'message'),
    Output('plot_3d_surface_message', 'displayed'),
    Output('Update_3d', 'className'),],
    [Input('Update_3d', 'n_clicks'),],
    [Input('x_applicator', 'value'),
    Input('y_applicator', 'value'),
    Input('z_applicator', 'value'),
    Input('theta_applicator', 'value'),
    Input('phi_applicator', 'value'),
    Input('app_rot', 'value'),
    Input('kv_fields', 'value')],
    [State('kv_energy', 'value')])
def update_3D_plot(n_clicks, x, y, z, theta, phi, app_rot, field_size, energy):

    if n_clicks == None:
        return [], 'Please accept the applicator', False, 'button'
        raise PreventUpdate
    else:
        try: 
            SCAN
        except:
            message = 'Please import CT images first!'
            return [], message, True, 'button'
            raise PreventUpdate
            
        if energy == None:
            return [], 'Please select kV energy!', True, 'button'
            raise PreventUpdate

        if field_size == None:
            return [], 'Please select an applicator!', True, 'button'
            raise PreventUpdate
   
        if hasattr(SCAN, 'threeD_figure'):
            
            #Convert angles from degrees to radians
            theta_rad = np.radians(theta)
            phi_rad = np.radians(phi)
            
            combo_figure = copy.copy(SCAN.threeD_figure)
            z1 = 200*np.cos(theta_rad)
            x_temp = 200*np.sin(theta_rad)
            y1 = x_temp*np.sin(phi_rad)
            x1 = x_temp*np.cos(phi_rad)
            
            #Plotting the above ploints
            X = [x, x+x1]
            Y = [y, y+y1]
            Z = [z, z+z1]

            combo_figure.add_scatter3d(x = X, y = Y, z = Z, mode = 'lines+markers')
            
            #Creating a PHSP plane
            original_phsp = generate_original_phsp(field_size)

            #Moving PHSP in spherical polar coordinates
            new_phsp = move_plane(plane=original_phsp, spin=app_rot, theta=theta, phi=phi)

            temp_px, temp_py, temp_pz = EXT_pts(new_phsp)

            #Translating points from origin
            px = np.asarray(temp_px) + x
            py = np.asarray(temp_py) + y
            pz = np.asarray(temp_pz) + z

            combo_figure.add_mesh3d(x=px,y=py,z=pz,color='red',opacity=0.6)
    

            plot = dcc.Graph(figure=combo_figure, responsive=True, config={'autosizable':True}, style={'height':'100%'})
            
            o1 = 'DOSXYZnrc isocentre (x,y,z): {}'.format(str((round(x/10,2),round(y/10,2),round(z/10,2))))
            o2 = 'DOSXYZnrc Angle Theta from +z: {}'.format(str(theta))
            o3 = 'DOSXYZnrc Angle Phi from +x: {}'.format(str(phi))
            o4 = 'DOSXYZnrc d_source: {}'.format(str(0))
            o5 = 'DOSXYZnrc phi_col: {}'.format(str(app_rot))

            return [plot, '3D graph plotted', False, 'button-pressed']
        else:
            return [], 'Please calculate 3D surface first!', True, 'button'
            raise PreventUpdate

@app.callback(
    [Output('kv_fields', 'options'),
    Output('kv_fields', 'value'),
    Output('Update_3d', 'n_clicks')],
    Input('kv_energy', 'value')
)
def list_applicators(energy):
    try:
        SCAN
    except NameError:
        raise PreventUpdate

    opts=None
    if energy == 'beam1':
        opts = low_energy_applicators
    elif energy == 'beam2':
        opts = low_energy_applicators
    elif energy == 'beam3':
        opts = low_energy_applicators
    elif energy == 'beam4':
        opts = low_energy_applicators
    elif energy == 'beam5':
        opts = high_energy_applicators
    elif energy == 'beam6':
        opts = high_energy_applicators
    elif energy == 'beam7':
        opts = high_energy_applicators

    return [opts, None, None]

@app.callback(
    [Output('export_setup', 'className'),
    Output('export_dialog', 'message'),
    Output('export_dialog', 'displayed')],
    Input('export_setup', 'n_clicks'),
    [State('kv_energy', 'value'),
    State('kv_fields', 'value'),
    State('x_applicator', 'value'),
    State('y_applicator', 'value'),
    State('z_applicator', 'value'),
    State('theta_applicator', 'value'),
    State('phi_applicator', 'value'),
    State('app_rot', 'value')]
)
def export_set(n_clicks, energy, field, xapp, yapp, zapp, thetapp, phiapp, colapp):
    if n_clicks == None:
        raise PreventUpdate
    else:
        try: 
            SCAN
        except NameError:
            message = 'Please import CT images first!'
            return 'button', message, True
            raise PreventUpdate
            
        if energy == None:
            return 'button', 'Please select kV energy!', True
            raise PreventUpdate

        if field == None:
            return 'button', 'Please select a field size!', True
            raise PreventUpdate
   
        if hasattr(SCAN, 'threeD_figure'):

            phsp_file_path = str(energy)+str(field)+'.egsphsp1'

            phantom_file_path = gui_select_file('Please select the phantom file')
            phantom_file_name = phantom_file_path.split('\\')[-1]
            
            write_input_file(phantom_file_name, str(field), xapp, yapp, zapp, thetapp, phiapp, colapp, phsp_file_path)

            return 'button-pressed', 'Input file created successfully!', True

        else:
            return 'button', 'Please set up the applicator in the 3D plot!', True

if __name__ == '__main__':
    url = "http://127.0.0.1:8050/"
    webbrowser.open_new_tab(url)
    
    app.server.run(port=8050, host='127.0.0.1')
