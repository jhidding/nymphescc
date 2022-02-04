# Old stuff
Tried first with WxPython, but that library suffers from lack of documentation and ugly looking results (compared to the slickness of Gtk).

``` {.python file=nymphescc/wx.py}
from __future__ import annotations
import wx

from .messages import Setting, Group, read_settings



class SettingSlider(wx.BoxSizer):
    def __init__(self, parent: Controller, setting: Setting):
        wx.BoxSizer.__init__(self, wx.VERTICAL)
        label = wx.StaticText(
            parent,
            label=setting.name.upper(),
            size=(50, -1),
            style=wx.ALIGN_CENTRE | wx.TEXT_ALIGNMENT_CENTER)
        slider = wx.Slider(
            parent,
            minValue=setting.bounds.lower,
            maxValue=setting.bounds.upper,
            value=0,
            style=wx.SL_VERTICAL | wx.SL_VALUE_LABEL | wx.SL_INVERSE,
            name=setting.name,
            size=wx.Size(-1, 300))
        if setting.description is not None:
            label.SetHelpText(setting.description)
            slider.SetHelpText(setting.description)
        self.Add(slider, wx.EXPAND)
        box = wx.BoxSizer()
        box.AddSpacer(10)
        box.Add(label, wx.EXPAND)
        self.Add(box, wx.ALIGN_CENTER_HORIZONTAL)


class SettingsGroup(wx.StaticBoxSizer):
    def __init__(self, parent: wx.Window, name: str, group: Group):
        wx.StaticBoxSizer.__init__(self, wx.HORIZONTAL, parent, name)
        for setting in group.content:
            if setting.bounds.upper != 127:
                continue
            slider = SettingSlider(parent, setting)
            self.Add(slider, wx.EXPAND)

class Controller(wx.Frame):
    def __init__(self, settings: dict[str, Group]):
        wx.Frame.__init__(self, None, title="NymphesCC", size=(800,600))
        self.CreateStatusBar()
        vertical_stack = wx.BoxSizer(wx.VERTICAL)
        horiz1 = wx.BoxSizer()
        horiz2 = wx.BoxSizer()
        groups1 = ["oscillator", "filter"]
        groups2 = ["envelope.filter", "envelope.amplitude", "lfo.lfo-1", "lfo.lfo-2"]
        for select in groups1:
            horiz1.AddSpacer(5)
            horiz1.Add(SettingsGroup(self, select, settings[select]))
            horiz1.AddSpacer(5)
        for select in groups2:
            horiz2.AddSpacer(5)
            horiz2.Add(SettingsGroup(self, select, settings[select]))
            horiz2.AddSpacer(5)
        vertical_stack.Add(horiz1)
        vertical_stack.Add(horiz2)
        self.SetSizer(vertical_stack) 
        self.Show(True)



def main():
    app = wx.App(False)
    settings = read_settings()
    frame = Controller(settings)
    app.MainLoop()
```


