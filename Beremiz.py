#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of Beremiz, a Integrated Development Environment for
#programming IEC 61131-3 automates supporting plcopen standard and CanFestival. 
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


updateinfo_url = None

import os, sys, getopt, wx
import __builtin__
from wx.lib.agw.advancedsplash import AdvancedSplash
import tempfile
import shutil
import random
import time
from types import ListType

CWD = os.path.split(os.path.realpath(__file__))[0]

def Bpath(*args):
    return os.path.join(CWD,*args)

if __name__ == '__main__':
    def usage():
        print "\nUsage of Beremiz.py :"
        print "\n   %s [Projectpath] [Buildpath]\n"%sys.argv[0]
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:e:", ["help", "updatecheck=", "extend="])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)

    extensions=[]
        
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-u", "--updatecheck"):
            updateinfo_url = a
        if o in ("-e", "--extend"):
            extensions.append(a)
    
    if len(args) > 2:
        usage()
        sys.exit()
    elif len(args) == 1:
        projectOpen = args[0]
        buildpath = None
    elif len(args) == 2:
        projectOpen = args[0]
        buildpath = args[1]
    else:
        projectOpen = None
        buildpath = None
    
    if os.path.exists("BEREMIZ_DEBUG"):
        __builtin__.__dict__["BMZ_DBG"] = True
    else :
        __builtin__.__dict__["BMZ_DBG"] = False

    app = wx.PySimpleApp(redirect=BMZ_DBG)
    app.SetAppName('beremiz')
    wx.InitAllImageHandlers()
    
    # popup splash
    bmp = wx.Image(Bpath("images", "splash.png")).ConvertToBitmap()
    #splash=AdvancedSplash(None, bitmap=bmp, style=wx.SPLASH_CENTRE_ON_SCREEN, timeout=4000)
    splash=AdvancedSplash(None, bitmap=bmp)
    wx.Yield()

    if updateinfo_url is not None:
        updateinfo = "Fetching %s" % updateinfo_url
        # warn for possible updates
        def updateinfoproc():
            global updateinfo
            try :
                import urllib2
                updateinfo = urllib2.urlopen(updateinfo_url,None).read()
            except :
                updateinfo = "update info unavailable." 
                
        from threading import Thread
        splash.SetText(text=updateinfo)
        wx.Yield()
        updateinfoThread = Thread(target=updateinfoproc)
        updateinfoThread.start()
        updateinfoThread.join(2)
        splash.SetText(text=updateinfo)
        wx.Yield()

from util.TranslationCatalogs import AddCatalog
from util.BitmapLibrary import AddBitmapFolder, GetBitmap

AddCatalog(os.path.join(CWD, "locale"))
AddBitmapFolder(os.path.join(CWD, "images"))

if __name__ == '__main__':
    # Import module for internationalization
    import gettext
    
    __builtin__.__dict__['_'] = wx.GetTranslation
    
    # Load extensions
    for extfilename in extensions:
        extension_folder = os.path.split(os.path.realpath(extfilename))[0]
        sys.path.append(extension_folder)
        AddCatalog(os.path.join(extension_folder, "locale"))
        AddBitmapFolder(os.path.join(extension_folder, "images"))
        execfile(extfilename, locals())

import wx.lib.buttons, wx.lib.statbmp, wx.stc
import cPickle
import types, time, re, platform, time, traceback, commands

from docutil import OpenHtmlFrame
from IDEFrame import IDEFrame, AppendMenu
from IDEFrame import TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU, DISPLAYMENU, PROJECTTREE, POUINSTANCEVARIABLESPANEL, LIBRARYTREE, SCALING, PAGETITLES 
from IDEFrame import EncodeFileSystemPath, DecodeFileSystemPath
from editors.EditorPanel import EditorPanel
from editors.Viewer import Viewer
from editors.TextViewer import TextViewer
from editors.GraphicViewer import GraphicViewer
from editors.ResourceEditor import ConfigurationEditor, ResourceEditor
from editors.DataTypeEditor import DataTypeEditor
from util.MiniTextControler import MiniTextControler
from util.ProcessLogger import ProcessLogger
from controls.LogViewer import LogViewer
from controls.CustomStyledTextCtrl import CustomStyledTextCtrl

from PLCControler import LOCATION_CONFNODE, LOCATION_MODULE, LOCATION_GROUP, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY, ITEM_PROJECT, ITEM_RESOURCE
from ProjectController import ProjectController, GetAddMenuItems, MATIEC_ERROR_MODEL, ITEM_CONFNODE


MAX_RECENT_PROJECTS = 10

if wx.Platform == '__WXMSW__':
    faces = {
        'mono' : 'Courier New',
        'size' : 8,
    }
else:
    faces = {
        'mono' : 'Courier',
        'size' : 10,
    }

