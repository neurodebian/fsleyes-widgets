#!/usr/bin/env python
#
# imagelistpanel.py - A panel which displays a list of images in the image
# list.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""A panel which displays a list of image list in the image list (see
:class:fsl.data.image.ImageList), and allows the user to add/remove
images, and to change their order.
"""

import logging
log = logging.getLogger(__name__)


import wx
import pwidgets.elistbox as elistbox

import fsl.fslview.controlpanel as controlpanel


class ImageListPanel(controlpanel.ControlPanel):
    """A :class:`~fsl.fslview.controls.controlpanel.ControlPanel` which
    contains an :class:`~pwidgets.EditableListBox` displaying the list
    of loaded images.
    
    The list box allows the image order to be changed, and allows images to be
    added and removed from the list.
    """
    
    def __init__(self, parent, imageList, displayCtx):
        """Create and lay out an :class:`ImageListPanel`.

        :param parent:     The :mod:`wx` parent object.
        :param imageList:  A :class:`~fsl.data.image.ImageList` instance.
        :param displayCtx: A
                           :class:`~fsl.fslview.displaycontext.DisplayContext`
                           instance.
        """
        
        controlpanel.ControlPanel.__init__(self, parent, imageList, displayCtx)

        # list box containing the list of images - it 
        # is populated in the _imageListChanged method
        self._listBox = elistbox.EditableListBox(
            self,
            style=(elistbox.ELB_REVERSE    | 
                   elistbox.ELB_TOOLTIP    | 
                   elistbox.ELB_ENABLEABLE |
                   elistbox.ELB_EDITABLE))

        # listeners for when the user does
        # something with the list box
        self._listBox.Bind(elistbox.EVT_ELB_SELECT_EVENT, self._lbSelect)
        self._listBox.Bind(elistbox.EVT_ELB_MOVE_EVENT,   self._lbMove)
        self._listBox.Bind(elistbox.EVT_ELB_REMOVE_EVENT, self._lbRemove)
        self._listBox.Bind(elistbox.EVT_ELB_ADD_EVENT,    self._lbAdd)
        self._listBox.Bind(elistbox.EVT_ELB_ENABLE_EVENT, self._lbEnable)
        self._listBox.Bind(elistbox.EVT_ELB_EDIT_EVENT,   self._lbEdit)

        self._sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self._sizer)

        self._sizer.Add(self._listBox, flag=wx.EXPAND, proportion=1)

        self._imageList.addListener(
            'images',
            self._name,
            self._imageListChanged)

        self._displayCtx.addListener(
            'selectedImage',
            self._name,
            self._selectedImageChanged)

        def onDestroy(ev):
            ev.Skip()

            # This handler gets called when child windows
            # are destroyed (e.g. items in the embedded
            # elistbox), so this check is necessary.
            if ev.GetEventObject() != self: return
            
            self._imageList .removeListener('images',        self._name)
            self._displayCtx.removeListener('selectedImage', self._name)

            # these listeners are added in the
            # _imageListChanged method, below
            for image in self._imageList:
                display = self._displayCtx.getDisplayProperties(image)
                image  .removeListener('name',    self._name)
                display.removeListener('enabled', self._name)

        self.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)

        # This flag is set by the listbox listeners (bound above),
        # and read by the _imageListChanged, to ensure that user
        # actions on the list box do not trigger a list box refresh.
        self._listBoxNeedsUpdate = True

        self._imageListChanged()
        self._selectedImageChanged()

        self.Layout()


    def _selectedImageChanged(self, *a):
        """Called when the
        :attr:`~fsl.fslview.displaycontext.DisplayContext.selectedImage`
        property changes. Updates the selected item in the list box.
        """
        
        if not self._listBoxNeedsUpdate:
            return

        if len(self._imageList) > 0:
            self._listBox.SetSelection(self._displayCtx.selectedImage)

        
    def _imageListChanged(self, *a):
        """Called when the :class:`~fsl.data.image.ImageList.images`
        list changes.

        If the change was due to user action on the
        :class:`~pwidgets.EditableListBox`, this method does nothing.
        Otherwise, this method updates the :class:`~pwidgets.EditableListBox`
        """
        if not self._listBoxNeedsUpdate:
            return

        selection = self._listBox.GetSelection()
        self._listBox.Clear()

        for i in range(len(self._imageList)):

            image   = self._imageList[i]
            display = self._displayCtx.getDisplayProperties(image)
            name    = image.name
            if name is None: name = ''

            self._listBox.Append(name, image, image.imageFile)
            
            if display.enabled: self._listBox.EnableItem( i)
            else:               self._listBox.DisableItem(i)

            def nameChanged(img):
                idx = self._imageList.index(img)
                name = img.name 
                if name is None: name = '' 
                self._listBox.SetString(idx, name)

            def enabledChanged(img):
                display = self._displayCtx.getDisplayProperties(image)
                idx     = self._imageList.index(img)

                if display.enabled: self._listBox.EnableItem( idx)
                else:               self._listBox.DisableItem(idx)

            image.addListener(
                'name',
                self._name,
                lambda c, va, vi, img=image: nameChanged(img),
                overwrite=True)

            display.addListener(
                'enabled',
                self._name,
                lambda c, va, vi, img=image: enabledChanged(img),
                overwrite=True)

        if len(self._imageList) > 0:
            self._listBox.SetSelection(selection)
        
        
    def _lbMove(self, ev):
        """Called when an image name is moved in the
        :class:`~pwidgets.elistbox.EditableListBox`. Reorders the
        :class:`~fsl.data.image.ImageList` to reflect the change.
        """
        self._listBoxNeedsUpdate = False
        self._imageList.move(ev.oldIdx, ev.newIdx)
        self._displayCtx.selectedImage = ev.newIdx
        self._listBoxNeedsUpdate = True

        
    def _lbSelect(self, ev):
        """Called when an image is selected in the
        :class:`~pwidgets.elistbox.EditableListBox`. Sets the
        :attr:`fsl.data.image.ImageList.selectedImage property.
        """
        self._listBoxNeedsUpdate = False
        self._displayCtx.selectedImage = ev.idx
        self._listBoxNeedsUpdate = True

        
    def _lbAdd(self, ev):
        """Called when the 'add' button on the list box is pressed.
        Calls the :meth:`~fsl.data.image.ImageList.addImages` method.
        """

        if self._imageList.addImages():
            self._displayCtx.selectedImage = len(self._imageList) - 1
            
            # Double check that the list box has been updated,
            # as even though the selected image may have changed,
            # the index of that selected image may be the same.
            self._listBox.SetSelection(self._displayCtx.selectedImage)


    def _lbRemove(self, ev):
        """Called when an item is removed from the image listbox.

        Removes the corresponding image from the
        :class:`~fsl.data.image.ImageList`. 
        """
        self._listBoxNeedsUpdate = False
        self._imageList.pop(ev.idx)
        self._listBoxNeedsUpdate = True


    def _lbEnable(self, ev):
        """Called when an item is enabled/disabled on the image list box.

        Toggles the image display enabled property accordingly.
        """

        img             = self._imageList[ev.idx]
        display         = self._displayCtx.getDisplayProperties(img)
        display.enabled = ev.enabled


    def _lbEdit(self, ev):
        """Called when an item label is edited on the image list box.
        Sets the corresponding image name to the new label.
        """
        
        img = self._imageList[ev.idx]
        img.name = ev.label
