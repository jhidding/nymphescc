---
title: "NymphesCC"
subtitle: "MIDI controller using WxPython"
author: "Johan Hidding"
---

``` {.python file=nymphescc/__init__.py}
__version__ = "0.1.0"
```

From the Nymphes manual we get a table with MIDI CC messages.

# The GUI
``` {.python file=nymphescc/messages.py}
from __future__ import annotations
from importlib import resources
import dhall
from pathlib import Path
from dataclasses import dataclass, is_dataclass
import typing
from typing import Optional, Union
import types


class ConfigError(Exception):
    pass


@dataclass
class ConfigValueError(ConfigError):
    setting: Setting
    what: str


@dataclass
class ConfigParserError(ConfigError):
    input_str: str
    what: str


@dataclass
class Bounds:
    lower: int
    upper: int


@dataclass
class Tic:
    value: int
    label: str


@dataclass
class Setting:
    """Setting class.

    Attributes:
        name: name of the setting.
        long: human readable name.
        cc: MIDI CC code
        mod: MIDI CC code of modulator setting
        bounds: lower (inclusive) and upper (exclusive) bounds
        tics: list of known values with description
        labels: list of aliases for settings, should have same length
            as bounds interval.
        flags: list of related settings.
    """
    name: str
    long: str
    cc: int
    bounds: Bounds
    description: Optional[str]
    mod: Optional[int]
    tics: Optional[list[Tic]]
    labels: Optional[list[str]]

    def validate(self):
        if not (self.bounds.lower < self.bounds.upper):
            raise ConfigValueError(self, "illegal bounds")
        if self.enum is not None \
        and len(self.labels) != (self.bounds.upper - self.bounds.lower + 1):
            raise ConfigValueError(self, "wrong number of labels")


@dataclass
class Group:
    name: str
    long: str
    description: Optional[str]
    content: list[Setting]


def isgeneric(annot):
    return hasattr(annot, "__origin__") \
        and hasattr(annot, "__args__")


def construct(annot, json):
    """Construct an object from a given type from a JSON stream.

    The `annot` type should be one of: str, int, list[T], Optional[T],
    or a dataclass, and the JSON data should match exactly the given
    definitions in the dataclass hierarchy.
    """
    if annot is str:
        assert isinstance(json, str)
        return json
    if annot is int:
        assert isinstance(json, int)
        return json
    if isgeneric(annot) and typing.get_origin(annot) is list:
        assert isinstance(json, list)
        return [construct(typing.get_args(annot)[0], item) for item in json]
    if isgeneric(annot) and typing.get_origin(annot) is Union \
        and typing.get_args(annot)[1] is types.NoneType:
        if json is None:
            return None
        else:
            return construct(typing.get_args(annot)[0], json)
    if is_dataclass(annot):
        assert isinstance(json, dict)
        arg_annot = typing.get_type_hints(annot)
        assert all(k in json for k in arg_annot)
        args = { k: construct(v, json[k])
                 for k, v in arg_annot.items() }
        return annot(**args)


def read_settings():
    with resources.open_text(__package__, "messages.dhall") as inp:
        raw_data = dhall.load(inp)
    group_lst = construct(list[Group], raw_data)
    return { grp.name: grp for grp in group_lst }


if __name__ == "__main__":
    print(read_settings())
```

``` {.python file=nymphescc/main.py}
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


``` {.python file=nymphescc/gtk.py}
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

def on_activate(app):
    win = Gtk.ApplicationWindow(application=app)
    btn = Gtk.Button(label="Hello, World!")
    btn.connect('clicked', lambda x: win.close())
    win.set_child(btn)
    win.present()

app = Gtk.Application(application_id='org.gtk.Example')
app.connect('activate', on_activate)
app.run(None)
```
