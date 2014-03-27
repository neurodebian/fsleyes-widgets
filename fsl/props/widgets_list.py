#!/usr/bin/env python
#
# widgets_list.py - A widget for editing a props.List property.
#
# The code in this file really belongs in widgets.py, but it is
# large and complex enough to warrent its own module.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import sys
import os

import Tkinter as tk
import            ttk

import widgets



def _pasteDataDialog(parent, hasProps, propObj):
    """
    Displays a dialog containing an editable text field, allowing the
    user to type/paste bulk data which will be used to populate the list
    (one line per item).
    
    Parameters:
      - parent:   Tkinter parent object 
      - hasProps: The props.HasProperties object which owns propObj. 
      - propObj:  The props.List property object
    """

    window  = tk.Toplevel()
    frame   = ttk.Frame(window)
    listObj = getattr(hasProps, propObj.label)

    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(   0, weight=1)

    # TODO label explaining what to do
    text    = tk.Text(frame, wrap="none")
    vScroll = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=text.yview)
    hScroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=text.xview)

    initText = '\n'.join([str(l).strip() for l in listObj])
    text.insert('1.0', initText)

    def pasteIntoList():
        """
        Called when the user pushes 'Ok'. Copies whatever the
        user typed/pasted into the text area into the list.
        """

        listData = text.get('1.0', 'end').strip()
        listData = listData.split('\n')
        listData = [s.strip() for s in listData]

        setattr(hasProps, propObj.label, listData)
        
        window.destroy()

    # ok/cancel buttons
    btnFrame     = ttk.Frame(frame)
    okButton     = ttk.Button(btnFrame, text="Ok",     command=pasteIntoList)
    cancelButton = ttk.Button(btnFrame, text="Cancel", command=window.destroy)

    # lay out the widgets!
    text    .grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
    hScroll .grid(row=1, column=0, sticky=tk.E+tk.W)
    vScroll .grid(row=0, column=1, sticky=tk.N+tk.S)
    btnFrame.grid(row=2, column=0, sticky=tk.E+tk.W, columnspan=2)

    btnFrame.columnconfigure(0, weight=1)
    btnFrame.columnconfigure(1, weight=1)
    okButton    .grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
    cancelButton.grid(row=0, column=1, sticky=tk.N+tk.S+tk.E+tk.W)

    # make this window modal
    window.transient(parent)
    window.grab_set()
    parent.wait_window(window) 


