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
        if self.labels is not None \
        and len(self.labels) != (self.bounds.upper - self.bounds.lower + 1):
            raise ConfigValueError(self, "wrong number of labels")

    def is_scale(self):
        return self.bounds.lower == 0 and self.bounds.upper == 127

    def is_enum(self):
        return self.labels is not None


@dataclass
class Group:
    name: str
    long: str
    description: Optional[str]
    content: list[Setting]

    @property
    def scales(self):
        return list(filter(Setting.is_scale, self.content))

    @property
    def enums(self):
        return list(filter(Setting.is_enum, self.content))


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
from gi.repository import Gtk, Gio
from dataclasses import dataclass


from .messages import read_settings, Group, Setting


def slider_group(group: Group):
    frame = Gtk.Frame()
    frame.set_label(group.long)
    grid = Gtk.Grid()
    grid.set_column_spacing(6)
    grid.set_margin_bottom(5)
    grid.set_column_homogeneous(True)
    frame.set_child(grid)

    for i, s in enumerate(group.scales):
        slider = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, s.bounds.lower, s.bounds.upper, 1)
        slider.set_vexpand(True)
        slider.set_draw_value(True)
        slider.set_inverted(True)
        slider.set_value_pos(Gtk.PositionType.BOTTOM)
        if not s.tics:
            slider.add_mark(0, Gtk.PositionType.LEFT, None)
            slider.add_mark(63, Gtk.PositionType.LEFT, None)
            slider.add_mark(127, Gtk.PositionType.LEFT, None)
        else:
            for t in s.tics:
                slider.add_mark(t.value, Gtk.PositionType.LEFT, t.label)

        label = Gtk.Label()
        label.set_label(s.name.upper())
        grid.attach(slider, i, 0, 1, 1)
        grid.attach(label, i, 1, 1, 1)

    for i, s in enumerate(group.enums):
        combo = Gtk.ComboBoxText()
        combo.set_margin_end(5)
        for t in s.labels:
            combo.append(None, t)
        label = Gtk.Label.new(s.name.upper())
        if i == 0:
            combo.set_margin_top(5)
        grid.attach(label, 0, i+2, 1, 1)
        grid.attach(combo, 1, i+2, len(group.scales) - 1, 1)

    return frame


def mode_selector(group: Group):
    frame = Gtk.Frame()
    frame.set_label(group.long)
    setting = group.content[0]
    list_box = Gtk.ListBox()
    for name in ["Unmodulated"] + setting.labels:
        label = Gtk.Label()
        label.set_label(name)
        label.set_margin_top(5)
        label.set_margin_bottom(5)
        list_box.append(label)
    list_box.set_hexpand(True)
    list_box.set_selection_mode(Gtk.SelectionMode.BROWSE)
    list_box.select_row(list_box.get_row_at_index(0))
    frame.set_child(list_box)
    return frame


def on_activate(app):
    win = Gtk.ApplicationWindow(application=app, title="NymphesCC")
    win.set_default_size(1300, 768)
    header_bar = Gtk.HeaderBar()
    header_bar.set_show_title_buttons(True)
    side_bar_button = Gtk.Button()
    icon = Gio.ThemedIcon(name="document-open")
    image = Gtk.Image.new_from_gicon(icon)
    side_bar_button.set_child(image)
    header_bar.pack_start(side_bar_button)
    win.set_titlebar(header_bar)
    scrolled_win = Gtk.ScrolledWindow()

    settings = read_settings()
    layout = [("oscillator", 0, 0, 5, 1), 
              ("filter", 5, 0, 3, 1),
              ("envelope.filter", 0, 1, 2, 1),
              ("envelope.amplitude", 2, 1, 2, 1),
              ("lfo.lfo-1", 4, 1, 2, 1),
              ("lfo.lfo-2", 6, 1, 2, 1)]
    grid = Gtk.Grid()
    grid.set_column_spacing(5)
    grid.set_row_spacing(5)
    grid.set_column_homogeneous(True)
    grid.set_row_homogeneous(True)

    for s, x, y, w, h in layout:
        grid.attach(slider_group(settings[s]), x, y, w, h)
    grid.attach(mode_selector(settings["modulators"]), 8, 0, 1, 1)
    grid.set_margin_top(5)
    grid.set_margin_bottom(5)
    grid.set_margin_start(5)
    grid.set_margin_end(5)

    scrolled_win.set_child(grid)
    win.set_child(scrolled_win)
    win.present()


def main():
    app = Gtk.Application(application_id='org.gtk.Example')
    app.connect('activate', on_activate)
    app.run(None)
```
