#!/usr/bin/env python
#
# __init__.py - Superclasses for objects which perform 'actions'.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This package provides a collection of actions, and two package-level
classes - the :class:`Action` class, and the :class:`ActionProvider` class.

The :class:`Action` class represents some sort of action which may be
performed, enabled and disabled, and may be bound to a GUI menu item or
button.

Some 'global' actions are provided in this package, for example the
:class:`~fsl.fslview.actions.openfile.OpenFileAction`, and the
:class:`~fsl.fslview.actions.openstandard.OpenStandardAction`.

The :class:`ActionProvider` class represents some entity which can perform
one or more actions.  As the :class:`~fsl.fslview.panel.FSLViewPanel` class
derives from :class:`ActionProvider` pretty much everything in FSLView is
an :class:`ActionProvider`.
"""


import logging
log = logging.getLogger(__name__)


import props


def listGlobalActions():
    """Convenience function which returns a list containing all
    :class:`~fsl.fslview.action.Action` classes in the :mod:`actions` package.
    """

    import openfile
    import openstandard
    import loadcolourmap

    OpenFileAction      = openfile     .OpenFileAction
    OpenStandardAction  = openstandard .OpenStandardAction
    LoadColourMapAction = loadcolourmap.LoadColourMapAction

    return [OpenFileAction, OpenStandardAction, LoadColourMapAction]


class Action(props.HasProperties):
    """Class which represents an action of some sort.

    The actual action which is performed may be specified either by
    specifying it it during initialisation (the ``action`` parameter to
    :meth:`__init__`), or by subclasses overriding the :meth:`doAction`
    method. The former method will take precedence over the latter.
    """

    
    enabled = props.Boolean(default=True)
    """Controls whether the action is currently enabled or disabled.
    When this property is ``False`` calls to :meth:`doAction` will
    result in a ``RuntimeError``.
    """

    
    def __init__(self, imageList, displayCtx, action=None):
        """
        :arg imageList:  A :class:`~fsl.data.image.ImageList` instance
                         containing the list of images being displayed.

        :arg displayCtx: A :class:`~fsl.fslview.displaycontext.DisplayContext`
                         instance defining how the images are to be displayed.
        """
        self._imageList        = imageList
        self._displayCtx       = displayCtx
        self._boundWidgets     = []
        
        if action is not None:
            self.doAction = action
            
        self.__enabledDoAction = self.doAction

        self.addListener('enabled',
                         'Action_{}_internal'.format(id(self)),
                         self._enabledChanged)

        
    def bindToWidget(self, parent, evType, widget):
        """Binds this action to the given :class:`wx.Button`. """

        def wrappedAction(ev):
            self.doAction()
            
        parent.Bind(evType, wrappedAction, widget)
        self._boundWidgets.append(widget)


    def _enabledChanged(self, *a):
        """Internal method which is called when the :attr:`enabled` property
        changes. Enables/disables the action, and any bound widgets.
        """
        if self.enabled: self.doAction = self.__enabledDoAction
        else:            self.doAction = self.__disabledDoAction

        for widget in self._boundWidgets:
            widget.Enable(self.enabled)


    def __disabledDoAction(self):
        """This method gets called when the action is disabled."""
        raise RuntimeError('{} is disabled'.format(self.__class__.__name__))
    

    def __enabledDoAction(self):
        """This method is set in :meth:`__init__`; it gets called when the
        action is enabled."""
        pass

    
    def doAction(self):
        """This method must be overridden by subclasses.

        It performs the action, or raises a ``RuntimeError`` if the action
        is disabled.
        """
        raise NotImplementedError('Action object must implement '
                                  'the doAction method') 


class ActionProvider(props.HasProperties):
    """An :class:`ActionProvider` is some entity which can perform actions.

    Said entity is also a :class:`~props.HasProperties` instance, so can
    optionally define some properties which, along with any defined actions,
    will ultimately be exposed to the user.
    """

    def __init__(self, imageList, displayCtx, actions=None):
        """Create an :class:`ActionProvider` instance.

        :arg imageList:  A :class:`~fsl.data.image.ImageList` instance
                         containing the list of images being displayed.

        :arg displayCtx: A :class:`~fsl.fslview.displaycontext.DisplayContext`
                         instance defining how the images are to be displayed. 

        :arg actions:    A dictionary containing ``{name -> function}``
                         mappings, where each function is an action that
                         should be made available to the user.
        """

        if actions is None:
            actions = {}

        self.__actions = {}

        for name, func in actions.items():
            act = Action(imageList, displayCtx, action=func)
            self.__actions[name] = act

            
    def addActionToggleListener(self, name, listenerName, func):
        """Add a listener function which will be called when the named action
        is enabled or disabled.
        """

        self.__actions[name].addListener('enabled', listenerName, func)

        
    def getActions(self):
        """Return a dictionary containing ``{name -> function}`` mappings for
        all defined actions.
        """
        return dict(self.__actions)


    def isEnabled(self, name):
        """Return ``True`` if the named action is enabled, ``False`` otherwise.
        """
        return self.__actions[name].enabled

    
    def enable(self, name, enable=True):
        """Enables/disables the named action. """ 
        self.__actions[name].enabled = enable

        
    def disable(self, name):
        """Disables the named action. """ 
        self.__actions[name].enabled = False


    def toggle(self, name):
        """Toggles the state of the named action. """ 
        self.__actions[name].enabled = not self.__actions[name].enabled


    def run(self, name):
        """Performs the named action."""
        self.__actions[name].doAction()
