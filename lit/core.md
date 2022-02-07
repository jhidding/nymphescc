# Core data model
At the core we have a bank with known values for each Midi CC. The application should have an external MIDI In for 3rd party devices and a duplex connection with the Nymphes. Messages from MIDI In should be forwarded to the Nymphes, while messages from Nymphes should only affect the internal state of NymphesCC.

``` {.python file=nymphescc/core.py}
from abc import abstractmethod
from dataclasses import dataclass
import logging
from queue import Queue
from threading import Event
from .messages import read_settings, modulators, Setting, Group
import mido
import io


@dataclass
class Port:
    name: str
    caps: str
    selected_mod: int = 0

    @abstractmethod
    def send_cc(self, channel, param, value):
        pass


class BytesPort(Port):
    def __init__(self, name, caps, buffer=b""):
        super().__init__(name, caps)
        self._file = io.BytesIO(buffer)

    def send_cc(self, channel, param, value):
        msg = mido.Message("control_change", channel=channel, param=param, value=value)
        self._file.write(msg.bin())

    @property
    def bytes(self):
        return self._file.getbuffer()

    def read_cc(self):
        for msg in mido.Parser().feed(self.bytes):
            if msg.is_cc():
                yield msg.channel, msg.param, msg.value


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

    def auto_connect(self):
        if self.caps == "in":
            ports = alsa_client.list_ports(input=True)
            try:
                target = next(p for p in ports if p.client_name == "Nymphes")
            except StopIteration:
                logging.warn("Could not auto-connect to Nymphes.")
            else:
                self._port.connect_from(target)
        if self.caps == "out":
            ports = alsa_client.list_ports(output=True)
            try:
                target = next(p for p in ports if p.client_name == "Nymphes")
            except StopIteration:
                logging.warn("Could not auto-connect to Nymphes.")
            else:
                self._port.connect_to(target)

    def send_cc(self, channel, param, value):
        alsa_client.event_output(
            ControlChangeEvent(channel, param, value),
            port=self._port)
        alsa_client.drain_output()

    def read_cc(self, quit_event: Event, timeout=0.1):
        port_id = self._port.get_info().port_id
        while True:
            event = alsa_client.event_input(timeout=timeout)
            if event is None:
                if quit_event.is_set():
                    return
                else:
                    continue
            if event is not None and event.dest.port_id == port_id:
                match event:
                    case ControlChangeEvent():
                        yield event.channel, event.param, event.value
                    case _:
                        logging.debug("skipped MIDI event: %s", str(event))


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
```

## Reading messages

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


def modulators(settings):
    labels = settings["modulators"].content[0].labels
    return ["Baseline"] + labels


if __name__ == "__main__":
    print(read_settings())
```

