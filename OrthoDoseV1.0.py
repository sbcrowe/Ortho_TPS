#=====================================================================================
#=====================================IMPORTS=========================================
#=====================================================================================
#Dash application modules
import dash
from dash import dash_table
from dash.dependencies import Input, Output, State
from dash import dcc
from dash import html
from dash.exceptions import PreventUpdate

#Plotly modules
import plotly.graph_objs as go
from plotly.graph_objs import *

#Windows modules
import webbrowser
from win32com.shell import shell
import win32ui, win32con
import sys
import os

#Math modules
import numpy as np
from skimage.draw import polygon

#Extra modules
import pandas as pd
import pydicom as dcm
from pydicom.dataset import Dataset, FileDataset

#=====================================================================================
#======================CONSTANTS - TO BE CHANGED BY BT USERS==========================
#=====================================================================================

#Dose to water (Gy) in the surface voxel on the central axis for each simulated applicator
#Used to calculate the ratio of 'MC output' to 'measured output' for each applicator
# and hence scale the MC dose distribution based on the simulated applicator and prescribed MU
kv_outputs_mc = {
    '70_20_2D':3.958506911759973e-19,
    '70_20_3D':4.1503459962139987e-19,
    '70_20_4D':4.2852819765688218e-19,
    '70_20_5D':4.366870732268827e-19,
    '70_20_6D':4.537034533030582e-19,
    '100_20_2D':4.840150990293687e-19,
    '100_20_3D':5.061577335418189e-19,
    '100_20_4D':5.351807498163192e-19,
    '100_20_5D':5.4113860613874605e-19,
    '100_20_6D':5.541235789435803e-19,
    '125_20_2D':4.171117399214944e-19,
    '125_20_3D':4.447983290918233e-19,
    '125_20_4D':4.589398794150027e-19,
    '125_20_5D':4.8263939957620295e-19,
    '125_20_6D':5.049022180268748e-19,
    '70_30_8D':2.0070586216606875e-19,
    '70_30_10D':2.0184092263603424e-19,
    '70_30_14D':2.0217031392466074e-19,
    '70_30_6x6':1.9945967591520616e-19,
    '70_30_6x8':1.935017837717809e-19,
    '70_30_10x10':2.0403153120062763e-19,
    '70_30_10x14':2.073294907169787e-19,
    '100_30_8D':2.4764959497228094e-19,
    '100_30_10D':2.5631171060013474e-19,
    '100_30_14D':2.7296612478926117e-19,
    '100_30_6x6':2.46311481199651e-19,
    '100_30_6x8':2.4565430348026873e-19,
    '100_30_10x10':2.6205254302184537e-19,
    '100_30_10x14':2.6666164308466577e-19,
    '125_30_8D':2.206437438502784e-19,
    '125_30_10D':2.3425521600181996e-19,
    '125_30_14D':2.476058836507617e-19,
    '125_30_6x6':2.1996290546821866e-19,
    '125_30_6x8':2.23216543707321e-19,
    '125_30_10x10':2.3593876919051205e-19,
    '125_30_10x14':2.4575416197019804e-19,
    '200_50_5D':8.381977204480659e-20,
    '200_50_6x6':8.785661067657833e-20,
    '200_50_6x8':8.694161123033447e-20,
    '200_50_8x8':9.081629787707117e-20,
    '200_50_6x10':8.845903367054842e-20,
    '200_50_8x10':9.158250082490652e-20,
    '200_50_10x10':9.537282728074242e-20,
    '200_50_12x12':9.78160720577491e-20,
    '200_50_8x15':9.763050777359724e-20,
    '200_50_10x15':9.85248515694854e-20,
    '200_50_15x15':1.0323234435310166e-19,
    '200_50_10x20':9.783992368941467e-20,
    '200_50_20x20':1.0734048962603096e-19
}

#Measured kilovoltage unit outputs on the surface of the water phantom 
#on the centra axis of the beam for 100 MU
#cGy/100MU divided by 10,000 = Gy/MU
kv_outputs_real = {
    '70_20_2D':193.1/10000,
    '70_20_3D':203.5/10000,
    '70_20_4D':208.8/10000,
    '70_20_5D':214.5/10000,
    '70_20_6D':218.5/10000,
    '100_20_2D':183.9/10000,
    '100_20_3D':195.9/10000,
    '100_20_4D':203.6/10000,
    '100_20_5D':208.5/10000,
    '100_20_6D':212.0/10000,
    '125_20_2D':174.1/10000,
    '125_20_3D':186.4/10000,
    '125_20_4D':195.6/10000,
    '125_20_5D':202.0/10000,
    '125_20_6D':208.6/10000,
    '70_30_8D':99.1/10000,
    '70_30_10D':100.0/10000,
    '70_30_14D':102.6/10000,
    '70_30_6x6':97.2/10000,
    '70_30_6x8':98.4/10000,
    '70_30_10x10':101.2/10000,
    '70_30_10x14':101.4/10000,
    '100_30_8D':99.1/10000,
    '100_30_10D':100.0/10000,
    '100_30_14D':104.9/10000,
    '100_30_6x6':97.1/10000,
    '100_30_6x8':98.3/10000,
    '100_30_10x10':102.3/10000,
    '100_30_10x14':103.2/10000,
    '125_30_8D':97.1/10000,
    '125_30_10D':100.0/10000,
    '125_30_14D':105.4/10000,
    '125_30_6x6':94.9/10000,
    '125_30_6x8':95.9/10000,
    '125_30_10x10':102.2/10000,
    '125_30_10x14':103.4/10000,
    '200_50_5D':85.9/10000,
    '200_50_6x6':91.7/10000,
    '200_50_6x8':94.9/10000,
    '200_50_8x8':97.4/10000,
    '200_50_6x10':95.5/10000,
    '200_50_8x10':99.7/10000,
    '200_50_10x10':100.0/10000,
    '200_50_12x12':106.0/10000,
    '200_50_8x15':102.1/10000,
    '200_50_10x15':106.2/10000,
    '200_50_15x15':110.1/10000,
    '200_50_10x20':107.5/10000,
    '200_50_20x20':113.2/10000,
}

#=====================================================================================
#======================================FUNCTIONS======================================
#=====================================================================================

# Browsing/Directories functions
def orientation_label(X, Y, T):
    '''
    Used to generate letters indicating CT right/left/ant/post/sup/inf in all 
    appropriate plots.
    '''
    L = dict(x=X, y=Y, text=T, showarrow=False, font=dict(family='"Segoe UI",Arial,sans-serif', size=20, color="#ffffff"), 
    bordercolor="#000000", borderwidth=2, borderpad=3, bgcolor="#f25504", opacity=1)

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
    Opens a browser and returns the path to the selected directory.
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


def gui_select_file(title, start_dir=None):
    '''
    Opens a browser and returns the path to the selected file.
    '''
    fd = win32ui.CreateFileDialog(1)

    fd.SetOFNTitle(title)

    if fd.DoModal()==win32con.IDCANCEL:
        sys.exit(1)
        
    filepath = fd.GetPathName()
    
    return filepath


def gui_save_file():
    '''
    Opens a save-file dialog.
    
    '''
    flags = win32con.OFN_OVERWRITEPROMPT
    fd = win32ui.CreateFileDialog(0, None, None, flags, "RTdose Files (*.dcm)|*.dcm||")

    fd.SetOFNTitle('Save RTdose file as')

    if fd.DoModal()==win32con.IDCANCEL:
        sys.exit(1)
        
    #if fd.DoModal()==win32con.IDOK:
    n = fd.GetPathName()
    
    return n


# Importing CT array and dose cube

def load_CT_array(array_path, allow_pickle=True):
    ct_array = np.load(array_path)
    
    voxels = ct_array[0]
    xpos = ct_array[1]
    ypos = ct_array[2]
    zpos = ct_array[3]
    
    return voxels, xpos, ypos, zpos


def create_DOSE_cube(my_path):
    '''
    Takes the path to the .3ddose file and returns a 3D dose cube.
    '''
    print('Reading 3ddose file...')
    sim = pd.read_csv(my_path, encoding ='latin1')
    
    print('     Reading coordinates...')

    xpo = np.array(sim.values[0,:][0].split()).astype('float') * 10
    ypo = np.array(sim.values[1,:][0].split()).astype('float') * 10
    zpo = np.array(sim.values[2,:][0].split()).astype('float') * 10
    
    print('     Reading dose values...')

    sim_val = np.array(sim.values[3,:][0].split()).astype('float') #Dose values
    sim_err = np.array(sim.values[4,:][0].split()).astype('float') #Percentage error values
    act_err = np.asarray(sim_val * sim_err) #Values multiplied by their percentage errors

    print('3ddose file read!')

    print('Creating 3D dose array...')
    num_vox = np.array(sim.columns.values)[0].split()

    ERROR_cube = act_err.reshape(int(num_vox[2]),int(num_vox[1]),int(num_vox[0])) #(Z,Y,X)
    DOSE_cube = sim_val.reshape(int(num_vox[2]),int(num_vox[1]),int(num_vox[0])) #(Z,Y,X)
    print('3D dose array created!')
    
    print('Creating dose grid...')
    #Interpolating dose to a fine grid for accurate DVH calculation
    finexgrid = np.arange(xpo[0], xpo[-1], SCAN.fine_x_step)
    fineygrid = np.arange(ypo[0], ypo[-1], SCAN.fine_y_step)
    zgrid = np.arange(zpo[0], zpo[-1], SCAN.z_step)
    print('Dose grid created!')
    PERCENTAGE_ERROR_cube = np.around((ERROR_cube/DOSE_cube)*100,1)

    return DOSE_cube, finexgrid, fineygrid, zgrid, PERCENTAGE_ERROR_cube


# Plotting CT 

