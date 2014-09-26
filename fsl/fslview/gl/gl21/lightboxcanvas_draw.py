#!/usr/bin/env python
#
# ligntboxcanavs_draw.py - Render multiple image slices on one canvas in an
# OpenGL 2.1 compatible manner.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""Render multiple image slices on a
:class:`~fsl.fslview.gl.lightboxcanvas.LightBoxCanvas` canvas in an Open

.. note:: This module is extremely tightly coupled to the
:class:`~fsl.fslview.gl.slicecanvas.SliceCanvas`,
:class:`~fsl.fslview.gl.lightboxcanvas.LightBoxCanvas` class, and to the
:mod:`~fsl.fslview.gl.gl21.slicecanvas_draw` module.
"""

import logging
log = logging.getLogger(__name__)

import OpenGL.GL as gl
import numpy     as np


def drawCursor(canvas):
    """Draws a cursor at the current canvas position (the
    :attr:`~fsl.fslview.gl.SliceCanvas.pos` property).
    """
    
    sliceno = int(np.floor((canvas.pos.z - canvas.zrange.xlo) /
                           canvas.sliceSpacing))
    xlen    = canvas.imageList.bounds.getLen(canvas.xax)
    ylen    = canvas.imageList.bounds.getLen(canvas.yax)
    xmin    = canvas.imageList.bounds.getLo( canvas.xax)
    ymin    = canvas.imageList.bounds.getLo( canvas.yax)
    row     = canvas._totalRows - int(np.floor(sliceno / canvas.ncols)) - 1
    col     = int(np.floor(sliceno % canvas.ncols)) 

    xpos, ypos = canvas.worldToCanvas(*canvas.pos.xyz)

    xverts = np.zeros((2, 3))
    yverts = np.zeros((2, 3)) 

    xverts[:, canvas.xax] = xpos
    xverts[0, canvas.yax] = ymin + (row)     * ylen
    xverts[1, canvas.yax] = ymin + (row + 1) * ylen
    xverts[:, canvas.zax] = canvas.pos.z + 1

    yverts[:, canvas.yax] = ypos
    yverts[0, canvas.xax] = xmin + (col)     * xlen
    yverts[1, canvas.xax] = xmin + (col + 1) * xlen
    yverts[:, canvas.zax] = canvas.pos.z + 1

    gl.glBegin(gl.GL_LINES)
    gl.glColor3f(0, 1, 0)
    gl.glVertex3f(*xverts[0])
    gl.glVertex3f(*xverts[1])
    gl.glVertex3f(*yverts[0])
    gl.glVertex3f(*yverts[1])
    gl.glEnd() 

    
def draw(canvas):
    """Draws the currently visible slices to the canvas."""

    startSlice   = canvas.ncols * canvas.topRow
    endSlice     = startSlice + canvas.nrows * canvas.ncols

    if endSlice > canvas._nslices:
        endSlice = canvas._nslices    

    # clear the canvas
    gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

    # enable transparency
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    # disable interpolation
    gl.glShadeModel(gl.GL_FLAT)

    # Draw all the slices for all the images.
    for i, image in enumerate(canvas.imageList):

        try: globj = image.getAttribute(canvas.name)
        except KeyError:
            continue

        if (globj is None) or (not globj.ready()):
            continue 
        
        log.debug('Drawing {} slices ({} - {}) for image {}'.format(
            endSlice - startSlice, startSlice, endSlice, i))
        
        for zi in range(startSlice, endSlice):
            globj.draw(canvas._sliceLocs[ i][zi],
                       canvas._transforms[i][zi])
            
    if canvas.showCursor:
        drawCursor(canvas)
