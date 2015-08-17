#!/usr/bin/env python
#
# lightboxopts.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import copy

import sceneopts

import fsl.fslview.gl.canvasopts as canvasopts


class LightBoxOpts(sceneopts.SceneOpts):

    sliceSpacing   = copy.copy(canvasopts.LightBoxCanvasOpts.sliceSpacing)
    zax            = copy.copy(canvasopts.LightBoxCanvasOpts.zax)
    ncols          = copy.copy(canvasopts.LightBoxCanvasOpts.ncols)
    nrows          = copy.copy(canvasopts.LightBoxCanvasOpts.nrows)
    topRow         = copy.copy(canvasopts.LightBoxCanvasOpts.topRow)
    zrange         = copy.copy(canvasopts.LightBoxCanvasOpts.zrange)
    showGridLines  = copy.copy(canvasopts.LightBoxCanvasOpts.showGridLines)
    highlightSlice = copy.copy(canvasopts.LightBoxCanvasOpts.highlightSlice)
