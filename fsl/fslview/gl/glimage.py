#!/usr/bin/env python
#
# glimage.py - OpenGL vertex/texture creation for 2D slice rendering of a 3D
#              image.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""Defines the :class:`GLImage` class, which creates and encapsulates the data
and logic required to render 2D slice of a 3D image. The :class:`GLImage` class
provides the interface defined in the :mod:`~fsl.fslview.gl.globject` module.

One stand-alone function is also contained in this module, the
:func:`genVertexData` function. This function contains the code to actually
generate the vertex information necessary to render an image (which is the
same across OpenGL versions).

The :class:`GLImage` class makes use of the functions defined in the
:mod:`fsl.fslview.gl.gl14.glimage_funcs` or the
:mod:`fsl.fslview.gl.gl21.glimage_funcs` modules, which provide OpenGL version
specific details for creation/storage of the vertex/colour/texture data.

These version dependent modules must provide the following functions:

  - `init(GLImage, xax, yax)`: Perform any necessary initialisation.

  - `genVertexData(GLImage)`: Create and prepare vertex and texture
     coordinates, using the :func:`genVertexData` function. 
                               
  - `genImageData(GLImage)`: Retrieve and prepare the image data to be
    displayed.

  - `genColourMap(GLImage)`: Create and prepare the colour map used to
    colour image voxels.

  - `draw(GLImage, zpos, xform=None)`: Draw a slice of the image at the given
    Z position. If xform is not None, it must be applied as a transformation
    on the vertex coordinates.

  - `destroy(GLimage)`: Perform any necessary clean up.

