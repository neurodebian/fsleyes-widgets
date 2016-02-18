#!/usr/bin/env python
#
# floatspin.py - Alternate implementation to wx.SpinCtrlDouble and
#                wx.lib.agw.floatspin.FloatSpin.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module provides the :class:`FloatSpinCtrl` class, a spin control for
modifying a floating point value.
"""


import re
import logging

import                    wx
import wx.lib.newevent as wxevent


log = logging.getLogger(__name__)


class FloatSpinCtrl(wx.Panel):
    """A ``FloatSpinCtrl`` is a :class:`wx.Panel` which contains a
    :class:`wx.TextCtrl` and a :class:`wx.SpinButton`, allowing the user to
    modify a floating point (or integer) value.

    The ``FloatSpinCtrl`` is an alternative to :class:`wx.SpinCtrl`,
    :class:`wx.SpinCtrlDouble`, and :class:`wx.lib.agw.floatspin.FloatSpin`.

     - :class:`wx.SpinCtrlDouble`: Under Linux/GTK, this widget does not allow
        the user to enter values that are not a multiple of the increment.

     - :class:`wx.lib.agw.floatspin.FloatSpin`. Differs from the
       :class:`wx.SpinCtrl` API in various annoying ways, and formatting is a
       pain.
    """

    def __init__(self,
                 parent,
                 minValue=0,
                 maxValue=100,
                 increment=1,
                 value=0,
                 style=0):
        """Create a ``FloatSpinCtrl``.

        The following style flags are available:
          .. autosummary::
             FSC_MOUSEWHEEL
             FSC_INTEGER
             FSC_NO_LIMIT

        :arg parent:    The parent of this control (e.g. a :class:`wx.Panel`).

        :arg minValue:  Initial minimum value.

        :arg maxValue:  Initial maximum value.

        :arg increment: Default increment to apply when the user changes the
                        value via the spin button or mouse wheel.

        :arg value:     Initial value.

        :arg style:     Style flags - a combination of :data:`FSC_MOUSEWHEEL`,
                        :data:`FSC_INTEGER`, and :data:`FSC_NO_LIMIT`.
        """
        wx.Panel.__init__(self, parent)

        self.__integer = style & FSC_INTEGER
        self.__nolimit = style & FSC_NO_LIMIT

        # The value is set at the
        # end of this method
        self.__value     = None
        self.__increment = increment
        self.__realMin   = float(minValue)
        self.__realMax   = float(maxValue)
        self.__realRange = abs(self.__realMax - self.__realMin)

        # We use the full signed 32 bit integer
        # range offered by the wx.SpinButton class.
        self.__realSpinMin = -2 ** 31
        self.__realSpinMax =  2 ** 31 - 1

        # Unless the no limit style has been
        # specified, in which case we map the
        # real data range to 16 bits, and
        # allow the rest of the 32 bit range
        # to account for overflow. In either
        # case, the spin button is configured
        # to use the full 32 bit range.
        if  self.__nolimit:
            self.__spinMin = -2 ** 15
            self.__spinMax =  2 ** 15 - 1
        else:
            self.__spinMin = self.__realSpinMin
            self.__spinMax = self.__realSpinMax
            
        self.__spinRange = abs(self.__spinMax - self.__spinMin)

        self.__text = wx.TextCtrl(  self,
                                    style=wx.TE_PROCESS_ENTER)
        self.__spin = wx.SpinButton(self,
                                    style=wx.SP_VERTICAL | wx.SP_ARROW_KEYS)

        self.__spin.SetRange(self.__realSpinMin, self.__realSpinMax)

        if self.__integer:
            self.__format      = '{:d}'
            self.__textPattern = re.compile('^-?[0-9]*$')
        else:
            self.__format      = '{:.7G}'
            self.__textPattern = re.compile('^-?[0-9]*\.?[0-9]*$')

        # Events on key down, enter, focus
        # lost, and on the spin control
        self.__text.Bind(wx.EVT_KEY_DOWN,   self.__onKeyDown)
        self.__text.Bind(wx.EVT_TEXT_ENTER, self.__onText)
        self.__text.Bind(wx.EVT_KILL_FOCUS, self.__onKillFocus)
        self.__spin.Bind(wx.EVT_SPIN_UP,    self.__onSpinUp)
        self.__spin.Bind(wx.EVT_SPIN_DOWN,  self.__onSpinDown)

        # Event on mousewheel
        # if style enabled
        if style & FSC_MOUSEWHEEL:
            self.__spin.Bind(wx.EVT_MOUSEWHEEL, self.__onMouseWheel)
            self.__text.Bind(wx.EVT_MOUSEWHEEL, self.__onMouseWheel)

        # Under linux/GTK, text controls absorb
        # mousewheel events, so we bind our own
        # handler to prevent this.
        elif wx.Platform == '__WXGTK__':
            def wheel(ev):
                self.GetParent().GetEventHandler().ProcessEvent(ev)
            self.__spin.Bind(wx.EVT_MOUSEWHEEL, wheel)
            self.__text.Bind(wx.EVT_MOUSEWHEEL, wheel)

        # Under linux/GTK, double-clicking the
        # textctrl selects the word underneath
        # the cursor, whereas we want it to
        # select the entire textctrl contents.
        # Mouse event behaviour cannot be overridden
        # under OSX, but its behaviour is more
        # sensible, so a hack is not necessary.
        if wx.Platform == '__WXGTK__':
            self.__text.Bind(wx.EVT_LEFT_DCLICK, self.__onDoubleClick)

        self.__sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.__sizer.Add(self.__text, flag=wx.EXPAND, proportion=1)
        self.__sizer.Add(self.__spin)
        
        self.SetSizer(self.__sizer)

        # Under linus/GTK, calling spin.SetValue()
        # from within an EVT_SPIN event handler
        # seems to generate another EVT_SPIN event,
        # which triggers an infinite recursive loop.
        # The skipSpin attribute  is used as an
        # internal semaphore in the SetValue method,
        # telling it not to update the spin button
        # value.
        self.__skipSpin = False

        self.SetRange(minValue, maxValue)
        self.SetValue(value)
        self.SetIncrement(increment)

    
    def GetValue(self):
        """Returns the current value."""
        return self.__value
    

    def GetMin(self):
        """Returns the current minimum value."""
        return float(self.__realMin)

    
    def GetMax(self):
        """Returns the current maximum value."""
        return float(self.__realMax)


    def GetIncrement(self):
        """Returns the current inrement."""
        return self.__increment


    def SetIncrement(self, inc):
        """Sets the inrement."""
        if self.__integer: self.__increment = int(round(inc))
        else:              self.__increment =           inc

        
    def GetRange(self):
        """Returns the current data range, a tuple containing the
        ``(min, max)`` values.
        """
        return (self.__realMin, self.__realMax)


    def SetMin(self, minval):
        """Sets the minimum value."""
        self.SetRange(minval, self.__realMax)

    
    def SetMax(self, maxval):
        """Sets the maximum value."""
        self.SetRange(self.__realMin, maxval)

    
    def SetRange(self, minval, maxval):
        """Sets the minimum and maximum values."""

            
        if self.__integer:
            minval = int(round(minval))
            maxval = int(round(maxval))
            inc    = 1
        else:
            inc = (maxval - minval) / 100.0

        if minval >= maxval:
            maxval = minval + 1

        self.__realMin   = float(minval)
        self.__realMax   = float(maxval)
        self.__realRange = abs(self.__realMax - self.__realMin)
        self.__increment = inc

        self.SetValue(self.__value)

    
    def SetValue(self, value):
        """Sets the value.

        :returns ``True`` if the value was changed, ``False`` otherwise.
        """

        if value == self.__value:
            return

        # Throttle the value so it stays
        # within the min/max, unless the 
        # FSC_NO_LIMIT style flag is set.
        if not self.__nolimit:
            if value < self.__realMin: value = self.__realMin
            if value > self.__realMax: value = self.__realMax

        if self.__integer:
            value = int(round(value))
        
        oldValue     = self.__value
        self.__value = value

        self.__text.ChangeValue(self.__format.format(value))

        if not self.__skipSpin:
            self.__spin.SetValue(self.__realToSpin(value))

        return value != oldValue


    def __onKillFocus(self, ev):
        """Called when the text field of this ``FloatSpinCtrl`` loses focus.
        Generates an :attr:`.EVT_FLOATSPIN` event.
        """
        ev.Skip()

        log.debug('Spin lost focus - simulating text event')
        self.__onText(ev)


    def __onKeyDown(self, ev):
        """Called on ``wx.EVT_KEY_DOWN`` events. If the user pushes the up or
        down arrow keys, the value is changed (using the :meth:`__onSpinUp`
        and :meth:`__onSpinDown` methods).
        """
        up   = wx.WXK_UP
        down = wx.WXK_DOWN
        key  = ev.GetKeyCode()

        log.debug('Key down event: {} (looking for up [{}] '
                  'or down [{}])'.format(key, up, down))

        if   key == up:   self.__onSpinUp()
        elif key == down: self.__onSpinDown()
        else:             ev.Skip()

        
    def __onText(self, ev):
        """Called when the user changes the value via the text control.

        This method is called when the enter key is pressed.

        If the value has changed, a :data:`FloatSpinEvent` is generated.
        """

        val = self.__text.GetValue().strip()
        
        if self.__textPattern.match(val) is None:
            self.SetValue(self.__value)
            return

        log.debug('Spin text - attempting to change value '
                  'from {} to {}'.format(self.__value, val))

        try:
            if self.__integer: val = int(  val)
            else:              val = float(val)
        except:
            self.SetValue(self.__value)
            return

        if self.SetValue(val):
            wx.PostEvent(self, FloatSpinEvent(value=self.__value)) 


    def __onSpinDown(self, ev=None):
        """Called when the *down* button on the ``wx.SpinButton`` is pushed.

        Decrements the value by the current increment and generates a
        :data:`FloatSpinEvent`.
        """
        
        log.debug('Spin down button - attempting to change value '
                  'from {} to {}'.format(self.__value,
                                         self.__value - self.__increment))

        self.__skipSpin = True
        
        if self.SetValue(self.__value - self.__increment):
            wx.PostEvent(self, FloatSpinEvent(value=self.__value))
            
        self.__skipSpin = False

        
    def __onSpinUp(self, ev=None):
        """Called when the *up* button on the ``wx.SpinButton`` is pushed.

        Increments the value by the current increment and generates a
        :data:`FloatSpinEvent`.
        """
        
        log.debug('Spin up button - attempting to change value '
                  'from {} to {}'.format(self.__value,
                                         self.__value + self.__increment))

        self.__skipSpin = True

        try:
            if self.SetValue(self.__value + self.__increment):
                wx.PostEvent(self, FloatSpinEvent(value=self.__value))
        finally:
            self.__skipSpin = False


    def __onMouseWheel(self, ev):
        """If the :data:`FSC_MOUSEWHEEL` style flag is set, this method is
        called on mouse wheel events.

        Calls :meth:`__onSpinUp` on an upwards rotation, and
        :meth:`__onSpinDown` on a downwards rotation.
        """

        log.debug('Mouse wheel - delegating to spin event handlers')

        rot = ev.GetWheelRotation()

        if ev.GetWheelAxis() == wx.MOUSE_WHEEL_HORIZONTAL:
            rot = -rot

        if   rot > 0: self.__onSpinUp()
        elif rot < 0: self.__onSpinDown()


    def __onDoubleClick(self, ev):
        """Called when the user double clicks in the ``TextCtrl``. Selects
        the entire contents of the ``TextCtrl``.
        """
        self.__text.SelectAll()

        
    def __realToSpin(self, value):
        """Converts the given value from real space to spin button space."""

        if self.__integer:
            value = int(round(value))

        value     = float(value)
        spinMin   = float(self.__spinMin)
        realMin   = float(self.__realMin)
        realRange = float(self.__realRange)
        spinRange = float(self.__spinRange)

        value     = spinMin + (value - realMin) * (spinRange / realRange)

        # Don't allow the value to flow over
        # the real wx.SpinButton range.
        if   value < self.__realSpinMin: value = self.__realSpinMin
        elif value > self.__realSpinMax: value = self.__realSpinMax
        
        return int(round(value))        


_FloatSpinEvent, _EVT_FLOATSPIN = wxevent.NewEvent()


EVT_FLOATSPIN = _EVT_FLOATSPIN
"""Identifier for the :data:`FloatSpinEvent` event. """


FloatSpinEvent = _FloatSpinEvent
"""Event emitted when the floating point value is changed by the user. A
``FloatSpinEvent`` has the following attributes:

  - ``value``: The new value.
"""


FSC_MOUSEWHEEL = 1
"""If set, mouse wheel events on the control will change the value. """


FSC_INTEGER = 2
"""If set, the control stores an integer value, rather than a floating point
value.
"""

FSC_NO_LIMIT = 4
"""If set, the control will allow the user to enter values that are outside
of the current minimum/maximum limits.
"""
