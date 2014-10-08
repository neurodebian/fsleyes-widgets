#!/usr/bin/env python
#
# osmesaslicecanvas.py - A SliceCanvas which uses OSMesa for off-screen OpenGL
# rendering.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""Provides the :class:`OSMesaSliceCanvas` which supports off-screen
rendering.
"""

import logging
log = logging.getLogger(__name__)


import fsl.fslview.gl   as fslgl
import slicecanvas      as sc
       

class OSMesaSliceCanvas(sc.SliceCanvas,
                        fslgl.OSMesaCanvasTarget):
    """A :class:`~fsl.fslview.gl.slicecanvas.SliceCanvas`
    which uses OSMesa for static off-screen OpenGL rendering.
    """
    
    def __init__(self,
                 imageList,
                 zax=0,
                 width=0,
                 height=0,
                 bgColour=(0, 0, 0, 255)):
        """See the :class:`~fsl.fslview.gl.slicecanvas.SliceCanvas` constructor
        for details on the other parameters.

        :arg width:    Canvas width in pixels
        
        :arg height:   Canvas height in pixels

        :arg bgColour: Canvas background colour
        """

        fslgl.OSMesaCanvasTarget.__init__(self, width, height, bgColour)
        sc.SliceCanvas          .__init__(self, imageList, zax)