"""

import logging
log = logging.getLogger(__name__)

import OpenGL.GL      as gl
import numpy          as np

import fsl.fslview.gl as fslgl
import                   globject

class GLImage(object):
    """The :class:`GLImage` class encapsulates the data and logic required to
    render 2D slices of a 3D image.
    """
 
    def __init__(self, image, display):
        """Creates a GLImage object bound to the given image, and associated
        image display.

        :arg image:        A :class:`~fsl.data.image.Image` object.
        
        :arg imageDisplay: A :class:`~fsl.fslview.displaycontext.ImageDisplay`
                           object which describes how the image is to be
                           displayed.
        """

        self.image   = image
        self.display = display
        self._ready  = False


    def ready(self):
        """Returns `True` when the OpenGL data/state has been initialised, and the
        image is ready to be drawn, `False` before.
        """
        return self._ready

        
    def init(self, xax, yax):
        """Initialise the OpenGL data required to render the given image.

        The real initialisation takes place in this method - it must
        only be called after an OpenGL context has been created.
        """
        
        # Add listeners to this image so the view can be
        # updated when its display properties are changed
        self._configDisplayListeners()

        self.setAxes(xax, yax)
        fslgl.glimage_funcs.init(self, xax, yax)

        # Initialise the image data, and
        # generate vertex/texture coordinates
        self.imageData = fslgl.glimage_funcs.genImageData(self)

        # The colour map, used for converting 
        # image data to a RGBA colour.
        self.colourTexture    = gl.glGenTextures(1)
        self.colourResolution = 256
        self.genColourTexture(self.colourResolution)
        
        self._ready = True


    def setAxes(self, xax, yax):
        """This method should be called when the image display axes change.
        
        It regenerates vertex information accordingly.
        """
        
        self.xax         = xax
        self.yax         = yax
        self.zax         = 3 - xax - yax
        wc, tc, idxs, nv = fslgl.glimage_funcs.genVertexData(self)
        self.worldCoords = wc
        self.texCoords   = tc
        self.indices     = idxs
        self.nVertices   = nv

        
    def draw(self, zpos, xform=None):
        """Draws a 2D slice of the image at the given real world Z location.
        This is performed via a call to the OpenGL version-dependent `draw`
        function, contained in one of the :mod:`~fsl.fslview.gl.gl14` or
        :mod:`~fsl.fslview.gl.gl21` packages.

        If `xform` is not None, it is applied as an affine transformation to
        the vertex coordinates of the rendered image data.
        """
        fslgl.glimage_funcs.draw(self, zpos, xform)


    def destroy(self):
        """This should be called when this :class:`GLImage` object is no
        longer needed. It performs any needed clean up of OpenGL data (e.g.
        deleting texture handles).
        """
        gl.glDeleteTextures(1, self.colourTexture)
        fslgl.glimage_funcs.destroy(self)


    def genVertexData(self):
        """Generates vertex coordinates (for rendering voxels) and
        texture coordinates (for colouring voxels) in world space.

        Generates X/Y vertex coordinates, in the display coordinate system for
        the given image, which define a set of pixels for displaying the image
        at an arbitrary position along the world Z dimension.  These pixels
        are represented by an OpenGL triangle strip. See the
        :func:`~fsl.fslview.gl.globject.calculateSamplePoints` and
        :func:`~fsl.fslview.gl.globject.samplePointsToTriangleStrip` functions
        for more details.

        :arg image:   The :class:`~fsl.data.image.Image` object to
                      generate vertex and texture coordinates for.

        :arg display: A :class:`~fsl.fslview.displaycontext.ImageDisplay`
                      object which defines how the image is to be
                      rendered.

        :arg xax:     The world space axis which corresponds to the
                      horizontal screen axis (0, 1, or 2).

        :arg yax:     The world space axis which corresponds to the
                      vertical screen axis (0, 1, or 2).
        """

        worldCoords, xpixdim, ypixdim, xlen, ylen = \
          globject.calculateSamplePoints(
              self.image, self.display, self.xax, self.yax)

        # All voxels are rendered using a triangle strip,
        # with rows connected via degenerate vertices
        worldCoords, texCoords, indices = globject.samplePointsToTriangleStrip(
            worldCoords, xpixdim, ypixdim, xlen, ylen, self.xax, self.yax)

        return worldCoords, texCoords, indices

    
    def genColourTexture(self, colourResolution):
        """Configures the colour texture used to colour image voxels.

        Also createss a transformation matrix which transforms an image data
        value to the range (0-1), which may then be used as a texture
        coordinate into the colour map texture. This matrix is stored as an
        attribute of this :class:`GLImage` object called
        :attr:`colourMapXForm`.

        OpenGL does different things to 3D texture data depending on its type
        - integer types are normalised from [0, INT_MAX] to [0, 1], The
        :func:`_checkDataType` method calculates an appropriate transformation
        matrix to transform the image data to the appropriate texture
        coordinate range, which is then returned by this function, and
        subsequently used in the :func:`draw` function.

        As an aside, floating point texture data types are, by default,
        *clamped*, to the range [0, 1]! This can be overcome by using a more
        recent versions of OpenGL, or by using the ARB.texture_rg.GL_R32F data
        format.
        """

        display = self.display

        imin = display.displayRange[0]
        imax = display.displayRange[1]

        # This transformation is used to transform voxel values
        # from their native range to the range [0.0, 1.0], which
        # is required for texture colour lookup. Values below
        # or above the current display range will be mapped
        # to texture coordinate values less than 0.0 or greater
        # than 1.0 respectively.
        cmapXform = np.identity(4, dtype=np.float32)
        cmapXform[0, 0] = 1.0 / (imax - imin)
        cmapXform[3, 0] = -imin * cmapXform[0, 0]

        self.colourMapXForm = cmapXform

        # Create [self.colourResolution] rgb values,
        # spanning the entire range of the image
        # colour map
        colourRange     = np.linspace(0.0, 1.0, colourResolution)
        colourmap       = display.cmap(colourRange)
        colourmap[:, 3] = display.alpha

        # Make out-of-range values transparent
        # if clipping is enabled 
        if display.clipLow:  colourmap[ 0, 3] = 0.0
        if display.clipHigh: colourmap[-1, 3] = 0.0 

        # The colour data is stored on
        # the GPU as 8 bit rgba tuples
        colourmap = np.floor(colourmap * 255)
        colourmap = np.array(colourmap, dtype=np.uint8)
        colourmap = colourmap.ravel(order='C')

        # GL texture creation stuff
        gl.glBindTexture(gl.GL_TEXTURE_1D, self.colourTexture)
        gl.glTexParameteri(gl.GL_TEXTURE_1D,
                           gl.GL_TEXTURE_MAG_FILTER,
                           gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_1D,
                           gl.GL_TEXTURE_MIN_FILTER,
                           gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_1D,
                           gl.GL_TEXTURE_WRAP_S,
                           gl.GL_CLAMP_TO_EDGE)

        gl.glTexImage1D(gl.GL_TEXTURE_1D,
                        0,
                        gl.GL_RGBA8,
                        colourResolution,
                        0,
                        gl.GL_RGBA,
                        gl.GL_UNSIGNED_BYTE,
                        colourmap)
        gl.glBindTexture(gl.GL_TEXTURE_1D, 0)

        
    def _configDisplayListeners(self):
        """Adds a bunch of listeners to the
        :class:`~fsl.fslview.displaycontext.ImageDisplay` object which defines
        how the given image is to be displayed.

        This is done so we can update the colour, vertex, and image data when
        display properties are changed.
        """ 

        def vertexUpdate(*a):
            wc, tc, idx, nv = fslgl.glimage_funcs.genVertexData(self)
            self.worldCoords = wc
            self.texCoords   = tc
            self.indices     = idx
            self.nVertices   = nv

        def imageUpdate(*a):
            self.imageData = fslgl.glimage_funcs.genImageData(self)
        
        def colourUpdate(*a):
            self.genColourTexture(self.colourResolution)

        display = self.display
        lnrName = 'GlImage_{}'.format(id(self))

        display.addListener('transform',       lnrName, vertexUpdate)
        display.addListener('interpolation',   lnrName, imageUpdate)
        display.addListener('alpha',           lnrName, colourUpdate)
        display.addListener('displayRange',    lnrName, colourUpdate)
        display.addListener('clipLow',         lnrName, colourUpdate)
        display.addListener('clipHigh',        lnrName, colourUpdate)
        display.addListener('cmap',            lnrName, colourUpdate)
        display.addListener('voxelResolution', lnrName, vertexUpdate)
        display.addListener('worldResolution', lnrName, vertexUpdate)
        display.addListener('volume',          lnrName, imageUpdate)
