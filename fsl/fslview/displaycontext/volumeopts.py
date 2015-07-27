#!/usr/bin/env python
#
# volumeopts.py - Defines the VolumeOpts class.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module defines the :class:`VolumeOpts` class, which contains
display options for rendering :class:`.GLVolume` instances.
"""

import logging

import numpy as np

import props

import fsl.data.strings       as strings
import fsl.utils.transform    as transform
import fsl.fslview.colourmaps as fslcm

import display as fsldisplay


log = logging.getLogger(__name__)


class ImageOpts(fsldisplay.DisplayOpts):
    """A class which describes how an :class:`.Image` should be displayed. 
    """

    
    volume = props.Int(minval=0, maxval=0, default=0, clamped=True)
    """If the data is 4D , the current volume to display."""    

    
    resolution = props.Real(maxval=10, default=1, clamped=True)
    """Data resolution in world space. The minimum value is set in __init__.""" 


    transform = props.Choice(
        ('affine', 'pixdim', 'id'),
        labels=[strings.choices['ImageOpts.transform.affine'],
                strings.choices['ImageOpts.transform.pixdim'],
                strings.choices['ImageOpts.transform.id']],
        default='pixdim')
    """This property defines how the overlay should be transformd into the display
    coordinate system.
    
      - ``affine``: Use the affine transformation matrix stored in the image
        (the ``qform``/``sform`` fields in NIFTI1 headers).
                    
      - ``pixdim``: Scale voxel sizes by the ``pixdim`` fields in the image
        header.
    
      - ``id``: Perform no scaling or transformation - voxels will be
        interpreted as :math:`1mm^3` isotropic, with the origin at voxel
        (0,0,0).
    """

 
    def __init__(self, *args, **kwargs):

        # The transform property cannot be unsynced
        # across different displays, as it affects
        # the display context bounds, wich also
        # cannot be unsynced
        nounbind = kwargs.get('nounbind', [])
        nounbind.append('transform')

        kwargs['nounbind'] = nounbind

        fsldisplay.DisplayOpts.__init__(self, *args, **kwargs)

        overlay = self.overlay

        self.addListener('transform', self.name, self.__transformChanged)

        # The display<->* transformation matrices
        # are created in the _setupTransforms method
        self.__xforms = {}
        self.__setupTransforms()
        self.__transformChanged()
 
        # is this a 4D volume?
        if self.overlay.is4DImage():
            self.setConstraint('volume', 'maxval', overlay.shape[3] - 1)

        # limit resolution to the image dimensions
        self.resolution = min(overlay.pixdim[:3])
        self.setConstraint('resolution', 'minval', self.resolution)


    def destroy(self):
        fsldisplay.DisplayOpts.destroy(self)

        
    def __transformChanged(self, *a):
        """Calculates the min/max values of a 3D bounding box, in the display
        coordinate system, which is big enough to contain the image. Sets the
        :attr:`.DisplayOpts.bounds` property accordingly.
        """

        lo, hi = transform.axisBounds(
            self.overlay.shape[:3], self.getTransform('voxel', 'display'))
        
        self.bounds[:] = [lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]]

                            
    def __setupTransforms(self):
        """Calculates transformation matrices between all of the possible
        spaces in which the overlay may be displayed.

        These matrices are accessible via the :meth:`getTransform` method.
        """

        image          = self.overlay

        voxToIdMat     = np.eye(4)
        voxToPixdimMat = np.diag(list(image.pixdim[:3]) + [1.0])
        voxToAffineMat = image.voxToWorldMat.T
        
        idToVoxMat        = transform.invert(voxToIdMat)
        idToPixdimMat     = transform.concat(idToVoxMat, voxToPixdimMat)
        idToAffineMat     = transform.concat(idToVoxMat, voxToAffineMat)

        pixdimToVoxMat    = transform.invert(voxToPixdimMat)
        pixdimToIdMat     = transform.concat(pixdimToVoxMat, voxToIdMat)
        pixdimToAffineMat = transform.concat(pixdimToVoxMat, voxToAffineMat)

        affineToVoxMat    = image.worldToVoxMat.T
        affineToIdMat     = transform.concat(affineToVoxMat, voxToIdMat)
        affineToPixdimMat = transform.concat(affineToVoxMat, voxToPixdimMat)
        
        self.__xforms['id',  'id']     = np.eye(4)
        self.__xforms['id',  'pixdim'] = idToPixdimMat 
        self.__xforms['id',  'affine'] = idToAffineMat

        self.__xforms['pixdim', 'pixdim'] = np.eye(4)
        self.__xforms['pixdim', 'id']     = pixdimToIdMat
        self.__xforms['pixdim', 'affine'] = pixdimToAffineMat
 
        self.__xforms['affine', 'affine'] = np.eye(4)
        self.__xforms['affine', 'id']     = affineToIdMat
        self.__xforms['affine', 'pixdim'] = affineToPixdimMat 


    def getTransform(self, from_, to, xform=None):
        """Return a matrix which may be used to transform coordinates
        from ``from_`` to ``to``. Valid values for ``from_`` and ``to``
        are:
          - ``id``:      Voxel coordinates
        
          - ``pixdim``:  Voxel coordinates, scaled by voxel dimensions
        
          - ``affine``:  World coordinates, as defined by the NIFTI1
                         ``qform``/``sform``. See
                         :attr:`~fsl.data.image.Image.voxToWorldMat`.
        
          - ``voxel``:   Equivalent to ``id``.
        
          - ``display``: Equivalent to the current value of :attr:`transform`.
        
          - ``world``;   Equivalent to ``affine``.

        If the ``xform`` parameter is provided, and one of ``from_`` or ``to``
        is ``display``, the value of ``xform`` is used instead of the current
        value of :attr:`transform`.
        """

        if xform is None:
            xform = self.transform

        if   from_ == 'display': from_ = xform
        elif from_ == 'world':   from_ = 'affine'
        elif from_ == 'voxel':   from_ = 'id'
        
        if   to    == 'display': to    = xform
        elif to    == 'world':   to    = 'affine'
        elif to    == 'voxel':   to    = 'id'

        return self.__xforms[from_, to]


    def transformDisplayLocation(self, oldLoc):

        lastVal = self.getLastValue('transform')

        if lastVal is None:
            lastVal = self.transform
        
        # Calculate the image world location using the
        # old display<-> world transform, then transform
        # it back to the new world->display transform. 
        worldLoc = transform.transform(
            [oldLoc],
            self.getTransform(lastVal, 'world'))[0]
        
        newLoc  = transform.transform(
            [worldLoc],
            self.getTransform('world', 'display'))[0]
        
        return newLoc


class VolumeOpts(ImageOpts):
    """A class which describes how an :class:`.Image` should be displayed.

    This class doesn't have much functionality - it is up to things which
    actually display an :class:`.Image` to adhere to the properties stored in
    the associated :class:`.Display` and :class:`VolumeOpts` object.
    """

    
    displayRange = props.Bounds(
        ndims=1,
        labels=[strings.choices['VolumeOpts.displayRange.min'],
                strings.choices['VolumeOpts.displayRange.max']])
    """Image values which map to the minimum and maximum colour map colours."""

    
    clippingRange = props.Bounds(
        ndims=1,
        labels=[strings.choices['VolumeOpts.displayRange.min'],
                strings.choices['VolumeOpts.displayRange.max']])
    """Values outside of this range are not shown."""

    
    invertClipping = props.Boolean(default=False)
    """If ``True``, the behaviour of ``clippingRange`` is inverted, i.e.
    values inside the clipping range are clipped, instead of those outside
    the clipping range.
    """

    
    cmap = props.ColourMap(default=fslcm.getColourMaps()[0],
                           cmapNames=fslcm.getColourMaps())
    """The colour map, a :class:`matplotlib.colors.Colourmap` instance."""

    
    interpolation = props.Choice(
        ('none', 'linear', 'spline'),
        labels=[strings.choices['VolumeOpts.interpolation.none'],
                strings.choices['VolumeOpts.interpolation.linear'],
                strings.choices['VolumeOpts.interpolation.spline']])
    """How the value shown at a real world location is derived from the
    corresponding data value(s). 'No interpolation' is equivalent to nearest
    neighbour interpolation.
    """


    invert = props.Boolean(default=False)
    """Invert the colour map."""


    def __init__(self,
                 overlay,
                 display,
                 overlayList,
                 displayCtx,
                 parent=None,
                 **kwargs):
        """Create a :class:`VolumeOpts` instance for the specified image."""

        # Attributes controlling image display. Only
        # determine the real min/max for small images -
        # if it's memory mapped, we have no idea how big
        # it may be! So we calculate the min/max of a
        # sample (either a slice or an image, depending
        # on whether the image is 3D or 4D)
        if np.prod(overlay.shape) > 2 ** 30:
            sample = overlay.data[..., overlay.shape[-1] / 2]
            self.dataMin = float(sample.min())
            self.dataMax = float(sample.max())
        else:
            self.dataMin = float(overlay.data.min())
            self.dataMax = float(overlay.data.max())

        dRangeLen    = abs(self.dataMax - self.dataMin)
        dMinDistance = dRangeLen / 10000.0

        self.clippingRange.xmin = self.dataMin - dMinDistance
        self.clippingRange.xmax = self.dataMax + dMinDistance
        
        # By default, the lowest values
        # in the image are clipped
        self.clippingRange.xlo  = self.dataMin + dMinDistance
        self.clippingRange.xhi  = self.dataMax + dMinDistance

        self.displayRange.xlo  = self.dataMin
        self.displayRange.xhi  = self.dataMax

        # The Display.contrast property expands/contracts
        # the display range, by a scaling factor up to
        # approximately 10.
        self.displayRange.xmin = self.dataMin - 10 * dRangeLen
        self.displayRange.xmax = self.dataMax + 10 * dRangeLen
        
        self.setConstraint('displayRange', 'minDistance', dMinDistance)

        ImageOpts.__init__(self,
                           overlay,
                           display,
                           overlayList,
                           displayCtx,
                           parent,
                           **kwargs)

        # The displayRange property of every child VolumeOpts
        # instance is linked to the corresponding 
        # Display.brightness/contrast properties, so changes
        # in one are reflected in the other.
        if parent is not None:
            display.addListener('brightness', self.name, self.__briconChanged)
            display.addListener('contrast',   self.name, self.__briconChanged)
            self   .addListener('displayRange',
                                self.name,
                                self.__displayRangeChanged)

            # Because displayRange and bri/con are intrinsically
            # linked, it makes no sense to let the user sync/unsync
            # them independently. So here we are binding the boolean
            # sync properties which control whether the dRange/bricon
            # properties are synced with their parent. So when one
            # property is synced/unsynced, the other ones are too.
            self.bindProps(self   .getSyncPropertyName('displayRange'),
                           display,
                           display.getSyncPropertyName('brightness'))
            self.bindProps(self   .getSyncPropertyName('displayRange'), 
                           display,
                           display.getSyncPropertyName('contrast'))


    def destroy(self):

        if self.getParent() is not None:
            display = self.display
            display.removeListener('brightness',   self.name)
            display.removeListener('contrast',     self.name)
            self   .removeListener('displayRange', self.name)
            self.unbindProps(self   .getSyncPropertyName('displayRange'),
                             display,
                             display.getSyncPropertyName('brightness'))
            self.unbindProps(self   .getSyncPropertyName('displayRange'), 
                             display,
                             display.getSyncPropertyName('contrast'))

        ImageOpts.destroy(self)


    def __toggleListeners(self, enable=True):
        """This method enables/disables the property listeners which
        are registered on the :attr:`displayRange` and
        :attr:`.Display.brightness`/:attr:`.Display.contrast`/ properties.
        
        Because these properties are linked via the
        :meth:`__displayRangeChanged` and :meth:`__briconChanged` methods,
        we need to be careful about avoiding recursive callbacks.

        Furthermore, because the properties of both :class:`VolumeOpts` and
        :class:`.Display` instances are possibly synchronised to a parent
        instance (which in turn is synchronised to other children), we need to
        make sure that the property listeners on these other sibling instances
        are not called when our own property values change. So this method
        disables/enables the property listeners on all sibling ``VolumeOpts``
        and ``Display`` instances.
        """

        parent = self.getParent()

        # this is the parent instance
        if parent is None:
            return

        # The parent.getChildren() method will
        # contain this VolumeOpts instance,
        # so the below loop toggles listeners
        # for this instance, the parent instance,
        # and all of the other children of the
        # parent
        peers  = [parent] + parent.getChildren()

        for peer in peers:

            if enable:
                peer.display.enableListener('brightness',   peer.name)
                peer.display.enableListener('contrast',     peer.name)
                peer        .enableListener('displayRange', peer.name)
            else:
                peer.display.disableListener('brightness',   peer.name)
                peer.display.disableListener('contrast',     peer.name)
                peer        .disableListener('displayRange', peer.name) 
                

    def __briconChanged(self, *a):
        """Called when the ``brightness``/``contrast`` properties of the
        :class:`.Display` instance change.
        
        Updates the :attr:`displayRange` property accordingly.

        See :func:`.colourmaps.briconToDisplayRange`.
        """

        dlo, dhi = fslcm.briconToDisplayRange(
            (self.dataMin, self.dataMax),
            self.display.brightness / 100.0,
            self.display.contrast   / 100.0)

        self.__toggleListeners(False)
        self.displayRange.x = [dlo, dhi]
        self.__toggleListeners(True)

        
    def __displayRangeChanged(self, *a):
        """Called when the `attr`:displayRange: property changes.

        Updates the :attr:`.Display.brightness` and :attr:`.Display.contrast`
        properties accordingly.

        See :func:`.colourmaps.displayRangeToBricon`.
        """

        brightness, contrast = fslcm.displayRangeToBricon(
            (self.dataMin, self.dataMax),
            self.displayRange.x)
        
        self.__toggleListeners(False)

        # update bricon
        self.display.brightness = brightness * 100
        self.display.contrast   = contrast   * 100

        self.__toggleListeners(True)