def plot_ROI(cube,slicez,slicex,slicey,window,plot_dose,min_dose,max_dose, cA, cS, cC, plot_contours):

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
    
    
    if plot_dose:
        if hasattr(SCAN, 'dose_cube'):
            DOSE_cube_copy = np.copy(SCAN.updated_dose)
            ERROR_cube_copy = np.copy(SCAN.error_cube)
            
            #Hiding zero dose and dose outside of selected range
            DOSE_cube_copy[DOSE_cube_copy==0] = None
            DOSE_cube_copy[DOSE_cube_copy<float(min_dose)] = None
            DOSE_cube_copy[DOSE_cube_copy>float(max_dose)] = None

            ERROR_cube_copy[DOSE_cube_copy==0] = None
            ERROR_cube_copy[DOSE_cube_copy<float(min_dose)] = None
            ERROR_cube_copy[DOSE_cube_copy>float(max_dose)] = None

            axial_dose_slice_idx = (np.abs(cube.zdose - slicez)).argmin()
            coronal_dose_slice_idx = (np.abs(cube.ydose - slicey)).argmin()
            saggital_dose_slice_idx = (np.abs(cube.xdose - slicex)).argmin()
            
            axial_dose_xs = np.around(cube.xdose,2)
            axial_dose_ys = np.around(cube.ydose,2)

            saggital_dose_xs = np.around(cube.ydose,2)
            saggital_dose_ys = np.around(cube.zdose,2)

            coronal_dose_xs = np.around(cube.xdose,2)
            coronal_dose_ys = np.around(cube.zdose,2)
            
            #axial_z = np.around(DOSE_cube_copy[axial_dose_slice_idx,:,:],2)
            #saggital_z = np.around(DOSE_cube_copy[:,:,saggital_dose_slice_idx],2)
            #coronal_z = np.around(DOSE_cube_copy[:,coronal_dose_slice_idx,:],2)

            axial_z = DOSE_cube_copy[axial_dose_slice_idx,:,:]
            saggital_z = DOSE_cube_copy[:,:,saggital_dose_slice_idx]
            coronal_z = DOSE_cube_copy[:,coronal_dose_slice_idx,:]

            axial_error_z = ERROR_cube_copy[axial_dose_slice_idx,:,:]
            saggital_error_z = ERROR_cube_copy[:,:,saggital_dose_slice_idx]
            coronal_error_z = ERROR_cube_copy[:,coronal_dose_slice_idx,:]
            
            #current_dose_min = np.min((axial_z, saggital_z, coronal_z))
            #current_dose_max = np.max((axial_z, saggital_z, coronal_z))
            
            current_dose_min = float(min_dose)
            current_dose_max = float(max_dose)
            
            hover_axial = 'Dose: %{z}+/-%{customdata}%, <br> x: %{x}, <br> y: %{y}'
            hover_saggital = 'Dose: %{z}+/-%{customdata}%, <br> y: %{x}, <br> z: %{y}'
            hover_coronal = 'Dose: %{z}+/-%{customdata}%, <br> x: %{x}, <br> z: %{y}'
    
    
            axial_dose = go.Heatmap(
                            x=axial_dose_xs,
                            y=axial_dose_ys,
                            z=axial_z,
                            showscale=False,
                            opacity=0.5,
                            colorscale='Jet',
                            name='Dose',
                            #hoverinfo='z+name',
                            customdata = axial_error_z,
                            hoverongaps = False,
                            hoverlabel=dict(bgcolor='green'),
                            hovertemplate = hover_axial,
                            zmin = current_dose_min,
                            zmax = current_dose_max
                        )
            saggital_dose = go.Heatmap(
                            x=saggital_dose_xs,
                            y=saggital_dose_ys,
                            z=saggital_z,
                            showscale=False,
                            opacity=0.5,
                            colorscale='Jet',
                            name='Dose',
                            #hoverinfo='z+name',
                            customdata = saggital_error_z,
                            hoverongaps = False,
                            hoverlabel=dict(bgcolor='green'),
                            hovertemplate = hover_saggital,
                            zmin = current_dose_min,
                            zmax = current_dose_max
                        )
            coronal_dose = go.Heatmap(
                            x=coronal_dose_xs,
                            y=coronal_dose_ys,
                            z=coronal_z,
                            showscale=True,
                            opacity=0.5,
                            colorscale='Jet',
                            name='Dose',
                            #hoverinfo='z+name',
                            customdata = coronal_error_z,
                            hoverongaps = False,
                            hoverlabel=dict(bgcolor='green'),
                            hovertemplate = hover_coronal,
                            zmin = current_dose_min,
                            zmax = current_dose_max,
                            colorbar=dict(thickness=10,
                                       ticklen=3, tickcolor='white',
                                       tickfont=dict(size=18, color='white'))
                        )
    
    
    
    
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
    
    
    layout_axial = {'autosize':True,
              'shapes': [saggital_line_on_axial,coronal_line_on_axial,
                        axial_outline_bottom, axial_outline_top, axial_outline_right, axial_outline_left,],
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
                        saggital_outline_bottom, saggital_outline_top, saggital_outline_right, saggital_outline_left],
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
                        coronal_outline_bottom, coronal_outline_top, coronal_outline_right, coronal_outline_left],
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
    if plot_dose:
        if plot_contours:
            saggital_fig = go.Figure([saggital_heatmap,saggital_dose]+cS, layout_saggital)
            coronal_fig = go.Figure([coronal_heatmap,coronal_dose]+cC, layout_coronal)
            axial_fig = go.Figure([axial_heatmap,axial_dose]+cA, layout_axial)
        else:
            saggital_fig = go.Figure([saggital_heatmap,saggital_dose], layout_saggital)
            coronal_fig = go.Figure([coronal_heatmap,coronal_dose], layout_coronal)
            axial_fig = go.Figure([axial_heatmap,axial_dose], layout_axial)
    else:
        if plot_contours:
            saggital_fig = go.Figure([saggital_heatmap]+cS, layout_saggital)
            coronal_fig = go.Figure([coronal_heatmap]+cC, layout_coronal)
            axial_fig = go.Figure([axial_heatmap]+cA, layout_axial)
        else:
            saggital_fig = go.Figure(saggital_heatmap, layout_saggital)
            coronal_fig = go.Figure(coronal_heatmap, layout_coronal)
            axial_fig = go.Figure(axial_heatmap, layout_axial)
    
    return saggital_fig, coronal_fig, axial_fig


class patient:
    
    def __init__(self, cube, xs, ys, zs):
        
        self.cube = cube
        self.xs = xs
        self.ys = ys
        self.zs = zs

def create_dcc_graph(fig):
    G = dcc.Graph(
        figure=fig,
        config={
            'displayModeBar':False,
            'autosizable':True,
            'responsive':True,
            'scrollZoom': True
        }, 
        style={
            'height':'100%'
        }
    )
    return G


def find_index(array, value):
    index = (np.abs(array - value)).argmin()
    
    return index

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
                                        'font-size':'20px'}} for i in SCAN.HFS_zs[::30]}
        else:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'20px'}} for i in SCAN.HFS_zs[::-1][::30]}
        
    elif view == 'S':
        Sstep = SCAN.x_step
        Smin = np.min(SCAN.HFS_xs)
        Smax = np.max(SCAN.HFS_xs)
        Svalue = SCAN.HFS_xs[int(len(SCAN.HFS_xs)/2)]
        
        if SCAN.HFS_xs[0]<SCAN.HFS_xs[-1]:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'20px'}} for i in SCAN.HFS_xs[::30]}
        else:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'20px'}} for i in SCAN.HFS_xs[::-1][::30]}
        
    elif view == 'C':
        Sstep = SCAN.y_step
        Smin = np.min(SCAN.HFS_ys)
        Smax = np.max(SCAN.HFS_ys)
        Svalue = SCAN.HFS_ys[int(len(SCAN.HFS_ys)/2)]
        
        if SCAN.HFS_ys[0]<SCAN.HFS_ys[-1]:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'20px'}} for i in SCAN.HFS_ys[::30]}
        else:
            Smarks = {int(i) : {'label' : int(i), 
                                'style':{'color':'white',
                                        'font-size':'20px'}} for i in SCAN.HFS_ys[::-1][::30]}
        
    return Sstep, Smin, Smax, Svalue, Smarks 


# Application
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
            print('File: ', s, ' does not have SOPInstanceUID')
        
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
        
    return x_coordinates, y_coordinates


class structure:
    
    def __init__(self, number, name, color, total_volume, dose_cube, truncated_volume, cube):
        self.number = number
        self.name = name
        self.color = color
        self.total_volume = total_volume/1000
        self.dose_cube = dose_cube
        self.truncated_volume = truncated_volume/1000
        self.cube = cube


def calculate_volume(cube):#, xs, ys, zs):
    dummy_cube = np.ones((cube.shape[0], cube.shape[1], cube.shape[2]))
    
    dummy_cube = dummy_cube*SCAN.dose_voxel_volume
                
    return dummy_cube


class scan:
    '''
    CT cube class which stores all the useful information from the
    DICOM files uploaded.
    '''
    
    def __init__(self, slices):
        
        self.phantom_created = False
        self.progress = 0
        self.stage = 1
        
        #Raw files
        self.slices = slices
        
        #Basic information to display
        self.patient_name = str(self.slices[0].PatientName)
        self.patient_id = str(self.slices[0].PatientID)
        self.patient_dob = str(self.slices[0].PatientBirthDate)
        self.orientation = str(self.slices[0].PatientPosition)
        try:
            aq_date = str(self.slices[0].AcquisitionDate)
        except:
            aq_date = '00000000000'
        self.acquisition_date = aq_date[6:] + '/' + aq_date[4:6] + '/' + aq_date[:4] 
        
        #Resolution in x, y, z directions
        self.x_step = self.slices[0].PixelSpacing[0]
        self.y_step = self.slices[0].PixelSpacing[1]
        self.z_step = self.slices[0].SliceThickness
        
        #Subdividing voxels for accurate volume calculations
        #self.fine_x_step = float(self.x_step)/2
        #self.fine_y_step = float(self.y_step)/2

        self.fine_x_step = self.x_step
        self.fine_y_step = self.y_step
        
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
        
        voxel_volume = self.x_step * self.y_step * self.z_step
        self.volume_cube = np.ones((self.HFS_cube.shape[0], self.HFS_cube.shape[1], self.HFS_cube.shape[2])) * voxel_volume
        
        self.dose_voxel_volume = self.fine_x_step * self.fine_y_step * self.z_step
        #self.dose_volume_cube = np.ones((self.HFS_cube.shape[0], self.HFS_cube.shape[1], self.HFS_cube.shape[2])) * voxel_volume


