# ~\~ language=Python filename=nymphescc/core.py
# ~\~ begin <<lit/core.md|nymphescc/core.py>>[0]
from dataclasses import dataclass
import asyncio
from queue import Queue
from .messages import read_settings, modulators, Setting, Group


@dataclass
class Port:
    name: str
    caps: str
    selected_mod: int = 0


try:
    import alsa_midi
except ImportError:
    alsa_client = None
else:
    from alsa_midi import WRITE_PORT, READ_PORT, PortType, ControlChangeEvent
    alsa_client = alsa_midi.SequencerClient("NymphesCC")


class AlsaPort(Port):
    def __init__(self, name, caps):
        super().__init__(name, caps)
        match caps:
            case "in":
                self._port = alsa_client.create_port(name, WRITE_PORT, type=PortType.MIDI_GENERIC)
            case "out":
                self._port = alsa_client.create_port(name, READ_PORT, type=PortType.MIDI_GENERIC)
            case _:
                raise ValueError(f"Unknown port caps '{caps}'")
        print(self._port)

    def send_cc(self, channel, param, value):
        print("out:", channel, param, value)
        alsa_client.event_output(
            ControlChangeEvent(channel, param, value),
            port=self._port)
        alsa_client.drain_output()

    def read_cc(self):
        port_id = self._port.get_info().port_id
        while True:
            event = alsa_client.event_input()
            if event is not None and event.dest.port_id == port_id:
                match event:
                    case ControlChangeEvent():
                        print("inp:", event.channel, event.param, event.value)
                        yield event.channel, event.param, event.value


@dataclass
class Register:
    flat_config: dict[str, Setting]
    midi_map: dict[int, tuple[str, str]]
    values: dict[int, dict[str, int]]
    ports: dict[str, Port] = None

    def gui_msg(self, ctrl, mod, value):
        if value != self.values[mod][ctrl]:
            self.values[mod][ctrl] = value
            return True
        else:
            return False

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