from threading import Lock,Timer,currentThread
MainThread = currentThread().ident
REFRESH_PERIOD = 0.1
from time import time as gettime
class LogPseudoFile:
    """ Base class for file like objects to facilitate StdOut for the Shell."""
    def __init__(self, output, risecall):
        self.red_white = 1
        self.red_yellow = 2
        self.black_white = wx.stc.STC_STYLE_DEFAULT
        self.output = output
        self.risecall = risecall
        # to prevent rapid fire on rising log panel
        self.rising_timer = 0
        self.lock = Lock()
        self.YieldLock = Lock()
        self.RefreshLock = Lock()
        self.TimerAccessLock = Lock()
        self.stack = []
        self.LastRefreshTime = gettime()
        self.LastRefreshTimer = None

    def write(self, s, style = None):
        if self.lock.acquire():
            self.stack.append((s,style))
            self.lock.release()
            current_time = gettime()
            self.TimerAccessLock.acquire()
            if self.LastRefreshTimer:
                self.LastRefreshTimer.cancel()
                self.LastRefreshTimer=None
            self.TimerAccessLock.release()
            if current_time - self.LastRefreshTime > REFRESH_PERIOD and self.RefreshLock.acquire(False):
                self._should_write()
            else:
                self.TimerAccessLock.acquire()
                self.LastRefreshTimer = Timer(REFRESH_PERIOD, self._timer_expired)
                self.LastRefreshTimer.start()
                self.TimerAccessLock.release()

    def _timer_expired(self):
        if self.RefreshLock.acquire(False):
            self._should_write()
        else:
            self.TimerAccessLock.acquire()
            self.LastRefreshTimer = Timer(REFRESH_PERIOD, self._timer_expired)
            self.LastRefreshTimer.start()
            self.TimerAccessLock.release()

    def _should_write(self):
        wx.CallAfter(self._write)
        if MainThread == currentThread().ident:
            app = wx.GetApp()
            if app is not None:
                if self.YieldLock.acquire(0):
                    app.Yield()
                    self.YieldLock.release()

    def _write(self):
        if self.output :
            self.output.Freeze()
            self.lock.acquire()
            for s, style in self.stack:
                if style is None : style=self.black_white
                if style != self.black_white:
                    self.output.StartStyling(self.output.GetLength(), 0xff)
                
                # Temporary deactivate read only mode on StyledTextCtrl for
                # adding text. It seems that text modifications, even 
                # programmatically, are disabled in StyledTextCtrl when read
                # only is active 
                self.output.SetReadOnly(False)
                self.output.AppendText(s)
                self.output.SetReadOnly(True)
                
                if style != self.black_white:
                    self.output.SetStyling(len(s), style)
            self.stack = []
            self.lock.release()
            self.output.Thaw()
            self.LastRefreshTime = gettime()
            try:
                self.RefreshLock.release()
            except:
                pass
            newtime = time.time()
            if newtime - self.rising_timer > 1:
                self.risecall(self.output)
            self.rising_timer = newtime
        
    def write_warning(self, s):
        self.write(s,self.red_white)

    def write_error(self, s):
        self.write(s,self.red_yellow)

    def writeyield(self, s):
        self.write(s)
        wx.GetApp().Yield()

    def flush(self):
        # Temporary deactivate read only mode on StyledTextCtrl for clearing
        # text. It seems that text modifications, even programmatically, are
        # disabled in StyledTextCtrl when read only is active 
        self.output.SetReadOnly(False)
        self.output.SetText("")
        self.output.SetReadOnly(True)
    
    def isatty(self):
        return False

ID_FILEMENURECENTPROJECTS = wx.NewId()

