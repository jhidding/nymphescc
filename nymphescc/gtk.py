# ~\~ language=Python filename=nymphescc/gtk.py
# ~\~ begin <<README.md|nymphescc/gtk.py>>[0]
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
        if not s.tics:
            slider.add_mark(0, Gtk.PositionType.LEFT, None)
            slider.add_mark(63, Gtk.PositionType.LEFT, None)
            slider.add_mark(127, Gtk.PositionType.LEFT, None)
        else:
            for t in s.tics:
                slider.add_mark(t.value, Gtk.PositionType.LEFT, t.label)

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


def mode_selector(group: Group):
    frame = Gtk.Frame()
    frame.set_label(group.long)
    setting = group.content[0]
    list_box = Gtk.ListBox()
    for name in ["Unmodulated"] + setting.labels:
        label = Gtk.Label()
        label.set_label(name)
        label.set_margin_top(5)
        label.set_margin_bottom(5)
        list_box.append(label)
    list_box.set_hexpand(True)
    list_box.set_selection_mode(Gtk.SelectionMode.BROWSE)
    list_box.select_row(list_box.get_row_at_index(0))
    frame.set_child(list_box)
    return frame


def on_activate(app):
    win = Gtk.ApplicationWindow(application=app, title="NymphesCC")
    win.set_default_size(1300, 768)
    header_bar = Gtk.HeaderBar()
    header_bar.set_show_title_buttons(True)
    side_bar_button = Gtk.Button()
    icon = Gio.ThemedIcon(name="document-open")
    image = Gtk.Image.new_from_gicon(icon)
    side_bar_button.set_child(image)
    header_bar.pack_start(side_bar_button)
    win.set_titlebar(header_bar)
    scrolled_win = Gtk.ScrolledWindow()

    settings = read_settings()
    layout = [("oscillator", 0, 0, 5, 1), 
              ("filter", 5, 0, 3, 1),
              ("envelope.filter", 0, 1, 2, 1),
              ("envelope.amplitude", 2, 1, 2, 1),
              ("lfo.lfo-1", 4, 1, 2, 1),
              ("lfo.lfo-2", 6, 1, 2, 1)]
    grid = Gtk.Grid()
    grid.set_column_spacing(5)
    grid.set_row_spacing(5)
    grid.set_column_homogeneous(True)
    grid.set_row_homogeneous(True)

    for s, x, y, w, h in layout:
        grid.attach(slider_group(settings[s]), x, y, w, h)
    grid.attach(mode_selector(settings["modulators"]), 8, 0, 1, 1)
    grid.set_margin_top(5)
    grid.set_margin_bottom(5)
    grid.set_margin_start(5)
    grid.set_margin_end(5)

    scrolled_win.set_child(grid)
    win.set_child(scrolled_win)
    win.present()


def main():
    app = Gtk.Application(application_id='org.gtk.Example')
    app.connect('activate', on_activate)
    app.run(None)
# ~\~ end
