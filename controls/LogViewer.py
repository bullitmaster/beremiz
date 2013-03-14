#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2013: Edouard TISSERANT and Laurent BESSARD
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

from datetime import datetime
from time import time as gettime

import wx

from graphics import DebugViewer, REFRESH_PERIOD
from targets.typemapping import LogLevelsCount, LogLevels
from util.BitmapLibrary import GetBitmap

THUMB_SIZE_RATIO = 1. / 8.

class MyScrollBar(wx.Panel):
    
    def __init__(self, parent, size):
        wx.Panel.__init__(self, parent, size=size)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnResize)
        
        self.ThumbPosition = 0. # -1 <= ThumbPosition <= 1
        self.ThumbScrollingStartPos = None
    
    def GetRangeRect(self):
        width, height = self.GetClientSize()
        return wx.Rect(0, width, width, height - 2 * width)
    
    def GetThumbRect(self):
        width, height = self.GetClientSize()
        range_rect = self.GetRangeRect()
        thumb_size = range_rect.height * THUMB_SIZE_RATIO
        thumb_range = range_rect.height - thumb_size
        thumb_center_position = (thumb_size + (self.ThumbPosition + 1) * thumb_range) / 2.
        thumb_start = int(thumb_center_position - thumb_size / 2.)
        thumb_end = int(thumb_center_position + thumb_size / 2.)
        return wx.Rect(1, range_rect.y + thumb_start, width - 1, thumb_end - thumb_start)
    
    def RefreshThumbPosition(self, thumb_position=None):
        if thumb_position is None:
            thumb_position = self.ThumbPosition
        if self.Parent.IsMessagePanelTop():
            thumb_position = max(0., thumb_position)
        if self.Parent.IsMessagePanelBottom():
            thumb_position = min(0., thumb_position)
        if thumb_position != self.ThumbPosition:
            self.ThumbPosition = thumb_position
            self.Parent.SetScrollSpeed(self.ThumbPosition)
        self.Refresh()
    
    def OnLeftDown(self, event):
        self.CaptureMouse()
        posx, posy = event.GetPosition()
        width, height = self.GetClientSize()
        range_rect = self.GetRangeRect()
        thumb_rect = self.GetThumbRect()
        if range_rect.InsideXY(posx, posy):
            if thumb_rect.InsideXY(posx, posy):
                self.ThumbScrollingStartPos = wx.Point(posx, posy)
            elif posy < thumb_rect.y:
                self.Parent.ScrollToLast()
            elif posy > thumb_rect.y + thumb_rect.height:
                self.Parent.ScrollToFirst()
        elif posy < width:
            pass
        elif posy > height - width:
            pass
        event.Skip()
        
    def OnLeftUp(self, event):
        self.ThumbScrollingStartPos = None
        self.RefreshThumbPosition(0.)
        if self.HasCapture():
            self.ReleaseMouse()
        event.Skip()
        
    def OnMotion(self, event):
        if event.Dragging() and self.ThumbScrollingStartPos is not None:
            posx, posy = event.GetPosition()
            width, height = self.GetClientSize()
            range_rect = self.GetRangeRect()
            thumb_size = range_rect.height * THUMB_SIZE_RATIO
            thumb_range = range_rect.height - thumb_size
            self.RefreshThumbPosition(
                max(-1., min((posy - self.ThumbScrollingStartPos.y) * 2. / thumb_range, 1.)))
        event.Skip()
    
    def OnResize(self, event):
        self.Refresh()
        event.Skip()
    
    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.Clear()
        dc.BeginDrawing()
        
        width, height = self.GetClientSize()
        
        thumb_rect = self.GetThumbRect()
        exclusion_rect = wx.Rect(thumb_rect.x, thumb_rect.y,
                                 thumb_rect.width, thumb_rect.height)
        if self.Parent.IsMessagePanelTop():
            exclusion_rect.y, exclusion_rect.height = width, exclusion_rect.y + exclusion_rect.height - width
        if self.Parent.IsMessagePanelBottom():
            exclusion_rect.height = height - width - exclusion_rect.y
        if exclusion_rect != thumb_rect:
            colour = wx.NamedColour("LIGHT GREY")
            dc.SetPen(wx.Pen(colour))
            dc.SetBrush(wx.Brush(colour))
        
            dc.DrawRectangle(exclusion_rect.x, exclusion_rect.y, 
                             exclusion_rect.width, exclusion_rect.height)
        
        dc.SetPen(wx.GREY_PEN)
        dc.SetBrush(wx.GREY_BRUSH)
        
        dc.DrawPolygon([wx.Point(width / 2, 1),
                        wx.Point(1, width - 2),
                        wx.Point(width - 1, width - 2)])
        
        dc.DrawPolygon([wx.Point(width / 2, height - 1),
                        wx.Point(2, height - width + 1),
                        wx.Point(width - 1, height - width + 1)])
            
        dc.DrawRectangle(thumb_rect.x, thumb_rect.y, 
                         thumb_rect.width, thumb_rect.height)
        
        dc.EndDrawing()
        event.Skip()

