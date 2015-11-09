#!/usr/bin/env python
#
# autotextctrl.py - The AutoTextCtrl class.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module provides the :class:`AutoTextCtrl` class, an alternative to the
``wx.TextCtrl``, which has auto-completion capability.

I wrote this class because ``wx.TextCtrl`` auto-completion does not work under
OSX, and the ``wx.ComboBox`` does not give me enough fine-grained control with
respect to managing focus.
"""


import wx
import wx.lib.newevent as wxevent


class AutoTextCtrl(wx.Panel):
    """The ``AutoTextCtrl`` class is essentially a ``wx.TextCtrl`` which is able
    to dynamically show a list of options to the user, with a
    :class:`AutoCompletePopup`.
    """

    
    def __init__(self, parent, style=0):
        """Create an ``AutoTextCtrl``.

        :arg parent: The ``wx`` parent object.
        :arg style:  Can be :data:`ATC_CASE_SENSITIVE` to restrict the
                     auto-completion options to case sensitive matches.
        """

        self.__caseSensitive = style & ATC_CASE_SENSITIVE
        
        wx.Panel.__init__(self, parent)

        self.__textCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.__sizer    = wx.BoxSizer(wx.HORIZONTAL)
        
        self.__sizer.Add(self.__textCtrl, flag=wx.EXPAND, proportion=1)
        self.SetSizer(self.__sizer)
        
        self.__options = []

        self.__textCtrl.Bind(wx.EVT_TEXT,       self.__onText)
        self.__textCtrl.Bind(wx.EVT_TEXT_ENTER, self.__onEnter)

        
    def AutoComplete(self, options):
        """Set the list of options to be shown to the user. """
        self.__options = list(options)


    def GetValue(self):
        """Returns the current value shown on this ``AutoTextCtrl``. """
        return self.__textCtrl.GetValue()

        
    def SetValue(self, value):
        """Sets the current value shown on this ``AutoTextCtrl``.

        .. note:: Calling this method will result in an ``wx.EVT_TEXT``
                  event being generated - use :meth:`ChangeValue` if you
                  do not want this to occur.
        """
        self.__textCtrl.SetValue(value)

        
    def ChangeValue(self, value):
        """Sets the current value shown on this ``AutoTextCtrl``. """
        self.__textCtrl.ChangeValue(value) 


    def __onText(self, ev):
        """Called when the user changes the text shown on this ``AutoTextCtrl``.
        Creates an :class:`AutoCompletePopup`.
        """

        text = self.__textCtrl.GetValue()
        self.__showPopup(text)


    def __onEnter(self, ev):
        """Called when the user presses enter in this ``AutoTextCtrl``. Generates
        an :data:`EVT_ATC_TEXT_ENTER` event.
        """
        value = self.__textCtrl.GetValue()
        ev = AutoTextCtrlEnterEvent(text=value)
        wx.PostEvent(self, ev)


    def __showPopup(self, text):
        """Creates an :class:`AutoCompletePopup` which displays a list of
        auto-completion options, matching the given prefix text, to the user.

        The popup is not displayed if there are no options with the given
        prefix.
        """

        text  = text.strip()
        style = 0
        
        if self.__caseSensitive:
            style |= ATC_CASE_SENSITIVE

        popup  = AutoCompletePopup(
            self,
            self,
            text,
            self.__options,
            style)

        if popup.GetCount() == 0:
            popup.Destroy()
            return

        # Make sure we get the focus back 
        # when the popup is destroyed
        def refocus(ev):
            self.GetTopLevelParent().Raise()
            self.__textCtrl.SetFocus()
            self.__textCtrl.SetInsertionPointEnd()

        popup.Bind(wx.EVT_WINDOW_DESTROY, refocus)

        # The popup has its own textctrl - we
        # position the popup so that its textctrl
        # is displayed on top of our textctrl,
        # with the option list underneath.
        width, height = self.__textCtrl.GetSize().Get()
        posx, posy    = self.__textCtrl.GetScreenPosition().Get()

        popup.SetSize((width, -1))
        popup.SetPosition((posx,  posy))
        popup.Show()


ATC_CASE_SENSITIVE = 1
"""Syle flag for use with the :class:`AutoTextCtrl` class. If set, the
auto-completion pattern matching will be case sensitive.
"""

        
_AutoTextCtrlEnterEvent, _EVT_ATC_TEXT_ENTER = wxevent.NewEvent()


EVT_ATC_TEXT_ENTER = _EVT_ATC_TEXT_ENTER
"""Identifier for the :data:`AutoTextCtrlEnterEvent`, which is generated
when the user presses enter in an :class:`AutoTextCtrl`.
"""


AutoTextCtrlEnterEvent = _AutoTextCtrlEnterEvent
"""Event generated when the user presses enter in an :class:`AutoTextCtrl`.
Contains a single attribute, ``text``, which contains the text in the
``AutoTextCtrl``.
"""


class AutoCompletePopup(wx.PopupWindow):
    """The ``AutoCompletePopup`` class is used by the :class:`AutoTextCtrl`
    to display a list of completion options to the user.
    """

    def __init__(self, parent, atc, text, options, style=0):
        """Create an ``AutoCompletePopup``.

        :arg parent:  The ``wx`` parent object.
        :arg atc:     The :class:`AutoTextCtrl` that is using this popup.
        :arg text:    Initial text value.
        :arg options: A list of all possible auto-completion options.
        :arg style:   Set to :data:`ATC_CASE_SENSITIVE` to make the
                      pattern matching case sensitive.
        """

        wx.PopupWindow.__init__(self, parent)

        self.__caseSensitive = style & ATC_CASE_SENSITIVE
        self.__atc           = atc
        self.__options       = options
        self.__textCtrl      = wx.TextCtrl(self, style=(wx.TE_PROCESS_ENTER |
                                                        wx.WANTS_CHARS))
        self.__listBox       = wx.ListBox(self,  style=(wx.LB_SINGLE        |
                                                        wx.WANTS_CHARS))
        
        self.__listBox .Set(self.__getMatches(text))
        self.__textCtrl.SetValue(text)
        self.__textCtrl.SetInsertionPointEnd()

        self.__sizer = wx.BoxSizer(wx.VERTICAL)
        self.__sizer.Add(self.__textCtrl, flag=wx.EXPAND)
        self.__sizer.Add(self.__listBox,  flag=wx.EXPAND, proportion=1)
        self.SetSizer(self.__sizer)

        self.Layout()
        self.Fit()

        self.__textCtrl.Bind(wx.EVT_TEXT,           self.__onText)
        self.__textCtrl.Bind(wx.EVT_TEXT_ENTER,     self.__onEnter)
        self.__textCtrl.Bind(wx.EVT_CHAR_HOOK,      self.__onChar)
        self.__listBox .Bind(wx.EVT_CHAR_HOOK,      self.__onListChar)
        self.__listBox .Bind(wx.EVT_LISTBOX_DCLICK, self.__onListMouseDblClick)
        
        self           .Bind(wx.EVT_KILL_FOCUS,     self.__onKillFocus)
        self.__textCtrl.Bind(wx.EVT_KILL_FOCUS,     self.__onKillFocus)
        self.__listBox .Bind(wx.EVT_KILL_FOCUS,     self.__onKillFocus)

        
    def GetCount(self):
        """Returns the number of auto-completion options currently available.
        """
        return self.__listBox.GetCount()
        

    def __onKillFocus(self, ev):
        """Called when this ``AutoCompletePopup`` loses focus. Calls
        :meth:`__destroy`.
        """

        objs = (self, self.__textCtrl, self.__listBox)
        
        if wx.Window.FindFocus() not in objs:
            self.__destroy()

        
    def __destroy(self):
        """Called by various event handlers. Copies the current value in
        this ``AutoCompletePopup`` to the owning :class:`AutoTextCtrl`,
        and then (asynchronously) destroys this ``AutoCompletePopup``.
        """
        value = self.__textCtrl.GetValue()
        atc   = self.__atc
        atc.ChangeValue(value)
        
        def destroy():
            try:
                self.Close()
                self.Destroy()
                
            except wx.PyDeadObjectError:
                pass

        wx.CallAfter(destroy)


    def __getMatches(self, prefix):
        """Returns a list of auto-completion options which match the given
        prefix.
        """
        
        prefix  = prefix.strip()
        options = self.__options

        if not self.__caseSensitive:
            prefix  = prefix.lower()
            options = [o.lower() for o in options]
                
        matches = [o.startswith(prefix) for o in options]

        if len(prefix) == 0 or len(options) == 0 or options[0] == prefix:
            return []

        return [o for o, m in zip(self.__options, matches) if m]


    def __onChar(self, ev):
        """Called on an ``EVT_CHAR_HOOK`` event from the text control. """
        
        down  = wx.WXK_DOWN
        esc   = wx.WXK_ESCAPE
        enter = wx.WXK_RETURN
        key   = ev.GetKeyCode()

        if key not in (down, enter, esc):
            ev.Skip()
            return

        # The user hitting enter/escape will result
        # in this popup being destroyed
        if key in (esc, enter):
            self.__destroy()
            return

        # If the user hits the down 
        # arrow, focus the listbox
        self.__listBox.SetFocus()
        self.__listBox.SetSelection(0)
                

    def __onText(self, ev):
        """Called on an ``EVT_TEXT`` event from the text control."""
        
        text    = self.__textCtrl.GetValue()
        matches = self.__getMatches(text)
        
        if len(matches) == 0: self.__destroy()
        else:                 self.__listBox.Set(matches)


    def __onEnter(self, ev):
        """Called on an ``EVT_TEXT_ENTER`` event from the text control."""
        self.__destroy()


    def __onListChar(self, ev):
        """Called on an ``EVT_CHAR_HOOK`` event from the list box.
        """
        key   = ev.GetKeyCode()
        enter = wx.WXK_RETURN
        esc   = wx.WXK_ESCAPE
        up    = wx.WXK_UP

        if key not in (enter, esc, up):
            ev.Skip()
            return

        sel = self.__listBox.GetSelection()
        val = self.__listBox.GetString(sel)

        # If the user pushed the up arrow,
        # and we're at the top of the list,
        # give the focus to the text control
        if key == up:
            if sel == 0:
                self.__textCtrl.SetFocus()
            else:
                ev.Skip()
            return

        # If the user pushed enter, copy
        # the current list selection to
        # the text control.
        if key == enter:
            self.__textCtrl.SetValue(val)

        # The user hitting enter or escape
        # will result in this popup being
        # destroyed
        self.__destroy()


    def __onListMouseDblClick(self, ev):
        """Called when the user double clicks an item in the list box. """
        ev.Skip()
        
        sel = self.__listBox.GetSelection()
        val = self.__listBox.GetString(sel)

        self.__textCtrl.SetValue(val)
        self.__destroy()
