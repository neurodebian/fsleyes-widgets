#!/usr/bin/env python
#
# layout.py - Utility functions for calculating canvas sizes and laying them
# out.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""Utility functions for calculating canvas sizes and laying them out.

This module provides functions which implement a simple layout manager, for
laying out canvases and associated orientation labels. It is used primarily by
the :mod:`~fsl.tools.render` application, for off-screen rendering.

The main entry points for the layout manager are:

  - :func:`buildOrthoLayout`: Creates a tree of objects representing a group
                              of canvases laid out either horizontally,
                              vertically, or in a grid.

  - :func:`layoutToBitmap`:   Converts a layout tree into a rgba bitmap, a
                              ``numpy.uint8`` array of size
                              ``(height, width, 4)``.

This module also provides a few functions, for calculating the display size,
in pixels, of one or more canvases which are displaying a defined coordinate
system. The canvas sizes are calculated so that their aspect ratio, relative
to the respective horizontal/vertical display axes, are maintained, and that
the canvases are sized proportionally with respect to each other. These
functions are used both by :mod:`~fsl.tools.render`, and also by the
:class:`~fsl.fslview.views.orthopanel.OrthoPanel`, for calculating canvas
sizes when they are displayed in :mod:`~fsl.tools.fslview`.

The following size calculation functions are available:

  - :func:`calcGridSizes`:       Calculates canvas sizes for laying out in a
                                 grid
  - :func:`calcHorizontalSizes`: Calculates canvas sizes for laying out
                                 horizontally.
  - :func:`calcVerticalSizes`:   Calculates canvas sizes for laying out
                                 vertically.

Each of these functions require the following parameters:

  - ``canvasaxes``: A sequence of 2-tuples, one for each canvas, with each
                    tuple specifying the indices of the coordinate system
                    axes which map to the horizontal and vertical canvas
                    axes.
 
  - ``bounds``:     A sequence of three floating point values, specifying the
                    length of each axis in the coordinate system being
                    displayed.

  - ``width``:      The total available width in which all of the canvases are
                    to be displayed.

  - ``height``:     The total available height in which all of the canvases are
                    to be displayed.