DATE_INFO_SIZE = 10
MESSAGE_INFO_SIZE = 30

class LogMessage:
    
    def __init__(self, tv_sec, tv_nsec, level, level_bitmap, msg):
        self.Date = datetime.fromtimestamp(tv_sec)
        self.Seconds = self.Date.second + tv_nsec * 1e-9
        self.Date = self.Date.replace(second=0)
        self.Level = level
        self.LevelBitmap = level_bitmap
        self.Message = msg
        self.DrawDate = True
    
    def __cmp__(self, other):
        if self.Date == other.Date:
            return cmp(self.Seconds, other.Seconds)
        return cmp(self.Date, other.Date)
    
    def Draw(self, dc, offset, width, draw_date):
        if draw_date:
            datetime_text = self.Date.strftime("%d/%m/%y %H:%M")
            dw, dh = dc.GetTextExtent(datetime_text)
            dc.DrawText(datetime_text, (width - dw) / 2, offset + (DATE_INFO_SIZE - dh) / 2)
            offset += DATE_INFO_SIZE
        
        seconds_text = "%12.9f" % self.Seconds
        sw, sh = dc.GetTextExtent(seconds_text)
        dc.DrawText(seconds_text, 5, offset + (MESSAGE_INFO_SIZE - sh) / 2)
        
        bw, bh = self.LevelBitmap.GetWidth(), self.LevelBitmap.GetHeight()
        dc.DrawBitmap(self.LevelBitmap, 10 + sw, offset + (MESSAGE_INFO_SIZE - bh) / 2)
        
        mw, mh = dc.GetTextExtent(self.Message)
        dc.DrawText(self.Message, 15 + sw + bw, offset + (MESSAGE_INFO_SIZE - mh) / 2)
        
    def GetHeight(self, draw_date):
        if draw_date:
            return DATE_INFO_SIZE + MESSAGE_INFO_SIZE
        return MESSAGE_INFO_SIZE

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR

CHANGE_TIMESTAMP_BUTTONS = [(_("1d"), DAY),
                            (_("1h"), HOUR),
                            (_("1m"), MINUTE),
                            (_("1s"), SECOND)]
REVERSE_CHANGE_TIMESTAMP_BUTTONS = CHANGE_TIMESTAMP_BUTTONS[:]
REVERSE_CHANGE_TIMESTAMP_BUTTONS.reverse()

