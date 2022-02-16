# ~\~ language=Python filename=nymphescc/core.py
# ~\~ begin <<lit/core.md|nymphescc/core.py>>[0]
from dataclasses import dataclass
import logging
from threading import Event
from .messages import read_settings, modulators, Setting, Group
import mido
import io
from typing import Iterator, Protocol


class BytesPort:
    def __init__(self, buffer=b""):
        self.selected_mod = 0
        self._file = io.BytesIO(buffer)

    def is_input_port(self) -> bool:
        return True

    def is_output_port(self) -> bool:
        return True

    def send_cc(self, channel: int, param: int, value: int):
        msg = mido.Message("control_change", channel=channel, param=param, value=value)
        self._file.write(msg.bin())

    @property
    def bytes(self):
        return self._file.getbuffer()

    def read_cc(self, _) -> Iterator[tuple[int, int, int]]:
        for msg in mido.Parser().feed(self.bytes):
            if msg.is_cc():
                yield msg.channel, msg.param, msg.value


import alsa_midi
from alsa_midi import WRITE_PORT, READ_PORT, PortCaps, PortType, ControlChangeEvent


class AlsaPort:
    def __init__(self, client, name, caps):
        self.caps = caps
        self.selected_mod = 0
        self._client = client
        match caps:
            case "in":
                self._port = self._client.create_port(name, WRITE_PORT, type=PortType.MIDI_GENERIC)
            case "out":
                self._port = self._client.create_port(name, READ_PORT, type=PortType.MIDI_GENERIC)
            case _:
                raise ValueError(f"Unknown port caps '{caps}'")

    def auto_connect(self):
        try:
            if self.caps == "out":
                ports = self._client.list_ports(output=True)
                target = next(p for p in ports if p.client_name == "Nymphes")
                self._port.connect_to(target)
            if self.caps == "in":
                ports = self._client.list_ports(input=True)
                target = next(p for p in ports if p.client_name == "Nymphes")
                self._port.connect_from(target)
        except StopIteration:
            logging.warn("Nymphes device not found")
            return
        except alsa_midi.ALSAError as e:
            logging.error(e)
            return

        logging.debug("connected to: %s", str(target))

    def send_cc(self, channel: int, param: int, value: int):
        self._client.event_output(
            ControlChangeEvent(channel, param, value),
            port=self._port)
        self._client.drain_output()

    def read_cc(self, quit_event: Event, timeout=0.1):
        port_id = self._port.get_info().port_id
        while True:
            event = self._client.event_input(timeout=timeout)
            if event is None:
                if quit_event.is_set():
                    return
                else:
                    continue
            if event is not None and event.dest.port_id == port_id:
                if isinstance(event, ControlChangeEvent):
                    yield event.channel, event.param, event.value
                else:
                    logging.debug("skipped MIDI event: %s", str(event))


@dataclass
class Register:
    flat_config: dict[str, Setting]
    midi_map: dict[int, tuple[str, str]]
    values: dict[int, dict[str, int]]

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
        baseline_values = { k: 0 for k in flat_config.keys() }
        values = { mod: { k: 0 for k, v in flat_config.items() if v.mod is not None}
                   for mod in range(1, len(modulators(config))) } \
               | { 0: baseline_values }

        return Register(
            flat_config,
            midi_map_global | midi_map_baseline | midi_map_mod,
            values)

    def send_cc(self, port, ctrl, mod, value):
        if mod is not None and mod != 0:
            if port.selected_mod != mod:
                port.send_cc(0, self.flat_config["modulators.selector"].cc, mod - 1)
                port.selected_mod = mod
            port.send_cc(0, self.flat_config[ctrl].mod, value)
        else:
            port.send_cc(0, self.flat_config[ctrl].cc, value)

    def send_all(self, port):
        for mod, s in self.values.items():
            for ctrl, value in s.items():
                self.send_cc(port, ctrl, mod, value)
# ~\~ end