class Beremiz(IDEFrame):
    
    def _init_utils(self):
        self.ConfNodeMenu = wx.Menu(title='')
        self.RecentProjectsMenu = wx.Menu(title='')
        
        IDEFrame._init_utils(self)
        
    def _init_coll_FileMenu_Items(self, parent):
        AppendMenu(parent, help='', id=wx.ID_NEW,
              kind=wx.ITEM_NORMAL, text=_(u'New') + '\tCTRL+N')
        AppendMenu(parent, help='', id=wx.ID_OPEN,
              kind=wx.ITEM_NORMAL, text=_(u'Open') + '\tCTRL+O')
        parent.AppendMenu(ID_FILEMENURECENTPROJECTS, _("&Recent Projects"), self.RecentProjectsMenu)
        parent.AppendSeparator()
        AppendMenu(parent, help='', id=wx.ID_SAVE,
              kind=wx.ITEM_NORMAL, text=_(u'Save') + '\tCTRL+S')
        AppendMenu(parent, help='', id=wx.ID_SAVEAS,
              kind=wx.ITEM_NORMAL, text=_(u'Save as') + '\tCTRL+SHIFT+S')
        AppendMenu(parent, help='', id=wx.ID_CLOSE,
              kind=wx.ITEM_NORMAL, text=_(u'Close Tab') + '\tCTRL+W')
        AppendMenu(parent, help='', id=wx.ID_CLOSE_ALL,
              kind=wx.ITEM_NORMAL, text=_(u'Close Project') + '\tCTRL+SHIFT+W')
        parent.AppendSeparator()
        AppendMenu(parent, help='', id=wx.ID_PAGE_SETUP,
              kind=wx.ITEM_NORMAL, text=_(u'Page Setup') + '\tCTRL+ALT+P')
        AppendMenu(parent, help='', id=wx.ID_PREVIEW,
              kind=wx.ITEM_NORMAL, text=_(u'Preview') + '\tCTRL+SHIFT+P')
        AppendMenu(parent, help='', id=wx.ID_PRINT,
              kind=wx.ITEM_NORMAL, text=_(u'Print') + '\tCTRL+P')
        parent.AppendSeparator()
        AppendMenu(parent, help='', id=wx.ID_EXIT,
              kind=wx.ITEM_NORMAL, text=_(u'Quit') + '\tCTRL+Q')
        
        self.Bind(wx.EVT_MENU, self.OnNewProjectMenu, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.OnOpenProjectMenu, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnSaveProjectMenu, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.OnSaveProjectAsMenu, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.OnCloseTabMenu, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.OnCloseProjectMenu, id=wx.ID_CLOSE_ALL)
        self.Bind(wx.EVT_MENU, self.OnPageSetupMenu, id=wx.ID_PAGE_SETUP)
        self.Bind(wx.EVT_MENU, self.OnPreviewMenu, id=wx.ID_PREVIEW)
        self.Bind(wx.EVT_MENU, self.OnPrintMenu, id=wx.ID_PRINT)
        self.Bind(wx.EVT_MENU, self.OnQuitMenu, id=wx.ID_EXIT)
        
        self.AddToMenuToolBar([(wx.ID_NEW, "new", _(u'New'), None),
                               (wx.ID_OPEN, "open", _(u'Open'), None),
                               (wx.ID_SAVE, "save", _(u'Save'), None),
                               (wx.ID_SAVEAS, "saveas", _(u'Save As...'), None),
                               (wx.ID_PRINT, "print", _(u'Print'), None)])
    
    def _RecursiveAddMenuItems(self, menu, items):
        for name, text, help, children in items:
            new_id = wx.NewId()
            if len(children) > 0:
                new_menu = wx.Menu(title='')
                menu.AppendMenu(new_id, text, new_menu)
                self._RecursiveAddMenuItems(new_menu, children)
            else:
                AppendMenu(menu, help=help, id=new_id, 
                       kind=wx.ITEM_NORMAL, text=text)
                self.Bind(wx.EVT_MENU, self.GetAddConfNodeFunction(name), 
                          id=new_id)    
    
    def _init_coll_AddMenu_Items(self, parent):
        IDEFrame._init_coll_AddMenu_Items(self, parent, False)
        
        # Disable add resource until matiec is able to handle multiple ressource definition
        #new_id = wx.NewId()
        #AppendMenu(parent, help='', id=new_id,
        #          kind=wx.ITEM_NORMAL, text=_(u'&Resource'))
        #self.Bind(wx.EVT_MENU, self.AddResourceMenu, id=new_id)
        
        self._RecursiveAddMenuItems(parent, GetAddMenuItems())
    
    def _init_coll_HelpMenu_Items(self, parent):
        parent.Append(help='', id=wx.ID_ABOUT,
              kind=wx.ITEM_NORMAL, text=_(u'About'))
        self.Bind(wx.EVT_MENU, self.OnAboutMenu, id=wx.ID_ABOUT)
    
    def _init_coll_ConnectionStatusBar_Fields(self, parent):
        parent.SetFieldsCount(3)

        parent.SetStatusText(number=0, text='')
        parent.SetStatusText(number=1, text='')
        parent.SetStatusText(number=2, text='')

        parent.SetStatusWidths([-1, 300, 200])
    
    def _init_ctrls(self, prnt):
        IDEFrame._init_ctrls(self, prnt)
        
        self.EditMenuSize = self.EditMenu.GetMenuItemCount()
        
        inspectorID = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnOpenWidgetInspector, id=inspectorID)
        accels = [wx.AcceleratorEntry(wx.ACCEL_CTRL|wx.ACCEL_ALT, ord('I'), inspectorID)]
        for method,shortcut in [("Stop",     wx.WXK_F4),
                                ("Run",      wx.WXK_F5),
                                ("Transfer", wx.WXK_F6),
                                ("Connect",  wx.WXK_F7),
                                ("Build",    wx.WXK_F11)]:
            def OnMethodGen(obj,meth):
                def OnMethod(evt):
                    if obj.CTR is not None:
                       obj.CTR.CallMethod('_'+meth)
                    wx.CallAfter(self.RefreshStatusToolBar)
                return OnMethod
            newid = wx.NewId()
            self.Bind(wx.EVT_MENU, OnMethodGen(self,method), id=newid)
            accels += [wx.AcceleratorEntry(wx.ACCEL_NORMAL, shortcut,newid)]
        
        self.SetAcceleratorTable(wx.AcceleratorTable(accels))
        
        self.LogConsole = CustomStyledTextCtrl(
                  name='LogConsole', parent=self.BottomNoteBook, pos=wx.Point(0, 0),
                  size=wx.Size(0, 0))
        self.LogConsole.Bind(wx.EVT_SET_FOCUS, self.OnLogConsoleFocusChanged)
        self.LogConsole.Bind(wx.EVT_KILL_FOCUS, self.OnLogConsoleFocusChanged)
        self.LogConsole.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnLogConsoleUpdateUI)
        self.LogConsole.SetReadOnly(True)
        self.LogConsole.SetWrapMode(wx.stc.STC_WRAP_CHAR)
        
        # Define Log Console styles
        self.LogConsole.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, "face:%(mono)s,size:%(size)d" % faces)
        self.LogConsole.StyleClearAll()
        self.LogConsole.StyleSetSpec(1, "face:%(mono)s,fore:#FF0000,size:%(size)d" % faces)
        self.LogConsole.StyleSetSpec(2, "face:%(mono)s,fore:#FF0000,back:#FFFF00,size:%(size)d" % faces)
        
        # Define Log Console markers
        self.LogConsole.SetMarginSensitive(1, True)
        self.LogConsole.SetMarginType(1, wx.stc.STC_MARGIN_SYMBOL)
        self.LogConsole.MarkerDefine(0, wx.stc.STC_MARK_CIRCLE, "BLACK", "RED")
        
        self.LogConsole.SetModEventMask(wx.stc.STC_MOD_INSERTTEXT)
        
        self.LogConsole.Bind(wx.stc.EVT_STC_MARGINCLICK, self.OnLogConsoleMarginClick)
        self.LogConsole.Bind(wx.stc.EVT_STC_MODIFIED, self.OnLogConsoleModified)
        
        self.MainTabs["LogConsole"] = (self.LogConsole, _("Console"))
        self.BottomNoteBook.AddPage(*self.MainTabs["LogConsole"])
        #self.BottomNoteBook.Split(self.BottomNoteBook.GetPageIndex(self.LogConsole), wx.RIGHT)
        
        self.LogViewer = LogViewer(self.BottomNoteBook, self)
        self.MainTabs["LogViewer"] = (self.LogViewer, _("PLC Log"))
        self.BottomNoteBook.AddPage(*self.MainTabs["LogViewer"])
        #self.BottomNoteBook.Split(self.BottomNoteBook.GetPageIndex(self.LogViewer), wx.RIGHT)
        
        StatusToolBar = wx.ToolBar(self, -1, wx.DefaultPosition, wx.DefaultSize,
                wx.TB_FLAT | wx.TB_NODIVIDER | wx.NO_BORDER)
        StatusToolBar.SetToolBitmapSize(wx.Size(25, 25))
        StatusToolBar.Realize()
        self.Panes["StatusToolBar"] = StatusToolBar
        self.AUIManager.AddPane(StatusToolBar, wx.aui.AuiPaneInfo().
                  Name("StatusToolBar").Caption(_("Status ToolBar")).
                  ToolbarPane().Top().Position(1).
                  LeftDockable(False).RightDockable(False))
        
        self.AUIManager.Update()
        
        self.ConnectionStatusBar = wx.StatusBar(self, style=wx.ST_SIZEGRIP)
        self._init_coll_ConnectionStatusBar_Fields(self.ConnectionStatusBar)
        self.SetStatusBar(self.ConnectionStatusBar)
        
    def __init__(self, parent, projectOpen=None, buildpath=None, ctr=None, debug=True):
        IDEFrame.__init__(self, parent, debug)
        self.Log = LogPseudoFile(self.LogConsole,self.SelectTab)
        
        self.local_runtime = None
        self.runtime_port = None
        self.local_runtime_tmpdir = None
        
        self.LastPanelSelected = None
        
        # Define Tree item icon list
        self.LocationImageList = wx.ImageList(16, 16)
        self.LocationImageDict = {}
        
        # Icons for location items
        for imgname, itemtype in [
            ("CONFIGURATION", LOCATION_CONFNODE),
            ("RESOURCE",      LOCATION_MODULE),
            ("PROGRAM",       LOCATION_GROUP),
            ("VAR_INPUT",     LOCATION_VAR_INPUT),
            ("VAR_OUTPUT",    LOCATION_VAR_OUTPUT),
            ("VAR_LOCAL",     LOCATION_VAR_MEMORY)]:
            self.LocationImageDict[itemtype] = self.LocationImageList.Add(GetBitmap(imgname))
        
        # Icons for other items
        for imgname, itemtype in [
            ("Extension", ITEM_CONFNODE)]:
            self.TreeImageDict[itemtype] = self.TreeImageList.Add(GetBitmap(imgname))
        
        # Add beremiz's icon in top left corner of the frame
        self.SetIcon(wx.Icon(Bpath("images", "brz.ico"), wx.BITMAP_TYPE_ICO))
        
        if projectOpen is not None:
            projectOpen = DecodeFileSystemPath(projectOpen, False)
        
        if projectOpen is not None and os.path.isdir(projectOpen):
            self.CTR = ProjectController(self, self.Log)
            self.Controler = self.CTR
            result = self.CTR.LoadProject(projectOpen, buildpath)
            if not result:
                self.LibraryPanel.SetController(self.Controler)
                self.ProjectTree.Enable(True)
                self.PouInstanceVariablesPanel.SetController(self.Controler)
                self.RefreshConfigRecentProjects(os.path.abspath(projectOpen))
                self._Refresh(PROJECTTREE, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)
            else:
                self.ResetView()
                self.ShowErrorMessage(result)
        else:
            self.CTR = ctr
            self.Controler = ctr
            if ctr is not None:
                self.LibraryPanel.SetController(self.Controler)
                self.ProjectTree.Enable(True)
                self.PouInstanceVariablesPanel.SetController(self.Controler)
                self._Refresh(PROJECTTREE, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)
        if self.EnableDebug:
            self.DebugVariablePanel.SetDataProducer(self.CTR)
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseFrame)
        
        self._Refresh(TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU, DISPLAYMENU)
        self.RefreshAll()
        self.LogConsole.SetFocus()

    def RefreshTitle(self):
        name = _("Beremiz")
        if self.CTR is not None:
            projectname = self.CTR.GetProjectName()
            if self.CTR.ProjectTestModified():
                projectname = "~%s~" % projectname
            self.SetTitle("%s - %s" % (name, projectname))
        else:
            self.SetTitle(name)

    def StartLocalRuntime(self, taskbaricon = True):
        if (self.local_runtime is None) or (self.local_runtime.exitcode is not None):
            # create temporary directory for runtime working directory
            self.local_runtime_tmpdir = tempfile.mkdtemp()
            # choose an arbitrary random port for runtime
            self.runtime_port = int(random.random() * 1000) + 61131
            # launch local runtime
            self.local_runtime = ProcessLogger(self.Log,
                "\"%s\" \"%s\" -p %s -i localhost %s %s"%(
                    sys.executable,
                    Bpath("Beremiz_service.py"),
                    self.runtime_port,
                    {False : "-x 0", True :"-x 1"}[taskbaricon],
                    self.local_runtime_tmpdir),
                no_gui=False,
                timeout=500, keyword = "working",
                cwd = self.local_runtime_tmpdir)
            self.local_runtime.spin()
        return self.runtime_port
    
    def KillLocalRuntime(self):
        if self.local_runtime is not None:
            # shutdown local runtime
            self.local_runtime.kill(gently=False)
            # clear temp dir
            shutil.rmtree(self.local_runtime_tmpdir)
            
            self.local_runtime = None

    def OnOpenWidgetInspector(self, evt):
        # Activate the widget inspection tool
        from wx.lib.inspection import InspectionTool
        if not InspectionTool().initialized:
            InspectionTool().Init()

        # Find a widget to be selected in the tree.  Use either the
        # one under the cursor, if any, or this frame.
        wnd = wx.FindWindowAtPointer()
        if not wnd:
            wnd = self
        InspectionTool().Show(wnd, True)

    def OnLogConsoleFocusChanged(self, event):
        self.RefreshEditMenu()
        event.Skip()

    def OnLogConsoleUpdateUI(self, event):
        self.SetCopyBuffer(self.LogConsole.GetSelectedText(), True)
        event.Skip()

    def OnLogConsoleMarginClick(self, event):
        line_idx = self.LogConsole.LineFromPosition(event.GetPosition())
        wx.CallAfter(self.SearchLineForError, self.LogConsole.GetLine(line_idx))
        event.Skip()
        
    def OnLogConsoleModified(self, event):
        line_idx = self.LogConsole.LineFromPosition(event.GetPosition())
        line = self.LogConsole.GetLine(line_idx)
        if line:
            result = MATIEC_ERROR_MODEL.match(line)
            if result is not None:
                self.LogConsole.MarkerAdd(line_idx, 0)
        event.Skip()

    def SearchLineForError(self, line):
        if self.CTR is not None:
            result = MATIEC_ERROR_MODEL.match(line)
            if result is not None:
                first_line, first_column, last_line, last_column, error = result.groups()
                infos = self.CTR.ShowError(self.Log,
                                                  (int(first_line), int(first_column)), 
                                                  (int(last_line), int(last_column)))
    
    ## Function displaying an Error dialog in PLCOpenEditor.
    #  @return False if closing cancelled.
    def CheckSaveBeforeClosing(self, title=_("Close Project")):
        if self.CTR.ProjectTestModified():
            dialog = wx.MessageDialog(self,
                                      _("There are changes, do you want to save?"),
                                      title,
                                      wx.YES_NO|wx.CANCEL|wx.ICON_QUESTION)
            answer = dialog.ShowModal()
            dialog.Destroy()
            if answer == wx.ID_YES:
                self.CTR.SaveProject()
            elif answer == wx.ID_CANCEL:
                return False
        
        for idx in xrange(self.TabsOpened.GetPageCount()):
            window = self.TabsOpened.GetPage(idx)
            if not window.CheckSaveBeforeClosing():
                return False
        
        return True
    
    def GetTabInfos(self, tab):
        if (isinstance(tab, EditorPanel) and 
            not isinstance(tab, (Viewer, 
                                 TextViewer, 
                                 GraphicViewer, 
                                 ResourceEditor, 
                                 ConfigurationEditor, 
                                 DataTypeEditor))):
            return ("confnode", tab.Controler.CTNFullName(), tab.GetTagName())
        elif (isinstance(tab, TextViewer) and 
              (tab.Controler is None or isinstance(tab.Controler, MiniTextControler))):
            return ("confnode", None, tab.GetInstancePath())
        else:
            return IDEFrame.GetTabInfos(self, tab)
    
    def LoadTab(self, notebook, page_infos):
        if page_infos[0] == "confnode":
            if page_infos[1] is None:
                confnode = self.CTR
            else:
                confnode = self.CTR.GetChildByName(page_infos[1])
            return notebook.GetPageIndex(confnode._OpenView(*page_infos[2:]))
        else:
            return IDEFrame.LoadTab(self, notebook, page_infos)
    
    def OnCloseFrame(self, event):
        for evt_type in [wx.EVT_SET_FOCUS, 
                         wx.EVT_KILL_FOCUS, 
                         wx.stc.EVT_STC_UPDATEUI]:
            self.LogConsole.Unbind(evt_type)
        if self.CTR is None or self.CheckSaveBeforeClosing(_("Close Application")):
            if self.CTR is not None:
                self.CTR.KillDebugThread()
            self.KillLocalRuntime()
            
            self.SaveLastState()
            
            event.Skip()
        else:
            event.Veto()
    
    def RefreshFileMenu(self):
        self.RefreshRecentProjectsMenu()
        
        MenuToolBar = self.Panes["MenuToolBar"]
        if self.CTR is not None:
            selected = self.TabsOpened.GetSelection()
            if selected >= 0:
                window = self.TabsOpened.GetPage(selected)
                viewer_is_modified = window.IsModified()
                is_viewer = isinstance(window, Viewer)
            else:
                viewer_is_modified = is_viewer = False
            if self.TabsOpened.GetPageCount() > 0:
                self.FileMenu.Enable(wx.ID_CLOSE, True)
                if is_viewer:
                    self.FileMenu.Enable(wx.ID_PREVIEW, True)
                    self.FileMenu.Enable(wx.ID_PRINT, True)
                    MenuToolBar.EnableTool(wx.ID_PRINT, True)
                else:
                    self.FileMenu.Enable(wx.ID_PREVIEW, False)
                    self.FileMenu.Enable(wx.ID_PRINT, False)
                    MenuToolBar.EnableTool(wx.ID_PRINT, False)
            else:
                self.FileMenu.Enable(wx.ID_CLOSE, False)
                self.FileMenu.Enable(wx.ID_PREVIEW, False)
                self.FileMenu.Enable(wx.ID_PRINT, False)
                MenuToolBar.EnableTool(wx.ID_PRINT, False)
            self.FileMenu.Enable(wx.ID_PAGE_SETUP, True)
            project_modified = self.CTR.ProjectTestModified() or viewer_is_modified
            self.FileMenu.Enable(wx.ID_SAVE, project_modified)
            MenuToolBar.EnableTool(wx.ID_SAVE, project_modified)
            self.FileMenu.Enable(wx.ID_SAVEAS, True)
            MenuToolBar.EnableTool(wx.ID_SAVEAS, True)
            self.FileMenu.Enable(wx.ID_CLOSE_ALL, True)
        else:
            self.FileMenu.Enable(wx.ID_CLOSE, False)
            self.FileMenu.Enable(wx.ID_PAGE_SETUP, False)
            self.FileMenu.Enable(wx.ID_PREVIEW, False)
            self.FileMenu.Enable(wx.ID_PRINT, False)
            MenuToolBar.EnableTool(wx.ID_PRINT, False)
            self.FileMenu.Enable(wx.ID_SAVE, False)
            MenuToolBar.EnableTool(wx.ID_SAVE, False)
            self.FileMenu.Enable(wx.ID_SAVEAS, False)
            MenuToolBar.EnableTool(wx.ID_SAVEAS, False)
            self.FileMenu.Enable(wx.ID_CLOSE_ALL, False)
    
    def RefreshRecentProjectsMenu(self):
        try:
            recent_projects = map(DecodeFileSystemPath, 
                                  self.GetConfigEntry("RecentProjects", []))
        except:
            recent_projects = []
        self.FileMenu.Enable(ID_FILEMENURECENTPROJECTS, len(recent_projects) > 0)
        for idx, projectpath in enumerate(recent_projects):
            text = u'%d: %s' % (idx + 1, projectpath)
            
            if idx < self.RecentProjectsMenu.GetMenuItemCount():
                item = self.RecentProjectsMenu.FindItemByPosition(idx)
                id = item.GetId()
                item.SetItemLabel(text)
                self.Disconnect(id, id, wx.EVT_BUTTON._getEvtType())
            else:
                id = wx.NewId()
                AppendMenu(self.RecentProjectsMenu, help='', id=id, 
                           kind=wx.ITEM_NORMAL, text=text)
            self.Bind(wx.EVT_MENU, self.GenerateOpenRecentProjectFunction(projectpath), id=id)
        
    def GenerateOpenRecentProjectFunction(self, projectpath):
        def OpenRecentProject(event):
            if self.CTR is not None and not self.CheckSaveBeforeClosing():
                return
            
            self.OpenProject(projectpath)
        return OpenRecentProject
    
    def GenerateMenuRecursive(self, items, menu):
        for kind, infos in items:
            if isinstance(kind, ListType):
                text, id = infos
                submenu = wx.Menu('')
                self.GenerateMenuRecursive(kind, submenu)
                menu.AppendMenu(id, text, submenu)
            elif kind == wx.ITEM_SEPARATOR:
                menu.AppendSeparator()
            else:
                text, id, help, callback = infos
                AppendMenu(menu, help='', id=id, kind=kind, text=text)
                if callback is not None:
                    self.Bind(wx.EVT_MENU, callback, id=id)
    
    def RefreshEditorToolBar(self):
        IDEFrame.RefreshEditorToolBar(self)
        self.AUIManager.GetPane("EditorToolBar").Position(2)
        self.AUIManager.GetPane("StatusToolBar").Position(1)
        self.AUIManager.Update()
    
    def RefreshStatusToolBar(self):
        StatusToolBar = self.Panes["StatusToolBar"]
        StatusToolBar.ClearTools()
        
        if self.CTR is not None:
            
            for confnode_method in self.CTR.StatusMethods:
                if "method" in confnode_method and confnode_method.get("shown",True):
                    id = wx.NewId()
                    StatusToolBar.AddSimpleTool(id, 
                        GetBitmap(confnode_method.get("bitmap", "Unknown")), 
                        confnode_method["tooltip"])
                    self.Bind(wx.EVT_MENU, self.GetMenuCallBackFunction(confnode_method["method"]), id=id)
            
            StatusToolBar.Realize()
            self.AUIManager.GetPane("StatusToolBar").BestSize(StatusToolBar.GetBestSize()).Show()
        else:
            self.AUIManager.GetPane("StatusToolBar").Hide()
        self.AUIManager.GetPane("EditorToolBar").Position(2)
        self.AUIManager.GetPane("StatusToolBar").Position(1)
        self.AUIManager.Update()
    
    def RefreshEditMenu(self):
        IDEFrame.RefreshEditMenu(self)
        if self.FindFocus() == self.LogConsole:
            self.EditMenu.Enable(wx.ID_COPY, True)
            self.Panes["MenuToolBar"].EnableTool(wx.ID_COPY, True)
        
        if self.CTR is not None:
            selected = self.TabsOpened.GetSelection()
            if selected >= 0:
                panel = self.TabsOpened.GetPage(selected)
            else:
                panel = None
            if panel != self.LastPanelSelected:
                for i in xrange(self.EditMenuSize, self.EditMenu.GetMenuItemCount()):
                    item = self.EditMenu.FindItemByPosition(self.EditMenuSize)
                    if item is not None:
                        if item.IsSeparator():
                            self.EditMenu.RemoveItem(item)
                        else:
                            self.EditMenu.Delete(item.GetId())
                self.LastPanelSelected = panel
                if panel is not None:
                    items = panel.GetConfNodeMenuItems()
                else:
                    items = []
                if len(items) > 0:
                    self.EditMenu.AppendSeparator()
                    self.GenerateMenuRecursive(items, self.EditMenu)
            if panel is not None:
                panel.RefreshConfNodeMenu(self.EditMenu)
        else:
            for i in xrange(self.EditMenuSize, self.EditMenu.GetMenuItemCount()):
                item = self.EditMenu.FindItemByPosition(i)
                if item is not None:
                    if item.IsSeparator():
                        self.EditMenu.RemoveItem(item)
                    else:
                        self.EditMenu.Delete(item.GetId())
            self.LastPanelSelected = None
        self.MenuBar.UpdateMenus()
    
    def RefreshAll(self):
        self.RefreshStatusToolBar()
    
    def GetMenuCallBackFunction(self, method):
        """ Generate the callbackfunc for a given CTR method"""
        def OnMenu(event):
            # Disable button to prevent re-entrant call 
            event.GetEventObject().Disable()
            # Call
            getattr(self.CTR, method)()
            # Re-enable button 
            event.GetEventObject().Enable()
        return OnMenu
    
    def GetConfigEntry(self, entry_name, default):
        return cPickle.loads(str(self.Config.Read(entry_name, cPickle.dumps(default))))
    
    def ResetConnectionStatusBar(self):
        for field in xrange(self.ConnectionStatusBar.GetFieldsCount()):
            self.ConnectionStatusBar.SetStatusText('', field)
    
    def ResetView(self):
        IDEFrame.ResetView(self)
        self.ConfNodeInfos = {}
        if self.CTR is not None:
            self.CTR.CloseProject()
        self.CTR = None
        self.Log.flush()
        if self.EnableDebug:
            self.DebugVariablePanel.SetDataProducer(None)
            self.ResetConnectionStatusBar()
    
    def RefreshConfigRecentProjects(self, projectpath):
        try:
            recent_projects = map(DecodeFileSystemPath, 
                                  self.GetConfigEntry("RecentProjects", []))
        except:
            recent_projects = []
        if projectpath in recent_projects:
            recent_projects.remove(projectpath)
        recent_projects.insert(0, projectpath)
        self.Config.Write("RecentProjects", cPickle.dumps(
            map(EncodeFileSystemPath, recent_projects[:MAX_RECENT_PROJECTS])))
        self.Config.Flush()
    
    def ResetPerspective(self):
        IDEFrame.ResetPerspective(self)
        self.RefreshStatusToolBar()
    
    def OnNewProjectMenu(self, event):
        if self.CTR is not None and not self.CheckSaveBeforeClosing():
            return
        
        try:
            defaultpath = DecodeFileSystemPath(self.Config.Read("lastopenedfolder"))
        except:
            defaultpath = os.path.expanduser("~")
        
        dialog = wx.DirDialog(self , _("Choose a project"), defaultpath)
        if dialog.ShowModal() == wx.ID_OK:
            projectpath = dialog.GetPath()
            self.Config.Write("lastopenedfolder", 
                              EncodeFileSystemPath(os.path.dirname(projectpath)))
            self.Config.Flush()
            self.ResetView()
            ctr = ProjectController(self, self.Log)
            result = ctr.NewProject(projectpath)
            if not result:
                self.CTR = ctr
                self.Controler = self.CTR
                self.LibraryPanel.SetController(self.Controler)
                self.ProjectTree.Enable(True)
                self.PouInstanceVariablesPanel.SetController(self.Controler)
                self.RefreshConfigRecentProjects(projectpath)
                if self.EnableDebug:
                    self.DebugVariablePanel.SetDataProducer(self.CTR)
                self._Refresh(PROJECTTREE, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)
            else:
                self.ResetView()
                self.ShowErrorMessage(result)
            self.RefreshAll()
            self._Refresh(TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU)
        dialog.Destroy()
    
    def OnOpenProjectMenu(self, event):
        if self.CTR is not None and not self.CheckSaveBeforeClosing():
            return
        
        try:
            defaultpath = DecodeFileSystemPath(self.Config.Read("lastopenedfolder"))
        except:
            defaultpath = os.path.expanduser("~")
        
        dialog = wx.DirDialog(self , _("Choose a project"), defaultpath, style=wx.DEFAULT_DIALOG_STYLE|
                                                                               wx.RESIZE_BORDER)
        if dialog.ShowModal() == wx.ID_OK:
            self.OpenProject(dialog.GetPath())
        dialog.Destroy()
    
    def OpenProject(self, projectpath):
        if os.path.isdir(projectpath):
            self.Config.Write("lastopenedfolder", 
                              EncodeFileSystemPath(os.path.dirname(projectpath)))
            self.Config.Flush()
            self.ResetView()
            self.CTR = ProjectController(self, self.Log)
            self.Controler = self.CTR
            result = self.CTR.LoadProject(projectpath)
            if not result:
                self.LibraryPanel.SetController(self.Controler)
                self.ProjectTree.Enable(True)
                self.PouInstanceVariablesPanel.SetController(self.Controler)
                self.RefreshConfigRecentProjects(projectpath)
                if self.EnableDebug:
                    self.DebugVariablePanel.SetDataProducer(self.CTR)
                self._Refresh(PROJECTTREE, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)
            else:
                self.ResetView()
                self.ShowErrorMessage(result)
            self.RefreshAll()
        else:
            self.ShowErrorMessage(_("\"%s\" folder is not a valid Beremiz project\n") % projectpath)
        self._Refresh(TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU)
    
    def OnCloseProjectMenu(self, event):
        if self.CTR is not None and not self.CheckSaveBeforeClosing():
            return
        
        self.ResetView()
        self._Refresh(TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU)
        self.RefreshAll()
    
    def OnSaveProjectMenu(self, event):
        selected = self.TabsOpened.GetSelection()
        if selected != -1:
            window = self.TabsOpened.GetPage(selected)
            window.Save()
        if self.CTR is not None:
            self.CTR.SaveProject()
            self.RefreshAll()
            self._Refresh(TITLE, FILEMENU, EDITMENU, PAGETITLES)
    
    def OnSaveProjectAsMenu(self, event):
        selected = self.TabsOpened.GetSelection()
        if selected != -1:
            window = self.TabsOpened.GetPage(selected)
            window.SaveAs()
        if self.CTR is not None:
            self.CTR.SaveProjectAs()
            self.RefreshAll()
            self._Refresh(TITLE, FILEMENU, EDITMENU, PAGETITLES)
    
    def OnQuitMenu(self, event):
        self.Close()
        
    def OnAboutMenu(self, event):
        OpenHtmlFrame(self,_("About Beremiz"), Bpath("doc", "about.html"), wx.Size(550, 500))
    
    def OnProjectTreeItemBeginEdit(self, event):
        selected = event.GetItem()
        if self.ProjectTree.GetPyData(selected)["type"] == ITEM_CONFNODE:
            event.Veto()
        else:
            IDEFrame.OnProjectTreeItemBeginEdit(self, event)
    
    def OnProjectTreeRightUp(self, event):
        item = event.GetItem()
        item_infos = self.ProjectTree.GetPyData(item)
        
        if item_infos["type"] == ITEM_CONFNODE:
            confnode_menu = wx.Menu(title='')
            
            confnode = item_infos["confnode"]
            if confnode is not None:
                menu_items = confnode.GetContextualMenuItems()
                if menu_items is not None:
                    for text, help, callback in menu_items:
                        new_id = wx.NewId()
                        confnode_menu.Append(help=help, id=new_id, kind=wx.ITEM_NORMAL, text=text)
                        self.Bind(wx.EVT_MENU, callback, id=new_id)
                else:
                    for name, XSDClass, help in confnode.CTNChildrenTypes:
                        new_id = wx.NewId()
                        confnode_menu.Append(help=help, id=new_id, kind=wx.ITEM_NORMAL, text=_("Add") + " " + name)
                        self.Bind(wx.EVT_MENU, self.GetAddConfNodeFunction(name, confnode), id=new_id)

            new_id = wx.NewId()
            AppendMenu(confnode_menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("Delete"))
            self.Bind(wx.EVT_MENU, self.GetDeleteMenuFunction(confnode), id=new_id)
                
            self.PopupMenu(confnode_menu)
            confnode_menu.Destroy()
            
            event.Skip()
        elif item_infos["type"] != ITEM_PROJECT:
            parent = self.ProjectTree.GetItemParent(item)
            parent_name = self.ProjectTree.GetItemText(parent)
            if item_infos["type"] != ITEM_RESOURCE or parent_name == _("Resources"):
                IDEFrame.OnProjectTreeRightUp(self, event)
        else:
            IDEFrame.OnProjectTreeRightUp(self, event)
    
    def OnProjectTreeItemActivated(self, event):
        selected = event.GetItem()
        name = self.ProjectTree.GetItemText(selected)
        item_infos = self.ProjectTree.GetPyData(selected)
        if item_infos["type"] == ITEM_CONFNODE:
            item_infos["confnode"]._OpenView()
            event.Skip()
        elif item_infos["type"] == ITEM_PROJECT:
            self.CTR._OpenView()
        else:
            IDEFrame.OnProjectTreeItemActivated(self, event)
    
    def ProjectTreeItemSelect(self, select_item):
        if select_item is not None and select_item.IsOk():
            name = self.ProjectTree.GetItemText(select_item)
            item_infos = self.ProjectTree.GetPyData(select_item)
            if item_infos["type"] == ITEM_CONFNODE:
                item_infos["confnode"]._OpenView(onlyopened=True)
            elif item_infos["type"] == ITEM_PROJECT:
                self.CTR._OpenView(onlyopened=True)
            else:
                IDEFrame.ProjectTreeItemSelect(self, select_item)
    
    def SelectProjectTreeItem(self, tagname):
        if self.ProjectTree is not None:
            root = self.ProjectTree.GetRootItem()
            if root.IsOk():
                words = tagname.split("::")
                if len(words) == 1:
                    if tagname == "Project":
                        self.SelectedItem = root
                        self.ProjectTree.SelectItem(root)
                        self.ResetSelectedItem()
                    else:
                        return self.RecursiveProjectTreeItemSelection(root, 
                              [(word, ITEM_CONFNODE) for word in tagname.split(".")])
                elif words[0] == "R":
                    return self.RecursiveProjectTreeItemSelection(root, [(words[2], ITEM_RESOURCE)])
                elif not os.path.exists(words[0]):
                    IDEFrame.SelectProjectTreeItem(self, tagname)
            
    def GetAddConfNodeFunction(self, name, confnode=None):
        def AddConfNodeMenuFunction(event):
            wx.CallAfter(self.AddConfNode, name, confnode)
        return AddConfNodeMenuFunction
    
    def GetDeleteMenuFunction(self, confnode):
        def DeleteMenuFunction(event):
            wx.CallAfter(self.DeleteConfNode, confnode)
        return DeleteMenuFunction
    
    def AddResourceMenu(self, event):
        config_names = self.CTR.GetProjectConfigNames()
        if len(config_names) > 0:
            tagname = self.Controler.ProjectAddConfigurationResource(config_names[0])
            if tagname is not None:
                self._Refresh(TITLE, FILEMENU, EDITMENU, PROJECTTREE, POUINSTANCEVARIABLESPANEL)
                self.EditProjectElement(ITEM_RESOURCE, tagname)
        
    def AddConfNode(self, ConfNodeType, confnode=None):
        if self.CTR.CheckProjectPathPerm():
            ConfNodeName = "%s_0" % ConfNodeType
            if confnode is not None:
                confnode.CTNAddChild(ConfNodeName, ConfNodeType)
            else:
                self.CTR.CTNAddChild(ConfNodeName, ConfNodeType)
            self._Refresh(TITLE, FILEMENU, PROJECTTREE)
            
    def DeleteConfNode(self, confnode):
        if self.CTR.CheckProjectPathPerm():
            dialog = wx.MessageDialog(self, 
                _("Really delete node '%s'?") % confnode.CTNName(), 
                _("Remove %s node") % confnode.CTNType, 
                wx.YES_NO|wx.NO_DEFAULT)
            if dialog.ShowModal() == wx.ID_YES:
                confnode.CTNRemove()
                del confnode
                self._Refresh(TITLE, FILEMENU, PROJECTTREE)
            dialog.Destroy()