class LogViewer(DebugViewer, wx.Panel):
    
    def __init__(self, parent, window):
        wx.Panel.__init__(self, parent, style=wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER)
        DebugViewer.__init__(self, None, False, False)
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=5)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(filter_sizer, border=5, flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.GROW)
        
        self.MessageFilter = wx.ComboBox(self, style=wx.CB_READONLY)
        self.MessageFilter.Append(_("All"))
        levels = LogLevels[:3]
        levels.reverse()
        for level in levels:
            self.MessageFilter.Append(_(level))
        self.Bind(wx.EVT_COMBOBOX, self.OnMessageFilterChanged, self.MessageFilter)
        filter_sizer.AddWindow(self.MessageFilter, 1, border=5, flag=wx.RIGHT|wx.GROW)
        
        self.SearchMessage = wx.SearchCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.SearchMessage.ShowSearchButton(True)
        self.SearchMessage.ShowCancelButton(True)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnSearchMessageChanged, self.SearchMessage)
        self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, 
              self.OnSearchMessageSearchButtonClick, self.SearchMessage)
        self.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, 
              self.OnSearchMessageCancelButtonClick, self.SearchMessage)
        filter_sizer.AddWindow(self.SearchMessage, 3, flag=wx.GROW)
        
        message_panel_sizer = wx.FlexGridSizer(cols=3, hgap=0, rows=1, vgap=0)
        message_panel_sizer.AddGrowableCol(1)
        message_panel_sizer.AddGrowableRow(0)
        main_sizer.AddSizer(message_panel_sizer, border=5, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.GROW)
        
        buttons_sizer = wx.BoxSizer(wx.VERTICAL)
        for label, callback in [("+" + text, self.GenerateOnDurationButton(duration)) 
                                for text, duration in CHANGE_TIMESTAMP_BUTTONS] +\
                               [("-" + text, self.GenerateOnDurationButton(-duration)) 
                                for text, duration in REVERSE_CHANGE_TIMESTAMP_BUTTONS]:
            button = wx.Button(self, label=label)
            self.Bind(wx.EVT_BUTTON, callback, button)
            buttons_sizer.AddWindow(button, 1, wx.ALIGN_CENTER_VERTICAL)
        message_panel_sizer.AddSizer(buttons_sizer, flag=wx.GROW)
        
        self.MessagePanel = wx.Panel(self)
        if wx.Platform == '__WXMSW__':
            self.Font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName='Courier New')
        else:
            self.Font = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName='Courier')    
        self.MessagePanel.Bind(wx.EVT_MOUSEWHEEL, self.OnMessagePanelMouseWheel)
        self.MessagePanel.Bind(wx.EVT_PAINT, self.OnMessagePanelPaint)
        self.MessagePanel.Bind(wx.EVT_SIZE, self.OnMessagePanelResize)
        message_panel_sizer.AddWindow(self.MessagePanel, flag=wx.GROW)
        
        self.MessageScrollBar = MyScrollBar(self, wx.Size(16, -1))
        message_panel_sizer.AddWindow(self.MessageScrollBar, flag=wx.GROW)
        
        self.SetSizer(main_sizer)
    
        self.MessageFilter.SetSelection(0)
        self.LogSource = None
        self.ResetLogMessages()
        self.ParentWindow = window
    
        self.LevelIcons = [GetBitmap("LOG_" + level) for level in LogLevels]
        self.LevelFilters = [range(i) for i in xrange(4, 0, -1)]
        self.CurrentFilter = self.LevelFilters[0]
        self.CurrentSearchValue = ""
        
        self.ScrollSpeed = 0.
        self.LastStartTime = None
        self.ScrollTimer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.OnScrollTimer, self.ScrollTimer)
    
    def __del__(self):
        self.ScrollTimer.Stop()
    
    def ResetLogMessages(self):
        self.previous_log_count = [None]*LogLevelsCount
        self.OldestMessages = []
        self.LogMessages = []
        self.CurrentMessage = None
        self.HasNewData = False
    
    def SetLogSource(self, log_source):
        self.LogSource = log_source
        if log_source is not None:
            self.ResetLogMessages()
            self.RefreshView()
    
    def GetLogMessageFromSource(self, msgidx, level):
        if self.LogSource is not None:
            answer = self.LogSource.GetLogMessage(level, msgidx)
            if answer is not None:
                msg, tick, tv_sec, tv_nsec = answer
                return LogMessage(tv_sec, tv_nsec, level, self.LevelIcons[level], msg)
        return None
    
    def SetLogCounters(self, log_count):
        new_messages = []
        for level, count, prev in zip(xrange(LogLevelsCount), log_count, self.previous_log_count):
            if count is not None and prev != count:
                if prev is None:
                    dump_end = count - 2
                else:
                    dump_end = prev - 1
                for msgidx in xrange(count-1, dump_end,-1):
                    new_message = self.GetLogMessageFromSource(msgidx, level)
                    if new_message is not None:
                        if prev is None:
                            self.OldestMessages.append((msgidx, new_message))
                            if len(new_messages) == 0 or new_message > new_messages[0]:
                                new_messages = [new_message]
                        else:
                            new_messages.insert(0, new_message)
                    else:
                        if prev is None:
                            self.OldestMessages.append((-1, None))
                        break
                self.previous_log_count[level] = count
        new_messages.sort()
        if len(new_messages) > 0:
            self.HasNewData = True
            old_length = len(self.LogMessages)
            for new_message in new_messages:
                self.LogMessages.append(new_message)
            if self.CurrentMessage is None or self.CurrentMessage == old_length - 1:
                self.CurrentMessage = len(self.LogMessages) - 1
            self.NewDataAvailable(None)
    
    def FilterLogMessage(self, message):
        return message.Level in self.CurrentFilter and message.Message.find(self.CurrentSearchValue) != -1
    
    def GetNextMessage(self, msgidx):
        while msgidx < len(self.LogMessages) - 1:
            message = self.LogMessages[msgidx + 1]
            if self.FilterLogMessage(message):
                return message, msgidx + 1
            msgidx += 1
        return None, None
    
    def GetPreviousMessage(self, msgidx):
        message = None
        while 0 < msgidx < len(self.LogMessages):
            message = self.LogMessages[msgidx - 1]
            if self.FilterLogMessage(message):
                return message, msgidx - 1
            msgidx -= 1
        if len(self.LogMessages) > 0:
            message = self.LogMessages[0]
            while message is not None:
                level = message.Level
                oldest_msgidx, oldest_message = self.OldestMessages[level]
                if oldest_msgidx > 0:
                    old_message = self.GetLogMessageFromSource(oldest_msgidx - 1, level)
                    if old_message is not None:
                        self.OldestMessages[level] = (oldest_msgidx - 1, old_message)
                    else:
                        self.OldestMessages[level] = (-1, None)
                else:
                    self.OldestMessages[level] = (-1, None)
                message = None
                for idx, msg in self.OldestMessages:
                    if msg is not None and (message is None or msg > message):
                        message = msg
                if message is not None:
                    self.LogMessages.insert(0, message)
                    if self.CurrentMessage is not None:
                        self.CurrentMessage += 1
                    else:
                        self.CurrentMessage = 0
                    if self.FilterLogMessage(message):
                        return message, 0
        return None, None
    
    def RefreshNewData(self, *args, **kwargs):
        if self.HasNewData:
            self.HasNewData = False
            self.RefreshView()
        DebugViewer.RefreshNewData(self, *args, **kwargs)
    
    def RefreshView(self):
        width, height = self.MessagePanel.GetClientSize()
        bitmap = wx.EmptyBitmap(width, height)
        dc = wx.BufferedDC(wx.ClientDC(self.MessagePanel), bitmap)
        dc.Clear()
        dc.SetFont(self.Font)
        dc.BeginDrawing()
        
        if self.CurrentMessage is not None:
            message_idx = self.CurrentMessage
            message = self.LogMessages[message_idx]
            draw_date = True
            offset = 5
            while offset < height and message is not None:
                message.Draw(dc, offset, width, draw_date)
                offset += message.GetHeight(draw_date)
                
                previous_message, message_idx = self.GetPreviousMessage(message_idx)
                if previous_message is not None:
                    draw_date = message.Date != previous_message.Date
                message = previous_message
        
        dc.EndDrawing()
        
        self.MessageScrollBar.RefreshThumbPosition()
    
    def IsMessagePanelTop(self, message_idx=None):
        if message_idx is None:
            message_idx = self.CurrentMessage
        if message_idx is not None:
            return self.GetNextMessage(message_idx)[0] is None
        return True
    
    def IsMessagePanelBottom(self, message_idx=None):
        if message_idx is None:
            message_idx = self.CurrentMessage
        if message_idx is not None:
            width, height = self.MessagePanel.GetClientSize()
            offset = 5
            message = self.LogMessages[message_idx]
            draw_date = True
            while message is not None and offset < height:
                offset += message.GetHeight(draw_date)
                previous_message, message_idx = self.GetPreviousMessage(message_idx)
                if previous_message is not None:
                    draw_date = message.Date != previous_message.Date
                message = previous_message
            return offset < height
        return True
    
    def ScrollMessagePanel(self, scroll):
        if self.CurrentMessage is not None:
            message = self.LogMessages[self.CurrentMessage]
            while scroll > 0 and message is not None:
                message, msgidx = self.GetNextMessage(self.CurrentMessage)
                if message is not None:
                    self.CurrentMessage = msgidx
                    scroll -= 1
            while scroll < 0 and message is not None and not self.IsMessagePanelBottom():
                message, msgidx = self.GetPreviousMessage(self.CurrentMessage)
                if message is not None:
                    self.CurrentMessage = msgidx
                    scroll += 1
            self.RefreshView()
    
    def ResetMessagePanel(self):
        if len(self.LogMessages) > 0:
            self.CurrentMessage = len(self.LogMessages) - 1
            message = self.LogMessages[self.CurrentMessage]
            while message is not None and not self.FilterLogMessage(message):
                message, self.CurrentMessage = self.GetPreviousMessage(self.CurrentMessage)
            self.RefreshView()
    
    def OnMessageFilterChanged(self, event):
        self.CurrentFilter = self.LevelFilters[self.MessageFilter.GetSelection()]
        self.ResetMessagePanel()
        event.Skip()
    
    def OnSearchMessageChanged(self, event):
        self.CurrentSearchValue = self.SearchMessage.GetValue()
        self.ResetMessagePanel()
        event.Skip()
        
    def OnSearchMessageSearchButtonClick(self, event):
        self.CurrentSearchValue = self.SearchMessage.GetValue()
        self.ResetMessagePanel()
        event.Skip()
    
    def OnSearchMessageCancelButtonClick(self, event):
        self.CurrentSearchValue = ""
        self.SearchMessage.SetValue("")
        self.ResetMessagePanel()
        event.Skip()
    
    def GenerateOnDurationButton(self, duration):
        def OnDurationButton(event):
            event.Skip()
        return OnDurationButton
    
    def OnMessagePanelMouseWheel(self, event):
        self.ScrollMessagePanel(event.GetWheelRotation() / event.GetWheelDelta())
        event.Skip()
    
    def OnMessagePanelPaint(self, event):
        self.RefreshView()
        event.Skip()
    
    def OnMessagePanelResize(self, event):
        if self.IsMessagePanelBottom():
            self.ScrollToFirst()
        else:
            self.RefreshView()
        event.Skip()
    
    def OnScrollTimer(self, event):
        if self.ScrollSpeed != 0.:
            speed_norm = abs(self.ScrollSpeed)
            period = REFRESH_PERIOD / speed_norm
            self.ScrollMessagePanel(-speed_norm / self.ScrollSpeed)
            self.LastStartTime = gettime()
            self.ScrollTimer.Start(int(period * 1000), True)
        event.Skip()
    
    def SetScrollSpeed(self, speed):
        if speed == 0.:
            self.ScrollTimer.Stop()
        else:
            speed_norm = abs(speed)
            period = REFRESH_PERIOD / speed_norm
            current_time = gettime()
            if self.LastStartTime is not None:
                elapsed_time = current_time - self.LastStartTime
                if elapsed_time > period:
                    self.ScrollMessagePanel(-speed_norm / speed)
                    self.LastStartTime = current_time
                else:
                    period -= elapsed_time
            else:
                self.LastStartTime = current_time
            self.ScrollTimer.Start(int(period * 1000), True)
        self.ScrollSpeed = speed    
    
    def ScrollToLast(self):
        if len(self.LogMessages) > 0:
            self.CurrentMessage = len(self.LogMessages) - 1
            message = self.LogMessages[self.CurrentMessage]
            if not self.FilterLogMessage(message):
                message, self.CurrentMessage = self.GetPreviousMessage(self.CurrentMessage)
            self.RefreshView()

    def ScrollToFirst(self):
        if len(self.LogMessages) > 0:
            message_idx = 0
            message = self.LogMessages[message_idx]
            if not self.FilterLogMessage(message):
                next_message, msgidx = self.GetNextMessage(message_idx)
                if next_message is not None:
                    message_idx = msgidx
                    message = next_message
            while message is not None:
                message, msgidx = self.GetPreviousMessage(message_idx)
                if message is not None:
                    message_idx = msgidx
            message = self.LogMessages[message_idx]
            if self.FilterLogMessage(message):
                while message is not None:
                    message, msgidx = self.GetNextMessage(message_idx)
                    if message is not None:
                        if not self.IsMessagePanelBottom(msgidx):
                            break
                        message_idx = msgidx
                self.CurrentMessage = message_idx
            else:
                self.CurrentMessage = None
            self.RefreshView()
