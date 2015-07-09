#!/usr/bin/env python
#
# timeseriescontrolpanel.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import wx

import                        props
import pwidgets.widgetlist as widgetlist

import fsl.fslview.panel as fslpanel
import fsl.data.strings  as strings


class TimeSeriesControlPanel(fslpanel.FSLViewPanel):

    def __init__(self, parent, overlayList, displayCtx, tsPanel):

        fslpanel.FSLViewPanel.__init__(self, parent, overlayList, displayCtx)

        self.__tsPanel = tsPanel
        self.__widgets = widgetlist.WidgetList(self)
        self.__sizer   = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self.__sizer)
        self.__sizer.Add(self.__widgets, flag=wx.EXPAND, proportion=1)

        tsProps   = ['plotMode',
                     'usePixdim',
                     'showCurrent']
        plotProps = ['xLogScale',
                     'yLogScale',
                     'smooth',
                     'legend',
                     'ticks',
                     'grid',
                     'autoScale']

        self.__widgets.AddGroup(
            'tsSettings',
            strings.labels[self, 'tsSettings'])

        for prop in tsProps:
            self.__widgets.AddWidget(
                props.makeWidget(self.__widgets, tsPanel, prop),
                displayName=strings.properties[tsPanel, prop],
                groupName='tsSettings')

        self.__widgets.AddGroup(
            'plotSettings',
            strings.labels[tsPanel, 'plotSettings'])
        
        for prop in plotProps:
            self.__widgets.AddWidget(
                props.makeWidget(self.__widgets, tsPanel, prop),
                displayName=strings.properties[tsPanel, prop],
                groupName='plotSettings')

        xlabel = props.makeWidget(self.__widgets, tsPanel, 'xlabel')
        ylabel = props.makeWidget(self.__widgets, tsPanel, 'ylabel')

        labels = wx.BoxSizer(wx.HORIZONTAL)

        labels.Add(wx.StaticText(self.__widgets,
                                 label=strings.labels[tsPanel, 'xlabel']))
        labels.Add(xlabel, flag=wx.EXPAND, proportion=1)
        labels.Add(wx.StaticText(self.__widgets,
                                 label=strings.labels[tsPanel, 'ylabel']))
        labels.Add(ylabel, flag=wx.EXPAND, proportion=1) 

        limits = props.makeListWidgets(self.__widgets, tsPanel, 'limits')
        xlims  = wx.BoxSizer(wx.HORIZONTAL)
        ylims  = wx.BoxSizer(wx.HORIZONTAL)
        
        xlims.Add(limits[0], flag=wx.EXPAND, proportion=1)
        xlims.Add(limits[1], flag=wx.EXPAND, proportion=1)
        ylims.Add(limits[2], flag=wx.EXPAND, proportion=1)
        ylims.Add(limits[3], flag=wx.EXPAND, proportion=1) 

        self.__widgets.AddWidget(
            labels,
            strings.labels[tsPanel, 'labels'],
            groupName='plotSettings')
        self.__widgets.AddWidget(
            xlims,
            strings.labels[tsPanel, 'xlim'],
            groupName='plotSettings')
        self.__widgets.AddWidget(
            ylims,
            strings.labels[tsPanel, 'ylim'],
            groupName='plotSettings')

        displayCtx .addListener('selectedOverlay',
                                self._name,
                                self.__selectedOverlayChanged)
        overlayList.addListener('overlays',
                                self._name,
                                self.__selectedOverlayChanged)

        tsPanel.addListener('showCurrent',
                            self._name,
                            self.__showCurrentChanged)

        self.__showCurrentChanged()

        # This attribute keeps track of the currently
        # selected overlay, but only if said overlay
        # is a FEATImage.
        self.__selectedOverlay = None
        self.__selectedOverlayChanged()


    def destroy(self):
        self._displayCtx .removeListener('selectedOverlay', self._name)
        self._overlayList.removeListener('overlays',        self._name)

        if self.__selectedOverlay is not None:
            display = self._displayCtx.getDisplay(self.__selectedOverlay)
            display.removeListener('name', self._name)


    def __showCurrentChanged(self, *a):
        widgets     = self.__widgets
        tsPanel     = self.__tsPanel
        showCurrent = tsPanel.showCurrent
        areShown    = widgets.HasGroup('currentSettings')

        if (not showCurrent) and areShown:
            widgets.RemoveGroup('currentSettings')

        elif showCurrent and (not areShown):

            self.__widgets.AddGroup('currentSettings',
                                    strings.labels[self, 'currentSettings'])

            colour    = props.makeWidget(widgets, tsPanel, 'currentColour')
            alpha     = props.makeWidget(widgets, tsPanel, 'currentAlpha',
                                         showLimits=False, spin=False)
            lineWidth = props.makeWidget(widgets, tsPanel, 'currentLineWidth')
            lineStyle = props.makeWidget(widgets, tsPanel, 'currentLineStyle')

            self.__widgets.AddWidget(
                colour,
                displayName=strings.properties[tsPanel, 'currentColour'],
                groupName='currentSettings')
            self.__widgets.AddWidget(
                alpha,
                displayName=strings.properties[tsPanel, 'currentAlpha'],
                groupName='currentSettings')
            self.__widgets.AddWidget(
                lineWidth,
                displayName=strings.properties[tsPanel, 'currentLineWidth'],
                groupName='currentSettings') 
            self.__widgets.AddWidget(
                lineStyle,
                displayName=strings.properties[tsPanel, 'currentLineStyle'],
                groupName='currentSettings')
            

    def __selectedOverlayNameChanged(self, *a):
        display = self._displayCtx.getDisplay(self.__selectedOverlay)
        self.__widgets.RenameGroup(
            'currentFEATSettings',
            strings.labels[self, 'currentFEATSettings'].format(
                display.name))

    
    def __selectedOverlayChanged(self, *a):

        # We're assuminbg that the TimeSeriesPanel has
        # already updated its current TimeSeries for
        # the newly selected overlay.
        
        import fsl.fslview.views.timeseriespanel as tsp

        if self.__selectedOverlay is not None:
            display = self._displayCtx.getDisplay(self.__selectedOverlay)
            display.removeListener('name', self._name)
            self.__selectedOverlay = None

        if self.__widgets.HasGroup('currentFEATSettings'):
            self.__widgets.RemoveGroup('currentFEATSettings')

        ts = self.__tsPanel.getCurrent()

        if ts is None or not isinstance(ts, tsp.FEATTimeSeries):
            return

        overlay = ts.overlay
        display = self._displayCtx.getDisplay(overlay)

        self.__selectedOverlay = overlay

        display.addListener('name',
                            self._name,
                            self.__selectedOverlayNameChanged)

        self.__widgets.AddGroup(
            'currentFEATSettings',
            displayName=strings.labels[self, 'currentFEATSettings'].format(
                display.name))

        full    = props.makeWidget(     self.__widgets, ts, 'plotFullModelFit')
        res     = props.makeWidget(     self.__widgets, ts, 'plotResiduals')
        evs     = props.makeListWidgets(self.__widgets, ts, 'plotEVs')
        pes     = props.makeListWidgets(self.__widgets, ts, 'plotPEFits')
        copes   = props.makeListWidgets(self.__widgets, ts, 'plotCOPEFits')
        reduced = props.makeWidget(     self.__widgets, ts, 'plotReduced')
        data    = props.makeWidget(     self.__widgets, ts, 'plotData') 

        self.__widgets.AddWidget(
            data,
            displayName=strings.properties[ts, 'plotData'],
            groupName='currentFEATSettings') 
        self.__widgets.AddWidget(
            full,
            displayName=strings.properties[ts, 'plotFullModelFit'],
            groupName='currentFEATSettings')
        
        self.__widgets.AddWidget(
            res,
            displayName=strings.properties[ts, 'plotResiduals'],
            groupName='currentFEATSettings')
        
        self.__widgets.AddWidget(
            reduced,
            displayName=strings.properties[ts, 'plotReduced'],
            groupName='currentFEATSettings')

        for i, ev in enumerate(evs):

            evName = 'EV{}'.format(i + 1)
            self.__widgets.AddWidget(
                ev,
                displayName=strings.properties[ts, 'plotEVs'].format(i + 1,
                                                                     evName),
                groupName='currentFEATSettings')
            
        for i, pe in enumerate(pes):
            evName = 'EV{}'.format(i + 1)
            self.__widgets.AddWidget(
                pe,
                displayName=strings.properties[ts, 'plotPEFits'].format(i + 1,
                                                                        evName),
                groupName='currentFEATSettings') 

        copeNames = overlay.contrastNames()
        for i, (cope, name) in enumerate(zip(copes, copeNames)):
            self.__widgets.AddWidget(
                cope,
                displayName=strings.properties[ts, 'plotCOPEFits'].format(
                    i + 1, name),
                groupName='currentFEATSettings') 
