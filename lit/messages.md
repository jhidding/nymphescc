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
### Wave form {.setting name=wave cc=70 mod=31}
``` {.values}
{ tics = Some [tic 0 "⩘", tic 63 "⎍", tic 127 "⋀"] }
```
Controls the shape of the generated wave, going from sawtooth through square, to triangle waves.

### Pulse width {.setting name=pw cc=12 mod=36}
Control the pulse width of the square wave form. This can be modulated using LFO 2.

### Level {.setting name=lvl cc=9 mod=32}
Sets the amplitude of the wave form.

### Sub-oscillator {.setting name=sub cc=10 mod=33}
Amplitude of sub-oscillator, which produces a square wave one octave below the main oscillator.

### Noise level {.setting name=noise cc=11 mod=34}
Amplitude of white noise, mixed in with main oscillator and sub-oscillator.

### Glide {.setting name=gld cc=5 mod=37}
``` {.values}
{ flags = Some ["misc.legato"] }
```
Allow notes to glide (portamento). The behaviour strongly depends on the playing mode. Optionally, glide will respond to legato playing.

### Low frequency oscillator {.setting name=lfo cc=13 mod=35}
Control the change in pitch of the main oscillator with the LFO, from subtle vibrato to extreme whoopy sounds.

### Envelope Generator {.setting name=eg cc=14 mod=41}
Control how much the filter envelope modulates the pitch of the oscillator. Envelopes are unipolar.

### Detune {.setting name=dtn cc=15 mod=39}
Detune notes when in stacked modes (i.e. multiple oscillators per node: UNI A, UNI B, TRI, DUO).

### Chord control {.setting name=chord cc=16 mod=40}
Choose from different predefined chords (see Chords tab).

## Filter control {.group name=filter}
### Hipass Cutoff {.setting name=hpf cc=81 mod=45}
``` {.values}
{ tics = Some [tic 0 "33 hZ", tic 63 "", tic 127 "17 khZ"] }
```
Sets the cutoff frequency of the hipass filter. Hipass is piped after lopass, creating a bandpass.

### Lopass Cutoff {.setting name=cut cc=74 mod=42}
``` {.values}
{ tics = Some [tic 0 "33 hZ", tic 63 "", tic 127 "17 khZ"] }
```
Sets the cutoff frequency of the lopass filter.

### Resonance {.setting name=res cc=71 mod=43}
Sets the amount of filter resonance, i.e. how much upper frequencies are amplified.

### Tracking {.setting name=track cc=4 mod=46}
Sets how much the filter cutoff tracks the frequency of the main oscillator. At `127` the cutoff frequncy tracks the oscillator pitch 1:1. In combination with high resonance this can create beautiful overtones.

If you set this to other fractions (e.g. `63` for quarter tones), use only noise as a sound source, and beef up resonance, you can play microtonal music!

### Envelope generator {.setting name=eg cc=3 mod=44}
Sets how much the filter envelope modulates the filter cutoff.

### Low frequency oscillator {.setting name=lfo cc=8 mod=47}
Sets how much LFO 1 modulates the filter frequency cutoff.

## Envelope {.group name=envelope}
The envelopes follow classic Attack/Decay/Sustain/Release pattern.

* Attack: time taken to reach maximum amplitude
* Decay: time taken to reach sustain level
* Sustain: relative amplitude of sustain level
* Release: time taken after release to reach 0 amp.

### Filter Envelope {.group name=filter}
#### Attack {.setting name=a cc=79 mod=48}
#### Decay {.setting name=d cc=80 mod=49}
#### Sustain {.setting name=s cc=82 mod=50}
#### Release {.setting name=r cc=83 mod=51}
### Amplitude Envelope {.group name=amplitude}
#### Attack {.setting name=a cc=73 mod=52}
#### Decay {.setting name=d cc=84 mod=53}
#### Sustain {.setting name=s cc=85 mod=54}
#### Release {.setting name=r cc=72 mod=55}

## LFO Control {.group name=lfo}
### LFO 1 {.group name=lfo-1}
#### Type {.setting name=type cc=22}
``` {.values}
{ bounds = range 0 3, labels = Some [ "BPM", "LOW", "HIGH", "TRACK" ] }
```
#### Sync {.setting name=sync cc=23}
``` {.values}
{ bounds = range 0 1, labels = Some [ "FREE", "KEY SYNC" ] }
```
#### Rate {.setting name=rate cc=18 mod=56}
#### Wave {.setting name=wave cc=19 mod=57}
#### Delay {.setting name=delay cc=20 mod=58}
#### Fade {.setting name=fade cc=21 mod=59}
### LFO 2 {.group name=lfo-2}
#### Type {.setting name=type cc=28}
``` {.values}
{ bounds = range 0 3, labels = Some [ "BPM", "LOW", "HIGH", "TRACK" ] }
```
#### Sync {.setting name=sync cc=29}
``` {.values}
{ bounds = range 0 1, labels = Some [ "FREE", "KEY SYNC" ] }
```
#### Rate {.setting name=rate cc=24 mod=60}
#### Wave {.setting name=wave cc=25 mod=61}
#### Delay {.setting name=delay cc=26 mod=62}
#### Fade {.setting name=fade cc=27 mod=63}

## Reverb Control {.group name=reverb}
### Size {.setting name=size cc=75 mod=65}
### Decay {.setting name=decay cc=76 mod=66}
### Filter {.setting name=filter cc=77 mod=67}
### Mix {.setting name=mix cc=78 mod=69}

## Modulators {.group name=modulators}
### Selector {.setting name=selector cc=30}
``` {.values}
{ bounds = range 0 3, labels = Some ["LFO 2", "Mod Wheel", "Velocity", "Aftertouch"] }
```

## Misc {.group name=misc}
### Amp level {.setting name=amp cc=7}
Amplification, set to default 127.

### Play mode {.setting name=mode cc=17}
``` {.values}
{ bounds = range 0 5, labels = Some ["POLY", "UNI A", "UNI B", "TRI", "DUO", "MONO"] }
```
### Legato {.setting name=legato cc=68}
``` {.values}
{ bounds = range 0 1 }
```
