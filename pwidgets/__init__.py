#!/usr/bin/env python
#
# __init__.py - Custom wx widgets used by the props package.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""The ``pwidgets`` (short for *props widgets*) package contains various
custom :mod:`wx` widgets used by the :mod:`props` package.  None of the
widgets defined in this package have any dependency on ``props`` - they are
standalone controls which can be used in any application.


Some of the controls in ``pwidgets`` are duplicates of controls which are
already available in ``wx`` or ``wx.lib.agw``. In these instances, I wrote my
own implementations to work around annoying, quirky, and/or downright buggy
behaviour in the existing controls. The following controls are available:


 .. autosummary::
    :nosignatures:

    ~pwidgets.texttag.AutoTextCtrl
    ~pwidgets.bitmapradio.BitmapRadioBox
    ~pwidgets.bitmaptoggle.BitmapToggleButton
    ~pwidgets.colourbutton.ColourButton
    ~pwidgets.elistbox.EditableListBox
    ~pwidgets.floatslider.FloatSlider
    ~pwidgets.floatspin.FloatSpinCtrl
    ~pwidgets.notebook.Notebook
    ~pwidgets.numberdialog.NumberDialog
    ~pwidgets.rangeslider.RangePanel
    ~pwidgets.rangeslider.RangeSliderSpinPanel
    ~pwidgets.floatslider.SliderSpinPanel
    ~pwidgets.texttag.StaticTextTag
    ~pwidgets.texttag.TextTagPanel
    ~pwidgets.widgetgrid.WidgetGrid
    ~pwidgets.widgetlist.WidgetList
"""
