# Core data model
At the core we have a bank with known values for each Midi CC. The application should have an external MIDI In for 3rd party devices and a duplex connection with the Nymphes. Messages from MIDI In should be forwarded to the Nymphes, while messages from Nymphes should only affect the internal state of NymphesCC.

``` {.python file=nymphescc/core.py}
from .messages import read_settings, Setting, Group


class Register:
    
```

