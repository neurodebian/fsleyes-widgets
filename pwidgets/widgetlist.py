#!/usr/bin/env python
#
# widgetlist.py - A widget which displays a list of groupable widgets.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module provides the :class:`WidgetList` class, which displays a list
of widgets. The widgets can be grouped arbitrarily, and widgets and groups can
be dynamically added and removed.

"""

from collections import OrderedDict

import wx
import wx.lib.scrolledpanel as scrolledpanel


class Widget(object):
    """
    """
    def __init__(self,
                 displayName,
                 tooltip,
                 label,
                 widget,
                 sizer):
        self.displayName = displayName
        self.tooltip     = tooltip
        self.label       = label
        self.widget      = widget
        self.sizer       = sizer


    def SetBackgroundColour(self, colour):
        self.label.SetBackgroundColour(colour)

        if isinstance(self.widget, wx.Sizer):
            for c in self.widget.GetChildren():
                c.GetWindow().SetBackgroundColour(colour)
        else:
            self.widget.SetBackgroundColour(colour)

    
    def Destroy(self):
        self.label.Destroy()
        if isinstance(self.widget, wx.Sizer):
            self.widget.Clear(True)
        else:
            self.widget.Destroy() 
                             

class Group(object):
    """The ``Group`` class is used internally by :class:`PropertyList`
    instances to represent groups of properties that are in the list.
    """ 
    def __init__(self,
                 groupName,
                 displayName,
                 parentPanel,
                 colPanel,
                 widgPanel,
                 sizer):
        self.groupName   = groupName
        self.displayName = displayName
        self.parentPanel = parentPanel
        self.colPanel    = colPanel
        self.widgPanel   = widgPanel
        self.sizer       = sizer
        self.widgets     = OrderedDict()


class WidgetList(scrolledpanel.ScrolledPanel):


    _defaultOddColour   = '#eaeaea'
    _defaultEvenColour  = '#ffffff'
    _defaultGroupColour = '#eaeaff'

    
    def __init__(self, parent):
        scrolledpanel.ScrolledPanel.__init__(self, parent)

        self.__sizer       = wx.BoxSizer(wx.VERTICAL)
        self.__widgSizer   = wx.BoxSizer(wx.VERTICAL)
        self.__groupSizer  = wx.BoxSizer(wx.VERTICAL)
        self.__widgets     = OrderedDict()
        self.__groups      = OrderedDict()

        self.__oddColour   = WidgetList._defaultOddColour
        self.__evenColour  = WidgetList._defaultEvenColour
        self.__groupColour = WidgetList._defaultGroupColour

        self.__sizer.Add(self.__widgSizer,  flag=wx.EXPAND)
        self.__sizer.Add(self.__groupSizer, flag=wx.EXPAND)

        self.SetSizer(self.__sizer)
        self.SetBackgroundColour((255, 255, 255))
        self.SetupScrolling()
        self.SetAutoLayout(1)

        

    def __makeWidgetKey(self, widget):
        return str(id(widget))


    def __setLabelWidths(self, widgets):

        if len(widgets) == 0:
            return

        dc        = wx.ClientDC(widgets[0].label)
        lblWidths = [dc.GetTextExtent(w.displayName)[0] for w in widgets]
        maxWidth  = max(lblWidths)

        for w in widgets:
            w.label.SetMinSize((maxWidth + 10, -1))
            w.label.SetMaxSize((maxWidth + 10, -1))
 

    def __setColours(self):
        def setWidgetColours(widgDict):
            for i, widg in enumerate(widgDict.values()):
                
                if i % 2: colour = self.__oddColour
                else:     colour = self.__evenColour
                widg.SetBackgroundColour(colour)

        setWidgetColours(self.__widgets)
                    
        for group in self.__groups.values():

            setWidgetColours(group.widgets)
            group.parentPanel.SetBackgroundColour(self.__groupColour)
            group.colPanel   .SetBackgroundColour(self.__groupColour)


    def __refresh(self, *a):
        self.__setColours()
        self.FitInside()
        self.Layout()


    def SetColours(self, odd=None, even=None, group=None):
        if odd   is not None: self.__oddColour   = odd
        if even  is not None: self.__evenColour  = even
        if group is not None: self.__groupColour = group
        self.__setColours()


    def HasGroup(self, groupName):
        return groupName in self.__groups


    def RenameGroup(self, groupName, newDisplayName):
        group = self.__groups[groupName]
        group.displayName = newDisplayName
        group.colPanel.SetLabel(newDisplayName)

        
    def AddGroup(self, groupName, displayName=None):

        if displayName is None:
            displayName = groupName

        if groupName in self.__groups:
            raise ValueError('A group with name {} '
                             'already exists'.format(groupName))

        parentPanel = wx.Panel(self, style=wx.SUNKEN_BORDER)
        colPanel    = wx.CollapsiblePane(parentPanel, label=displayName)
        widgPanel   = colPanel.GetPane()
        widgSizer   = wx.BoxSizer(wx.VERTICAL)
        
        widgPanel.SetSizer(widgSizer)
        parentPanel.SetWindowStyleFlag(wx.SUNKEN_BORDER)
        self.__groupSizer.Add(parentPanel, border=10, flag=wx.EXPAND | wx.ALL)

        parentSizer = wx.BoxSizer(wx.VERTICAL)
        parentSizer.Add(colPanel, flag=wx.EXPAND, proportion=1)
        parentPanel.SetSizer(parentSizer)

        group = Group(groupName,
                      displayName,
                      parentPanel,
                      colPanel,
                      widgPanel,
                      widgSizer)

        self.__groups[groupName] = group
        self.__refresh()

        colPanel.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.__refresh)


    def AddWidget(self, widget, displayName, tooltip=None, groupName=None):
        """Add an arbitrary widget to the property list.

        Accepts :class:`wx.Window` instances, or :class:`wx.Sizer` instances,
        although support for the latter is basic - only one level of nesting
        is possible, unless all of the child objects are created with this
        ``PropertyList`` as their parent.
        """

        if groupName is None:
            widgDict    = self.__widgets
            parent      = self
            parentSizer = self.__widgSizer
        else:
            group       = self.__groups[groupName]
            widgDict    = group.widgets
            parent      = group.widgPanel
            parentSizer = group.sizer 

        key = self.__makeWidgetKey(widget)

        if key in widgDict:
            raise ValueError('Widgets {} already exist'.format(key))

        if isinstance(widget, wx.Sizer):
            for child in widget.GetChildren():
                child.GetWindow().Reparent(parent)
        else:
            widget.Reparent(parent)
            
        label = wx.StaticText(parent, label=displayName, style=wx.ALIGN_RIGHT)
        widgSizer = wx.BoxSizer(wx.HORIZONTAL)

        widgSizer.Add(label,  flag=wx.EXPAND)
        widgSizer.Add(widget, flag=wx.EXPAND, proportion=1)
        
        parentSizer.Add(widgSizer,
                        flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
                        border=5)

        widg = Widget(displayName,
                      tooltip,
                      label,
                      widget,
                      widgSizer)

        widgDict[key] = widg

        self.__setLabelWidths(widgDict.values())
        self.__refresh()
        

    def RemoveWidget(self, widget, groupName=None):
        key = self.__makeWidgetKey(widget)

        if groupName is None:
            parentSizer = self.__widgSizer
            widgDict    = self.__widgets
        else:
            group       = self.__groups[groupName]
            parentSizer = group.sizer 
            widgDict    = group.widgets

        widg = widgDict.pop(key)
        parentSizer.Detach(widg.sizer)

        widg.Destroy()
        self.__refresh()

        
    def RemoveGroup(self, groupName):
        group = self.__groups.pop(groupName)
        self.__groupSizer.Detach(group.parentPanel)
        group.parentPanel.Destroy()
        self.__refresh()


    def Clear(self):
        keys = self.__widgets.keys()
        for key in keys:
            widg = self.__widgets.pop(key)
            self.__propSizer.Detach(widg.sizer)
            widg.Destroy()
        self.__refresh()
        
        
    def ClearGroup(self, groupName):
        group = self.__groups[groupName]
        group.sizer.Clear(True)
        group.props.clear()
        self.__refresh()


    def IsExpanded(self, groupName):
        return self.__groups[groupName].colPanel.IsExpanded()

    
    def Expand(self, groupName, expand=True):
        panel = self.__groups[groupName].colPanel
        if expand: panel.Expand()
        else:      panel.Collapse()
        self.__refresh()

        
if __name__ == '__main__':

    import props

    class Test(props.HasProperties):
        myint    = props.Int()
        mybool   = props.Boolean()
        myreal   = props.Real(minval=0, maxval=10, clamped=True)
        mystring = props.String()
        mybounds = props.Bounds(ndims=2)

        myreal2    = props.Real(minval=0, maxval=10, clamped=True)
        myreal3    = props.Real(minval=0, maxval=10, clamped=True)
        mystring2  = props.String()
        mystring3  = props.String()
        mybool2    = props.Boolean()
        myint2     = props.Boolean()


    testObj = Test()
    testObj.mybounds.xmin = 0
    testObj.mybounds.xmax = 10
    testObj.mybounds.ymin = 10
    testObj.mybounds.ymax = 20 
    app     = wx.App()
    frame   = wx.Frame(None)
    wlist   = WidgetList(frame)

    widg = wx.TextCtrl(wlist)
    widg.SetValue('Bah, humbug!')

    wlist.AddWidget(props.makeWidget(wlist, testObj, 'myint'), 'My int')
    wlist.AddWidget(props.makeWidget(wlist, testObj, 'mybool'), 'mybool')
    wlist.AddWidget(
        props.makeWidget(wlist, testObj, 'myreal',
                         showLimits=False, spin=False),
        'My real')
    wlist.AddWidget(props.makeWidget(wlist, testObj, 'mystring'), 'mystring')

    wlist.AddWidget(widg, 'My widget')
    
    wlist.AddGroup('extra1', 'Extras 1')
    wlist.AddGroup('extra2', 'Extras 2')
    
    wlist.AddWidget(
        props.makeWidget(wlist, testObj, 'myreal2', showLimits=False),
        'myreal2', groupName='extra1')
    wlist.AddWidget(
        props.makeWidget(wlist, testObj, 'myreal3', spin=False),
        'myreal3', groupName='extra1')
    wlist.AddWidget(
        props.makeWidget(wlist, testObj, 'mystring2'),
        'mystring2', groupName='extra1')
    wlist.AddWidget(
        props.makeWidget(wlist, testObj, 'mybounds', showLimits=False),
        'My bounds, hur', groupName='extra1', )
    wlist.AddWidget(
        props.makeWidget(wlist, testObj, 'mystring3'),
        'mystring3', groupName='extra2')
    wlist.AddWidget(
        props.makeWidget(wlist, testObj, 'mybool2'),
        'mybool2', groupName='extra2')
    wlist.AddWidget(
        props.makeWidget(wlist, testObj, 'myint2'),
        'myint2', groupName='extra2')

    frame.Layout()
    frame.Fit()

    frame.Show()
    app.MainLoop()
