# Core data model
At the core we have a bank with known values for each Midi CC. The application should have an external MIDI In for 3rd party devices and a duplex connection with the Nymphes. Messages from MIDI In should be forwarded to the Nymphes, while messages from Nymphes should only affect the internal state of NymphesCC.

``` {.python file=nymphescc/core.py}
from dataclasses import dataclass
from .messages import read_settings, modulators, Setting, Group


@dataclass
class Port:
    name: str
    selected_mod: int


@dataclass
class Register:
    flat_config: dict[str, Setting]
    midi_map: dict[int, tuple[str, str]]
    values: dict[str, dict[str, int]]
    ports: dict[str, Port] = None   

    @staticmethod
    def new():
        config = read_settings()
        flat_config = \
            { group.name + "." + setting.name: setting
              for group in config.items()
              for setting in group.content }
        midi_map_global = \
            { v.cc: ("global", k)
              for k, v in flat_config.items()
              if v.mod is None }
        midi_map_baseline = \
            { v.cc: ("baseline", k)
              for k, v in flat_config.items() 
              if v.mod }
        midi_map_mod = \
            { v.mod: ("mod", k)
              for k, v in flat_config.items()
              if v.mod }
        values = { mod: { k: 0 for k in config.keys() }
                   for mod in modulators(config) }

        return Register(
            flat_config,
            midi_map_global | midi_map_baseline | midi_map_mod,
            values)
```

