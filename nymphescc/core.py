# ~\~ language=Python filename=nymphescc/core.py
# ~\~ begin <<lit/core.md|nymphescc/core.py>>[0]
from dataclasses import dataclass
from queue import Queue
from .messages import read_settings, modulators, Setting, Group


@dataclass
class Port:
    name: str
    selected_mod: int


@dataclass
class Register:
    flat_config: dict[str, Setting]
    midi_map: dict[int, tuple[str, str]]
    values: dict[int, dict[str, int]]
    ports: dict[str, Port] = None

    def gui_msg(self, ctrl, mod, value):
        self.values[mod][ctrl] = value

    @staticmethod
    def new():
        config = read_settings()
        flat_config = \
            { group.name + "." + setting.name: setting
              for group in config.values()
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
        values = { mod: { k: 0 for k in flat_config.keys() }
                   for mod in range(len(modulators(config))) }

        return Register(
            flat_config,
            midi_map_global | midi_map_baseline | midi_map_mod,
            values)
# ~\~ end
