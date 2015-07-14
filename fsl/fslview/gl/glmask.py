#!/usr/bin/env python
#
# glmask.py - OpenGL rendering of a binary mask image.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module defines the :class:`GLMask` class, which provides functionality
for OpenGL rendering of a 3D volume as a binary mask.

When created, a :class:`GLMask` instance assumes that the provided
:class:`.Image` instance has an ``overlayType`` of ``mask``, and that its
associated :class:`.Display` instance contains a :class:`.MaskOpts` instance,
containing mask-specific display properties.

The :class:`GLMask` class uses the functionality of the :class:`.GLVolume`
class through inheritance.
"""

import logging

import numpy                  as np

import fsl.fslview.gl         as fslgl
import fsl.fslview.colourmaps as colourmaps
import                           glvolume


log = logging.getLogger(__name__)


class GLMask(glvolume.GLVolume):
    """The :class:`GLMask` class encapsulates logic to render 2D slices of a
    :class:`.Image` instance as a binary mask in OpenGL.

    ``GLMask`` is a subclass of the :class:`.GLVolume class. It overrides a
    few key methods of ``GLVolume``, but most of the logic is provided by
    ``GLVolume``.
    """


    def addDisplayListeners(self):
        """Overrides :meth:`.GLVolume.addDisplayListeners`.

        Adds a bunch of listeners to the :class:`.Display` object, and the
        associated :class:`.MaskOpts` instance, which define how the mask
        image should be displayed.
        """

        display = self.display
        opts    = self.displayOpts
        name    = self.name
        
        def shaderUpdate(*a):
            fslgl.glvolume_funcs.updateShaderState(self)
            self.onUpdate() 
            
        def colourUpdate(*a):
            self.refreshColourTexture()
            fslgl.glvolume_funcs.updateShaderState(self)
            self.onUpdate()

        def imageRefresh(*a):
            self.refreshImageTexture()
            fslgl.glvolume_funcs.updateShaderState(self)
            self.onUpdate()

        def imageUpdate(*a):
            volume     = opts.volume
            resolution = opts.resolution

            self.imageTexture.set(volume=volume, resolution=resolution)
            
            fslgl.glvolume_funcs.updateShaderState(self) 
            self.onUpdate()

        display.addListener('softwareMode',  name, shaderUpdate, weak=False)
        display.addListener('alpha',         name, colourUpdate, weak=False)
        display.addListener('brightness',    name, colourUpdate, weak=False)
        display.addListener('contrast',      name, colourUpdate, weak=False)
        opts   .addListener('colour',        name, colourUpdate, weak=False)
        opts   .addListener('threshold',     name, colourUpdate, weak=False)
        opts   .addListener('invert',        name, colourUpdate, weak=False)
        opts   .addListener('volume',        name, imageUpdate,  weak=False)
        opts   .addListener('resolution',    name, imageUpdate,  weak=False)
        
        opts.addSyncChangeListener(
            'volume',     name, imageRefresh, weak=False)
        opts.addSyncChangeListener(
            'resolution', name, imageRefresh, weak=False)


    def removeDisplayListeners(self):
        """Overrides :meth:`.GLVolume.removeDisplayListeners`.

        Removes all the listeners added by :meth:`addDisplayListeners`.
        """

        display = self.display
        opts    = self.displayOpts
        name    = self.name
        
        display.removeListener(          'softwareMode',  name)
        display.removeListener(          'alpha',         name)
        display.removeListener(          'brightness',    name)
        display.removeListener(          'contrast',      name)
        opts   .removeListener(          'colour',        name)
        opts   .removeListener(          'threshold',     name)
        opts   .removeListener(          'invert',        name)
        opts   .removeListener(          'volume',        name)
        opts   .removeListener(          'resolution',    name)
        opts   .removeSyncChangeListener('volume',        name)
        opts   .removeSyncChangeListener('resolution',    name)


    def testUnsynced(self):
        """Overrides :meth:`.GLVolume.testUnsynced`.
        """
        return (not self.displayOpts.isSyncedToParent('volume') or
                not self.displayOpts.isSyncedToParent('resolution'))

        
    def refreshColourTexture(self, *a):
        """Overrides :meth:`.GLVolume.refreshColourTexture`.

        Creates a colour texture which contains the current mask colour, and a
        transformation matrix which maps from the current
        :attr:`.MaskOpts.threshold` range to the texture range, so that voxels
        within this range are coloured, and voxels outside the range are
        transparent (or vice versa, if the :attr:`.MaskOpts.invert` flag is
        set).
        """

        display = self.display
        opts    = self.displayOpts
        alpha   = display.alpha / 100.0
        colour  = opts.colour
        dmin    = opts.threshold[0]
        dmax    = opts.threshold[1]
        
        colour[3] = 1.0
        colour = colourmaps.applyBricon(colour,
                                        display.brightness / 100.0,
                                        display.contrast   / 100.0)

        if opts.invert:
            cmap   = np.tile([0.0, 0.0, 0.0, 0.0], (4, 1))
            border = np.array(opts.colour, dtype=np.float32)
        else:
            cmap   = np.tile([opts.colour],        (4, 1))
            border = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            
        self.colourTexture.set(cmap=cmap,
                               border=border,
                               displayRange=(dmin, dmax),
                               alpha=alpha)
