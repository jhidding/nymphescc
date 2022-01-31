---
title: "NymphesCC"
subtitle: "MIDI controller using PySimpleGUI"
author: "Johan Hidding"
---

``` {.python file=nymphescc/__init__.py}
__version__ = "0.1.0"
```

From the Nymphes manual we get a table with MIDI CC messages.

``` {.config file=nymphescc/messages.ini}
[Oscillator Control]
PW               = 11, 0-127
Wave             = 12, 0-127
OSC              = 13, 0-127
Sub              = 14, 0-127
Noise            = 15, 0-127
LFO              = 16, 0-127
EG               = 17, 0-127
Det              = 18, 0-127
Chord            = 19, 0-127


[Filter Control]
HPF              =  3, 0-127
LPF              =  4, 0-127
Gld              =  5, 0-127
Trk              =  6, 0-127
AMP              =  7, 0-127
Res              =  8, 0-127
EG               =  9, 0-127
LFO              = 10, 0-127


[Envelope Control]
FA        = 20, 0-127
FD        = 21, 0-127
FS        = 22, 0-127
FR        = 23, 0-127
AA        = 24, 0-127
AD        = 25, 0-127
AS        = 26, 0-127
AR        = 27, 0-127

[Play Mode]
Mode                    = 30, 0-5, POLY / UNI A / UNI B / TRI / DUO / MONO

[LFO Control]
LFO 1 Rate              = 31, 0-127
LFO 1 Wave              = 32, 0-127
LFO 1 Delay             = 33, 0-127
LFO 1 Fade              = 34, 0-127
LFO 1 Type              = 35, 0-3, BPM / LOW / HIGH / TRACK
LFO 1 SYNC              = 36, 0-1, FREE / KEY SYNC
LFO 2 Rate Depth        = 37, 0-127
LFO 2 Wave              = 38, 0-127
LFO 2 Delay Depth       = 39, 0-127
LFO 2 Fade Depth        = 40, 0-127
LFO 2 TYPE              = 41, 0-3, LOW / HIGH / TRACK / BPM
LFO 2 SYNC              = 42, 0-1, FREE / KEY SYNC

[Reverb Control]
Reverb Size             = 44, 0-127
Reverb Decay            = 45, 0-127
Reverb Filter           = 46, 0-127
Reverb Mix              = 47, 0-127

[Mod Source Control]
Selector                = 50, 0-3, LFO 2 / ModWheel / Velocity / Aftertouch
OSC Wave Depth          = 51, 0-127
OSC Level Depth         = 52, 0-127
Sub Level Depth         = 53, 0-127
Noise Level Depth       = 54, 0-127
LFO Pitch Depth Depth   = 55, 0-127
PulseWidth Depth        = 56, 0-127
Glide Depth             = 57, 0-127
Detune Depth            = 58, 0-127
Chord Selector Depth    = 59, 0-127
EG Pitch Depth Depth    = 60, 0-127
LPF Cutoff Depth        = 61, 0-127
Resonance Depth         = 62, 0-127
LPF EG Depth Depth      = 63, 0-127

Sustain Pedal           = 64, 0-1, OFF / ON
HPF Cutoff Depth        = 65, 0-127
LPF Tracking Depth      = 66, 0-127
LPF Cutoff / LFO Depth  = 67, 0-127
Legato                  = 68, 0-1, OFF / ON
Filter EG Attack Depth  = 69, 0-127
Filter EG Decay Depth   = 70, 0-127
Filter EG Sustain Depth = 71, 0-127
Filter EG Release Depth = 72, 0-127
AMP EG Attack Depth     = 73, 0-127
AMP EG Decay Depth      = 74, 0-127
AMP EG Sustain Depth    = 75, 0-127
AMP EG Release Depth    = 76, 0-127
LFO 1 Rate Depth        = 77, 0-127
LFO 1 Wave Depth        = 78, 0-127
LFO 1 Delay Depth       = 79, 0-127
LFO 1 Fade Depth        = 80, 0-127
LFO 2 Rate Depth        = 81, 0-127
LFO 2 Wave Depth        = 82, 0-127
LFO 2 Delay Depth       = 83, 0-127
LFO 2 Fade Depth        = 84, 0-127
```

## Settings
Every setting has a name, a range and possibly an enum representation. We stored the CC messages as an INI file, parsable by `configparser`. This is very readable, but has the downside that we need to do some manual checks.

