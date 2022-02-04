# GUI
The GUI is using Gtk 4.0.

``` {.python file=nymphescc/gtk.py}
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio
from dataclasses import dataclass


from .messages import read_settings, Group, Setting


def slider_group(group: Group):
    frame = Gtk.Frame()
    frame.set_label(group.long)
    grid = Gtk.Grid()
    grid.set_column_spacing(6)
    grid.set_margin_bottom(5)
    grid.set_column_homogeneous(True)
    frame.set_child(grid)

    for i, s in enumerate(group.scales):
        slider = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, s.bounds.lower, s.bounds.upper, 1)
        slider.set_vexpand(True)
        slider.set_draw_value(True)
        slider.set_inverted(True)
        slider.set_value_pos(Gtk.PositionType.BOTTOM)
        # if not s.tics:
        slider.add_mark(0, Gtk.PositionType.LEFT, None)
        slider.add_mark(63, Gtk.PositionType.LEFT, None)
        slider.add_mark(127, Gtk.PositionType.LEFT, None)
        # else:
        #    for t in s.tics:
        #        slider.add_mark(t.value, Gtk.PositionType.LEFT, t.label)

        label = Gtk.Label()
        label.set_label(s.name.upper())
        grid.attach(slider, i, 0, 1, 1)
        grid.attach(label, i, 1, 1, 1)

    for i, s in enumerate(group.enums):
        combo = Gtk.ComboBoxText()
        combo.set_margin_end(5)
        for t in s.labels:
            combo.append(None, t)
        label = Gtk.Label.new(s.name.upper())
        if i == 0:
            combo.set_margin_top(5)
        grid.attach(label, 0, i+2, 1, 1)
        grid.attach(combo, 1, i+2, len(group.scales) - 1, 1)

    return frame


def list_box_label(name: str):
    label = Gtk.Label()
    label.set_label(name)
    label.set_margin_top(5)
    label.set_margin_bottom(5)
    return label


def list_box_setting(setting: Setting):
    list_box = Gtk.ListBox()
    for name in setting.labels:
        list_box.append(list_box_label(name))
    list_box.set_hexpand(True)
    list_box.set_selection_mode(Gtk.SelectionMode.BROWSE)
    list_box.set_vexpand(True)
    return list_box


def mode_selector(mod_group: Group, play_group: Group):
    vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 5)

    frame = Gtk.Frame()
    frame.set_label(mod_group.long)
    setting = mod_group.content[0]
    list_box = list_box_setting(setting)
    list_box.insert(list_box_label("Unmodulated"), 0)
    list_box.select_row(list_box.get_row_at_index(0))
    frame.set_child(list_box)
    vbox.append(frame)

    frame = Gtk.Frame()
    setting = next(s for s in play_group.content if s.name == "mode")
    frame.set_label(setting.long)
    list_box = list_box_setting(setting)
    frame.set_child(list_box)
    vbox.append(frame)

    return vbox


def on_activate(app):
    win = Gtk.ApplicationWindow(application=app, title="NymphesCC")
    win.set_default_size(1500, 1000)
    header_bar = Gtk.HeaderBar()
    header_bar.set_show_title_buttons(True)
    side_bar_button = Gtk.Button()
    win.set_titlebar(header_bar)

    settings = read_settings()
    layout = [("oscillator", 0, 0, 5, 1), 
              ("filter", 5, 0, 3, 1),
              ("envelope.filter", 0, 1, 2, 1),
              ("envelope.amplitude", 2, 1, 2, 1),
              ("lfo.lfo-1", 4, 1, 2, 1),
              ("lfo.lfo-2", 6, 1, 2, 1),
              ("reverb", 8, 1, 2, 1)]
    grid = Gtk.Grid()
    grid.set_column_spacing(5)
    grid.set_row_spacing(5)
    grid.set_column_homogeneous(True)
    grid.set_row_homogeneous(True)

    for s, x, y, w, h in layout:
        grid.attach(slider_group(settings[s]), x, y, w, h)
    grid.attach(mode_selector(settings["modulators"], settings["misc"]), 8, 0, 2, 1)
    grid.set_margin_top(5)
    grid.set_margin_bottom(5)
    grid.set_margin_start(5)
    grid.set_margin_end(5)

    side_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    new_snapshot_button = Gtk.Button()
    new_snapshot_button.set_child(Gtk.Image.new_from_icon_name("value-increase-symbolic"))
    session_tree_view = Gtk.TreeView()
    scrolled_side = Gtk.ScrolledWindow()
    scrolled_side.set_child(session_tree_view)
    scrolled_side.set_vexpand(True)
    side_box.append(scrolled_side)
    side_box.append(new_snapshot_button)

    scrolled_main = Gtk.ScrolledWindow()
    scrolled_main.set_child(grid)
    paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
    paned.set_start_child(side_box)
    paned.set_end_child(scrolled_main)
    paned.set_position(200)
    win.set_child(paned)
    win.present()


def main():
    app = Gtk.Application(application_id='org.gtk.Example')
    app.connect('activate', on_activate)
    app.run(None)
```
