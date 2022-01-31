# ~\~ language=Python filename=nymphescc/main.py
# ~\~ begin <<README.md|nymphescc/main.py>>[0]
from __future__ import annotations
import wx

from .messages import Setting, Group, read_settings

class SettingSlider(wx.BoxSizer):
    def __init__(self, parent: Controller, setting: Setting):
        wx.BoxSizer.__init__(self, wx.VERTICAL)
        label = wx.StaticText(
            parent,
            label=setting.name,
            style=wx.ALIGN_CENTRE_HORIZONTAL)
        slider = wx.Slider(
            parent,
            minValue=setting.bounds.lower,
            maxValue=setting.bounds.upper,
            value=0,
            style=wx.SL_VERTICAL | wx.SL_VALUE_LABEL | wx.SL_INVERSE,
            name=setting.name,
            size=wx.Size(-1, 300))
        self.Add(label)
        self.Add(slider, wx.EXPAND)

class SettingsGroup(wx.StaticBoxSizer):
    def __init__(self, parent: wx.Window, name: str, group: Group):
        wx.StaticBoxSizer.__init__(self, wx.HORIZONTAL, parent, name)
        for setting in group.content:
            slider = SettingSlider(parent, setting)
            self.Add(slider, wx.EXPAND)

class Controller(wx.Frame):
    def __init__(self, settings: dict[str, Group]):
        wx.Frame.__init__(self, None, title="NymphesCC", size=(800,600))
        self.CreateStatusBar()
        sizer = wx.BoxSizer()
        groups = ["oscillator", "filter", "envelope.filter", "envelope.amplitude"]
        for select in groups:
            sizer.AddSpacer(5)
            sizer.Add(SettingsGroup(self, select, settings[select]))
            sizer.AddSpacer(5)
        self.SetSizer(sizer) 
        self.Show(True)


def main():
    app = wx.App(False)
    settings = read_settings()
    frame = Controller(settings)
    app.MainLoop()
# ~\~ end
