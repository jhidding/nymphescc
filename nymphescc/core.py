# ~\~ language=Python filename=nymphescc/core.py
# ~\~ begin <<lit/core.md|nymphescc/core.py>>[0]
from dataclasses import dataclass
from .messages import read_settings, modulators, Setting, Group


@dataclass
class Register:
    flat_config: dict[str, Setting]
    midi_map: dict[int, tuple[str, str]]
    values: dict[str, dict[str, int]]

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
# ~\~ end