``` {.python file=nymphescc/setting.py}
<<setting-imports>>
from dataclasses import dataclass
<<config-error>>

@dataclass
class Setting:
    """Setting class.

    Attributes:
        name: name of the setting.
        cc_code: MIDI CC code
        bounds: lower (inclusive) and upper (exclusive) bounds
        enum: list of aliases for settings, should have same length
            as bounds interval.
    """
    name: str
    cc_code: int
    bounds: tuple[int, int]
    enum: Optional[list[str]]

    <<setting-parser>>

SettingsGroup = dict[str, Setting]
Settings = dict[str, SettingsGroup]

def read_settings() -> Settings:
    """Reads the settings from a module internal data file."""
    with resources.path("nymphescc", "messages.ini") as path:
        config = configparser.ConfigParser()
        config.optionxform = str  # type: ignore
        config.read(path)
        return { k: { n: Setting.parse(FileLoc(path, (k, n)), n, v)
                    for n, v in config[k].items() }
                for k in config.sections() }

<<setting-tests>>
```

``` {.python #setting-imports .hide}
from __future__ import annotations
from typing import Optional
from importlib import resources
import configparser
from pathlib import Path
```

``` {.python #config-error .hide}
@dataclass
class FileLoc:
    filename: Path
    setting: tuple[str, str]


class ConfigError(Exception):
    pass


@dataclass
class ConfigValueError(ConfigError):
    in_file: FileLoc
    setting: Setting
    what: str


@dataclass
class ConfigParserError(ConfigError):
    in_file: FileLoc
    input_str: str
    what: str
```

``` {.python #setting-parser .hide}
def validate(self, file_loc: FileLoc):
    if not (self.bounds[0] < self.bounds[1]):
        raise ConfigValueError(file_loc, self, "illegal bounds")
    if self.enum is not None \
    and len(self.enum) != (self.bounds[1] - self.bounds[0] + 1):
        raise ConfigValueError(file_loc, self, "wrong number of labels")

@staticmethod
def parse(section: FileLoc, name: str, inp: str) -> Setting:
    settings = inp.split(',')

    if len(settings) < 2 or len(settings) > 4:
        raise ConfigParserError(
            section, inp, "wrong number of comma-separated arguments")

    try:
        cc_code = int(settings[0])
    except ValueError:
        raise ConfigParserError(
            section, inp, "could not read control code argument")

    try:
        lower_bound, upper_bound = [int(x) for x in settings[1].split('-')]
    except ValueError:
        raise ConfigParserError(
            section, inp, "could not read bounds argument")

    if len(settings) == 3:
        enum = [x.strip() for x in settings[2].split("/")]
    else:
        enum = None

    result = Setting(name, cc_code, (lower_bound, upper_bound), enum)
    result.validate(section)
    return result
```

``` {.python #setting-tests .hide}
def test_messages_ini():
    settings = read_settings()
    ccs = sum([[s.cc_code for s in section.values()]
               for section in settings.values()], [])
    print(settings)
    assert len(ccs) == len(set(ccs))
```

``` {.python file=nymphescc/main.py}
from __future__ import annotations
import wx

from .setting import Settings, SettingsGroup, Setting, read_settings

class SettingSlider(wx.BoxSizer):
    def __init__(self, parent: Controller, setting: Setting):
        wx.BoxSizer.__init__(self, wx.VERTICAL)
        label = wx.StaticText(
            parent,
            label=setting.name,
            style=wx.ALIGN_CENTRE_HORIZONTAL)
        slider = wx.Slider(
            parent,
            minValue=setting.bounds[0],
            maxValue=setting.bounds[1],
            value=0,
            style=wx.SL_VERTICAL | wx.SL_VALUE_LABEL | wx.SL_INVERSE,
            name=setting.name,
            size=wx.Size(-1, 300))
        self.Add(label)
        self.Add(slider, wx.EXPAND)

class SettingsGroup(wx.StaticBoxSizer):
    def __init__(self, parent: wx.Window, name: str, group: SettingsGroup):
        wx.StaticBoxSizer.__init__(self, wx.HORIZONTAL, parent, name)
        for setting in group.values():
            slider = SettingSlider(parent, setting)
            self.Add(slider, wx.EXPAND)

class Controller(wx.Frame):
    def __init__(self, settings: Settings):
        wx.Frame.__init__(self, None, title="NymphesCC", size=(800,600))
        self.CreateStatusBar()
        sizer = wx.BoxSizer()
        groups = ["Oscillator Control", "Filter Control", "Envelope Control"]
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
```
