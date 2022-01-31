# ~\~ language=Python filename=nymphescc/setting.py
# ~\~ begin <<README.md|nymphescc/setting.py>>[0]
# ~\~ begin <<README.md|setting-imports>>[0]
from __future__ import annotations
from typing import Optional
from importlib import resources
import configparser
from pathlib import Path
# ~\~ end
from dataclasses import dataclass
# ~\~ begin <<README.md|config-error>>[0]
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
# ~\~ end

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

    # ~\~ begin <<README.md|setting-parser>>[0]
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
    # ~\~ end

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

# ~\~ begin <<README.md|setting-tests>>[0]
def test_messages_ini():
    settings = read_settings()
    ccs = sum([[s.cc_code for s in section.values()]
               for section in settings.values()], [])
    print(settings)
    assert len(ccs) == len(set(ccs))
# ~\~ end
# ~\~ end
