#!/usr/bin/env python
#
# viewpanel.py - Superclass for all FSLView view panels.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module provides the :class:`ViewPanel` class, which is the superclass
of all of the 'view' panels available in FSLView - see
:class:`~fsl.fslview.frame.FSLViewFrame`.
"""

import logging

import                   wx
import wx.lib.agw.aui as aui

import props

import fsl.fslview.panel    as fslpanel
import fsl.fslview.toolbar  as fsltoolbar
import fsl.fslview.profiles as profiles
import fsl.data.image       as fslimage
import fsl.data.strings     as strings


log = logging.getLogger(__name__)


#
# Here I am monkey patching the wx.agw.aui.framemanager.AuiFloatingFrame
# __init__ method.
#
# I am doing this because I have observed some strange behaviour when running
# a remote instance of this application over an SSH/X11 session, with the X11
# server (i.e. the local machine) running in OS X. When a combobox is embedded
# in a floating frame (either a pane or a toolbar), its dropdown list appears
# underneath the frame, meaning that the user is unable to actually select any
# items from the list!
#
# I have only seen this behaviour when using XQuartz 2.7.6, running under OSX
# 10.9 Mavericks.
#
# Ultimately, this appears to be caused by the wx.FRAME_TOOL_WINDOW style, as
# passed to the wx.MiniFrame constructor (from which the AuiFloatingFrame
# class derives). Removing this style flag fixes the problem, so this is
# exactly what I'm doing. I haven't looked any deeper into the situation.
#


# Store a reference to the real constructor.
AuiFloatingFrame__real__init__ = aui.AuiFloatingFrame.__init__


# My new constructor, which makes sure that
# the FRAME_TOOL_WINDOW style is not passed
# through to the AuiFloatingFrame constructor
def AuiFloatingFrame__init__(*args, **kwargs):

    if 'style' in kwargs:
        style = kwargs['style']

    # This is the default style, as defined 
    # in the AuiFloatingFrame constructor
    else:
        style = (wx.FRAME_TOOL_WINDOW     |
                 wx.FRAME_FLOAT_ON_PARENT |
                 wx.FRAME_NO_TASKBAR      |
                 wx.CLIP_CHILDREN)

    style &= ~wx.FRAME_TOOL_WINDOW

    kwargs['style'] = style
    
    return AuiFloatingFrame__real__init__(*args, **kwargs)

# Patch my constructor in
# to the class definition
aui.AuiFloatingFrame.__init__ = AuiFloatingFrame__init__


class ViewPanel(fslpanel.FSLViewPanel):

    profile = props.Choice()
    
    def __init__(self, parent, overlayList, displayCtx, actionz=None):

        fslpanel.FSLViewPanel.__init__(
            self, parent, overlayList, displayCtx, actionz)

        self.__profileManager = profiles.ProfileManager(
            self, overlayList, displayCtx)

        self.__panels = {}

        self.__auiMgr = aui.AuiManager(self,
                                       agwFlags=(aui.AUI_MGR_ALLOW_FLOATING |
                                                 aui.AUI_MGR_LIVE_RESIZE))        
        self.__auiMgr.Bind(aui.EVT_AUI_PANE_CLOSE, self.__onPaneClose)

        # Use a different listener name so that subclasses
        # can register on the same properties with self._name 
        lName = 'ViewPanel_{}'.format(self._name)
        
        self.addListener('profile', lName, self.__profileChanged)
        
        overlayList.addListener('overlays',
                                lName,
                                self.__selectedOverlayChanged)
        displayCtx .addListener('selectedOverlay',
                                lName,
                                self.__selectedOverlayChanged)

        self.__selectedOverlayChanged()

        # A very shitty necessity. When panes are floated,
        # the AuiManager sets the size of the floating frame
        # to the minimum size of the panel, without taking
        # into account the size of its borders/title bar,
        # meaning that the panel size is too small. Here,
        # we're just creating a dummy MiniFrame (from which
        # the AuiFloatingFrame derives), and saving the size
        # of its trimmings for later use in the togglePanel
        # method.
        ff         = wx.MiniFrame(self)

        # total size of frame
        size       = ff.GetSize().Get()

        # size of frame, sans trimmings
        clientSize = ff.GetClientSize().Get()
        
        ff.Destroy()

        self.__floatOffset = (size[0] - clientSize[0],
                              size[1] - clientSize[1])

        
    def destroy(self):
        """
        """
        
        # Make sure that any control panels are correctly destroyed
        for panelType, panel in self.__panels.items():
            panel.destroy()

        # Remove listeners from the overlay
        # list and display context
        lName = 'ViewPanel_{}'.format(self._name)

        self             .removeListener('profile',         lName)
        self._overlayList.removeListener('overlays',        lName)
        self._displayCtx .removeListener('selectedOverlay', lName)

        # Disable the  ProfileManager
        self.__profileManager.destroy()

        # Un-initialise the AUI manager
        self.__auiMgr.UnInit()

        # The AUI manager does not clear its
        # reference to this panel, so let's
        # do it here.
        self.__auiMgr._frame  = None
        self.__profileManager = None
        self.__auiMgr         = None
        self.__panels         = None

        fslpanel.FSLViewPanel.destroy(self)
        


    def setCentrePanel(self, panel):
        panel.Reparent(self)
        self.__auiMgr.AddPane(panel, wx.CENTRE)
        self.__auiMgrUpdate()


    def togglePanel(self, panelType, floatPane=False, *args, **kwargs):

        import fsl.fslview.layouts as layouts

        window = self.__panels.get(panelType, None)

        if window is not None:
            self.__onPaneClose(None, window)
            
        else:
            
            window   = panelType(
                self, self._overlayList, self._displayCtx, *args, **kwargs)

            paneInfo = aui.AuiPaneInfo()

            if isinstance(window, fsltoolbar.FSLViewToolBar):
                paneInfo.ToolbarPane()

                # We are going to put any new toolbars on 
                # the top of the panel, below any existing
                # toolbars. This is annoyingly complicated,
                # because the AUI designer(s) decided to
                # give the innermost layer an index of 0.
                # 
                # So in order to put a new toolbar at the
                # innermost layer, we need to adjust the
                # layers of all other existing toolbars
                
                for p in self.__panels.values():
                    if isinstance(p, fsltoolbar.FSLViewToolBar):
                        info = self.__auiMgr.GetPane(p)

                        # This is nasty - the agw.aui.AuiPaneInfo
                        # class doesn't have any publicly documented
                        # methods of querying its current state.
                        # So I'm accessing its undocumented instance
                        # attributes (determined by browsing the
                        # source code)
                        if info.IsDocked() and \
                           info.dock_direction == aui.AUI_DOCK_TOP:
                            info.Layer(info.dock_layer + 1)

                paneInfo.Layer(0)

                # When the toolbar contents change,
                # update the layout, so that the
                # toolbar's new size is accommodated
                window.Bind(fsltoolbar.EVT_TOOLBAR_EVENT, self.__auiMgrUpdate)

            paneInfo.LeftDockable( False) \
                    .RightDockable(False) \
                    .Caption(strings.titles[window])                

            # Dock the pane at the position specified
            # in fsl.fslview.layouts.locations, or
            # at the top of the panel if there is no
            # location specified 
            if floatPane is False:

                paneInfo.Direction(
                    layouts.locations.get(window, aui.AUI_DOCK_TOP))

            # Or, for floating panes, centre the
            # floating pane on this ViewPanel 
            else:

                selfPos    = self.GetScreenPosition().Get()
                selfSize   = self.GetSize().Get()
                selfCentre = (selfPos[0] + selfSize[0] * 0.5,
                              selfPos[1] + selfSize[1] * 0.5)

                paneSize = window.GetBestSize().Get()
                panePos  = (selfCentre[0] - paneSize[0] * 0.5,
                            selfCentre[1] - paneSize[1] * 0.5)

                paneInfo.Float() \
                        .FloatingPosition(panePos)
                    
            self.__auiMgr.AddPane(window, paneInfo)
            self.__panels[panelType] = window
            self.__auiMgrUpdate()


    def getPanel(self, panelType):
        """If an instance of ``panelType`` exists, it is returned.
        Otherwise ``None`` is returned.
        """
        if panelType in self.__panels: return self.__panels[panelType]
        else:                          return None
 

    def __selectedOverlayChanged(self, *a):
        """Called when the overlay list or selected overlay changed.

        This method is slightly hard-coded and hacky. For the time being, edit
        profiles are only going to be supported for ``volume`` image
        types, which are being displayed in ``id`` or ``pixdim`` space..
        This method checks the type of the selected overlay, and disables
        the ``edit`` profile option (if it is an option), so the user can
        only choose an ``edit`` profile on ``volume`` image types.
        """
        overlay = self._displayCtx.getSelectedOverlay()

        if overlay is None:
            return

        display     = self._displayCtx.getDisplay(overlay)
        opts        = display.getDisplayOpts()
        profileProp = self.getProp('profile')

        # edit profile is not an option -
        # nothing to be done
        if 'edit' not in profileProp.getChoices(self):
            return

        if not isinstance(overlay, fslimage.Image) or \
           display.overlayType != 'volume'         or \
           opts.transform not in ('id', 'pixdim'):
            
            # change profile if needed,
            if self.profile == 'edit':
                self.profile = 'view'

            # and disable edit profile
            profileProp.disableChoice('edit', self)
            
        # Otherwise make sure edit
        # is enabled for volume images
        else:
            profileProp.enableChoice('edit', self)


    def initProfile(self):
        """Must be called by subclasses, after they have initialised all
        of the attributes which may be needed by their corresponding
        Profile instances. 
        """
        self.__profileChanged()


    def getCurrentProfile(self):
        return self.__profileManager.getCurrentProfile()

        
    def __profileChanged(self, *a):
        """Called when the current :attr:`profile` property changes. Tells
        the :class:`~fsl.fslview.profiles.ProfileManager` about the change.

        The ``ProfileManager`` will then update mouse/keyboard listeners
        according to the new profile.
        """

        self.__profileManager.changeProfile(self.profile)

    
    def __auiMgrUpdate(self, *a):
        """Calls the :meth:`~wx.lib.agw.aui.AuiManager.Update` method
        on the ``AuiManager`` instance that is managing this panel.

        Ensures that the position of any floating panels is preserved,
        as the ``AuiManager`` tends to move them about in some
        circumstances.
        """

        # When a panel is added/removed from the AuiManager,
        # the position of floating panels seems to get reset
        # to their original position, when they were created.
        # Here, we explicitly set the position of each
        # floating frame, so the AuiManager doesn't move our
        # windows about the place.
        # 
        # We also explicitly tell the AuiManager what the
        # current minimum and best sizes are for every panel
        for panel in self.__panels.values():
            paneInfo = self.__auiMgr.GetPane(panel)
            parent   = panel.GetParent()
            minSize  = panel.GetMinSize().Get()

            # If the panel is floating, use its
            # current size as its 'best' size,
            # as otherwise it will immediately
            # resize the panel to its best size
            if paneInfo.IsFloating():
                bestSize = panel.GetSize().Get()

                # Unless it's current size is less
                # than its minimum size (which probably
                # means that it has just been added)
                if bestSize[0] < minSize[0] or \
                   bestSize[1] < minSize[1]:
                    bestSize = panel.GetBestSize().Get()
                    
            else:
                bestSize = panel.GetBestSize().Get()

            # See comments in __init__ about
            # this 'float offset' thing 
            floatSize = (bestSize[0] + self.__floatOffset[0],
                         bestSize[1] + self.__floatOffset[1])

            log.debug('New size for panel {} - min: {}, '
                      'best: {}, float: {}'.format(
                          type(panel).__name__, minSize, bestSize, floatSize))
            
            paneInfo.MinSize(     minSize)  \
                    .BestSize(    bestSize) \
                    .FloatingSize(floatSize)

            # Re-position floating panes, otherwise
            # the AuiManager will reset their position
            if paneInfo.IsFloating() and \
               isinstance(parent, aui.AuiFloatingFrame):
                paneInfo.FloatingPosition(parent.GetScreenPosition())

        self.__auiMgr.Update()

        
    def __onPaneClose(self, ev=None, panel=None):

        if ev is not None:
            ev.Skip()
            panel = ev.GetPane().window

        log.debug('Panel closed: {}'.format(type(panel).__name__))
        
        if isinstance(panel, (fslpanel  .FSLViewPanel,
                              fsltoolbar.FSLViewToolBar)):
            self.__panels.pop(type(panel))

            # calling fslpanel.FSLViewPanel.destroy()
            # here -  wx.Destroy is done below
            panel.destroy()

            # Even when the user closes a pane,
            # AUI does not detach said pane -
            # we have to do it manually
            self.__auiMgr.DetachPane(panel)
            self.__auiMgrUpdate()

        # WTF AUI. Sometimes this method gets called
        # twice for a panel, the second time with a
        # reference to a wx._wxpyDeadObject; in such
        # situations, the Destroy method call below
        # will result in an exception being raised.
        else:
            return
        
        panel.Destroy()
