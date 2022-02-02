# Settings {.messages}
From the Nymphes manual we get a table with MIDI CC messages.

``` {.dhall #schema}
let Range : Type = { lower : Natural, upper : Natural }
let range = \(lower : Natural) -> \(upper : Natural) ->
    { lower = lower, upper = upper }

let Tic : Type = { value : Natural, label : Text }
let tic = \(value : Natural) -> \(label : Text) ->
    { value = value, label = label }

let Setting =
    { Type    = { name : Text
                , long : Text
                , cc : Natural
                , bounds : Range
                , description : Optional Text
                , labels : Optional (List Text)
                , mod : Optional Natural
                , flags : Optional (List Text)
                , tics : Optional (List Tic) }
    , default = { bounds = range 0 127
                , description = None Text
                , labels = None (List Text)
                , mod = None Natural
                , flags = None (List Text)
                , tics = None (List Tic) } }
```

``` {.make target=messages.dhall dir=nymphescc}
nymphescc/messages.dhall: lit/messages.md .entangled/scripts/message-table.lua
    pandoc -t plain -f commonmark_x lit/messages.md --lua-filter .entangled/scripts/message-table.lua | dhall format --unicode > $@
```

## Oscillator Control {.group name=oscillator}
### Wave form {.setting name=wave cc=12 mod=51}
``` {.values}
{ tics = Some [tic 0 "⩘", tic 63 "⎍", tic 127 "⋀"] }
```
Controls the shape of the generated wave, going from sawtooth through square, to triangle waves.

### Pulse width {.setting name=pw cc=11 mod=56}
Control the pulse width of the square wave form. This can be modulated using LFO 2.

### Level {.setting name=lvl cc=13 mod=52}
Sets the amplitude of the wave form.

### Sub-oscillator {.setting name=sub cc=14 mod=53}
Amplitude of sub-oscillator, which produces a square wave one octave below the main oscillator.

### Noise level {.setting name=noise cc=15 mod=54}
Amplitude of white noise, mixed in with main oscillator and sub-oscillator.

### Glide {.setting name=gld cc=5 mod=57}
``` {.values}
{ flags = Some ["misc.legato"] }
```
Allow notes to glide (portamento). The behaviour strongly depends on the playing mode. Optionally, glide will respond to legato playing.

### Low frequency oscillator {.setting name=lfo cc=16 mod=55}
Control the change in pitch of the main oscillator with the LFO, from subtle vibrato to extreme whoopy sounds.

### Envelope Generator {.setting name=ev cc=17 mod=60}
Control how much the filter envelope modulates the pitch of the oscillator. Envelopes are unipolar.

### Detune {.setting name=dtn cc=18 mod=58}
Detune notes when in stacked modes (i.e. multiple oscillators per node: UNI A, UNI B, TRI, DUO).

### Chord control {.setting name=chord cc=19 mod=59}
Choose from different predefined chords (see Chords tab).

## Filter control {.group name=filter}
### Hipass Cutoff {.setting name=hpf cc=3 mod=65}
``` {.values}
{ tics = Some [tic 0 "33", tic 63 "", tic 127 "17k"] }
```
Sets the cutoff frequency of the hipass filter. Hipass is piped after lopass, creating a bandpass.

### Lopass Cutoff {.setting name=cut cc=4 mod=61}
``` {.values}
{ tics = Some [tic 0 "33", tic 63 "", tic 127 "17k"] }
```
Sets the cutoff frequency of the lopass filter.

### Resonance {.setting name=res cc=8 mod=62}
Sets the amount of filter resonance, i.e. how much upper frequencies are amplified.

### Tracking {.setting name=track cc=6 mod=66}
Sets how much the filter cutoff tracks the frequency of the main oscillator. At `127` the cutoff frequncy tracks the oscillator pitch 1:1. In combination with high resonance this can create beautiful overtones.

If you set this to other fractions (e.g. `63` for quarter tones), use only noise as a sound source, and beef up resonance, you can play microtonal music!

### Envelope generator {.setting name=eg cc=9 mod=63}
Sets how much the filter envelope modulates the filter cutoff.

### Low frequency oscillator {.setting name=lfo cc=10 mod=67}
Sets how much LFO 1 modulates the filter frequency cutoff.

## Envelope {.group name=envelope}
The envelopes follow classic Attack/Decay/Sustain/Release pattern.

* Attack: time taken to reach maximum amplitude
* Decay: time taken to reach sustain level
* Sustain: relative amplitude of sustain level
* Release: time taken after release to reach 0 amp.

### Pitch Envelope {.group name=filter}
#### Attack {.setting name=a cc=20 mod=69}
#### Decay {.setting name=d cc=21 mod=70}
#### Sustain {.setting name=s cc=22 mod=71}
#### Release {.setting name=r cc=23 mod=72}
### Amplitude Envelope {.group name=amplitude}
#### Attack {.setting name=a cc=24 mod=73}
#### Decay {.setting name=d cc=25 mod=74}
#### Sustain {.setting name=s cc=26 mod=75}
#### Release {.setting name=r cc=27 mod=76}

## LFO Control {.group name=lfo}
### LFO 1 {.group name=lfo-1}
#### Type {.setting name=type cc=35}
``` {.values}
{ bounds = range 0 3, labels = Some [ "BPM", "LOW", "HIGH", "TRACK" ] }
```
#### Sync {.setting name=sync cc=36}
``` {.values}
{ bounds = range 0 1, labels = Some [ "FREE", "KEY SYNC" ] }
```
#### Rate {.setting name=rate cc=31 mod=77}
#### Wave {.setting name=wave cc=32 mod=78}
#### Delay {.setting name=delay cc=33 mod=79}
#### Fade {.setting name=fade cc=34 mod=80}
### LFO 2 {.group name=lfo-2}
#### Type {.setting name=type cc=41}
``` {.values}
{ bounds = range 0 3, labels = Some [ "BPM", "LOW", "HIGH", "TRACK" ] }
```
#### Sync {.setting name=sync cc=42}
``` {.values}
{ bounds = range 0 1, labels = Some [ "FREE", "KEY SYNC" ] }
```
#### Rate {.setting name=rate cc=37 mod=81}
#### Wave {.setting name=wave cc=38 mod=82}
#### Delay {.setting name=delay cc=39 mod=83}
#### Fade {.setting name=fade cc=40 mod=84}

## Reverb Control {.group name=reverb}
### Size {.setting name=size cc=44}
### Decay {.setting name=decay cc=45}
### Filter {.setting name=filter cc=46}
### Mix {.setting name=mix cc=47}

## Modulators {.group name=modulators}
### Selector {.setting name=selector cc=5}
``` {.values}
{ bounds = range 0 3, labels = Some ["LFO 2", "Mod Wheel", "Velocity", "Aftertouch"] }
```

## Misc {.group name=misc}
### Amp level {.setting name=amp cc=7}
Undocumented.

### Play mode {.setting name=mode cc=30}
``` {.values}
{ bounds = range 0 5, labels = Some ["POLY", "UNI A", "UNI B", "TRI", "DUO", "MONO"] }
```
### Legato {.setting name=legato cc=68}
``` {.values}
{ bounds = range 0 1 }
```
