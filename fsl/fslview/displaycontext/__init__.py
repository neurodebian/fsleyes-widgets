#!/usr/bin/env python
#
# __init__.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#


import display


from displaycontext import DisplayContext
from display        import Display
from sceneopts      import SceneOpts
from orthoopts      import OrthoOpts
from lightboxopts   import LightBoxOpts
from volumeopts     import VolumeOpts
from maskopts       import MaskOpts
from vectoropts     import VectorOpts
from vectoropts     import LineVectorOpts
from modelopts      import ModelOpts


ALL_OVERLAY_TYPES = list(set(
    reduce(lambda a, b: a + b,
           display.OVERLAY_TYPES.values())))
"""This attribute contains a list of all possible overlay types - see the :
:attr:`.Display.overlayType` property.
"""