#-------------------------------------------------------------------------------
#                        Highlights showing functions
#-------------------------------------------------------------------------------

    def ShowHighlight(self, infos, start, end, highlight_type):
        config_name = self.Controler.GetProjectMainConfigurationName()
        if config_name is not None and infos[0] == self.Controler.ComputeConfigurationName(config_name):
            self.CTR._OpenView()
            selected = self.TabsOpened.GetSelection()
            if selected != -1:
                viewer = self.TabsOpened.GetPage(selected)
                viewer.AddHighlight(infos[1:], start, end, highlight_type)
        else:
            IDEFrame.ShowHighlight(self, infos, start, end, highlight_type)

#-------------------------------------------------------------------------------
#                               Exception Handler
#-------------------------------------------------------------------------------
import threading, traceback

Max_Traceback_List_Size = 20

def Display_Exception_Dialog(e_type, e_value, e_tb, bug_report_path):
    trcbck_lst = []
    for i,line in enumerate(traceback.extract_tb(e_tb)):
        trcbck = " " + str(i+1) + ". "
        if line[0].find(os.getcwd()) == -1:
            trcbck += "file : " + str(line[0]) + ",   "
        else:
            trcbck += "file : " + str(line[0][len(os.getcwd()):]) + ",   "
        trcbck += "line : " + str(line[1]) + ",   " + "function : " + str(line[2])
        trcbck_lst.append(trcbck)
        
    # Allow clicking....
    cap = wx.Window_GetCapture()
    if cap:
        cap.ReleaseMouse()

    dlg = wx.SingleChoiceDialog(None, 
        _("""
An unhandled exception (bug) occured. Bug report saved at :
(%s)

Please be kind enough to send this file to:
beremiz-devel@lists.sourceforge.net

You should now restart Beremiz.

Traceback:
""") % bug_report_path +
        str(e_type) + " : " + str(e_value), 
        _("Error"),
        trcbck_lst)
    try:
        res = (dlg.ShowModal() == wx.ID_OK)
    finally:
        dlg.Destroy()

    return res

