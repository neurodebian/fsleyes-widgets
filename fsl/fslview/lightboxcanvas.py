#!/usr/bin/env python
#
# lightboxcanvas.py - A wx.GLCanvas canvas which displays multiple slices
# along a single axis from a collection of 3D images.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import logging

log = logging.getLogger(__name__)

import wx

import numpy as np

import OpenGL.GL as gl

import props

import fsl.fslview.slicecanvas as slicecanvas


class LightBoxCanvas(slicecanvas.SliceCanvas):
    """
    An OpenGL canvas which displays multiple slices from a collection of 3D
    images (see fsl.data.fslimage.ImageList). The slices are laid out on the
    same canvas along rows and columns, with the slice at the minimum Z
    position translated to the top left of the canvas, and the slice with
    the maximum Z value translated to the bottom right.
    """

    # This property controls the spacing between
    # slices (in real world coordinates)
    sliceSpacing = props.Real(clamped=True, minval=0.1, default=1.0)

    # This property controls the number of slices
    # to be displayed on a single row.
    ncols = props.Int(clamped=True, minval=1, maxval=15, default=5)

    # These properties control the range, in world
    # coordinates, of the slices to be displayed
    zmin = props.Real(clamped=True)
    zmax = props.Real(clamped=True)

    _labels = {
        'zmin'         : 'First slice',
        'zmax'         : 'Last slice',
        'sliceSpacing' : 'Slice spacing',
        'ncols'        : 'Number of columns',
        'showCursor'   : 'Show cursor',
        'zax'          : 'Z axis'}

    _view = props.VGroup(('showCursor',
                          'zmin',
                          'zmax',
                          'sliceSpacing',
                          'ncols',
                          'zax'))

    
    def worldToCanvas(self, xpos, ypos, zpos):
        """
        Given an x/y/z location in the image list world (with xpos
        corresponding to the horizontal screen axis, ypos to the
        vertical axis, and zpos to the depth axis), converts
        it into an x/y position, in world coordinates, on the
        canvas.
        """
        sliceno = int(np.floor((zpos - self.zmin) / self.sliceSpacing))

        xlen = self.imageList.bounds.getLen(self.xax)
        ylen = self.imageList.bounds.getLen(self.yax)
        
        row = self._nrows - int(np.floor(sliceno / self.ncols)) - 1
        col =               int(np.floor(sliceno % self.ncols))

        xpos = xpos + xlen * col
        ypos = ypos + ylen * row
        
        return xpos, ypos

        
    def canvasToWorld(self, xpos, ypos):
        """
        Overrides SliceCanvas.canvasToWorld. Given pixel x/y
        coordinates on this canvas, translates them into the
        real world x/y/z coordinates of the displayed slice.
        Returns a 3-tuple containing the (x, y, z) coordinates
        (in the dimension order of the image list space). If the
        given canvas position is out of the image range, None
        is returned.
        """

        nrows = self._nrows
        ncols = self.ncols

        screenx, screeny = slicecanvas.SliceCanvas.canvasToWorld(
            self, xpos, ypos)

        xmin = self.imageList.bounds.getLo( self.xax)
        ymin = self.imageList.bounds.getLo( self.yax)
        xlen = self.imageList.bounds.getLen(self.xax)
        ylen = self.imageList.bounds.getLen(self.yax)

        xmax = xmin + ncols * xlen
        ymax = ymin + nrows * ylen

        col     =         int(np.floor((screenx - xmin) / xlen))
        row     = nrows - int(np.floor((screeny - ymin) / ylen)) - 1
        sliceno = row * ncols + col

        if screenx <  xmin or \
           screenx >  xmax or \
           screeny <  ymin or \
           screeny >  ymax or \
           sliceno <  0    or \
           sliceno >= self._nslices:
            return None

        xpos = screenx -          col      * xlen
        ypos = screeny - (nrows - row - 1) * ylen
        zpos = self.zmin + (sliceno + 0.5) * self.sliceSpacing

        pos = [0, 0, 0]
        pos[self.xax] = xpos
        pos[self.yax] = ypos
        pos[self.zax] = zpos

        return tuple(pos)

        
    def __init__(self,
                 parent,
                 imageList,
                 zax=2,
                 glContext=None,
                 scrollbar=None):
        """
        Create a LightBoxCanvas object. Parameters:
        
          - parent:    Parent wx object
        
          - imageList: a fsl.data.ImageList object which contains, or will
                       contain, a list of images to be displayed.
        
          - zax:       Image axis to be used as the 'depth' axis. Can be
                       changed via the LightBoxCanvas.zax property.

          - glContext: OpenGL context object. If None, one will be created.

          - scrollbar: A wx.ScrollBar object. If not provided, all slices
                       will be drawn on the screen.
        """

        if (scrollbar is not None) and (not scrollbar.IsVertical()):
            raise RuntimeError('LightBoxCanvas only supports '
                               'a vertical scrollbar')

        # These attributes are used to keep track of the total number
        # of displayed slices, the total number of rows, and the total
        # number of  rows displayed on the screen at once. If a
        # scrollbar was not passed in, all slices are displayed on the
        # canvas. Otherwise only a subset are displayed, but the user
        # is able to scroll through the slices. We're initialising
        # these attributes before SliceCanvas.__init__, because they
        # are required by the _updateDisplayBounds method, which ends
        # up getting called from SliceCanvas.__init__.
        self._scrollbar    = scrollbar
        self._nslices      = 0
        self._nrows        = 0
        self._rowsOnScreen = 0

        slicecanvas.SliceCanvas.__init__(
            self, parent, imageList, zax, glContext)

        if scrollbar is not None:

            # Trigger a redraw whenever the scrollbar is scrolled
            def onScroll(ev):

                # all slices are displayed on the screen
                # - the scrollbar is not currently needed
                if scrollbar.GetPageSize() >= scrollbar.GetRange():
                    scrollbar.SetThumbPosition(0)
                    
                # otherwise, figure out the area
                # to be displayed, and redraw
                else:
                    self._updateDisplayBounds()
                    self.Refresh()
                
            scrollbar.Bind(wx.EVT_SCROLL, onScroll)

        # default to showing the entire slice range
        self.zmin = imageList.bounds.zlo
        self.zmax = imageList.bounds.zhi

        # Pick a sensible default for the
        # slice spacing - the smallest pixdim
        # across all images in the list
        if len(imageList) > 0:
            self.sliceSpacing = min([i.pixdim[self.zax] for i in imageList])
 
        # Called when any of the slice properties
        # change. Regenerates slice locations and
        # display bounds, and redraws
        def sliceRangeChanged(*a):
            self._slicePropsChanged()
            self._updateDisplayBounds()
            self._genSliceLocations()
            self._updateScrollBar()
            self.Refresh()
        sliceRangeChanged()

        self.addListener('sliceSpacing',  self.name, sliceRangeChanged)
        self.addListener('ncols',         self.name, sliceRangeChanged)
        self.addListener('zmin',          self.name, sliceRangeChanged)
        self.addListener('zmax',          self.name, sliceRangeChanged)

        # Called on canvas resizes. Recalculates
        # the number of rows to be displayed, and
        # the display bounds, and redraws.
        def onResize(ev):
            self._slicePropsChanged()
            self._updateDisplayBounds()
            self._updateScrollBar()
            self.Refresh()
            ev.Skip()

        self.Bind(wx.EVT_SIZE, onResize)


    def _slicePropsChanged(self, *a):
        """
        Gets called whenever any of the properties which define the
        number and layout of the lightbox slices, change. Calculates
        the total number of slices to be displayed, the total number
        of rows, and the number of rows to be displayed on screen
        (which is different from the former if the canvas has a scroll
        bar).
        """
        
        xlen = self.imageList.bounds.getLen(self.xax)
        ylen = self.imageList.bounds.getLen(self.yax)
        zlen = self.zmax - self.zmin
        width, height = self.GetClientSize().Get()

        if xlen   == 0 or \
           ylen   == 0 or \
           width  == 0 or \
           height == 0:
            return

        self._nslices = int(np.floor(zlen / self.sliceSpacing))
        self._nrows   = int(np.ceil(self._nslices / float(self.ncols))) 

        # no scrollbar -> display all rows
        if self._scrollbar is None:
            self._rowsOnScreen = self._nrows

        # scrollbar -> display a selection of rows
        else:

            sliceWidth  = width / self.ncols
            sliceHeight = sliceWidth * (ylen / xlen)

            if sliceWidth == 0 or sliceHeight == 0:
                return

            self._rowsOnScreen = int(np.ceil(height / sliceHeight))

        if self._rowsOnScreen == 0:          self._rowsOnScreen = 1
        if self._rowsOnScreen > self._nrows: self._rowsOnScreen = self._nrows

        log.debug('{: 5.1f} - {: 5.1f}: slices={} rows={} ({} on screen) '
                  'columns={}'.format(self.zmin, self.zmax, self._nslices,
                                      self._nrows, self._rowsOnScreen,
                                      self.ncols))
        

    def _zAxisChanged(self, *a):
        """
        Overrides SliceCanvas._zAxisChanged. Called when the
        SliceCanvas.zax property changes. Calls the superclass
        implementation, and then sets the slice zmin/max bounds
        to the image bounds.
        """
        slicecanvas.SliceCanvas._zAxisChanged(self, *a)
        
        self.zmin = self.imageList.bounds.getLo(self.zax)
        self.zmax = self.imageList.bounds.getHi(self.zax)


    def _imageBoundsChanged(self, *a):
        """
        Overrides SliceCanvas._imageBoundsChanged. Called when
        the image bounds change. Updates the Z axis min/max values.
        """

        slicecanvas.SliceCanvas._imageBoundsChanged(self)

        imgzmin = self.imageList.bounds.getLo(self.zax)
        imgzmax = self.imageList.bounds.getHi(self.zax)

        self.setConstraint('zmin', 'minval', imgzmin)
        self.setConstraint('zmin', 'maxval', imgzmax)
        self.setConstraint('zmax', 'minval', imgzmin)
        self.setConstraint('zmax', 'maxval', imgzmax)

        # reset zmin/zmax in case they are
        # out of range of the new image bounds
        self.zmin = imgzmin
        self.zmax = imgzmax

        
    def _updateDisplayBounds(self):
        """
        Overrides SliceCanvas._updateDisplayBound. Called on
        canvas resizes, image bound changes and lightbox slice
        property changes. Calculates the required bounding box
        that is to be displayed, in real world coordinates.
        """

        xmin = self.imageList.bounds.getLo( self.xax)
        ymin = self.imageList.bounds.getLo( self.yax)
        xlen = self.imageList.bounds.getLen(self.xax)
        ylen = self.imageList.bounds.getLen(self.yax)

        if self._scrollbar is not None:

            off = (self._nrows -
                   self._scrollbar.GetThumbPosition() -
                   self._rowsOnScreen)

            ymin = ymin + ylen * off

        xmax = xmin + xlen * self.ncols
        ymax = ymin + ylen * self._rowsOnScreen

        slicecanvas.SliceCanvas._updateDisplayBounds(
            self, xmin, xmax, ymin, ymax)


    def _genSliceLocations(self):
        """
        Called when any of the slice display properties change. For every
        image in the image list, generates a list of transformation
        matrices, and a list of slice indices. The latter specifies the
        slice indices from the image to be displayed, and the former
        specifies the transformation matrix to be used to position the
        slice on the canvas.        
        """
        
        # calculate the locations, in real world coordinates,
        # of all slices to be displayed on the canvas
        sliceLocs = np.arange(
            self.zmin + self.sliceSpacing * 0.5,
            self.zmax,
            self.sliceSpacing)

        self._sliceIdxs  = []
        self._transforms = []

        # calculate the transformation for each
        # slice in each image, and the index of
        # each slice to be displayed
        for i, image in enumerate(self.imageList):
            
            self._transforms.append([])
            self._sliceIdxs .append([])

            for zi, zpos in enumerate(sliceLocs):

                imgZi = image.worldToVox(zpos, self.zax)
                xform = self._calculateSliceTransform(image, zi)

                self._transforms[-1].append(xform)
                self._sliceIdxs[ -1].append(imgZi)


    def _calculateSliceTransform(self, image, sliceno):
        """
        Calculates a transformation matrix for the given slice number
        (voxel index) in the given image. Each slice is displayed on
        the same canvas, but is translated to a specific row/column.
        So a copy of the voxToWorld transformation matrix of the given
        image is made, and a translation applied to it, to position 
        the slice in the correct location on the canvas.
        """

        nrows = self._nrows
        ncols = self.ncols

        xform = np.array(image.voxToWorldMat, dtype=np.float32)

        row = int(np.floor(sliceno / ncols))
        col = int(np.floor(sliceno % ncols))

        xlen = self.imageList.bounds.getLen(self.xax)
        ylen = self.imageList.bounds.getLen(self.yax)

        translate              = np.identity(4, dtype=np.float32)
        translate[3, self.xax] = xlen * col
        translate[3, self.yax] = ylen * (nrows - row - 1)
        translate[3, self.zax] = 0
        
        return xform.dot(translate)


    def _updateScrollBar(self):
        """
        If a scroll bar was passed in when this LightBoxCanvas was created,
        this method updates it to reflect the current state of the canvas
        size and the displayed list of slices.
        """
        
        if self._scrollbar is None: return
        
        if len(self.imageList) == 0:
            self._scrollbar.SetScrollbar(0, 0, 0, 0, True)
            return

        imgBounds  = self.imageList.bounds
        imgxlen    = imgBounds.getLen(self.xax)
        imgylen    = imgBounds.getLen(self.yax)
        dispBounds = self.displayBounds

        screenSize = self.GetClientSize()

        if screenSize.width  == 0 or \
           screenSize.height == 0 or \
           dispBounds.xlen   == 0 or \
           dispBounds.ylen   == 0 or \
           imgxlen           == 0 or \
           imgylen           == 0:
            return

        rowsOnScreen = self._rowsOnScreen
        oldPos       = self._scrollbar.GetThumbPosition()

        log.debug('Slice row: {}, '
                  'rows on screen: {} / {}'.format(
                      oldPos, rowsOnScreen, self._nrows))

        self._scrollbar.SetScrollbar(oldPos,
                                     rowsOnScreen,
                                     self._nrows,
                                     rowsOnScreen,
                                     True)


    def _drawCursor(self):
        """
        Draws a cursor at the current canvas position (the SliceCanvas.pos
        property).
        """
        
        sliceno = int(np.floor((self.pos.z - self.zmin) / self.sliceSpacing))
        xlen    = self.imageList.bounds.getLen(self.xax)
        ylen    = self.imageList.bounds.getLen(self.yax)
        xmin    = self.imageList.bounds.getLo( self.xax)
        ymin    = self.imageList.bounds.getLo( self.yax)
        row     = self._nrows - int(np.floor(sliceno / self.ncols)) - 1
        col     = int(np.floor(sliceno % self.ncols)) 

        xpos, ypos = self.worldToCanvas(*self.pos.xyz)

        xverts = np.zeros((2, 3))
        yverts = np.zeros((2, 3)) 

        xverts[:, self.xax] = xpos
        xverts[0, self.yax] = ymin + (row)     * ylen
        xverts[1, self.yax] = ymin + (row + 1) * ylen
        xverts[:, self.zax] = self.pos.z + 1

        yverts[:, self.yax] = ypos
        yverts[0, self.xax] = xmin + (col)     * xlen
        yverts[1, self.xax] = xmin + (col + 1) * xlen
        yverts[:, self.zax] = self.pos.z + 1

        gl.glBegin(gl.GL_LINES)
        gl.glColor3f(0, 1, 0)
        gl.glVertex3f(*xverts[0])
        gl.glVertex3f(*xverts[1])
        gl.glVertex3f(*yverts[0])
        gl.glVertex3f(*yverts[1])
        gl.glEnd() 

        
    def _draw(self, ev):
        """
        Draws the currently visible slices to the canvas.
        """

        # image data has not been initialised.
        if not self.glReady:
            wx.CallAfter(self._initGLData)
            return

        # No scrollbar -> draw all the slices 
        if self._scrollbar is None:
            startSlice = 0
            endSlice   = self._nslices

        # Scrollbar -> draw a selection of slices
        else:
            rowsOnScreen = self._scrollbar.GetPageSize()
            startRow     = self._scrollbar.GetThumbPosition()
            
            startSlice   = self.ncols * startRow
            endSlice     = startSlice + rowsOnScreen * self.ncols

            if endSlice > self._nslices:
                endSlice = self._nslices

        self.glContext.SetCurrent(self)
        self._setViewport()

        # clear the canvas
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        # load the shaders
        gl.glUseProgram(self.shaders)

        # enable transparency
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        # disable interpolation
        gl.glShadeModel(gl.GL_FLAT)

        # Draw all the slices for all the images.
        for i, image in enumerate(self.imageList):
            
            log.debug('Drawing {} slices ({} - {}) for image {}'.format(
                endSlice - startSlice, startSlice, endSlice, i))
            
            for zi in range(startSlice, endSlice):
                self._drawSlice(image,
                                self._sliceIdxs[ i][zi],
                                self._transforms[i][zi])

        gl.glUseProgram(0) 

        if self.showCursor:
            self._drawCursor()

        self.SwapBuffers()