def _editListDialog(parent, hasProps, propObj):
    """
    A dialog which displays a widget for every item in the list, and
    which allows the user to adjust the number of items in the list.
    """

    # listObj is a properties.ListWrapper object
    listObj  = getattr(hasProps, propObj.label)
    listType = propObj.listType

    # Get a reference to a function in the widgets module,
    # which can make individual widgets for each list item
    makeFunc = getattr(
        widgets, '_{}'.format(listType.__class__.__name__), None)

    if makeFunc is None:
        raise TypeError(
            'Unknown property type: {}'.format(propObj.__class__.__name__)) 

    # Edit widgets go on the frame. But frames are not scrollable.
    # So we embed the frame inside a canvas, which is scrollable.
    #
    # Widget layout is as follows:
    #   - window
    #     - canvasFrame
    #       - canvas
    #         - frame
    #       - scrollbar
    #     - okButton
    
    window      = tk.Toplevel()
    canvasFrame = ttk.Frame(window)
    canvas      = tk.Canvas(canvasFrame)
    frame       = ttk.Frame(canvas)
    scrollbar   = ttk.Scrollbar(canvasFrame, orient=tk.VERTICAL, command=canvas.yview)
    okButton    = ttk.Button(window, text='Ok', command=window.destroy)
    
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.create_window((4,4), window=frame, anchor=tk.NW, tag='frame')

    canvasFrame.pack(fill=tk.BOTH, expand=True)
    okButton   .pack(fill=tk.X)

    canvas   .pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.LEFT, fill=tk.Y)
    frame.columnconfigure(0, weight=1)

    # When the frame changes size, the canvas
    # scroll region is updated to fit it
    def updateCanvas(ev):
        bbox = canvas.bbox(tk.ALL)
        canvas.configure(scrollregion=bbox)

    # When the canvas changes size, the frame
    # is updated to fill it horizontally
    def resizeFrame(ev):
        width = canvas.winfo_width()
        canvas.itemconfig('frame', width=width-5) 
        
    frame .bind('<Configure>', updateCanvas)
    canvas.bind('<Configure>', resizeFrame)

    listWidgets = []

    # Make a widget for every element in the list
    for i in range(len(listObj)):
        propVal = propObj.getPropVal(hasProps, i)
        widget  = makeFunc(frame, hasProps, listType, propVal)
        listWidgets.append(widget)

    # A TK variable used in a spinbox created below,,
    # which stores the number of items in the list
    numRowsName = '{}_numRows'.format(propObj.label)
    numRows     = tk.IntVar(master=window,
                            name=numRowsName,
                            value=len(listObj))

    # Explicitly set minimum/maximum values on the
    # spinbox, otherwise it doesn't behave very nicely.
    minval = propObj.minlen if (propObj.minlen is not None) else 0
    maxval = propObj.maxlen if (propObj.maxlen is not None) else sys.maxint

    # Spinbox allowing user to change
    # number of items in the list
    numRowsBox = tk.Spinbox(frame,
                            from_=minval,
                            to=maxval,
                            textvariable=numRows,
                            increment=1)

    # Restrict spinbox values to numeric characters
    vcmd = (numRowsBox.register(lambda s: s.isdigit()), '%S')
    numRowsBox.configure(validate='key', validatecommand=vcmd)

    # layout spinbox and list widgets
    numRowsBox.grid(row=0, column=0, sticky=tk.W+tk.E)
    for i,w in enumerate(listWidgets):
        w.grid(row=i+1, column=0, sticky=tk.W+tk.E)

    def changeNumRows(*args):
        """
        Called when the numRows variable is changed (via the numRows
        spinbox). Adds or removes items from the property list, and
        corresponding widgets from the window.
        """

        oldLen = len(listObj)

        # If numRows.get() raises an error, it means
        # that the user has typed in non-numeric data. 
        try:    newLen = numRows.get()
        except: return

        # add rows
        while oldLen < newLen:

            # add a new element to the list
            listObj.append(listType.default)
            propVal = propObj.getPropVal(hasProps, -1)

            # add a widget
            widg = makeFunc(frame, hasProps, listType, propVal)
            widg.grid(row=len(listObj), column=0, sticky=tk.W+tk.E)
            listWidgets.append(widg)
 
            oldLen = oldLen + 1

        # remove rows
        while oldLen > newLen:

            # kill the tkVar
            listObj.pop()

            # kill the widget
            widg = listWidgets.pop()
            widg.grid_forget()
            widg.destroy()

            oldLen = oldLen - 1

    numRows.trace('w', changeNumRows)

    # make the list edit dialog modal
    window.transient(parent)
    window.grab_set()
    parent.wait_window(window)

    
def _List(parent, hasProps, propObj, propVal):
    """
    Creates and returns a ttk.Frame containing two buttons which,
    when pushed, display dialogs allowing the user to edit the
    values contained in the list.
    """

    frame = ttk.Frame(parent)

    # When the user pushes this button on the parent window,
    # a new window is displayed, allowing the user to edit
    # the values in the list individually
    editButton = ttk.Button(
        frame, text='Edit',
        command=lambda: _editListDialog(parent, hasProps, propObj))

    # When the user pushes this button, a new window is
    # displayed, allowing the user to type/paste bulk data
    pasteButton = ttk.Button(
        frame, text='Paste data',
        command=lambda: _pasteDataDialog(parent, hasProps, propObj))

    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)
    editButton .grid(row=0, column=0, sticky=tk.E+tk.W)
    pasteButton.grid(row=0, column=1, sticky=tk.E+tk.W)
        
    return frame
