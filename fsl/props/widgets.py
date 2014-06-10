#!/usr/bin/env python
#
# widgets.py - Generate wx GUI widgets for props.PropertyBase objects.
#
# The sole entry point for this module is the makeWidget function,
# which is called via the build module when it automatically
# builds a GUI for the properties of a props.HasProperties instance.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import sys

import os
import os.path as op

from collections import OrderedDict
from collections import Iterable

import wx
import wx.combo

import numpy             as np
import matplotlib.cm     as mplcm

# the List and number properties are complex
# enough to get their own modules.
from widgets_list   import _List
from widgets_number import _Number


def _propBind(hasProps, propObj, propVal, guiObj, evType, labelMap=None):
    """
    Sets up event callback functions such that, on a change to the given
    property value, the value displayed by the given GUI widget will be
    updated. Similarly, whenever a GUI event of the specified type (or
    types - you may pass in a list of event types) occurs, the property
    value will be set to the value controlled by the GUI widget. 

    If labelMap is provided, it should be a dictionary of value->label pairs
    where the label is what is displayed to the user, and the value is what is
    assigned to the property value when a corresponding label is selected. It
    is basically here to support Choice properties.
    """

    if not isinstance(evType, Iterable): evType = [evType]

    listenerName = 'WidgetBind_{}'.format(id(guiObj))
    valMap       = None

    if labelMap is not None:
        valMap = dict([(lbl, val) for (val, lbl) in labelMap.items()])

    def _guiUpdate(value, *a):
        """
        Called whenever the property value is changed.
        Sets the GUI widget value to that of the property.
        """

        if guiObj.GetValue() == value: return

        if valMap is not None: value = labelMap[value]

        # most wx widgets complain if you try to set their value to None
        if value is None: value = ''
        guiObj.SetValue(value)
        
    def _propUpdate(*a):
        """
        Called when the value controlled by the GUI widget
        is changed. Updates the property value.
        """

        value = guiObj.GetValue()

        if propVal.get() == value: return

        if labelMap is not None: propVal.set(valMap[value])
        else:                    propVal.set(value)

    _guiUpdate(propVal.get())

    # set up the callback functions
    for ev in evType: guiObj.Bind(ev, _propUpdate)
    propVal.addListener(listenerName, _guiUpdate)

    guiObj.Bind(wx.EVT_WINDOW_DESTROY,
                lambda ev: propVal.removeListener(listenerName))


def _setupValidation(widget, hasProps, propObj, propVal):
    """
    Configures input validation for the given widget, which is assumed
    to be managing the given prop (props.PropertyBase) object.  Any
    changes to the property value are validated and, if the new value
    is invalid, the widget background colour is changed to a light
    red, so that the user is aware of the invalid-ness.
    """

    invalidBGColour = '#ff9999'
    validBGColour   = widget.GetBackgroundColour()

    def _changeBGOnValidate(value, valid, instance):
        """
        Called whenever the property value changes. Checks
        to see if the new value is valid and changes the
        widget background colour according to the validity
        of the new value.
        """
        
        if valid: newBGColour = validBGColour
        else:     newBGColour = invalidBGColour
        
        widget.SetBackgroundColour(newBGColour)
        widget.Refresh()

    # We add a callback listener to the PropertyValue object,
    # rather than to the PropertyBase, as one property may be
    # associated with multiple variables, and we don't want
    # the widgets associated with those other variables to
    # change background.
    lName = 'widgets_py_ChangeBG_{}'.format(id(widget))
    propVal.addListener(lName, _changeBGOnValidate)

    # And ensure that the listener is
    # removed when the widget is destroyed
    widget.Bind(wx.EVT_WINDOW_DESTROY,
                lambda ev: propVal.removeListener(lName))

    # Validate the initial property value,
    # so the background is appropriately set
    _changeBGOnValidate(None, propVal.isValid(), None)
    

# The _lastFilePathDir variable is used to retain the
# most recentlyvisited directory in file dialogs. New
# file dialogs are initialised to display this
# directory.
#
# This is currently a global setting, but it may be
# more appropriate to make it a per-widget setting.
# Easily done, just make this a dict, with the widget
# (or property name) as the key.
_lastFilePathDir = None
def _FilePath(parent, hasProps, propObj, propVal):
    """
    Creates and returns a panel containing a text field and a
    Button. The button, when clicked, opens a file dialog
    allowing the user to choose a file/directory to open, or
    a location to save (this depends upon how the propObj
    [props.FilePath] object was configured).
    """

    global _lastFilePathDir
    if _lastFilePathDir is None:
        _lastFilePathDir = os.getcwd()

    value = propVal.get()
    if value is None: value = ''

    panel   = wx.Panel(parent)
    textbox = wx.TextCtrl(panel)
    button  = wx.Button(panel, label='Choose')

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(textbox, flag=wx.EXPAND, proportion=1)
    sizer.Add(button,  flag=wx.EXPAND)

    panel.SetSizer(sizer)
    panel.SetAutoLayout(1)
    sizer.Fit(panel)

    exists = propObj.getConstraint(hasProps, 'exists')
    isFile = propObj.getConstraint(hasProps, 'isFile')
    
    def _choosePath(ev):
        global _lastFilePathDir

        if exists and isFile:
            dlg = wx.FileDialog(parent,
                                message='Choose file',
                                defaultDir=_lastFilePathDir,
                                defaultFile=value,
                                style=wx.FD_OPEN)
            
        elif exists and (not isFile):
            dlg = wx.DirDialog(parent,
                               message='Choose directory',
                               defaultPath=_lastFilePathDir) 

        else:
            dlg = wx.FileDialog(parent,
                                message='Save file',
                                defaultDir=_lastFilePathDir,
                                defaultFile=value,
                                style=wx.FD_SAVE)


        dlg.ShowModal()
        path = dlg.GetPath()
        
        if path != '' and path is not None:
            _lastFilePathDir = op.dirname(path)
            propVal.set(path)
            
    _setupValidation(textbox, hasProps, propObj, propVal)
    _propBind(hasProps, propObj, propVal, textbox, wx.EVT_TEXT)

    button.Bind(wx.EVT_BUTTON, _choosePath)
    
    return panel
    

