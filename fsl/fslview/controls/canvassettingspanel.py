#!/usr/bin/env python
#
# canvassettingspanel.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import wx

import props

import pwidgets.widgetlist as widgetlist

import fsl.data.strings    as strings
import fsl.fslview.panel   as fslpanel


_CANVASPANEL_PROPS = [
    props.Widget('syncOverlayOrder'),
    props.Widget('syncLocation'),
    props.Widget('syncOverlayDisplay'),
    props.Widget('movieMode'),
    props.Widget('movieRate', spin=False, showLimits=False),
]

_SCENEOPTS_PROPS = [
    props.Widget('showCursor'),
    props.Widget('bgColour'),
    props.Widget('performance', spin=False, showLimits=False),
    props.Widget('showColourBar'),
    props.Widget('colourBarLabelSide', enabledWhen=lambda o: o.showColourBar),
    props.Widget('colourBarLocation',  enabledWhen=lambda o: o.showColourBar)
]

_ORTHOOPTS_PROPS = [
    props.Widget('layout'), 
    props.Widget('zoom', spin=False, showLimits=False),
    props.Widget('showLabels'),
    props.Widget('showXCanvas'),
    props.Widget('showYCanvas'),
    props.Widget('showZCanvas')
]

_LIGHTBOXOPTS_PROPS = [
    props.Widget('zax'),
    props.Widget('zoom',         showLimits=False, spin=False),
    props.Widget('sliceSpacing', showLimits=False),
    props.Widget('zrange',       showLimits=False),
    props.Widget('highlightSlice'),
    props.Widget('showGridLines') 
]


class CanvasSettingsPanel(fslpanel.FSLViewPanel):

    def __init__(self, parent, overlayList, displayCtx, canvasPanel):

        fslpanel.FSLViewPanel.__init__(self, parent, overlayList, displayCtx)

        self.__widgets = widgetlist.WidgetList(self)

        self.__sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self.__sizer)

        self.__sizer.Add(self.__widgets, flag=wx.EXPAND, proportion=1)

        import fsl.fslview.views.orthopanel    as orthopanel
        import fsl.fslview.views.lightboxpanel as lightboxpanel

        if isinstance(canvasPanel, orthopanel.OrthoPanel):
            panelGroup = 'ortho'
            panelProps = _ORTHOOPTS_PROPS
            
        elif isinstance(canvasPanel, lightboxpanel.LightBoxPanel):
            panelGroup = 'lightbox'
            panelProps = _LIGHTBOXOPTS_PROPS

        self.__widgets.AddGroup('scene' ,    strings.labels[self, 'scene'])
        self.__widgets.AddGroup( panelGroup, strings.labels[self,  panelGroup])

        for dispProp in _CANVASPANEL_PROPS:

            widget = props.buildGUI(self.__widgets,
                                    canvasPanel,
                                    dispProp,
                                    showUnlink=False)
            
            self.__widgets.AddWidget(
                widget,
                strings.properties[canvasPanel, dispProp.key],
                groupName='scene')

        opts = canvasPanel.getSceneOptions()

        for dispProp in _SCENEOPTS_PROPS:

            widget = props.buildGUI(self.__widgets,
                                    opts,
                                    dispProp,
                                    showUnlink=False)
            
            self.__widgets.AddWidget(
                widget,
                strings.properties[opts, dispProp.key],
                groupName='scene') 

        for dispProp in panelProps:

            widget = props.buildGUI(self.__widgets,
                                    opts,
                                    dispProp,
                                    showUnlink=False)
            
            self.__widgets.AddWidget(
                widget,
                strings.properties[opts, dispProp.key],
                groupName=panelGroup)

        self.__widgets.Expand('scene')
        self.__widgets.Expand(panelGroup)

        self.SetMinSize((21, 21))
