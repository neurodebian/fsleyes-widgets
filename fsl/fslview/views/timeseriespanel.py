#!/usr/bin/env python
#
# timeseriespanel.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import logging
log = logging.getLogger(__name__)

import wx

import props

import matplotlib as mpl

mpl.use('WXAgg')

import matplotlib.pyplot as plt
from   matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as Canvas

class TimeSeriesPanel(wx.Panel, props.HasProperties):


    def __init__(self, parent, imageList):

        wx.Panel.__init__(self, parent)
        props.HasProperties.__init__(self)

        self._imageList = imageList
        self._name      = '{}_{}'.format(self.__class__.__name__, id(self))

        self._figure = plt.Figure()
        self._axis   = self._figure.add_subplot(1, 1, 1)
        self._canvas = Canvas(self, -1, self._figure)

        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)
        self._sizer.Add(self._canvas, flag=wx.EXPAND, proportion=1)

        self._imageList.addListener(
            'selectedImage',
            self._name,
            self._selectedImageChanged)
        self._imageList.addListener(
            'location',
            self._name,
            self._locationChanged)
        self._imageList.addListener(
            'volume',
            self._name,
            self._locationChanged) 

        def onDestroy(ev):
            ev.Skip()
            self._imageList.removeListener('selectedImage', self._name)
            self._imageList.removeListener('location',      self._name)
            self._imageList.removeListener('volume',        self._name)

        self.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)

        self._selectedImageChanged()
        
        self.Layout()

        
    def _selectedImageChanged(self, *a):
        
        self._axis.clear()

        if len(self._imageList) == 0:
            return

        image = self._imageList[self._imageList.selectedImage]

        if not image.is4DImage():
            return

        self._voxPlot(image, *self._imageList.location.xyz)

        
    def _locationChanged(self, *a):
        
        self._axis.clear()

        if len(self._imageList) == 0:
            return 
        
        image = self._imageList[self._imageList.selectedImage]

        if not image.is4DImage():
            return

        self._voxPlot(image, *self._imageList.location.xyz) 



    def _voxPlot(self, image, x, y, z):

        x, y, z = image.worldToVox([[x, y, z]])[0]
        t       = self._imageList.volume

        inBounds = True
        for vox, shape in zip((x, y, z), image.shape):
            if vox >= shape or vox < 0:
                inBounds = False

        if inBounds:
            data = image.data[x, y, z, :]
            self._axis.plot(data, 'r-', lw=2)
        else:
            self._axis.text(
                0.5,
                0.5,
                'Out of bounds',
                color='#ff9090',
                ha='center',
                transform=self._axis.transAxes)

        if t < image.shape[3]:
            self._axis.axvline(t, lw=2, c='#000080')

        self._canvas.draw()
