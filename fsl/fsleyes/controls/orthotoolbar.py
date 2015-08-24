#!/usr/bin/env python
#
# orthotoolbar.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#


import props

import fsl.fsleyes.toolbar  as fsltoolbar
import fsl.fsleyes.icons    as fslicons
import fsl.fsleyes.tooltips as fsltooltips
import fsl.fsleyes.actions  as actions
import fsl.data.strings     as strings


class OrthoToolBar(fsltoolbar.FSLEyesToolBar):

    
    def __init__(self, parent, overlayList, displayCtx, ortho):

        actionz = {'more' : self.showMoreSettings}
        
        fsltoolbar.FSLEyesToolBar.__init__(
            self, parent, overlayList, displayCtx, 24, actionz)
        
        self.orthoPanel = ortho

        # The toolbar has buttons bound to some actions
        # on the Profile  instance - when the profile
        # changes (between 'view' and 'edit'), the
        # Profile instance changes too, so we need
        # to re-create these action buttons. I'm being
        # lazy and just re-generating the entire toolbar.
        ortho.addListener('profile', self._name, self.__makeTools)

        self.__makeTools()


    def __makeTools(self, *a):
        
        ortho     = self.orthoPanel
        orthoOpts = ortho.getSceneOptions()
        profile   = ortho.getCurrentProfile()

        icons = {
            'screenshot'  : fslicons.findImageFile('camera24'),
            'movieMode'   : fslicons.findImageFile('movie24'),
            'showXCanvas' : fslicons.findImageFile('sagittalSlice24'),
            'showYCanvas' : fslicons.findImageFile('coronalSlice24'),
            'showZCanvas' : fslicons.findImageFile('axialSlice24'),
            'more'        : fslicons.findImageFile('gear24'),

            'resetZoom'    : fslicons.findImageFile('resetZoom24'),
            'centreCursor' : fslicons.findImageFile('centre24'),

            'layout' : {
                'horizontal' : fslicons.findImageFile('horizontalLayout24'),
                'vertical'   : fslicons.findImageFile('verticalLayout24'),
                'grid'       : fslicons.findImageFile('gridLayout24'),
            }
        }

        tooltips = {
            'screenshot'   : fsltooltips.actions[   ortho,     'screenshot'],
            'movieMode'    : fsltooltips.properties[ortho,     'movieMode'],
            'zoom'         : fsltooltips.properties[orthoOpts, 'zoom'],
            'layout'       : fsltooltips.properties[orthoOpts, 'layout'],
            'showXCanvas'  : fsltooltips.properties[orthoOpts, 'showXCanvas'],
            'showYCanvas'  : fsltooltips.properties[orthoOpts, 'showYCanvas'],
            'showZCanvas'  : fsltooltips.properties[orthoOpts, 'showZCanvas'],
            'resetZoom'    : fsltooltips.actions[   profile,   'resetZoom'],
            'centreCursor' : fsltooltips.actions[   profile,   'centreCursor'],
            'more'         : fsltooltips.actions[   self,      'more'],
        }
        
        targets    = {'screenshot'   : ortho,
                      'movieMode'    : ortho,
                      'zoom'         : orthoOpts,
                      'layout'       : orthoOpts,
                      'showXCanvas'  : orthoOpts,
                      'showYCanvas'  : orthoOpts,
                      'showZCanvas'  : orthoOpts,
                      'resetZoom'    : profile,
                      'centreCursor' : profile,
                      'more'         : self}


        toolSpecs = [

            actions.ActionButton('more',
                                 icon=icons['more'],
                                 tooltip=tooltips['more']),
            actions.ActionButton('screenshot',
                                 icon=icons['screenshot'],
                                 tooltip=tooltips['screenshot']),
            props  .Widget(      'showXCanvas',
                                 icon=icons['showXCanvas'],
                                 tooltip=tooltips['showXCanvas']),
            props  .Widget(      'showYCanvas',
                                 icon=icons['showYCanvas'],
                                 tooltip=tooltips['showYCanvas']),
            props  .Widget(      'showZCanvas',
                                 icon=icons['showZCanvas'],
                                 tooltip=tooltips['showZCanvas']),
            props  .Widget(      'layout',
                                 icons=icons['layout'],
                                 tooltip=tooltips['layout']),
            props  .Widget(      'movieMode', 
                                 icon=icons['movieMode'],
                                 tooltip=tooltips['movieMode']), 
            actions.ActionButton('resetZoom',
                                 icon=icons['resetZoom'],
                                 tooltip=tooltips['resetZoom']),
            actions.ActionButton('centreCursor',
                                 icon=icons['centreCursor'],
                                 tooltip=tooltips['centreCursor']),
            
            props.Widget(        'zoom',
                                 spin=False,
                                 showLimits=False,
                                 tooltip=tooltips['zoom']),
        ]

        tools = []
        
        for spec in toolSpecs:
            widget = props.buildGUI(self, targets[spec.key], spec)

            if spec.key == 'zoom':
                widget = self.MakeLabelledTool(
                    widget,
                    strings.properties[targets[spec.key], 'zoom'])
            
            tools.append(widget)

        self.SetTools(tools, destroy=True) 

    
    def showMoreSettings(self, *a):
        import canvassettingspanel
        self.orthoPanel.togglePanel(canvassettingspanel.CanvasSettingsPanel,
                                    self.orthoPanel,
                                    floatPane=True)