def get_last_traceback(tb):
    while tb.tb_next:
        tb = tb.tb_next
    return tb


def format_namespace(d, indent='    '):
    return '\n'.join(['%s%s: %s' % (indent, k, repr(v)[:10000]) for k, v in d.iteritems()])


ignored_exceptions = [] # a problem with a line in a module is only reported once per session

def AddExceptHook(path, app_version='[No version]'):#, ignored_exceptions=[]):
    
    def handle_exception(e_type, e_value, e_traceback):
        traceback.print_exception(e_type, e_value, e_traceback) # this is very helpful when there's an exception in the rest of this func
        last_tb = get_last_traceback(e_traceback)
        ex = (last_tb.tb_frame.f_code.co_filename, last_tb.tb_frame.f_lineno)
        if ex not in ignored_exceptions:
            date = time.ctime()
            bug_report_path = path+os.sep+"bug_report_"+date.replace(':','-').replace(' ','_')+".txt"
            result = Display_Exception_Dialog(e_type,e_value,e_traceback,bug_report_path)
            if result:
                ignored_exceptions.append(ex)
                info = {
                    'app-title' : wx.GetApp().GetAppName(), # app_title
                    'app-version' : app_version,
                    'wx-version' : wx.VERSION_STRING,
                    'wx-platform' : wx.Platform,
                    'python-version' : platform.python_version(), #sys.version.split()[0],
                    'platform' : platform.platform(),
                    'e-type' : e_type,
                    'e-value' : e_value,
                    'date' : date,
                    'cwd' : os.getcwd(),
                    }
                if e_traceback:
                    info['traceback'] = ''.join(traceback.format_tb(e_traceback)) + '%s: %s' % (e_type, e_value)
                    last_tb = get_last_traceback(e_traceback)
                    exception_locals = last_tb.tb_frame.f_locals # the locals at the level of the stack trace where the exception actually occurred
                    info['locals'] = format_namespace(exception_locals)
                    if 'self' in exception_locals:
                        info['self'] = format_namespace(exception_locals['self'].__dict__)
                
                output = open(bug_report_path,'w')
                lst = info.keys()
                lst.sort()
                for a in lst:
                    output.write(a+":\n"+str(info[a])+"\n\n")

    #sys.excepthook = lambda *args: wx.CallAfter(handle_exception, *args)
    sys.excepthook = handle_exception

    init_old = threading.Thread.__init__
    def init(self, *args, **kwargs):
        init_old(self, *args, **kwargs)
        run_old = self.run
        def run_with_except_hook(*args, **kw):
            try:
                run_old(*args, **kw)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                sys.excepthook(*sys.exc_info())
        self.run = run_with_except_hook
    threading.Thread.__init__ = init

if __name__ == '__main__':
    # Install a exception handle for bug reports
    AddExceptHook(os.getcwd(),updateinfo_url)
    
    frame = Beremiz(None, projectOpen, buildpath)
    if splash:
        splash.Close()
    frame.Show()
    app.MainLoop()