def _Choice(parent, hasProps, propObj, propVal):
    """
    Creates and returns a ttk Combobox allowing the
    user to set the given propObj (props.Choice) object.
    """

    choices = propObj.choices
    labels  = propObj.choiceLabels
    valMap  = OrderedDict(zip(choices, labels))
    widget  = wx.ComboBox(
        parent,
        choices=labels,
        style=wx.CB_READONLY | wx.CB_DROPDOWN)

    _propBind(hasProps, propObj, propVal, widget, wx.EVT_COMBOBOX, valMap)
    
    return widget


def _String(parent, hasProps, propObj, propVal):
    """
    Creates and returns a ttk Entry object, allowing
    the user to edit the given propObj (props.String)
    object.
    """

    widget = wx.TextCtrl(parent)

    _propBind(hasProps, propObj, propVal, widget, wx.EVT_TEXT)
    _setupValidation(widget, hasProps, propObj, propVal)
    
    return widget



def _Real(parent, hasProps, propObj, propVal):
    return _Number(parent, hasProps, propObj, propVal)


def _Int(parent, hasProps, propObj, propVal):
    return _Number(parent, hasProps, propObj, propVal)


def _Percentage(parent, hasProps, propObj, propVal):
    # TODO Add '%' signs to Scale labels.
    return _Number(parent, hasProps, propObj, propVal) 
        

def _Boolean(parent, hasProps, propObj, propVal):
    """
    Creates and returns a check box, allowing the user
    to set the given propObj (props.Boolean) object.
    """

    checkBox = wx.CheckBox(parent)
    _propBind(hasProps, propObj, propVal, checkBox, wx.EVT_CHECKBOX)
    return checkBox


def _makeColourMapComboBox(parent, cmapDict, selected=None):
    """
    Makes a wx.combo.BitmapComboBox which allows the user to select a
    colour map from the given dictionary of
    (name -> matplotlib.colors.Colormap) mappings. The name of each
    colour map is shown in the combo box,, along with a little image
    for each colour map, showing the colour range.
    """
    
    bitmaps          = []
    width, height    = 75, 15

    cmapNames, cmaps = zip(*cmapDict.items())

    if selected is not None: selected = cmapNames.index(selected)
    else:                    selected = 0

    # Make a little bitmap for every colour map. The bitmap
    # is a (width*height*3) array of bytes
    for cmapName, cmap in zip(cmapNames, cmaps):
        
        # create a single colour  for each horizontal pixel
        colours = cmap(np.linspace(0.0, 1.0, width))

        # discard alpha values
        colours = colours[:, :3]

        # repeat each horizontal pixel (height) times
        colours = np.tile(colours, (height, 1, 1))

        # scale to [0,255] and cast to uint8
        colours = colours * 255
        colours = np.array(colours, dtype=np.uint8)

        # make a wx Bitmap from the colour data
        colours = colours.ravel(order='C')
        bitmap  = wx.BitmapFromBuffer(width, height, colours)

        bitmaps.append(bitmap)

    # create the combobox
    cbox = wx.combo.BitmapComboBox(
        parent, style=wx.CB_READONLY | wx.CB_DROPDOWN)

    for name, bitmap in zip(cmapNames, bitmaps):
        cbox.Append(name, bitmap)

    cbox.SetSelection(selected)

    return cbox


def _ColourMap(parent, hasProps, propObj, propVal):
    """
    Creates and returns a combobox, allowing the user to change
    the value of the given ColourMap property.
    """

    cmapNames = sorted(mplcm.datad.keys())
    cmapObjs  = map(mplcm.get_cmap, cmapNames)
    
    valMap    = OrderedDict(zip(cmapObjs,  cmapNames))
    labelMap  = OrderedDict(zip(cmapNames, cmapObjs))

    cbox = _makeColourMapComboBox(
        parent, labelMap, propVal.get().name)

    _propBind(hasProps, propObj, propVal, cbox, wx.EVT_COMBOBOX, valMap)
        
    return cbox   


def makeWidget(parent, hasProps, propName):
    """
    Given hasProps (a props.HasProperties object), propName (the name
    of a property of hasProps), and parent GUI object, creates and
    returns a widget, or a frame containing widgets, which may be
    used to edit the property.
    """

    propObj = hasProps.getProp(propName)
    propVal = propObj.getPropVal(hasProps)

    if propObj is None:
        raise ValueError('Could not find property {}.{}'.format(
            hasProps.__class__.__name__, propName))

    makeFunc = getattr(
        sys.modules[__name__],
        '_{}'.format(propObj.__class__.__name__), None)

    if makeFunc is None:
        raise ValueError(
            'Unknown property type: {}'.format(propObj.__class__.__name__))

    return makeFunc(parent, hasProps, propObj, propVal)