A convenience function :func:`calcSizes` is also available which, in addition
to the above parameters, accepts a string as its first parameter which must be
equal to one of ``horizontal``, ``vertical``, or ``grid``. It will then call
the appropriate layout-specific function.
"""

import logging
log = logging.getLogger(__name__)


import numpy as np


#
# The Space, Bitmap, HBox and VBox classes are used by a simple
# layout manager for laying out slice canvases, labels, and colour
# bars.
#

class Bitmap(object):
    """A class which encapsulates a RGBA bitmap (a ``numpy.uint8`` array of
    shape ``(height, width, 4)``)
    """

    def __init__(self, bitmap):
        self.bitmap = bitmap
        self.width  = bitmap.shape[1]
        self.height = bitmap.shape[0]

        
class Space(object):
    """A class which represents empty space of a specific width/height. """

    def __init__(self, width, height):
        self.width  = width
        self.height = height

        
class HBox(object):
    """A class which contains items to be laid out horizontally. """
    def __init__(self, items=None):
        self.width  = 0
        self.height = 0
        self.items = []
        if items is not None: map(self.append, items)

        
    def append(self, item):
        self.items.append(item)
        self.width = self.width + item.width
        if item.height > self.height:
            self.height = item.height

            
class VBox(object):
    """A class which contains items to be laid out vertically. """
    def __init__(self, items=None):
        self.width  = 0
        self.height = 0
        self.items = []
        if items is not None: map(self.append, items)

    def append(self, item):
        self.items.append(item)
        self.height = self.height + item.height
        if item.width > self.width:
            self.width = item.width


def padBitmap(bitmap, width, height, vert, bgColour):
    """Pads the given bitmap with zeros along the secondary axis,
    so that it fits in the given ``width``/``height``.

    If ``vert`` is ``True``, the bitmap is padded horizontally to
    fit ``width``. Otherwise, the bitmap is padded vertically to
    fit ``height``.
    """
    
    iheight = bitmap.shape[0]
    iwidth  = bitmap.shape[1]
    
    if vert:
        if iwidth < width:
            lpad   = np.floor((width - iwidth) / 2.0)
            rpad   = np.ceil( (width - iwidth) / 2.0)
            lpad   = np.zeros((iheight, lpad, 4), dtype=np.uint8)
            rpad   = np.zeros((iheight, rpad, 4), dtype=np.uint8)
            lpad[:] = bgColour
            rpad[:] = bgColour
            bitmap = np.hstack((lpad, bitmap, rpad))
    else:
        if iheight < height:
            tpad   = np.floor((height - iheight) / 2.0)
            bpad   = np.ceil(( height - iheight) / 2.0)
            tpad   = np.zeros((tpad, iwidth, 4), dtype=np.uint8)
            bpad   = np.zeros((bpad, iwidth, 4), dtype=np.uint8)
            tpad[:] = bgColour
            bpad[:] = bgColour 
            bitmap = np.vstack((tpad, bitmap, bpad))

    return bitmap


def layoutToBitmap(layout, bgColour):
    """Recursively turns the given ``layout`` object into a bitmap.

    The ``layout`` object is assumed to be one of the following:
      - a :class:`Bitmap` object
      - a :class:`Space` object
      - a :class:`HBox` object
      - a :class:`VBox` object

    The generated bitmap is returned as a ``numpy.uint8`` array of shape
    ``(height, width, 4)``.
    """

    if bgColour is None: bgColour = [0, 0, 0, 0]
    bgColour = np.array(bgColour, dtype=np.uint8)

    if isinstance(layout, Space):
        space = np.zeros((layout.height, layout.width, 4), dtype=np.uint8)
        space[:] = bgColour
        return space
    
    elif isinstance(layout, Bitmap):
        return np.array(layout.bitmap, dtype=np.uint8)

    # Otherwise it's assumed that the
    # layout object is a HBox or VBox

    if   isinstance(layout, HBox): vert = False
    elif isinstance(layout, VBox): vert = True

    # Recursively bitmapify the children of the box
    itemBmps = map(lambda i: layoutToBitmap(i, bgColour), layout.items)

    # Pad each of the bitmaps so they are all the same
    # size along the secondary axis (which is width
    # if the layout is a VBox, and height if the layout
    # is a HBox).
    width    = layout.width
    height   = layout.height 
    itemBmps = map(lambda bmp: padBitmap(bmp, width, height, vert, bgColour),
                   itemBmps)

    if vert: return np.vstack(itemBmps)
    else:    return np.hstack(itemBmps)


def buildCanvasBox(canvasBmp,
                   labelBmps,
                   showLabels,
                   labelSize):
    """Builds a layout containing the given canvas bitmap, and orientation
    labels (if ``showLabels`` is ``True``).
    """

    if not showLabels: return Bitmap(canvasBmp)

    row1Box = HBox([Space(labelSize, labelSize),
                    Bitmap(labelBmps['top']),
                    Space(labelSize, labelSize)])

    row2Box = HBox([Bitmap(labelBmps['left']),
                    Bitmap(canvasBmp),
                    Bitmap(labelBmps['right'])])

    row3Box = HBox([Space(labelSize, labelSize),
                    Bitmap(labelBmps['bottom']),
                    Space(labelSize, labelSize)])

    return VBox((row1Box, row2Box, row3Box))


def buildOrthoLayout(canvasBmps,
                     labelBmps,
                     layout,
                     showLabels,
                     labelSize):
    """Builds a layout tree containinbg the given canvas bitmaps, label
    bitmaps, and colour bar bitmap.
    """

    if labelBmps is None: labelBmps = [None] * len(canvasBmps)

    canvasBoxes = map(lambda cbmp, lbmps: buildCanvasBox(cbmp,
                                                         lbmps,
                                                         showLabels,
                                                         labelSize),
                      canvasBmps,
                      labelBmps)

    if   layout == 'horizontal': canvasBox = HBox(canvasBoxes)
    elif layout == 'vertical':   canvasBox = VBox(canvasBoxes)
    elif layout == 'grid':
        row1Box   = HBox([canvasBoxes[0], canvasBoxes[1]])
        row2Box   = HBox([canvasBoxes[2], Space(canvasBoxes[1].width,
                                                canvasBoxes[2].height)])
        canvasBox = VBox((row1Box, row2Box))

    return canvasBox


#
# Size calculation functions 
#


def calcSizes(layout, canvasaxes, bounds, width, height):
    """Convenience function which, based upon whether the `layout` argument
    is `horizontal`, `vertical`, or `grid`,  respectively calls one of:
      - :func:`calcHorizontalSizes`
      - :func:`calcVerticalSizes`
      - :func:`calcGridSizes`
    """
    
    layout = layout.lower()
    func   = None

    if   layout == 'horizontal': func = calcHorizontalSizes
    elif layout == 'vertical':   func = calcVerticalSizes
    elif layout == 'grid':       func = calcGridSizes

    # a bad value for layout
    # will result in an error
    return func(canvasaxes, bounds, width, height)

        
def calcGridSizes(canvasaxes, bounds, width, height):
    """Calculates the size of three canvases so that they are laid
    out in a grid, i.e.:

       0   1

       2

    If less than three canvases are specified, they are passed to the
    :func:`calcHorizontalLayout` function.
    """

    if len(canvasaxes) < 3:
        return calcHorizontalSizes(canvasaxes, bounds, width, height)

    canvasWidths  = [bounds[c[0]] for c in canvasaxes]
    canvasHeights = [bounds[c[1]] for c in canvasaxes]
    
    ttlWidth      = float(canvasWidths[ 0] + canvasWidths[ 1])
    ttlHeight     = float(canvasHeights[0] + canvasHeights[2])

    sizes = []

    for i in range(len(canvasaxes)):

        cw = width  * (canvasWidths[ i] / ttlWidth)
        ch = height * (canvasHeights[i] / ttlHeight) 

        acw, ach = _adjustPixelSize(canvasWidths[ i],
                                    canvasHeights[i],
                                    cw,
                                    ch)

        if (float(cw) / ch) > (float(acw) / ach): cw, ch = cw, ach
        else:                                     cw, ch = acw, ch
        
        sizes.append((cw, ch))

    return sizes


def calcPixWidth(wldWidth, wldHeight, pixHeight):
    """Given the dimensions of a 'world' space to be displayed,
    and the available height in pixels, calculates and returns
    the required pixel width.
    """
    return _adjustPixelSize(wldWidth,
                            wldHeight,
                            pixHeight * (2 ** 32),
                            pixHeight)[0]


def calcPixHeight(wldWidth, wldHeight, pixWidth):
    """Given the dimensions of a 'world' space to be displayed,
    and the available width in pixels, calculates and returns
    the required pixel height.
    """ 
    return _adjustPixelSize(wldWidth,
                            wldHeight,
                            pixWidth,
                            pixWidth * (2 ** 32))[1]


def calcVerticalSizes(canvasaxes, bounds, width, height):
    """Calculates the size of up to three canvases so  they are laid out
    vertically.
    """
    return _calcFlatSizes(canvasaxes, bounds, width, height, True)


def calcHorizontalSizes(canvasaxes, bounds, width, height):
    """Calculates the size of up to three canvases so  they are laid out
    horizontally.
    """ 
    return _calcFlatSizes(canvasaxes, bounds, width, height, False)

        
def _calcFlatSizes(canvasaxes, bounds, width, height, vert=True):
    """Used by the :func:`calcVerticalSizes` and :func:`calcHorizontalSizes`
    functions to lay the canvases out vertically (``vert=True``) or
    horizontally (``vert=False``).
    """

    # Get the canvas dimensions in world space
    canvasWidths  = [bounds[c[0]] for c in canvasaxes]
    canvasHeights = [bounds[c[1]] for c in canvasaxes]

    maxWidth  = float(max(canvasWidths))
    maxHeight = float(max(canvasHeights))
    ttlWidth  = float(sum(canvasWidths))
    ttlHeight = float(sum(canvasHeights))

    if vert: ttlWidth  = maxWidth
    else:    ttlHeight = maxHeight

    sizes = []
    for i in range(len(canvasaxes)):

        if ttlWidth  == 0: cw = 0
        else:              cw = width  * (canvasWidths[ i] / ttlWidth)

        if ttlHeight == 0: ch = 0
        else:              ch = height * (canvasHeights[i] / ttlHeight)

        acw, ach = _adjustPixelSize(canvasWidths[ i],
                                    canvasHeights[i],
                                    cw,
                                    ch)

        if vert: ch, cw = ach, width
        else:    cw, ch = acw, height

        sizes.append((cw, ch))

    return sizes


def _adjustPixelSize(wldWidth, wldHeight, pixWidth, pixHeight):
    """Potentially reduces the given pixel width/height such that the
    display space aspect ratio is maintained.
    """

    if pixWidth == 0 or pixHeight == 0:
        return 0, 0

    pixRatio = float(pixWidth) / pixHeight
    wldRatio = float(wldWidth) / wldHeight

    if   pixRatio > wldRatio:
        pixWidth  = wldWidth  * (pixHeight / wldHeight)
            
    elif pixRatio < wldRatio:
        pixHeight = wldHeight * (pixWidth  / wldWidth)

    return pixWidth, pixHeight
