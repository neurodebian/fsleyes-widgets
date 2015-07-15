#!/usr/bin/env python
#
# slicecanvas.py - Provides the SliceCanvas class, which contains the
# functionality to display a single slice from a collection of 3D overlays.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""Provides the :class:`SliceCanvas` class, which contains the functionality
to display a single slice from a collection of 3D overlays.

The :class:`SliceCanvas` class is not intended to be instantiated - use one
of the subclasses:

  - :class:`.OSMesaSliceCanvas` for static off-screen rendering of a scene.
    
  - :class:`.WXGLSliceCanvas` for interactive rendering on a
    :class:`wx.glcanvas.GLCanvas` canvas.

See also the :class:`.LightBoxCanvas` class.
"""

import logging
log = logging.getLogger(__name__)

import numpy                  as np 
import OpenGL.GL              as gl

import props

import fsl.data.image             as fslimage
import fsl.fslview.gl.routines    as glroutines
import fsl.fslview.gl.resources   as glresources
import fsl.fslview.gl.globject    as globject
import fsl.fslview.gl.textures    as textures
import fsl.fslview.gl.annotations as annotations


class SliceCanvas(props.HasProperties):
    """Represens a canvas which may be used to display a single 2D slice from a
    collection of 3D overlays.
    """

    
    pos = props.Point(ndims=3)
    """The currently displayed position. The ``pos.x`` and ``pos.y`` positions
    denote the position of a 'cursor', which is highlighted with green
    crosshairs. The ``pos.z`` position specifies the currently displayed
    slice. While the values of this point are in the display coordinate
    system, the dimension ordering may not be the same as the display
    coordinate dimension ordering. For this position, the x and y dimensions
    correspond to horizontal and vertical on the screen, and the z dimension
    to 'depth'.
    """

    
    zoom = props.Percentage(minval=100.0,
                            maxval=1000.0,
                            default=100.0,
                            clamped=True)
    """The :attr:`.DisplayContext.bounds` are divided by this zoom
    factor to produce the canvas display bounds.
    """

    
    displayBounds = props.Bounds(ndims=2)
    """The display bound x/y values specify the horizontal/vertical display
    range of the canvas, in display coordinates. This may be a larger area
    than the size of the displayed overlays, as it is adjusted to preserve
    the aspect ratio.
    """

    
    showCursor = props.Boolean(default=True)
    """If ``False``, the green crosshairs which show
    the current cursor location will not be drawn.
    """
 

    zax = props.Choice((0, 1, 2), ('X axis', 'Y axis', 'Z axis'))
    """The display coordinate system axis to be used as the screen 'depth'
    axis.
    """

    
    invertX = props.Boolean(default=False)
    """If True, the display is inverted along the X (horizontal screen) axis.
    """

    
    invertY = props.Boolean(default=False)
    """If True, the display is inverted along the Y (vertical screen) axis.
    """

    
    renderMode = props.Choice(('onscreen', 'offscreen', 'prerender'))
    """How the GLObjects are rendered to the canvas - onscreen is the
    default, but the other options will give better performance on
    slower platforms.
    """
    
    
    softwareMode = props.Boolean(default=False)
    """If ``True``, the :attr:`.Display.softwareMode` property for every
    displayed image is set to ``True``.
    """

    
    resolutionLimit = props.Real(default=0, minval=0, maxval=5, clamped=True)
    """The minimum resolution at which overlays should be drawn."""


    def calcPixelDims(self):
        """Calculate and return the approximate size (width, height) of one
        pixel in display space.
        """
        
        xmin, xmax = self.displayCtx.bounds.getRange(self.xax)
        ymin, ymax = self.displayCtx.bounds.getRange(self.yax)
        
        w, h = self._getSize()
        pixx = (xmax - xmin) / float(w)
        pixy = (ymax - ymin) / float(h) 

        return pixx, pixy

    
    def canvasToWorld(self, xpos, ypos):
        """Given pixel x/y coordinates on this canvas, translates them
        into xyz display coordinates.
        """

        realWidth                 = self.displayBounds.xlen
        realHeight                = self.displayBounds.ylen
        canvasWidth, canvasHeight = map(float, self._getSize())
            
        if self.invertX: xpos = canvasWidth  - xpos
        if self.invertY: ypos = canvasHeight - ypos

        if realWidth    == 0 or \
           canvasWidth  == 0 or \
           realHeight   == 0 or \
           canvasHeight == 0:
            return None
        
        xpos = self.displayBounds.xlo + (xpos / canvasWidth)  * realWidth
        ypos = self.displayBounds.ylo + (ypos / canvasHeight) * realHeight

        pos = [None] * 3
        pos[self.xax] = xpos
        pos[self.yax] = ypos
        pos[self.zax] = self.pos.z

        return pos


    def panDisplayBy(self, xoff, yoff):
        """Pans the canvas display by the given x/y offsets (specified in
        display coordinates).
        """

        if len(self.overlayList) == 0: return
        
        dispBounds = self.displayBounds
        ovlBounds  = self.displayCtx.bounds

        xmin, xmax, ymin, ymax = self.displayBounds[:]

        xmin = xmin + xoff
        xmax = xmax + xoff
        ymin = ymin + yoff
        ymax = ymax + yoff

        if dispBounds.xlen > ovlBounds.getLen(self.xax):
            xmin = dispBounds.xlo
            xmax = dispBounds.xhi
            
        elif xmin < ovlBounds.getLo(self.xax):
            xmin = ovlBounds.getLo(self.xax)
            xmax = xmin + self.displayBounds.getLen(0)
            
        elif xmax > ovlBounds.getHi(self.xax):
            xmax = ovlBounds.getHi(self.xax)
            xmin = xmax - self.displayBounds.getLen(0)
            
        if dispBounds.ylen > ovlBounds.getLen(self.yax):
            ymin = dispBounds.ylo
            ymax = dispBounds.yhi
            
        elif ymin < ovlBounds.getLo(self.yax):
            ymin = ovlBounds.getLo(self.yax)
            ymax = ymin + self.displayBounds.getLen(1)

        elif ymax > ovlBounds.getHi(self.yax):
            ymax = ovlBounds.getHi(self.yax)
            ymin = ymax - self.displayBounds.getLen(1)

        self.displayBounds[:] = [xmin, xmax, ymin, ymax]


    def centreDisplayAt(self, xpos, ypos):
        """Pans the display so the given x/y position is in the centre.
        """

        # work out current display centre
        bounds  = self.displayBounds
        xcentre = bounds.xlo + (bounds.xhi - bounds.xlo) * 0.5
        ycentre = bounds.ylo + (bounds.yhi - bounds.ylo) * 0.5

        # move to the new centre
        self.panDisplayBy(xpos - xcentre, ypos - ycentre)


    def panDisplayToShow(self, xpos, ypos):
        """Pans the display so that the given x/y position (in display
        coordinates) is visible.
        """

        bounds = self.displayBounds

        if xpos >= bounds.xlo and xpos <= bounds.xhi and \
           ypos >= bounds.ylo and ypos <= bounds.yhi: return

        xoff = 0
        yoff = 0

        if   xpos <= bounds.xlo: xoff = xpos - bounds.xlo
        elif xpos >= bounds.xhi: xoff = xpos - bounds.xhi
        
        if   ypos <= bounds.ylo: yoff = ypos - bounds.ylo
        elif ypos >= bounds.yhi: yoff = ypos - bounds.yhi
        
        if xoff != 0 or yoff != 0:
            self.panDisplayBy(xoff, yoff)


    def getAnnotations(self):
        """Returns a :class:`~fsl.fslview.gl.annotations.Annotations`
        instance, which can be used to annotate the canvas. 
        """
        return self._annotations

        
    def __init__(self, overlayList, displayCtx, zax=0):
        """Creates a canvas object. 

        :arg overlayList: An :class:`.OverlayList` object containing a
                          collection of overlays to be displayed.
        
        :arg displayCtx:  A :class:`.DisplayContext` object which describes
                          how the overlays should be displayed.
        
        :arg zax:        Display coordinate system axis perpendicular to the
                         plane to be displayed (the 'depth' axis), default 0.
        """

        props.HasProperties.__init__(self)

        self.overlayList = overlayList
        self.displayCtx  = displayCtx
        self.name        = '{}_{}'.format(self.__class__.__name__, id(self))

        # A GLObject instance is created for
        # every overlay in the overlay list,
        # and stored in this dictionary
        self._glObjects = {}

        # If render mode is offscren or prerender, these
        # dictionaries will contain a RenderTexture or
        # RenderTextureStack instance for each overlay in
        # the overlay list
        self._offscreenTextures = {}
        self._prerenderTextures = {}

        # The zax property is the image axis which maps to the
        # 'depth' axis of this canvas. The _zAxisChanged method
        # also fixes the values of 'xax' and 'yax'.
        self.zax = zax
        self.xax = (zax + 1) % 3
        self.yax = (zax + 2) % 3

        self._annotations = annotations.Annotations(self.xax, self.yax)
        self._zAxisChanged() 

        # when any of the properties of this
        # canvas change, we need to redraw
        self.addListener('zax',           self.name, self._zAxisChanged)
        self.addListener('pos',           self.name, self._draw)
        self.addListener('displayBounds', self.name, self._draw)
        self.addListener('showCursor',    self.name, self._refresh)
        self.addListener('invertX',       self.name, self._refresh)
        self.addListener('invertY',       self.name, self._refresh)
        self.addListener('zoom',          self.name, self._zoomChanged)
        self.addListener('renderMode',    self.name, self._renderModeChange)
        self.addListener('resolutionLimit',
                         self.name,
                         self._resolutionLimitChange) 
        
        # When the overlay list changes, refresh the
        # display, and update the display bounds
        self.overlayList.addListener('overlays',
                                     self.name,
                                     self._overlayListChanged)
        self.displayCtx .addListener('overlayOrder',
                                     self.name,
                                     self._refresh) 
        self.displayCtx .addListener('bounds',
                                     self.name,
                                     self._overlayBoundsChanged)


    def _initGL(self):
        """Call the _overlayListChanged method - it will generate
        any necessary GL data for each of the overlays
        """
        self._overlayListChanged()

        
    def _updateRenderTextures(self):
        """Called when the :attr:`renderMode` changes, when the overlay
        list changes, or when the  GLObject representation of an overlay
        changes.

        If the :attr:`renderMode` property is ``onscreen``, this method does
        nothing.

        Otherwise, creates/destroys :class:`.RenderTexture` or
        :class:`.RenderTextureStack` instances for newly added/removed
        overlays.
        """

        if self.renderMode == 'onscreen':
            return

        # If any overlays have been removed from the overlay
        # list, destroy the associated render texture stack
        if self.renderMode == 'offscreen':
            for ovl, texture in self._offscreenTextures.items():
                if ovl not in self.overlayList:
                    self._offscreenTextures.pop(ovl)
                    texture.destroy()
            
        elif self.renderMode == 'prerender':
            for ovl, (texture, name) in self._prerenderTextures.items():
                if ovl not in self.overlayList:
                    self._prerenderTextures.pop(ovl)
                    glresources.delete(name)

        # If any overlays have been added to the list,
        # create a new render textures for them
        for overlay in self.overlayList:

            if self.renderMode == 'offscreen':
                if overlay in self._offscreenTextures:
                    continue
                
            elif self.renderMode == 'prerender':
                if overlay in self._prerenderTextures:
                    continue 

            globj   = self._glObjects.get(overlay, None)
            display = self.displayCtx.getDisplay(overlay)

            if globj is None:
                continue

            # For offscreen render mode, GLObjects are
            # first rendered to an offscreen texture,
            # and then that texture is rendered to the
            # screen. The off-screen texture is managed
            # by a RenderTexture object.
            if self.renderMode == 'offscreen':
                
                name = '{}_{}_{}'.format(display.name, self.xax, self.yax)
                rt   = textures.GLObjectRenderTexture(
                    name,
                    globj,
                    self.xax,
                    self.yax)

                self._offscreenTextures[overlay] = rt
                
            # For prerender mode, slices of the
            # GLObjects are pre-rendered on a
            # stack of off-screen textures, which
            # is managed by a RenderTextureStack
            # object.
            elif self.renderMode == 'prerender':
                name = '{}_{}_zax{}'.format(
                    id(overlay),
                    textures.RenderTextureStack.__name__,
                    self.zax)

                if glresources.exists(name):
                    rt = glresources.get(name)
                    
                else:
                    rt = textures.RenderTextureStack(globj)
                    rt.setAxes(self.xax, self.yax)
                    glresources.set(name, rt)

                self._prerenderTextures[overlay] = rt, name

        self._refresh()

                
    def _renderModeChange(self, *a):
        """Called when the :attr:`renderMode` property changes."""

        log.debug('Render mode changed: {}'.format(self.renderMode))

        # destroy any existing render textures
        for ovl, texture in self._offscreenTextures.items():
            self._offscreenTextures.pop(ovl)
            texture.destroy()
            
        for ovl, (texture, name) in self._prerenderTextures.items():
            self._prerenderTextures.pop(ovl)
            glresources.delete(name)

        # Onscreen rendering - each GLObject
        # is rendered directly to the canvas
        # displayed on the screen, so render
        # textures are not needed.
        if self.renderMode == 'onscreen':
            self._refresh()
            return

        # Off-screen or prerender rendering - update
        # the render textures for every GLObject
        self._updateRenderTextures()


    def _resolutionLimitChange(self, *a):
        """Called when the :attr:`resolutionLimit` property changes.

        Updates the minimum resolution of all overlays in the overlay list.
        """

        for ovl in self.overlayList:

            # No support for non-volumetric overlay 
            # types yet (or maybe ever?)
            if not isinstance(ovl, fslimage.Image):
                continue

            opts   = self.displayCtx.getOpts(ovl)
            minres = min(ovl.pixdim[:3])

            if self.resolutionLimit > minres:
                minres = self.resolutionLimit

            if opts.resolution < minres:
                opts.resolution = minres


    def _zAxisChanged(self, *a):
        """Called when the :attr:`zax` property is changed. Calculates
        the corresponding X and Y axes, and saves them as attributes of
        this object. Also notifies the GLObjects for every overlay in
        the overlay list.
        """

        log.debug('{}'.format(self.zax))

        # Store the canvas position, in the
        # axis order of the display coordinate
        # system
        pos                  = [None] * 3
        pos[self.xax]        = self.pos.x
        pos[self.yax]        = self.pos.y
        pos[pos.index(None)] = self.pos.z

        # Figure out the new x and y axes
        # based on the new zax value
        dims = range(3)
        dims.pop(self.zax)
        self.xax = dims[0]
        self.yax = dims[1]

        self._annotations.setAxes(self.xax, self.yax)

        for ovl, globj in self._glObjects.items():

            if globj is not None:
                globj.setAxes(self.xax, self.yax)

        self._overlayBoundsChanged()

        # Reset the canvas position as, because the
        # z axis has been changed, the old coordinates
        # will be in the wrong dimension order
        self.pos.xyz = [pos[self.xax],
                        pos[self.yax],
                        pos[self.zax]]

        # If pre-rendering is enabled, the
        # render textures need to be updated, as
        # they are configured in terms of the
        # display axes. Easiest way to do this
        # is to destroy and re-create them
        self._renderModeChange()


    def __overlayTypeChanged(self, value, valid, display, name):
        """Called when the :attr:`.Display.overlayType` setting for any
        overlay changes. Makes sure that an appropriate :class:`.GLObject`
        has been created for the overlay (see the :meth:`__genGLObject`
        method).
        """

        log.debug('GLObject representation for {} '
                  'changed to {}'.format(display.name,
                                         display.overlayType))

        self.__genGLObject(display.getOverlay(), display)
        self._refresh()


    def __genGLObject(self, overlay, display, updateRenderTextures=True):
        """Creates a :class:`.GLObject` instance for the given ``overlay``,
        destroying any existing instance.

        If ``updateRenderTextures`` is ``True`` (the default), and the
        :attr:`.renderMode` is ``offscreen`` or ``prerender``, any
        render texture associated with the overlay is destroyed.
        """

        # Tell the previous GLObject (if
        # any) to clean up after itself
        globj = self._glObjects.pop(overlay, None)
        if globj is not None:
            globj.destroy()

            if updateRenderTextures:
                if self.renderMode == 'offscreen':
                    tex = self._offscreenTextures.pop(overlay, None)
                    if tex is not None:
                        tex.destroy()

                elif self.renderMode == 'prerender':
                    tex, name = self._prerenderTextures.pop(
                        overlay, (None, None))
                    if tex is not None:
                        glresources.delete(name)

        # We need a GL context to create a new GL
        # object. If we can't get it now, the
        # _glObjects value for this overlay will
        # stay as None, and the _draw method will
        # manually call this method again later.
        if not self._setGLContext():
            return None

        globj = globject.createGLObject(overlay, display)

        if globj is not None:
            globj.setAxes(self.xax, self.yax)
            globj.addUpdateListener(self.name, self._refresh)

        self._glObjects[overlay] = globj

        return globj
 
            
    def _overlayListChanged(self, *a):
        """This method is called every time an overlay is added or removed
        to/from the overlay list.

        For newly added overlays, it creates the appropriate :mod:`.GLObject`
        type, which initialises the OpenGL data necessary to render the
        overlay, and then triggers a refresh.
        """

        # Destroy any GL objects for overlays
        # which are no longer in the list
        for ovl, globj in self._glObjects.items():
            if ovl not in self.overlayList:
                self._glObjects.pop(ovl)
                if globj is not None:
                    globj.destroy()

        # Create a GL object for any new overlays,
        # and attach a listener to their display
        # properties so we know when to refresh
        # the canvas.
        for overlay in self.overlayList:

            # A GLObject already exists
            # for this overlay
            if overlay in self._glObjects:
                continue

            display = self.displayCtx.getDisplay(overlay)

            self.__genGLObject(overlay, display, updateRenderTextures=False)

            # Bind Display.softwareMode to SliceCanvas.softwareMode
            display.bindProps('softwareMode', self)

            display.addListener('overlayType',
                                self.name,
                                self.__overlayTypeChanged)
            
            display.addListener('enabled', self.name, self._refresh)

        self._updateRenderTextures()
        self._resolutionLimitChange()
        self._refresh()


    def _overlayBoundsChanged(self, *a):
        """Called when the display bounds are changed.

        Updates the constraints on the :attr:`pos` property so it is
        limited to stay within a valid range, and then calls the
        :meth:`_updateDisplayBounds` method.
        """

        ovlBounds = self.displayCtx.bounds

        self.pos.setMin(0, ovlBounds.getLo(self.xax))
        self.pos.setMax(0, ovlBounds.getHi(self.xax))
        self.pos.setMin(1, ovlBounds.getLo(self.yax))
        self.pos.setMax(1, ovlBounds.getHi(self.yax))
        self.pos.setMin(2, ovlBounds.getLo(self.zax))
        self.pos.setMax(2, ovlBounds.getHi(self.zax))

        self._updateDisplayBounds()


    def _zoomChanged(self, *a):
        """Called when the :attr:`.zoom` property changes. Updates the
        display bounds.
        """
        self._updateDisplayBounds()
        

    def _applyZoom(self, xmin, xmax, ymin, ymax):
        """'Zooms' in to the given rectangle according to the
        current value of the zoom property, keeping the view
        centre consistent with respect to the current value
        of the :attr:`displayBounds` property. Returns a
        4-tuple containing the updated bound values.
        """

        if self.zoom == 100.0:
            return (xmin, xmax, ymin, ymax)

        bounds     = self.displayBounds
        zoomFactor = 100.0 / self.zoom

        xlen    = xmax - xmin
        ylen    = ymax - ymin
        newxlen = xlen * zoomFactor
        newylen = ylen * zoomFactor
 
        # centre the zoomed-in rectangle on
        # the current displayBounds centre
        xmid = bounds.xlo + 0.5 * bounds.xlen
        ymid = bounds.ylo + 0.5 * bounds.ylen

        # new x/y min/max bounds
        xmin = xmid - 0.5 * newxlen
        xmax = xmid + 0.5 * newxlen
        ymin = ymid - 0.5 * newylen
        ymax = ymid + 0.5 * newylen

        xlen = xmax - xmin
        ylen = ymax - ymin

        # clamp x/y min/max values to the
        # displayBounds constraints
        if xmin < bounds.getMin(0):
            xmin = bounds.getMin(0)
            xmax = xmin + xlen
            
        elif xmax > bounds.getMax(0):
            xmax = bounds.getMax(0)
            xmin = xmax - xlen
            
        if ymin < bounds.getMin(1):
            ymin = bounds.getMin(1)
            ymax = ymin + ylen

        elif ymax > bounds.getMax(1):
            ymax = bounds.getMax(1)
            ymin = ymax - ylen

        return (xmin, xmax, ymin, ymax)

        
    def _updateDisplayBounds(self, xmin=None, xmax=None, ymin=None, ymax=None):
        """Called on canvas resizes, overlay bound changes, and zoom changes.
        
        Calculates the bounding box, in world coordinates, to be displayed on
        the canvas. Stores this bounding box in the displayBounds property. If
        any of the parameters are not provided, the
        :attr:`.DisplayContext.bounds` are used.

        :arg xmin: Minimum x (horizontal) value to be in the display bounds.
        :arg xmax: Maximum x value to be in the display bounds.
        :arg ymin: Minimum y (vertical) value to be in the display bounds.
        :arg ymax: Maximum y value to be in the display bounds.
        """

        if xmin is None: xmin = self.displayCtx.bounds.getLo(self.xax)
        if xmax is None: xmax = self.displayCtx.bounds.getHi(self.xax)
        if ymin is None: ymin = self.displayCtx.bounds.getLo(self.yax)
        if ymax is None: ymax = self.displayCtx.bounds.getHi(self.yax)

        log.debug('Required display bounds: X: ({}, {}) Y: ({}, {})'.format(
            xmin, xmax, ymin, ymax))

        canvasWidth, canvasHeight = self._getSize()
        dispWidth                 = float(xmax - xmin)
        dispHeight                = float(ymax - ymin)

        if canvasWidth  == 0 or \
           canvasHeight == 0 or \
           dispWidth    == 0 or \
           dispHeight   == 0:
            self.displayBounds[:] = [xmin, xmax, ymin, ymax]
            return

        # These ratios are used to determine whether
        # we need to expand the display range to
        # preserve the image aspect ratio.
        dispRatio   =       dispWidth    / dispHeight
        canvasRatio = float(canvasWidth) / canvasHeight

        # the canvas is too wide - we need
        # to expand the display width, thus 
        # effectively shrinking the display
        # along the horizontal axis
        if canvasRatio > dispRatio:
            newDispWidth = canvasWidth * (dispHeight / canvasHeight)
            xmin         = xmin - 0.5 * (newDispWidth - dispWidth)
            xmax         = xmax + 0.5 * (newDispWidth - dispWidth)

        # the canvas is too high - we need
        # to expand the display height
        elif canvasRatio < dispRatio:
            newDispHeight = canvasHeight * (dispWidth / canvasWidth)
            ymin          = ymin - 0.5 * (newDispHeight - dispHeight)
            ymax          = ymax + 0.5 * (newDispHeight - dispHeight)

        self.displayBounds.setLimits(0, xmin, xmax)
        self.displayBounds.setLimits(1, ymin, ymax) 

        xmin, xmax, ymin, ymax = self._applyZoom(xmin, xmax, ymin, ymax)

        log.debug('Final display bounds: X: ({}, {}) Y: ({}, {})'.format(
            xmin, xmax, ymin, ymax))

        self.displayBounds[:] = (xmin, xmax, ymin, ymax)

        
    def _setViewport(self,
                     xmin=None,
                     xmax=None,
                     ymin=None,
                     ymax=None,
                     zmin=None,
                     zmax=None,
                     size=None):
        """Sets up the GL canvas size, viewport, and projection.

        If any of the min/max parameters are not provided, they are
        taken from the :attr:`displayBounds` (x/y), and the 
        :attr:`DisplayContext.bounds` (z).

        :arg xmin: Minimum x (horizontal) location
        :arg xmax: Maximum x location
        :arg ymin: Minimum y (vertical) location
        :arg ymax: Maximum y location
        :arg zmin: Minimum z (depth) location
        :arg zmax: Maximum z location
        """

        xax = self.xax
        yax = self.yax
        zax = self.zax
        
        if xmin is None: xmin = self.displayBounds.xlo
        if xmax is None: xmax = self.displayBounds.xhi
        if ymin is None: ymin = self.displayBounds.ylo
        if ymax is None: ymax = self.displayBounds.yhi
        if zmin is None: zmin = self.displayCtx.bounds.getLo(zax)
        if zmax is None: zmax = self.displayCtx.bounds.getHi(zax)

        # If there are no images to be displayed,
        # or no space to draw, do nothing
        if size is None:
            size = self._getSize()
            
        width, height = size

        # clear the canvas
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        # enable transparency
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)        
        
        if (len(self.overlayList) == 0) or \
           (width  == 0)                or \
           (height == 0)                or \
           (xmin   == xmax)             or \
           (ymin   == ymax):
            return

        log.debug('Setting canvas bounds (size {}, {}): '
                  'X {: 5.1f} - {: 5.1f},'
                  'Y {: 5.1f} - {: 5.1f},'
                  'Z {: 5.1f} - {: 5.1f}'.format(
                      width, height, xmin, xmax, ymin, ymax, zmin, zmax))

        # Flip the viewport if necessary
        if self.invertX: xmin, xmax = xmax, xmin
        if self.invertY: ymin, ymax = ymax, ymin

        lo = [None] * 3
        hi = [None] * 3

        lo[xax], hi[xax] = xmin, xmax
        lo[yax], hi[yax] = ymin, ymax
        lo[zax], hi[zax] = zmin, zmax

        # set up 2D orthographic drawing
        glroutines.show2D(xax, yax, width, height, lo, hi)

        
    def _drawCursor(self):
        """Draws a green cursor at the current X/Y position."""
        
        # A vertical line at xpos, and a horizontal line at ypos
        xverts = np.zeros((2, 2))
        yverts = np.zeros((2, 2))

        xmin, xmax = self.displayCtx.bounds.getRange(self.xax)
        ymin, ymax = self.displayCtx.bounds.getRange(self.yax)

        x = self.pos.x
        y = self.pos.y

        # How big is one pixel in world space?
        pixx, pixy = self.calcPixelDims()

        # add a little padding to the lines if they are 
        # on the boundary, so they don't get cropped        
        if x <= xmin: x = xmin + 0.5 * pixx
        if x >= xmax: x = xmax - 0.5 * pixx
        if y <= ymin: y = ymin + 0.5 * pixy
        if y >= ymax: y = ymax - 0.5 * pixy

        xverts[:, 0] = x
        xverts[:, 1] = [ymin, ymax]
        yverts[:, 0] = [xmin, xmax]
        yverts[:, 1] = y 
        
        self._annotations.line(xverts[0], xverts[1], colour=(0, 1, 0), width=1)
        self._annotations.line(yverts[0], yverts[1], colour=(0, 1, 0), width=1)


    def _drawOffscreenTextures(self):
        """Draws all of the off-screen :class:`.GLObjectRenderTexture` instances to
        the canvas.

        This method is called by :meth:`_draw` if :attr:`renderMode` is
        set to ``offscreen``.
        """
        
        log.debug('Combining off-screen render textures, and rendering '
                  'to canvas (size {})'.format(self._getSize()))

        for overlay in self.displayCtx.getOrderedOverlays():
            
            rt      = self._offscreenTextures.get(overlay, None)
            display = self.displayCtx.getDisplay(overlay)
            opts    = display.getDisplayOpts()
            lo, hi  = opts.getDisplayBounds()

            if rt is None or not display.enabled:
                continue

            xmin, xmax = lo[self.xax], hi[self.xax]
            ymin, ymax = lo[self.yax], hi[self.yax]

            log.debug('Drawing overlay {} texture to {:0.3f}-{:0.3f}, '
                      '{:0.3f}-{:0.3f}'.format(
                          overlay, xmin, xmax, ymin, ymax))

            rt.drawOnBounds(
                self.pos.z, xmin, xmax, ymin, ymax, self.xax, self.yax) 

            
    def _draw(self, *a):
        """Draws the current scene to the canvas. """
        
        width, height = self._getSize()
        if width == 0 or height == 0:
            return

        if not self._setGLContext():
            return

        # Set the viewport to match the current 
        # display bounds and canvas size
        if self.renderMode is not 'offscreen':
            self._setViewport()

        for overlay in self.displayCtx.getOrderedOverlays():

            display = self.displayCtx.getDisplay(overlay)
            opts    = display.getDisplayOpts()
            globj   = self._glObjects.get(overlay, None)

            if not display.enabled:
                continue
            
            if globj is None:
                globj = self.__genGLObject(overlay, display)

            # On-screen rendering - the globject is
            # rendered directly to the screen canvas
            if self.renderMode == 'onscreen':
                log.debug('Drawing {} slice for overlay {} '
                          'directly to canvas'.format(
                              self.zax, display.name))

                globj.preDraw()
                globj.draw(self.pos.z)
                globj.postDraw() 

            # Off-screen rendering - each overlay is
            # rendered to an off-screen texture -
            # these textures are combined below.
            # Set up the texture as the rendering
            # target, and draw to it
            elif self.renderMode == 'offscreen':
                
                rt     = self._offscreenTextures.get(overlay, None)
                lo, hi = opts.getDisplayBounds()

                # Assume that all is well - the texture
                # just has not yet been created
                if rt is None:
                    continue
                
                log.debug('Drawing {} slice for overlay {} '
                          'to off-screen texture'.format(
                              self.zax, overlay.name))

                rt.bindAsRenderTarget()
                rt.setRenderViewport(self.xax, self.yax, lo, hi)
                
                gl.glClear(gl.GL_COLOR_BUFFER_BIT)

                globj.preDraw()
                globj.draw(self.pos.z)
                globj.postDraw()

                rt.unbindAsRenderTarget()
                rt.restoreViewport()

            # Pre-rendering - a pre-generated 2D
            # texture of the current z position
            # is rendered to the screen canvas
            elif self.renderMode == 'prerender':
                
                rt, name = self._prerenderTextures.get(overlay, (None, None))

                if rt is None:
                    continue

                log.debug('Drawing {} slice for overlay {} '
                          'from pre-rendered texture'.format(
                              self.zax, display.name)) 

                rt.draw(self.pos.z)

        # For off-screen rendering, all of the globjects
        # were rendered to off-screen textures - here,
        # those off-screen textures are all rendered on
        # to the screen canvas.
        if self.renderMode == 'offscreen':
            self._setViewport()
            self._drawOffscreenTextures() 

        if self.showCursor:
            self._drawCursor()

        self._annotations.draw(self.pos.z)

        self._postDraw()