def contour_structures(selected_structures, slider1,slider2,slider3):
    axial_slice_idx = (np.abs(SCAN.HFS_zs - slider1)).argmin()
    coronal_slice_idx = (np.abs(SCAN.HFS_ys - slider3)).argmin()
    saggital_slice_idx = (np.abs(SCAN.HFS_xs - slider2)).argmin()
    
    contour_plots_A = []
    contour_plots_S = []
    contour_plots_C = []
    
    for i in SCAN.structures:
        if i.number in selected_structures:
                
            a_masked = i.cube[axial_slice_idx,:,:].astype(np.float16)
            a_masked[a_masked==0] = None
            
            s_masked = i.cube[:,:,saggital_slice_idx].astype(np.float16)
            s_masked[s_masked==0] = None
            
            c_masked = i.cube[:,coronal_slice_idx,:].astype(np.float16)
            c_masked[c_masked==0] = None
            
            
            contour_i_plot_A = go.Heatmap(
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

            contour_i_plot_S = go.Heatmap(
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

            contour_i_plot_C = go.Heatmap(
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
            
            contour_plots_A.append(contour_i_plot_A)
            contour_plots_S.append(contour_i_plot_S)
            contour_plots_C.append(contour_i_plot_C)
            
    return contour_plots_A, contour_plots_S, contour_plots_C, 

def calc_dvh(structure_id, prescribed_dose, dose_cube):
    print('Structure: ', SCAN.structures[structure_id].name )
    print('Total volume: ',round(SCAN.structures[structure_id].total_volume,2))
    print('Truncated volume: ', round(SCAN.structures[structure_id].truncated_volume,2))
    
    doses_of_interest = dose_cube[SCAN.structures[structure_id].dose_cube==1]
    
    max_dose = np.max(doses_of_interest)

    mean_dose = sum(doses_of_interest)/len(doses_of_interest)
    
    fine_dose_bins = np.arange(0,float(prescribed_dose),0.1) # Fine dose bins 0-100Gy
    coarse_dose_bins = np.arange(float(prescribed_dose),max_dose,1) #Coarse dose bins 100+ Gy
    
    dose_bin_values = np.append(fine_dose_bins,coarse_dose_bins)
    
    def calc_dose_bin(dose_bin_value1, dose_bin_value2):
        n_voxels_of_interest = np.logical_and(doses_of_interest>=dose_bin_value1, doses_of_interest<=dose_bin_value2).sum()

        total_volume = n_voxels_of_interest * SCAN.dose_voxel_volume

        return total_volume
        
    Ds = dose_bin_values[1:]
    Vs = list(map(lambda a: calc_dose_bin(dose_bin_values[a],dose_bin_values[a+1]), range(len(dose_bin_values[:-1]))))
        
    cumulative_volume = list(map(lambda a: (sum(Vs[a:])/sum(Vs))*100 ,range(len(Ds))))
    abs_volumes = list(map(lambda a: (sum(Vs[a:])/1000) ,range(len(Ds))))
        
    SCAN.structures[structure_id].dose_bins = Ds
    SCAN.structures[structure_id].cumulative_volume = cumulative_volume #Relative volumes
    SCAN.structures[structure_id].volumes = abs_volumes #Absolute volumes
    SCAN.structures[structure_id].dmax = max(doses_of_interest)
    SCAN.structures[structure_id].dmin = min(doses_of_interest)
    SCAN.structures[structure_id].dmean = mean_dose
    return 


def colour_rows(d):
    '''
    Used to apply a style to rows of a table, namely the colour-coding.
    '''
    c_style=[{'if': {'column_id': 'Structure'},
             'width': '30%'},
            {'if': {'column_id': 'Dmin'},
             'width': '10%'},
            {'if': {'column_id': 'Dmax'},
             'width': '10%'},
            {'if': {'column_id': 'Dmean'},
             'width': '10%'},
            {'if': {'column_id': 'V %'},
             'width': '10%'},
            {'if': {'column_id': 'V cm3'},
             'width': '10%'},
            {'if': {'column_id': 'D %'},
             'width': '10%'},
            {'if': {'column_id': 'D Gy'},
             'width': '10%'}]
    
    for i in range(len(d)):
        row = d[i]
        colour = row['color']
        #c_style.append({'if': {'row_index':'odd'}, 'backgroundColor': '#A0A0A0'})
        c_style.append({'if': {'row_index':i,'column_id': 'Structure'}, 'backgroundColor': colour})

    return c_style


def gen_dicom_dose_file(dose_array, res_x, res_y):
    suffix = '.dcm'
    filename_little_endian = 'mydcm'
    filename_big_endian = 'mydcm'
    
    #Populate required values for file meta information
    file_meta = Dataset()
    
    file_meta.FileMetaInformationGroupLength = 186
    # Number of bytes following this File Meta Element (end of the value field)
    # up to and including the last File Meta Element of the Group 2 File Meta Information
    
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    # This is a two byte field where each bit identifies a version of this File Meta Information header.
    # In version 1 the first byte value is 00H and the second byte value is 01H
    
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2' #RT Dose file
    file_meta.MediaStorageSOPInstanceUID = dcm.uid.generate_uid()
    file_meta.ImplementationClassUID = '1.2.246.352.70.2.1.160.3'
    file_meta.ImplementationVersionName = 'DCIE 16.1'
    file_meta.TransferSyntaxUID = dcm.uid.ImplicitVRLittleEndian
    
    #Create the file dataset instance (initially no data elements but file metadata supplied)
    ds = FileDataset(filename_little_endian, {}, file_meta = file_meta, preamble = b'\0' * 128)
    
    #Set the transfer syntax
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    
    #Add data elements
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    ds.SOPInstanceUID = dcm.uid.generate_uid()
    ds.StudyInstanceUID = SCAN.slices[0].StudyInstanceUID
    ds.SeriesInstanceUID = dcm.uid.generate_uid()
    ds.FrameOfReferenceUID = SCAN.slices[0].FrameOfReferenceUID
    
    #Add patient info
    ds.PatientName = SCAN.patient_name
    ds.PatientID = SCAN.patient_id
    ds.PatientBirthDate = SCAN.patient_dob
    ds.ImagePositionPatient = [SCAN.xdose[0], SCAN.ydose[0], SCAN.zdose[0]] 
    #Orientation of dose is HFS irrespective of CT orientation
    #because DOSXYZphantom is always oriented in increasing x,y,z coordinates
    #and so the xdose[0] etc. are always going to be minimal coordinate (e.g. -165mm)
    #
    ds.ImageOrientationPatient = [1,0,0,0,1,0] #SCAN.slices[0].ImageOrientationPatient
    ds.Modality = 'RTDOSE'
    ds.PhotometricInterpretation = 'MONOCHROME2'
        
    #Set dose plotting data
    ds.GridFrameOffsetVector = list((SCAN.zdose - min(SCAN.zdose))[:-1])
    ds.SamplesPerPixel = 1
    ds.FrameIncrementPointer = dcm.tag.Tag(0x3004, 0x000c)
    ds.BitsAllocated = 32
    ds.BitsStored = 32
    ds.HighBit = 31
    ds.PixelRepresentation = 0
    ds.DoseUnits = 'GY'
    dose_scaling_factor = np.max(dose_array)/2000000000 #Maximum int32 value is 2.147 billion so scaling max dose to 2b to be safe
    scaled_dose = dose_array/dose_scaling_factor
    ds.DoseGridScaling = str(dose_scaling_factor)
    ds.DoseSummationType = 'PLAN'
    ds.SliceThickness = None
    
    myseq = Dataset()
    ds.ReferencedRTPlanSequence = dcm.sequence.Sequence([myseq])
    ds.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = dcm.uid.generate_uid()
    ds.ReferencedRTPlanSequence[0].ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.5'
    
    integer_scaled_dose = scaled_dose.astype(int)
    ds.PixelData = integer_scaled_dose.tobytes()
    ds.Rows = dose_array.shape[1]
    ds.Columns = dose_array.shape[2]
    ds.NumberOfFrames = SCAN.dose_cube.shape[0]
    ds.PixelSpacing = [str(res_x), str(res_y)]
    
    name = gui_save_file()
    dcm_name = name.split('\\')[-1]
    #Custom strings
    ds.SeriesDescription = dcm_name
    
    ds.save_as(name + '.dcm')
    print('DICOM Dose File saved successfully')
    
    return name + '.dcm'

def generate_dvh_table():
    dvh_table_dict = {
        'Structure':[i.name for i in SCAN.structures],
        'Dmin':[round(i.dmin,2) for i in SCAN.structures],
        'Dmax':[round(i.dmax,2) for i in SCAN.structures],
        'Dmean':[round(i.dmean,2) for i in SCAN.structures],
        'V %':[0 for i in SCAN.structures],
        'V cm3':[0 for i in SCAN.structures],
        'D %':[0 for i in SCAN.structures],
        'D Gy':[0 for i in SCAN.structures],
        'color':['rgba(%d,%d,%d,0.5)'%(i.color[0],i.color[1],i.color[2]) for i in SCAN.structures]
    }
    
    data_frame = pd.DataFrame(dvh_table_dict)
    
    table = dash_table.DataTable(
                id='DVH-table',
                columns=[
                    {"name": 'Structure', "id": 'Structure', 'editable':False},
                    {"name": 'Dmin', "id": 'Dmin', 'editable':False},
                    {"name": 'Dmax', "id": 'Dmax', 'editable':False},
                    {"name": 'Dmean', "id": 'Dmean', 'editable':False},
                    {"name": 'V %', "id": 'V %', 'editable':True, 'type':'numeric'},
                    {"name": 'V cm3', "id": 'V cm3', 'editable':True, 'type':'numeric'},
                    {"name": 'D %', "id": 'D %', 'editable':True, 'type':'numeric'},
                    {"name": 'D Gy', "id": 'D Gy', 'editable':True, 'type':'numeric'}
                ],
                data=data_frame.to_dict('records'),
                row_selectable="multi",
                editable=False,
                fixed_rows={'headers': True},
                style_table={'height': '79rem', 'overflowY': 'auto', 'max-height':'79rem'},
                style_cell = {
                    'font_family': '"Segoe UI",Arial,sans-serif',
                    'font_size': '20px',
                    'text_align': 'left',
                    'color':'black',
                    'backgroundColor':'#C0C0C0'
                },
                style_header={
                    'backgroundColor': '#696969',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                selected_rows=[i for i in range(len(SCAN.structures))],
                style_cell_conditional=colour_rows(data_frame.to_dict('records')),
            )
    return table

#=====================================================================================
#======================================APPLICATION====================================
#=====================================================================================

app = dash.Dash(__name__,)

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

app.title = 'OrthoDose'
app._favicon = ('favicon_d.ico')

SCAN = 1
del SCAN

#=====================================================================================
#============================APPLICATION LAYOUT=======================================
#=====================================================================================

app.layout = html.Div(
    children=[
        html.Div(
            id='disclaimer',
            hidden=False,
            style={'backgroundColor': colors['background'],
           'borderTop': '0.5vh solid #FF8000',
           'borderBottom': '0.5vh solid #FF8000',
           'borderLeft': '0.3vw solid #FF8000',
           'borderRight': '0.3vw solid #FF8000',
           'height':'100vh',
          },

            children=[
            html.H1('Disclaimer',style={
                                'height':'5%',
                                'textAlign': 'center',
                                'font-family': 'Arial, Helvetica, sans-serif',
                                'font-size':'5vh',
                                'letter-spacing':'0.2vw',
                                'font-weight':'bold',
                                'background-image': '-webkit-linear-gradient(#f79800,#EF3405)',
                                '-webkit-background-clip': 'text',
                                '-webkit-text-fill-color': 'transparent',
                            }),
            html.P('''By clicking \'I ACKNOWLEDGE\', you acknowledge and agree that this application is not CE marked and is not 
                    a certified medical device. Hence this software should not be used to make clinical decisions.
                    It is intended to be used solely for education and guidance purposes.
                    \n
                    \n
                    The application is provided 'as is' without warranty of any kind. In no event shall the author 
                    be liable for any claim, damages, harm or other liability, arising from, out of or in connection with
                    the application or the use or other dealings in the application.                     
                    
                      ''', style={'marginTop':'3vh','paddingLeft':'20vw','paddingRight':'20vw','color':'white', 'font-size':'x-large'}),
            html.Button('I acknowledge', id='acknowledge-button', n_clicks=0,style={'marginLeft':'20vw','marginTop':'3vh'})
            ]
        ),


        html.Div(
            id = 'main_application',
            hidden = True,
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
                        'height':'90vh',
                        'width':'100%',
                        'backgroundColor':colors['background'],
                    },
                    children=[
                        dcc.ConfirmDialog(
                            id='imported_CT',
                            message='',
                        ),
                        dcc.ConfirmDialog(
                            id='saved_dicom',
                            message='',
                        ),

                        dcc.ConfirmDialog(
                            id='error_dose_display',
                            message='',
                        ),
                        
                        dcc.Tabs(
                            style=tabs_styles,
                            children=[

                                dcc.Tab(
                                    label='Dose Distribution',
                                    style=tab_style,
                                    selected_style=tab_selected_style,
                                    children=[
                                        html.Div(
                                            children=[
                                                html.Div(
                                                    style={
                                                        'backgroundColor': '#272b30',
                                                        'height':'25%',
                                                        'width':'100%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': '#272b30',
                                                                'height':'100%',
                                                                'width':'20%',
                                                                'display':'inline-block',
                                                                'vertical-align': 'top',
                                                                #'borderLeft':'0.1vh solid #FF8000'
                                                            },
                                                            children=[
                                                                html.H3(
                                                                    children='Importer',
                                                                    style={
                                                                        'textAlign': 'center',
                                                                        'color': colors['text'],
                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                        'padding': '0',
                                                                        'marginTop': '0.5vh',
                                                                        'marginBottom': '0%',
                                                                        'paddingBottom':'0.5vh',
                                                                        'borderBottom':'0.1vh solid #FF8000'
                                                                    }
                                                                ),

                                                                html.Button(
                                                                    'Import CT Files',
                                                                    id = 'B_import_ct',
                                                                    n_clicks = None,
                                                                    title='Select a folder with DICOM CT data',
                                                                    style={'marginTop':'1.5vh', 'marginBottom':'1vh', 'width':'90%', 'height':'5.5vh',
                                                                        'marginLeft':'5%', 'marginRight':'5%'}
                                                                ),
                                                                
                                                                html.Button(
                                                                    'Import MC Dose',
                                                                    id = 'B_import_dose',
                                                                    n_clicks = None,
                                                                    title='Select a MC generated dose file',
                                                                    style={'marginTop':'0.7vh', 'marginBottom':'1vh', 'width':'90%', 'height':'5.5vh',
                                                                        'marginLeft':'5%', 'marginRight':'5%',}
                                                                ),
                                                            ]
                                                        ),
                                                        html.Div(
                                                            style={
                                                                'backgroundColor': '#272b30',
                                                                'height':'100%',
                                                                'width':'60%',
                                                                'display':'inline-block',
                                                                'vertical-align': 'top',
                                                                'borderLeft':'0.1vh solid #FF8000'                                                        
                                                            },
                                                            children=[
                                                                html.H3(
                                                                    children='Dose Normalization',
                                                                    style={
                                                                        'textAlign': 'center',
                                                                        'color': colors['text'],
                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                        'padding': '0',
                                                                        'marginTop': '0.5vh',
                                                                        'marginBottom': '0%',
                                                                        'paddingBottom':'0.5vh',
                                                                        'borderBottom':'0.1vh solid #FF8000'
                                                                    }
                                                                ),
                                                                html.Div(
                                                                    style={
                                                                    'backgroundColor': '#272b30',
                                                                        'height':'69%',
                                                                        'width':'77%',
                                                                        'display':'inline-block',
                                                                        'vertical-align': 'top',
                                                                        'marginTop':'1%'
                                                                    },
                                                                    children=[
                                                                        html.Div(
                                                                            style={
                                                                            'backgroundColor': '#272b30',
                                                                                'height':'50%',
                                                                                'width':'100%',
                                                                                'display':'inline-block',
                                                                                'vertical-align': 'top',
                                                                                'marginTop':'0%'
                                                                            },
                                                                            children=[
                                                                                html.H4(
                                                                                    children='Normalize to:',
                                                                                    style={
                                                                                        'textAlign': 'right',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        'width':'35%',
                                                                                        'marginLeft':'5%',
                                                                                        'marginRight':'1%',
                                                                                        'marginTop':'1vh'
                                                                                    }
                                                                                ),

                                                                                dcc.RadioItems(
                                                                                    id='norm_to',
                                                                                    options=[
                                                                                        {'label': 'Point', 'value': 'pt'},
                                                                                        {'label': 'Output', 'value': 'output'},
                                                                                    ],
                                                                                    value='output',
                                                                                    labelStyle={'display':'inline-block',
                                                                                            'font-size':'1.2vw',
                                                                                            'color':'white',
                                                                                            'margin-left': '0.1vw',
                                                                                            'margin-right': '1vw',},
                                                                                    inputStyle={'width':'2vw',
                                                                                            'height':'2vh',
                                                                                            'margin-left': '0.5vw',
                                                                                            'margin-right': '0vw'},
                                                                                    style={'width':'59%',
                                                                                            'display':'inline-block',
                                                                                            'marginBottom':'0.1vh'}
                                                                                ),
                                                                            ]
                                                                        ),

                                                                        html.Div(
                                                                            id='norm_container',
                                                                            style={
                                                                                'backgroundColor': '#272b30',
                                                                                'height':'50%',
                                                                                'width':'100%',
                                                                                'display':'inline-flex',
                                                                                #'justifyContent':'space-between',
                                                                                'vertical-align':'middle',
                                                                                'paddingTop':'1vh'
                                                                        
                                                                            },
                                                                            children=[
                                                                                html.H4(
                                                                                    children='X:',
                                                                                    style={
                                                                                        'textAlign': 'left',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        #'width':'35%',
                                                                                        'marginLeft':'1vw',
                                                                                        'marginRight':'0.3vw',
                                                                                        'marginTop':'0vh'
                                                                                    }
                                                                                ),

                                                                                dcc.Input(
                                                                                    id='xnorm',
                                                                                    type='numeric',
                                                                                    placeholder='X',
                                                                                    value=None,
                                                                                    debounce=True,
                                                                                    inputMode='numeric',
                                                                                    step=0.01,
                                                                                    style={
                                                                                        'display':'inline-block',
                                                                                        'width': '3vw', #'-webkit-fill-available',
                                                                                        'height':'4vh',
                                                                                        #'height': '-webkit-fill-available',
                                                                                        'vertical-align':'center'
                                                                                    }
                                                                                ),

                                                                                html.H4(
                                                                                    children='Y:',
                                                                                    style={
                                                                                        'textAlign': 'left',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        #'width':'35%',
                                                                                        'marginLeft':'1vw',
                                                                                        'marginRight':'0.3vw',
                                                                                        'marginTop':'0vh'
                                                                                    }
                                                                                ),

                                                                                dcc.Input(
                                                                                    id='ynorm',
                                                                                    type='numeric',
                                                                                    placeholder='Y',
                                                                                    value=None,
                                                                                    debounce=True,
                                                                                    inputMode='numeric',
                                                                                    step=0.01,
                                                                                    style={
                                                                                        'display':'inline-block',
                                                                                        'width': '3vw',
                                                                                        'height':'4vh',
                                                                                        #'height': '-webkit-fill-available',
                                                                                        'vertical-align':'center'
                                                                                    }
                                                                                ),

                                                                                html.H4(
                                                                                    children='Z:',
                                                                                    style={
                                                                                        'textAlign': 'left',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        #'width':'35%',
                                                                                        'marginLeft':'1vw',
                                                                                        'marginRight':'0.3vw',
                                                                                        'marginTop':'0vh'
                                                                                    }
                                                                                ),

                                                                                dcc.Input(
                                                                                    id='znorm',
                                                                                    type='numeric',
                                                                                    placeholder='Z',
                                                                                    value=None,
                                                                                    debounce=True,
                                                                                    inputMode='numeric',
                                                                                    step=0.01,
                                                                                    style={
                                                                                        'display':'inline-block',
                                                                                        'width': '3vw',
                                                                                        'height':'4vh',
                                                                                        #'height': '-webkit-fill-available',
                                                                                        'vertical-align':'center'
                                                                                    }
                                                                                ),

                                                                                html.H4(
                                                                                    children='Dose:',
                                                                                    style={
                                                                                        'textAlign': 'left',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        #'width':'35%',
                                                                                        'marginLeft':'4vw',
                                                                                        'marginRight':'0.3vw',
                                                                                        'marginTop':'0vh'
                                                                                    }
                                                                                ),

                                                                                dcc.Input(
                                                                                    id='norm_dose',
                                                                                    type='numeric',
                                                                                    placeholder='Gy',
                                                                                    value=None,
                                                                                    debounce=True,
                                                                                    inputMode='numeric',
                                                                                    step=0.01,
                                                                                    style={
                                                                                        'display':'inline-block',
                                                                                        'width': '3vw',
                                                                                        'height':'4vh',
                                                                                        #'height': '-webkit-fill-available',
                                                                                        'vertical-align':'center'
                                                                                    }
                                                                                ),
                                                                            ]
                                                                        ),
                                                                        html.Div(
                                                                            id='norm_container2',
                                                                            style={
                                                                                'backgroundColor': '#272b30',
                                                                                'height':'50%',
                                                                                'width':'100%',
                                                                                'display':'inline-flex',
                                                                                #'justifyContent':'space-between',
                                                                                'vertical-align':'middle',
                                                                                'paddingTop':'1vh'
                                                                        
                                                                            },
                                                                            children=[
                                                                                html.H4(
                                                                                    children='Applicator:',
                                                                                    style={
                                                                                        'textAlign': 'left',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        'width':'35%',
                                                                                        'marginLeft':'1vw',
                                                                                        'marginRight':'1%',
                                                                                        'vertical-align':'center',
                                                                                        'marginTop':'0vh'
                                                                                        
                                                                                    }
                                                                                ),

                                                                                dcc.Dropdown(
                                                                                    id='applicator_dropdown',
                                                                                    options=[
                                                                                        {'label': '70kV 20SSD 2D', 'value': '70_20_2D'},
                                                                                        {'label': '70kV 20SSD 3D', 'value': '70_20_3D'},
                                                                                        {'label': '70kV 20SSD 4D', 'value': '70_20_4D'},
                                                                                        {'label': '70kV 20SSD 5D', 'value': '70_20_5D'},
                                                                                        {'label': '70kV 20SSD 6D', 'value': '70_20_6D'},
                                                                                        {'label': '100kV 20SSD 2D', 'value': '100_20_2D'},
                                                                                        {'label': '100kV 20SSD 3D', 'value': '100_20_3D'},
                                                                                        {'label': '100kV 20SSD 4D', 'value': '100_20_4D'},
                                                                                        {'label': '100kV 20SSD 5D', 'value': '100_20_5D'},
                                                                                        {'label': '100kV 20SSD 6D', 'value': '100_20_6D'},
                                                                                        {'label': '125kV 20SSD 2D', 'value': '125_20_2D'},
                                                                                        {'label': '125kV 20SSD 3D', 'value': '125_20_3D'},
                                                                                        {'label': '125kV 20SSD 4D', 'value': '125_20_4D'},
                                                                                        {'label': '125kV 20SSD 5D', 'value': '125_20_5D'},
                                                                                        {'label': '125kV 20SSD 6D', 'value': '125_20_6D'},
                                                                                        {'label': '70kV 30SSD 8D', 'value': '70_30_8D'},
                                                                                        {'label': '70kV 30SSD 10D', 'value': '70_30_10D'},
                                                                                        {'label': '70kV 30SSD 14D', 'value': '70_30_14D'},
                                                                                        {'label': '70kV 30SSD 6x6', 'value': '70_30_6x6'},
                                                                                        {'label': '70kV 30SSD 6x8', 'value': '70_30_6x8'},
                                                                                        {'label': '70kV 30SSD 10x10', 'value': '70_30_10x10'},
                                                                                        {'label': '70kV 30SSD 10x14', 'value': '70_30_10x14'},
                                                                                        {'label': '100kV 30SSD 8D', 'value': '100_30_8D'},
                                                                                        {'label': '100kV 30SSD 10D', 'value': '100_30_10D'},
                                                                                        {'label': '100kV 30SSD 14D', 'value': '100_30_14D'},
                                                                                        {'label': '100kV 30SSD 6x6', 'value': '100_30_6x6'},
                                                                                        {'label': '100kV 30SSD 6x8', 'value': '100_30_6x8'},
                                                                                        {'label': '100kV 30SSD 10x10', 'value': '100_30_10x10'},
                                                                                        {'label': '100kV 30SSD 10x14', 'value': '100_30_10x14'},
                                                                                        {'label': '125kV 30SSD 8D', 'value': '125_30_8D'},
                                                                                        {'label': '125kV 30SSD 10D', 'value': '125_30_10D'},
                                                                                        {'label': '125kV 30SSD 14D', 'value': '125_30_14D'},
                                                                                        {'label': '125kV 30SSD 6x6', 'value': '125_30_6x6'},
                                                                                        {'label': '125kV 30SSD 6x8', 'value': '125_30_6x8'},
                                                                                        {'label': '125kV 30SSD 10x10', 'value': '125_30_10x10'},
                                                                                        {'label': '125kV 30SSD 10x14', 'value': '125_30_10x14'},
                                                                                        {'label': '200kV 50SSD 5D', 'value': '200_50_5D'},
                                                                                        {'label': '200kV 50SSD 6x6', 'value': '200_50_6x6'},
                                                                                        {'label': '200kV 50SSD 6x8', 'value': '200_50_6x8'},
                                                                                        {'label': '200kV 50SSD 8x8', 'value': '200_50_8x8'},
                                                                                        {'label': '200kV 50SSD 6x10', 'value': '200_50_6x10'},
                                                                                        {'label': '200kV 50SSD 8x10', 'value': '200_50_8x10'},
                                                                                        {'label': '200kV 50SSD 10x10', 'value': '200_50_10x10'},
                                                                                        {'label': '200kV 50SSD 12x12', 'value': '200_50_12x12'},
                                                                                        {'label': '200kV 50SSD 8x15', 'value': '200_50_8x15'},
                                                                                        {'label': '200kV 50SSD 10x15', 'value': '200_50_10x15'},
                                                                                        {'label': '200kV 50SSD 15x15', 'value': '200_50_15x15'},
                                                                                        {'label': '200kV 50SSD 10x20', 'value': '200_50_10x20'},
                                                                                        {'label': '200kV 50SSD 20x20', 'value': '200_50_20x20'},
                                                                                    ],
                                                                                    value=None,
                                                                                    style={
                                                                                        'display':'inline-block',
                                                                                        'width': '-webkit-fill-available',
                                                                                        'height':'4vh',
                                                                                        'vertical-align':'top',
                                                                                        'marginTop':'0vh'
                                                                                    }
                                                                                ),

                                                                                html.H4(
                                                                                    children='MU:',
                                                                                    style={
                                                                                        'textAlign': 'left',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        #'width':'35%',
                                                                                        'marginLeft':'1vw',
                                                                                        'marginRight':'0.3vw',
                                                                                        'marginTop':'0vh'
                                                                                    }
                                                                                ),

                                                                                dcc.Input(
                                                                                    id='prescribed_mu',
                                                                                    type='numeric',
                                                                                    placeholder='MU',
                                                                                    value=None,
                                                                                    debounce=True,
                                                                                    inputMode='numeric',
                                                                                    step=1,
                                                                                    style={
                                                                                        'display':'inline-block',
                                                                                        'width': '3vw',
                                                                                        'height':'4vh',
                                                                                        #'height': '-webkit-fill-available',
                                                                                        'vertical-align':'center',
                                                                                        'marginRight':'1vw',
                                                                                    }
                                                                                ),
                                                                            ]
                                                                        ),
                                                                    ]
                                                                ),

                                                                html.Div(
                                                                    style={
                                                                    'backgroundColor': '#272b30',
                                                                        'height':'69%',
                                                                        'width':'23%',
                                                                        'display':'inline-block',
                                                                        'vertical-align': 'top',
                                                                        'marginTop':'1%',
                                                                        'borderLeft':'0.1vh solid #FF8000',
                                                                        'paddingLeft':'2%'
                                                                    },
                                                                    children=[

                                                                        html.Div(
                                                                            style={
                                                                            'backgroundColor': '#272b30',
                                                                                'height':'50%',
                                                                                'width':'100%',
                                                                                'display':'inline-block',
                                                                                'vertical-align': 'middle',
                                                                            },
                                                                            children=[
                                                                                html.H4(
                                                                                    children='Min:',
                                                                                    style={
                                                                                        'textAlign': 'left',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        'width':'50%',
                                                                                        'marginLeft':'1%',
                                                                                        'marginTop':'1vh',
                                                                                        'marginRight':'1%'
                                                                                    }
                                                                                ),

                                                                                dcc.Input(
                                                                                    id='min_dose_display',
                                                                                    type='numeric',
                                                                                    placeholder='Gy',
                                                                                    value=0,
                                                                                    debounce=True,
                                                                                    inputMode='numeric',
                                                                                    style={
                                                                                        'display':'inline-block',
                                                                                        'width': '43%',
                                                                                        'height':'4vh',
                                                                                        'marginRight':'5%',
                                                                                        #'height': '-webkit-fill-available',
                                                                                        'vertical-align':'center'
                                                                                    }
                                                                                ),
                                                                            ]
                                                                        ),

                                                                        html.Div(
                                                                            style={
                                                                            'backgroundColor': '#272b30',
                                                                                'height':'50%',
                                                                                'width':'100%',
                                                                                'display':'inline-block',
                                                                                'vertical-align': 'middle',
                                                                                'paddingTop':'1vh'
                                                                            },
                                                                            children=[
                                                                                html.H4(
                                                                                    children='Max:',
                                                                                    style={
                                                                                        'textAlign': 'left',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        'width':'50%',
                                                                                        'marginLeft':'1%',
                                                                                        'marginTop':'0vh',
                                                                                        'marginRight':'1%'
                                                                                    }
                                                                                ),

                                                                                dcc.Input(
                                                                                    id='max_dose_display',
                                                                                    type='numeric',
                                                                                    placeholder='Gy',
                                                                                    value=None,
                                                                                    debounce=True,
                                                                                    inputMode='numeric',
                                                                                    style={
                                                                                        'display':'inline-block',
                                                                                        'width': '43%',
                                                                                        'height':'4vh',
                                                                                        'marginRight':'5%',
                                                                                        #'height': '-webkit-fill-available',
                                                                                        'vertical-align':'top'
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
                                                                'backgroundColor': '#272b30',
                                                                'height':'100%',
                                                                'width':'20%',
                                                                'display':'inline-block',
                                                                'vertical-align': 'top',
                                                                'borderLeft':'0.1vh solid #FF8000'
                                                            },
                                                            children=[
                                                                html.H3(
                                                                    children='Controls',
                                                                    style={
                                                                        'textAlign': 'center',
                                                                        'color': colors['text'],
                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                        'padding': '0',
                                                                        'marginTop': '0.5vh',
                                                                        'marginBottom': '0%',
                                                                        'paddingBottom':'0.5vh',
                                                                        'borderBottom':'0.1vh solid #FF8000'
                                                                    }
                                                                ),
                                                                
                                                                html.Button(
                                                                    'Update Dose',
                                                                    id = 'B_update_dose',
                                                                    n_clicks = None,
                                                                    title='Update dose distribution with chosen parameters',
                                                                    style={'marginTop':'1.5vh', 'marginBottom':'1vh', 'width':'90%', 'height':'5.5vh',
                                                                        'marginLeft':'5%', 'marginRight':'5%',}
                                                                ),

                                                                html.Button(
                                                                    'Export DICOM dose',
                                                                    id = 'B_save_dose',
                                                                    n_clicks = None,
                                                                    title='Save dose distribution in DICOM format',
                                                                    style={'marginTop':'0.7vh', 'marginBottom':'1vh', 'width':'90%', 'height':'5.5vh',
                                                                        'marginLeft':'5%', 'marginRight':'5%',}
                                                                ),
                                                                
                                                            ]
                                                        ),                                                    
                                                    ]
                                                ),
                                                
                                                html.Div(
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'75%',
                                                        'width':'29%',
                                                        'display':'inline-block',
                                                        'vertical-align': 'top',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1vh'
                                                    },
                                                    children=[
                                                        html.Div(
                                                            id='main_plot',
                                                            style={
                                                                'backgroundColor': '#272b30',
                                                                'height':'90%',
                                                                'width':'100%',
                                                                'display':'inline-block',
                                                                'vertical-align': 'top',
                                                                'marginBottom':'1%',
                                                                'marginTop':'1%'
                                                            },
                                                            children=[
                                                            ]
                                                        ),
                                                        dcc.Slider(
                                                            id='slider1',
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
                                                        'height':'75%',
                                                        'width':'29%',
                                                        'display':'inline-block',
                                                        'vertical-align': 'top',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1vh'
                                                    },
                                                    children=[
                                                        html.Div(
                                                            id='sub1_plot',
                                                            style={
                                                                'backgroundColor': '#272b30',
                                                                'height':'90%',
                                                                'width':'100%',
                                                                'display':'inline-block',
                                                                'vertical-align': 'top',
                                                                'marginBottom':'1%',
                                                                'marginTop':'1%'
                                                            },
                                                            children=[
                                                            ]
                                                        ),
                                                        dcc.Slider(
                                                            id='slider2',
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
                                                        'height':'75%',
                                                        'width':'32%',
                                                        'display':'inline-block',
                                                        'vertical-align': 'top',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1vh'
                                                    },
                                                    children=[
                                                        html.Div(
                                                            id='sub2_plot',
                                                            style={
                                                                'backgroundColor': '#272b30',
                                                                'height':'90%',
                                                                'width':'100%',
                                                                'display':'inline-block',
                                                                'vertical-align': 'top',
                                                                'marginBottom':'1%',
                                                                'marginTop':'1%'
                                                            },
                                                            children=[
                                                            ]
                                                        ),
                                                        dcc.Slider(
                                                            id='slider3',
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
                                                        'height':'70%',
                                                        'width':'5%',
                                                        'marginLeft':'1%',
                                                        'marginTop':'1%',
                                                        'display':'inline-block'
                                                    },
                                                    children=[
                                                        dcc.RangeSlider(
                                                            id='WLCT',
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
                                                ),
                                                        
                                            ],
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'83vh',
                                                'marginLeft':'1.5vh',
                                                'marginRight':'1.5vh'
                                            }
                                        ),
                                    ]
                                ),
                                
                                dcc.Tab(
                                    label='Dose Volume Histogram',
                                    style=tab_style,
                                    selected_style=tab_selected_style,
                                    children=[
                                        html.Div(
                                            children=[
                                                html.Div(
                                                    children=[
                                                        
                                                        
                                                        html.Div(
                                                            id='text-output',
                                                            children=[
                                                                html.Div(
                                                                    children=[
                                                                        dcc.ConfirmDialog(
                                                                            id='imported_structures_message',
                                                                            message='',
                                                                        ),
                                                                        html.Button(
                                                                            'Import Contours',
                                                                            id = 'B_import_struct',
                                                                            n_clicks = None,
                                                                            title='Select a DICOM RS structure file',
                                                                            style={'marginTop':'1.5vh', 'marginBottom':'1vh', 'width':'90%', 'height':'5.5vh',
                                                                                'marginLeft':'5%', 'marginRight':'5%',}
                                                                        ),
                                                                        html.Div(
                                                                            id='structures_checkboxes',
                                                                            style={
                                                                            'min-height':'3vh',
                                                                                'backgroundColor': colors['background'],
                                                                                'marginRight':'1%',
                                                                                'marginLeft':'1%',
                                                                                'width':'97%',
                                                                                'marginTop':'1vh',
                                                                                #'padding':'1vh',
                                                                                'maxHeight': '60%', 
                                                                                'overflow-y': 'scroll',
                                                                                'display':'inline-block',
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
                                                                                    inputStyle={'height':'20px',
                                                                                            'width':'20px',
                                                                                            'margin-right': '5px'}
                                                                                )
                                                                            ]
                                                                        ),
                                                                        
                                                                    ],
                                                                    style={
                                                                        'backgroundColor': '#272b30',
                                                                        'height':'100%',
                                                                        'width':'40%',
                                                                        'marginLeft':'1%',
                                                                        'marginRight':'1%',
                                                                        'display':'inline-block',
                                                                        'vertical-align': 'top',
                                                                        'borderRight':'0.1vh solid #FF8000',
                                                                    }
                                                                ),

                                                                html.Div(
                                                                    style={
                                                                    'backgroundColor': '#272b30',
                                                                        'height':'100%',
                                                                        'width':'58%',
                                                                        'display':'inline-block',
                                                                        'vertical-align': 'middle',
                                                                        #'paddingTop':'2vh'
                                                                    },
                                                                    children=[

                                                                        html.Div(
                                                                            style={
                                                                            'backgroundColor': '#272b30',
                                                                                'height':'30%',
                                                                                'width':'100%',
                                                                                'display':'inline-block',
                                                                                'vertical-align': 'middle',
                                                                                #'paddingTop':'2vh'
                                                                            },
                                                                            children=[
                                                                                html.H4(
                                                                                    children='Norm Dose:',
                                                                                    style={
                                                                                        'textAlign': 'right',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        'width':'35%',
                                                                                        'marginLeft':'1%',
                                                                                        'marginTop':'0vh',
                                                                                        'marginRight':'1%'
                                                                                    }
                                                                                ),

                                                                                dcc.Input(
                                                                                    id='d_100',
                                                                                    type='numeric',
                                                                                    placeholder='Gy',
                                                                                    value=None,
                                                                                    debounce=True,
                                                                                    inputMode='numeric',
                                                                                    style={
                                                                                        'display':'inline-block',
                                                                                        'width': '10%',
                                                                                        'height':'4vh',
                                                                                        'marginRight':'2%',
                                                                                        #'height': '-webkit-fill-available',
                                                                                        'vertical-align':'center'
                                                                                    }
                                                                                ),

                                                                                html.Button(
                                                                                    'Calculate DVH',
                                                                                    id = 'B_dvh',
                                                                                    n_clicks = None,
                                                                                    title='Calculate cumulative DVH',
                                                                                    style={'marginTop':'1.5vh', 'marginBottom':'1vh', 'width':'40%', 'height':'5.5vh',
                                                                                        'marginLeft':'5%', 'marginRight':'2%',}
                                                                                ),
                                                                            ]
                                                                        ),

                                                                        html.Div(
                                                                            style={
                                                                            'backgroundColor': '#272b30',
                                                                                'height':'30%',
                                                                                'width':'100%',
                                                                                'display':'inline-block',
                                                                                'vertical-align': 'middle',
                                                                                'paddingTop':'1vh'
                                                                            },
                                                                            children=[
                                                                                html.H4(
                                                                                    children='Volume Axis:',
                                                                                    style={
                                                                                        'textAlign': 'right',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        'width':'35%',
                                                                                        'marginLeft':'5%',
                                                                                        'marginRight':'1%',
                                                                                        'marginTop':'1vh'
                                                                                    }
                                                                                ),

                                                                                dcc.RadioItems(
                                                                                    id='volume_axis',
                                                                                    options=[
                                                                                        {'label': 'Absolute', 'value': 'abs'},
                                                                                        {'label': 'Relative', 'value': 'rel'},
                                                                                    ],
                                                                                    value='rel',
                                                                                    labelStyle={'display':'inline-block',
                                                                                            'font-size':'1.2vw',
                                                                                            'color':'white',
                                                                                            'margin-left': '0.1vw',
                                                                                            'margin-right': '1vw',},
                                                                                    inputStyle={'width':'2vw',
                                                                                            'height':'2vh',
                                                                                            'margin-left': '0.5vw',
                                                                                            'margin-right': '0vw'},
                                                                                    style={'width':'59%',
                                                                                            'display':'inline-block',
                                                                                            'marginBottom':'0.1vh'}
                                                                                ),
                                                                            ]
                                                                        ),

                                                                        html.Div(
                                                                            style={
                                                                            'backgroundColor': '#272b30',
                                                                                'height':'30%',
                                                                                'width':'100%',
                                                                                'display':'inline-block',
                                                                                'vertical-align': 'middle',
                                                                                'paddingTop':'1vh'
                                                                            },
                                                                            children=[
                                                                                html.H4(
                                                                                    children='Dose Axis:',
                                                                                    style={
                                                                                        'textAlign': 'right',
                                                                                        'color': colors['text'],
                                                                                        'font-family': 'Arial, Helvetica, sans-serif',
                                                                                        'padding': '0',
                                                                                        'display':'inline-block',
                                                                                        'width':'35%',
                                                                                        'marginLeft':'5%',
                                                                                        'marginRight':'1%',
                                                                                        'marginTop':'1vh'
                                                                                    }
                                                                                ),

                                                                                dcc.RadioItems(
                                                                                    id='dose_axis',
                                                                                    options=[
                                                                                        {'label': 'Absolute', 'value': 'abs'},
                                                                                        {'label': 'Relative', 'value': 'rel'},
                                                                                    ],
                                                                                    value='abs',
                                                                                    labelStyle={'display':'inline-block',
                                                                                            'font-size':'1.2vw',
                                                                                            'color':'white',
                                                                                            'margin-left': '0.1vw',
                                                                                            'margin-right': '1vw',},
                                                                                    inputStyle={'width':'2vw',
                                                                                            'height':'2vh',
                                                                                            'margin-left': '0.5vw',
                                                                                            'margin-right': '0vw'},
                                                                                    style={'width':'59%',
                                                                                            'display':'inline-block',
                                                                                            'marginBottom':'0.1vh'}
                                                                                ),
                                                                            ]
                                                                        )

                                                                    ]
                                                                ),

                                                                
                                                        
                                                            ],
                                                            style={
                                                                'backgroundColor': '#272b30', #colors['background'],
                                                                'height':'30%',
                                                                'width':'98%',
                                                                'marginLeft':'1%',
                                                                'marginRight':'1%',
                                                                'display':'inline-block',
                                                                'vertical-align': 'top',
                                                            }
                                                        ),

                                                        html.Div(
                                                            id='dvh_graph',
                                                            children=[
                                                            ],
                                                            style={
                                                                'backgroundColor': colors['background'],
                                                                'height':'70%',
                                                                'width':'90%',
                                                                'marginLeft':'5%',
                                                                'marginRight':'5%',
                                                                'display':'inline-block',
                                                                'vertical-align': 'top',
                                                            }
                                                        ),
                                                    ],
                                                    style={
                                                        'backgroundColor': colors['background'],
                                                        'height':'100%',
                                                        'width':'50%',
                                                        'display':'inline-block'
                                                    }
                                                ),

                                                html.Div(
                                                    id = 'dvh_table_container',
                                                    children=[

                                                    ],
                                                    style={
                                                        'backgroundColor': '#272b30',
                                                        'height':'100%',
                                                        'width':'50%',
                                                        'display':'inline-block',
                                                        'vertical-align': 'top',
                                                    }
                                                ),
                                            ],
                                            style={
                                                'backgroundColor': colors['background'],
                                                'height':'83vh',
                                                'marginLeft':'1.5vh',
                                                'marginRight':'1.5vh'
                                            }
                                        ),
                                    ]
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
#=========================PLOTTING CT====================================
#Disclaimer notice
@app.callback(
    [Output('disclaimer', 'hidden'), Output('main_application', 'hidden')],
    Input('acknowledge-button', 'n_clicks'))
def disclaim(n_clicks):
    if n_clicks > 0:
        return [True, False]
    else:
        raise PreventUpdate

#Uploading DICOM files
@app.callback(
    [Output('slider1', 'step'), Output('slider1', 'min'), Output('slider1', 'max'), Output('slider1', 'value'), Output('slider1', 'marks'),
     Output('slider2', 'step'), Output('slider2', 'min'), Output('slider2', 'max'), Output('slider2', 'value'), Output('slider2', 'marks'),
     Output('slider3', 'step'), Output('slider3', 'min'), Output('slider3', 'max'), Output('slider3', 'value'), Output('slider3', 'marks'),
    Output('WLCT', 'min'), Output('WLCT', 'max'), Output('WLCT', 'marks'), Output('WLCT', 'value'),
    Output('imported_CT', 'message'), Output('imported_CT', 'displayed'),
    Output('B_import_ct', 'className'), Output('B_import_dose', 'className'),
    Output('structures_checklist','options'), Output('B_import_struct','className'),
    Output('dvh_table_container','children'), Output('B_dvh','className')],
    [Input('B_import_ct', 'n_clicks'),
    Input('B_import_dose', 'n_clicks'),
    Input('B_import_struct','n_clicks'),
    Input('B_dvh','n_clicks')],
    State('d_100', 'value'))
def upload_DICOM(click_ct, click_dose, click_struct, click_dvh, d_100):
    if click_ct == None and click_dose == None and click_struct == None and click_dvh == None:
        raise PreventUpdate
    else:
        
        changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
        
        if 'B_import_ct' in changed_id:
            try:
                global SCAN
                
                ct_folder_path = gui_select_dir()
                ct_files, mess = load_dicom_files(ct_folder_path)

                if ct_files == False:
                    error_message = 'Failed to find DICOM files in: ' + ct_folder_path
                    return 1,0,1,1,[], 1,0,1,1,[],1,0,1,1,[],0,1, [], None, error_message, True, 'button', 'button',[],'button',[],'button'
                    raise PreventUpdate

                else:
                    SCAN = scan(ct_files)
                    SCAN.ct_folder_path = ct_folder_path

                    SCAN.updated = False

                    #Update WINDOW slider values
                    steps = int((np.max(SCAN.HFS_cube)-np.min(SCAN.HFS_cube))/15)
                    Wm = {i : {'label': '{}HU'.format(round(i,1)), 
                               'style': {'color':'white',
                                        'font-size':'20px'}} for i in range(int(np.min(SCAN.HFS_cube)), np.max(SCAN.HFS_cube), steps)}

                    Wmin=np.min(SCAN.HFS_cube)
                    Wmax=np.max(SCAN.HFS_cube)

                    Astep, ASmin, ASmax, ASvalue, ASmarks = update_slice_slider('A')
                    SStep, SSmin, SSmax, SSvalue, SSmarks = update_slice_slider('S')
                    CStep, CSmin, CSmax, CSvalue, CSmarks = update_slice_slider('C')

                    return [Astep, ASmin, ASmax, ASvalue, ASmarks, 
                            SStep, SSmin, SSmax, SSvalue, SSmarks,
                            CStep, CSmin, CSmax, CSvalue, CSmarks,
                            Wmin, Wmax, Wm, [-1024, 2000],
                            mess, True, 'button-pressed','button',[],'button',[],'button']
            except:
                return 1,0,1,1,[], 1,0,1,1,[],1,0,1,1,[],0,1, [], None, 'Error importing CT data!', True, 'button', 'button',[],'button',[],'button'
                raise PreventUpdate
  
        elif 'B_import_dose' in changed_id:
            try:
                SCAN
            except:
                return 1,0,1,1,[], 1,0,1,1,[],1,0,1,1,[],0,1, [], None, 'Please import CT data first!', True, 'button', 'button',[],'button',[],'button'
                raise PreventUpdate

            try:
                #Update WINDOW slider values
                steps = int((np.max(SCAN.HFS_cube)-np.min(SCAN.HFS_cube))/15)
                Wm = {i : {'label': '{}HU'.format(round(i,1)), 
                           'style': {'color':'white',
                                    'font-size':'20px'}} for i in range(int(np.min(SCAN.HFS_cube)), np.max(SCAN.HFS_cube), steps)}

                Wmin=np.min(SCAN.HFS_cube)
                Wmax=np.max(SCAN.HFS_cube)

                AStep, ASmin, ASmax, ASvalue, ASmarks = update_slice_slider('A')
                SStep, SSmin, SSmax, SSvalue, SSmarks = update_slice_slider('S')
                CStep, CSmin, CSmax, CSvalue, CSmarks = update_slice_slider('C')
                
                try:
                    dose_file_path = gui_select_file('Select .3ddose file')
                    SCAN.dose_cube, SCAN.xdose, SCAN.ydose, SCAN.zdose, SCAN.error_cube = create_DOSE_cube(dose_file_path) #SCAN.error_cube is actual percentage error values e.g. 1%
                    
                    print('Calculating dose voxel volumes...')
                    SCAN.dose_volume_cube = calculate_volume(SCAN.dose_cube)#, SCAN.xdose, SCAN.ydose, SCAN.zdose)
                    print('Dose voxel volumes calculated!')
                    Dmin=np.min(SCAN.dose_cube)
                    Dmax=np.format_float_scientific(np.max(SCAN.dose_cube),3)

                    button = 'button-pressed'
                    message = 'Dose file successfully imported!'
                    
                    if hasattr(SCAN, 'structures'):
                        delattr(SCAN, 'structures')                    
                except:

                    button = ''
                    message = 'Error reading dose file!'

                return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                        SStep, SSmin, SSmax, SSvalue, SSmarks,
                        CStep, CSmin, CSmax, CSvalue, CSmarks,
                        Wmin, Wmax, Wm, [-1024,2000],
                        message, True, 'button-pressed', button,[],'button',[],'button']

            except:
                return [Astep, ASmin, ASmax, ASvalue, ASmarks, 
                            SStep, SSmin, SSmax, SSvalue, SSmarks,
                            CStep, CSmin, CSmax, CSvalue, CSmarks,
                            Wmin, Wmax, Wm, [-1024,2000],
                            'CT successfully imported!', True, 'button-pressed','button',[],'button',[],'button']
                raise PreventUpdate
        
        elif 'B_import_struct' in changed_id:
            try:
                SCAN
            except:
                return 1,0,1,1,[], 1,0,1,1,[],1,0,1,1,[],0,1, [], None, 'Please import CT data first!', True, 'button', 'button',[],'button',[],'button'
                raise PreventUpdate

            #Update WINDOW slider values
            steps = int((np.max(SCAN.HFS_cube)-np.min(SCAN.HFS_cube))/15)
            Wm = {i : {'label': '{}HU'.format(round(i,1)), 
                       'style': {'color':'white',
                                'font-size':'20px'}} for i in range(int(np.min(SCAN.HFS_cube)), np.max(SCAN.HFS_cube), steps)}

            Wmin=np.min(SCAN.HFS_cube)
            Wmax=np.max(SCAN.HFS_cube)

            AStep, ASmin, ASmax, ASvalue, ASmarks = update_slice_slider('A')
            SStep, SSmin, SSmax, SSvalue, SSmarks = update_slice_slider('S')
            CStep, CSmin, CSmax, CSvalue, CSmarks = update_slice_slider('C')
                
                
            if not hasattr(SCAN, 'dose_cube'):
                return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                        SStep, SSmin, SSmax, SSvalue, SSmarks,
                        CStep, CSmin, CSmax, CSvalue, CSmarks,
                        Wmin, Wmax, Wm, [-1024,2000],
                        'Please import dose data first!', True, 'button-pressed', 'button',[],'button',[],'button']
                raise PreventUpdate
            else:
                structure_file_path = gui_select_file('Select DICOM structure file')

                try:
                    structure_file = dcm.read_file(structure_file_path)

                    if structure_file.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.3':
                        print('Structure file successfully read!')

                        SCAN.structures = []

                        for i, j in enumerate(structure_file.StructureSetROISequence):
                            number = j.ROINumber
                            name = j.ROIName

                            for m in structure_file.ROIContourSequence:
                                if m.ReferencedROINumber == number:
                                    print('Generating 3D contour:', name)
                                    color = m.ROIDisplayColor

                                    #Commented to save memory
                                    #sequence = m.ContourSequence
                                    #sequence = 1

                                    dummy_cube = np.zeros((SCAN.HFS_cube.shape[0], SCAN.HFS_cube.shape[1], SCAN.HFS_cube.shape[2]),dtype=np.int8)
                                    dummy_cube_dose = np.zeros((SCAN.dose_cube.shape[0],SCAN.dose_cube.shape[1],SCAN.dose_cube.shape[2]),dtype=np.int8)

                                    try:
                                        for seq in m.ContourSequence:
                                            xs = seq.ContourData[::3]
                                            ys = seq.ContourData[1::3]
                                            zs = seq.ContourData[2::3]                                         

                                            #Approach 1
                                            xs_idx = list(map(lambda a: (np.abs(SCAN.HFS_xs - a)).argmin(), xs))
                                            ys_idx = list(map(lambda a: (np.abs(SCAN.HFS_ys - a)).argmin(), ys))
                                            zs_idx = list(map(lambda a: (np.abs(SCAN.HFS_zs - a)).argmin(), zs))

                                            xs_dose_idx = list(map(lambda a: (np.abs(SCAN.xdose[:-1] - a)).argmin(), xs))
                                            ys_dose_idx = list(map(lambda a: (np.abs(SCAN.ydose[:-1] - a)).argmin(), ys))
                                            zs_dose_idx = list(map(lambda a: (np.abs(SCAN.zdose[:-1] - a)).argmin(), zs))

                                            #Can use polygon_perimeter to just draw contour -> add (,shape=dummy_cube[zs_idx[0]].shape,clip=True)
                                            xx, yy = polygon(xs_idx, ys_idx)
                                            dummy_cube[zs_idx[0],yy,xx] = 1

                                            xx_dose, yy_dose = polygon(xs_dose_idx, ys_dose_idx)
                                            dummy_cube_dose[zs_dose_idx[0],yy_dose,xx_dose] = 1

                                        #dummy_cube[dummy_cube==0] = 
                                        #dummy_cube_dose[dummy_cube_dose==0] = 
                                        print('Structure volume created!')
                                        
                                        #dummy_cube = (dummy_cube==1)
                                        #dummy_cube_dose = (dummy_cube_dose==1)

                                        total_volume = sum(SCAN.volume_cube[dummy_cube==1])
                                        truncated_volume = sum(SCAN.dose_volume_cube[dummy_cube_dose==1])

                                        s = structure(number, name, color, total_volume, dummy_cube_dose, truncated_volume, dummy_cube)
                                        SCAN.structures.append(s)
                                    except:
                                        print('Structure:', name, ' has no ContourSequence')

                        checklist_options = []
                        for i in SCAN.structures:
                            checklist_options.append({'label':i.name, 'value':i.number})

                        SCAN.stage = 2
                        return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                                SStep, SSmin, SSmax, SSvalue, SSmarks,
                                CStep, CSmin, CSmax, CSvalue, CSmarks,
                                Wmin, Wmax, Wm, [-1024,2000],
                                'Structures successfully imported!', True, 'button-pressed', 'button-pressed',checklist_options, 'button-pressed',[],'button']

                    else:
                        return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                                SStep, SSmin, SSmax, SSvalue, SSmarks,
                                CStep, CSmin, CSmax, CSvalue, CSmarks,
                                Wmin, Wmax, Wm, [-1024,2000],
                                'Selected file is not a DICOM structure set!', True, 'button-pressed', 'button-pressed',[],'button',[],'button']
                        raise PreventUpdate

                except:
                    return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                            SStep, SSmin, SSmax, SSvalue, SSmarks,
                            CStep, CSmin, CSmax, CSvalue, CSmarks,
                            Wmin, Wmax, Wm, [-1024,2000],
                            'Error reading selected DICOM structure set!', True, 'button-pressed', 'button-pressed',[],'button',[],'button']
                    raise PreventUpdate   
                    
        elif 'B_dvh' in changed_id:
            try:
                SCAN
            except:
                return 1,0,1,1,[], 1,0,1,1,[],1,0,1,1,[],0,1, [], None, 'Please import CT data first!', True, 'button', 'button',[],'button',[],'button'
                raise PreventUpdate

            #Update WINDOW slider values
            steps = int((np.max(SCAN.HFS_cube)-np.min(SCAN.HFS_cube))/15)
            Wm = {i : {'label': '{}HU'.format(round(i,1)), 
                       'style': {'color':'white',
                                'font-size':'20px'}} for i in range(int(np.min(SCAN.HFS_cube)), np.max(SCAN.HFS_cube), steps)}

            Wmin=np.min(SCAN.HFS_cube)
            Wmax=np.max(SCAN.HFS_cube)

            AStep, ASmin, ASmax, ASvalue, ASmarks = update_slice_slider('A')
            SStep, SSmin, SSmax, SSvalue, SSmarks = update_slice_slider('S')
            CStep, CSmin, CSmax, CSvalue, CSmarks = update_slice_slider('C')
            
            if not hasattr(SCAN, 'dose_cube'):          
                return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                        SStep, SSmin, SSmax, SSvalue, SSmarks,
                        CStep, CSmin, CSmax, CSvalue, CSmarks,
                        Wmin, Wmax, Wm, [-1024,2000],
                        'Please import dose file first!', True, 'button-pressed', 'button',[],'button',[],'button']
                raise PreventUpdate

            if not hasattr(SCAN, 'updated_dose'):
                return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                        SStep, SSmin, SSmax, SSvalue, SSmarks,
                        CStep, CSmin, CSmax, CSvalue, CSmarks,
                        Wmin, Wmax, Wm, [-1024,2000],
                        'Please normalize dose distribution first!', True, 'button-pressed', 'button-pressed',[],'button',[],'button']

            if not hasattr(SCAN, 'structures'):
                return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                        SStep, SSmin, SSmax, SSvalue, SSmarks,
                        CStep, CSmin, CSmax, CSvalue, CSmarks,
                        Wmin, Wmax, Wm, [-1024,2000],
                        'Please import structure file first!', True, 'button-pressed', 'button-pressed',[],'button',[],'button']
                raise PreventUpdate

            checklist_options = []
            for i in SCAN.structures:
                checklist_options.append({'label':i.name, 'value':i.number})
                    
            if d_100 == None:        
                return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                        SStep, SSmin, SSmax, SSvalue, SSmarks,
                        CStep, CSmin, CSmax, CSvalue, CSmarks,
                        Wmin, Wmax, Wm, [-1024,2000],
                        'Please enter 100% dose and try again!', 
                        True, 'button-pressed', 'button-pressed',checklist_options,'button-pressed',[],'button']
                raise PreventUpdate
            else:
                SCAN.prescribed_dose = float(d_100)

                
            for i in range(len(SCAN.structures)):
                calc_dvh(i,SCAN.prescribed_dose, SCAN.updated_dose)

            table = generate_dvh_table()

            return [AStep, ASmin, ASmax, ASvalue, ASmarks, 
                    SStep, SSmin, SSmax, SSvalue, SSmarks,
                    CStep, CSmin, CSmax, CSvalue, CSmarks,
                    Wmin, Wmax, Wm, [-1024,2000],
                    'DVHs calculated!',
                    True, 'button-pressed', 'button-pressed',checklist_options,'button-pressed',table,'button-pressed']
            raise PreventUpdate        
                
        
#Plotting CT images   
@app.callback(
    [Output('main_plot', 'children'),
    Output('sub1_plot', 'children'),
    Output('sub2_plot', 'children'),
    Output('error_dose_display', 'message'),
    Output('error_dose_display', 'displayed')],
    [Input('WLCT', 'value'),
    Input('slider1', 'value'),
    Input('slider2', 'value'),
    Input('slider3', 'value'),
    Input('B_update_dose', 'n_clicks'),
    Input('structures_checklist', 'value')], 
    [State('min_dose_display', 'value'),
    State('max_dose_display', 'value'),
    State('norm_to','value'),
    State('xnorm','value'),
    State('ynorm','value'),
    State('znorm','value'),
    State('norm_dose','value'),
    State('applicator_dropdown', 'value'),
    State('prescribed_mu', 'value'),])
def plot_graph_CT(hu_window, slider1, slider2, slider3, update_click, selected_structures, min_dose, max_dose, norm_to, xn, yn, zn, nd, applicator_dropdown, prescribed_mu):  
    
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    message = ''
    
    if 'B_update_dose' in changed_id:
        try: 
            SCAN
        except:
            return [],[],[],'Please import CT data first', True
            raise PreventUpdate
            
        if not hasattr(SCAN, 'dose_cube'):
            if hasattr(SCAN, 'structures'):
                contour_plots_A, contour_plots_S, contour_plots_C  = contour_structures(selected_structures, slider1,slider2,slider3)
                ps, pc, pa = plot_ROI(SCAN,slider1,slider2,slider3,hu_window, False, None, None,contour_plots_A, contour_plots_S, contour_plots_C, True)
            else:
                ps, pc, pa = plot_ROI(SCAN,slider1,slider2,slider3,hu_window, False, None, None, None, None, None, False)

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
            
            return PA,PS,PC,'Please import a dose file first', True
            raise PreventUpdate
        else:
            message = 'Dose updated! Please recalculate DVH... '
            disp = True
    
    try:
        SCAN
    except:
        raise PreventUpdate
        
    if hasattr(SCAN, 'dose_cube'):

        if norm_to == 'pt': #normalising to point
        
            if xn != None and yn != None and zn != None and nd != None:
                try:
                    #Get index of prescription point in dose array
                    x_idx = (np.abs(SCAN.xdose - float(xn))).argmin()
                    y_idx = (np.abs(SCAN.ydose - float(yn))).argmin()
                    z_idx = (np.abs(SCAN.zdose - float(zn))).argmin()

                    #Scale array by given dose
                    scale_factor = float(nd)/SCAN.dose_cube[z_idx,y_idx,x_idx]
                    print('Dose is rescaled to the prescription dose')
                    SCAN.updated_dose = np.copy(SCAN.dose_cube) * scale_factor
                    #SCAN.prescribed_dose = float(prescribed_dose)

                except:
                    message = 'Dose not updated! Please enter a numeric set of coordinates and prescription dose value!'
                    SCAN.updated_dose = np.copy(SCAN.dose_cube)
                
            else:
                SCAN.updated_dose = np.copy(SCAN.dose_cube)

        else: #normalizing to output (applicator and mu)
            if applicator_dropdown != None and prescribed_mu != None:
                try:
                    #print(applicator_dropdown)
                    #print(kv_outputs_real[applicator_dropdown])
                    #print(kv_outputs_mc[applicator_dropdown])
                    #Scale array by given dose
                    mc_to_real = float(kv_outputs_real[applicator_dropdown]/kv_outputs_mc[applicator_dropdown])
                    mc_to_real_mu = mc_to_real * int(prescribed_mu)

                    print('Dose is rescaled based on selected applicator and MU')
                    SCAN.updated_dose = np.copy(SCAN.dose_cube) * mc_to_real_mu
                    #SCAN.prescribed_dose = float(prescribed_mu)

                except:
                    message = 'Dose not updated! Please select an applicator and enter the MU!'
                    SCAN.updated_dose = np.copy(SCAN.dose_cube)
                
            else:
                SCAN.updated_dose = np.copy(SCAN.dose_cube)


        if max_dose == None:            
            max_dose = np.max(SCAN.updated_dose)
        if min_dose == None:            
            min_dose = np.min(SCAN.updated_dose)

        try:
            float(max_dose)
        except:
            max_dose = np.max(SCAN.updated_dose)
            message = message + ' Please enter a numeric value for max dose!'
        
        try:
            float(min_dose)
        except:
            min_dose = np.min(SCAN.updated_dose)
            message = message + ' Please enter a numeric value for min dose!'

        if hasattr(SCAN, 'structures'):
            contour_plots_A, contour_plots_S, contour_plots_C  = contour_structures(selected_structures, slider1,slider2,slider3)
            ps, pc, pa = plot_ROI(SCAN,slider1,slider2,slider3,hu_window, True, min_dose, max_dose, contour_plots_A, contour_plots_S, contour_plots_C, True)
        else:
            ps, pc, pa = plot_ROI(SCAN,slider1,slider2,slider3,hu_window, True, min_dose, max_dose, None, None, None, False)

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

        if message == '':
            disp = False
        return PA,PS,PC,message, disp

    else:
        if hasattr(SCAN, 'structures'):
            contour_plots_A, contour_plots_S, contour_plots_C  = contour_structures(selected_structures, slider1,slider2,slider3)
            ps, pc, pa = plot_ROI(SCAN,slider1,slider2,slider3,hu_window, False, None, None,contour_plots_A, contour_plots_S, contour_plots_C, True)
        else:
            ps, pc, pa = plot_ROI(SCAN,slider1,slider2,slider3,hu_window, False, None, None, None, None, None, False)

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

        if message == '':
            disp = False
            
        return PA,PS,PC,message, disp     


@app.callback([Output('tissue_dropdown', 'disabled'),
            Output('tissue_dropdown', 'value')],
                [Input('dose_to', 'value')],)
def disable_tissues (d_to):

    if d_to == 'dm':
        return [True,None]
    else:
        return [False, 'hn']



@app.callback( [Output('norm_container', 'style'),
                Output('norm_container2', 'style')],
                [Input('norm_to', 'value')],)
def display_norm_options (n_to):

    s1 = {'backgroundColor': '#272b30',
                'height':'50%',
                'width':'100%',
                'display':'inline-flex',
                #'justifyContent':'space-between',
                'vertical-align':'middle',
                'paddingTop':'1vh'}
    
    s2 = {'backgroundColor': '#272b30',
                'height':'50%',
                'width':'100%',
                'display':'none',
                #'justifyContent':'space-between',
                'vertical-align':'middle',
                'paddingTop':'1vh'}

    if n_to == 'pt':
        return [s1,s2]

    elif n_to == 'output':
        return [s2,s1]

    return stuff

@app.callback(
    [Output('dvh_graph','children'),],
    [Input('DVH-table', "derived_virtual_data"),
     Input('DVH-table', "derived_virtual_selected_rows"),
     Input('volume_axis', 'value'),
     Input('dose_axis', 'value'),],
    [State('d_100', 'value')])
def gen_material_table(rows, derived_virtual_selected_rows, volume_axis, dose_axis, prescribed_dose):
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
        
    selected = [rows[i] for i in derived_virtual_selected_rows]
    
    dvh_plot_data = []
    
    for i in selected:
        for struct in SCAN.structures:
            if struct.name == i['Structure']:
                if volume_axis == 'abs':
                    yplot = struct.volumes
                elif volume_axis == 'rel':
                    yplot = struct.cumulative_volume

                if dose_axis == 'abs':
                    xplot = struct.dose_bins

                elif dose_axis == 'rel':
                    xplot = (struct.dose_bins/float(prescribed_dose))*100

                dvh_trace = go.Scatter(
                            x=xplot,
                            y=yplot,
                            mode='lines',
                            name=struct.name,
                           line=dict(color='rgb(%d,%d,%d)'%(struct.color[0],struct.color[1],struct.color[2]))
                        )
                dvh_plot_data.append(dvh_trace)

    max_v = np.max(list(struct.truncated_volume for struct in SCAN.structures)) 

    if volume_axis == 'abs':
        ytitle = 'Volume (cc)'
        yrange = [0, max_v]
        ydtick = 2000
    elif volume_axis == 'rel':
        ytitle = 'Volume (% Volume inside dose grid)'
        yrange = [0, 105]
        ydtick = 10

    if dose_axis == 'abs':
        xtitle = 'Dose (Gy)'
        xrange = [0, float(prescribed_dose) + (float(prescribed_dose)*0.2)]
    elif dose_axis == 'rel':
        xtitle = 'Dose (% Norm dose)'
        xrange = [0, 105]

    dvh_layout = {#'title': 'CT ramp with shaded material cross section region',

                'legend_font_color':"white",
                   'xaxis':dict(
                                title=xtitle,
                                tickmode='linear',
                                ticks='outside',
                                tickangle=45,
                                dtick=10,
                                ticklen=8,
                                tickwidth=1,
                                tickcolor='white',
                               color='white',
                               #showgrid=False,
                               zeroline=True, zerolinewidth=2, zerolinecolor='Black',
                               range=xrange
                            ),
                   'yaxis':dict(
                                title=ytitle,
                                tickmode='linear',
                                ticks='outside',
                                dtick=ydtick,
                                ticklen=8,
                                tickwidth=1,
                                tickcolor='white',
                               color='white',
                               #showgrid=False,
                               zeroline=True, zerolinewidth=2, zerolinecolor='Black',
                               range=yrange
                            ),
                   'autosize':True,
                   'paper_bgcolor':colors['background'],
                    'plot_bgcolor':'#C0C0C0',
                    'margin':{'l':20, 'r':20, 't':10, 'b':35}
    }

    dvh_fig = go.Figure(data=dvh_plot_data, layout=dvh_layout)
    plot = dcc.Graph(id='CTR', figure=dvh_fig,config={
                'displayModeBar': False,
                'autosizable':True,
                'responsive':True
            },
                    style={
            'height':'100%'
        })
    return [plot]
 
    
@app.callback(  Output('DVH-table', 'data'),
                #[Input('DVH-table', 'data_timestamp')],
                [Input('DVH-table', 'data_timestamp')],
                 [State('DVH-table', 'data'),
                 State('DVH-table','active_cell')])
def get_active_cell_value (timestamp, data, active_cell):
    
    #print(timestamp)
    #print(data)
    #print(active_cell)
    if active_cell == None:
        raise PreventUpdate
    
    active_cell_column = active_cell['column_id']
    #print(active_cell_column)
    #Get Structure name from row id
    #active_structure_id = active_cell['row']
    #active_structure = data[active_structure_id]['Structure']
    #print(data[active_structure_id])
    #entered_value = data[active_structure_id][active_cell_column]
    
    for row in data:
        entered_value = row[active_cell_column]
        print('Enetered value was: ', entered_value, ' in column: ', active_cell_column)

        #Do the calculation
        structure = row['Structure']
        for struct in SCAN.structures:
            if struct.name == structure:
                DVH_x = struct.dose_bins
                DVH_y = struct.cumulative_volume
                #Volume in DVC tables can either be as a percentage of the whole structure or the structure volume where dose was scored
                #Going to use trunc volume for now
                trunc_vol = struct.truncated_volume
                #tot_vol = struct.total_volume

        #For the if statements below:
        #Absolute values are first converted to percentage and visa versa
        #Then they are interpolated from the DVH curve to get the ther quantity

        #If user enetered V cm3
        if active_cell_column == 'V cm3':
            print('Input is v_cm3', entered_value)
            v_cm3 = entered_value
            v_percent = (entered_value/trunc_vol) * 100
            d_gy = np.interp(v_percent, DVH_y[::-1], DVH_x[::-1])
            d_percent = (d_gy/SCAN.prescribed_dose)*100

        #elif user entered V %
        elif active_cell_column == 'V %':
            print('Input is v_%', entered_value)
            v_percent = entered_value
            v_cm3 = trunc_vol*(entered_value/100)
            d_gy = np.interp(entered_value, DVH_y[::-1], DVH_x[::-1])
            d_percent = (d_gy/SCAN.prescribed_dose)*100

        #elif user entered D Gy
        elif active_cell_column == 'D Gy':
            print('Input is d_gy', entered_value)
            d_gy = entered_value
            v_percent = np.interp(entered_value, DVH_x, DVH_y) 
            v_cm3 = (v_percent/100) * trunc_vol
            d_percent = (entered_value/SCAN.prescribed_dose)*100

        #elif user enetered D %
        elif active_cell_column == 'D %':
            print('Input is d_%', entered_value)
            d_percent = entered_value
            d_gy = SCAN.prescribed_dose*(entered_value/100)
            v_percent = np.interp(d_gy, DVH_x, DVH_y) 
            v_cm3 = (v_percent/100) * trunc_vol

        #print('prescribed dose:', SCAN.prescribed_dose)
        #print('D_gy: ', d_gy)
        #print('D_%: ', d_percent)
        #print('V_cm3: ', v_cm3)
        #print('V_%: ', v_percent)
        #print()  

        #Update other values
        row['D Gy'] = round(d_gy, 2)
        row['D %'] = round(d_percent, 2)
        row['V cm3'] = round(v_cm3, 2)
        row['V %'] = round(v_percent, 2)
    
    #print(data)
    return data

 
@app.callback([Output('B_save_dose','className'),
              Output('saved_dicom', 'message'),
            Output('saved_dicom', 'displayed')],
              Input('B_save_dose','n_clicks')
)
def save_dicom_dose(n_clicks):
    
    if n_clicks == None:
        raise PreventUpdate
    else:
        try:
            SCAN
        except:
            return 'button','Please import CT files first!',True
            raise PreventUpdate
            
        if not hasattr(SCAN, 'dose_cube'):
            return 'button','Please import dose file first!',True
            raise PreventUpdate
            
        #if not hasattr(SCAN, 'structures'):
            #return 'button','Please import structure file first!',True
            #raise PreventUpdate
            
        #if not hasattr(SCAN, 'prescribed_dose'):
        #    return 'button','Please enter prescribed dose and click \'Update Dose\' first!',True
        #    raise PreventUpdate
        
        my_dose_file_name = gen_dicom_dose_file(SCAN.updated_dose, SCAN.fine_x_step, SCAN.fine_y_step)
        complete_message = 'Monte Carlo dose distribution saved to DICOM dose file: ' + my_dose_file_name
        
        return 'button-pressed',complete_message,True
        raise PreventUpdate
        

if __name__ == '__main__':
    url = "http://127.0.0.1:8070/"
    webbrowser.open_new_tab(url)
    
    app.server.run(port=8070, host='127.0.0.1')
    
    #app.run_server(debug=False)



