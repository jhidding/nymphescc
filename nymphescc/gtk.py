# ~\~ language=Python filename=nymphescc/gtk.py
# ~\~ begin <<lit/gtk.md|nymphescc/gtk.py>>[0]
from queue import Queue
from threading import Thread
from importlib import resources
import re

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk
from dataclasses import dataclass


from .messages import read_settings, Group, Setting, modulators


def slider_group(group: Group, on_changed):
    sliders = {}
    combos = {}

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
        if s.mod is not None:
            slider.add_css_class("mod")
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
        qname = group.name + "." + s.name
        slider.connect("value-changed", on_changed, qname)
        sliders[qname] = slider

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
        qname = group.name + "." + s.name
        combo.connect("changed", on_changed, qname)
        combos[qname] = combo

    return frame, sliders | combos


def list_box_label(name: str):
    label = Gtk.Label()
    label.set_label(name)
    label.set_margin_top(5)
    label.set_margin_bottom(5)
    return label


def list_box_setting(items: list[str]):
    list_box = Gtk.ListBox()
    for name in items:
        list_box.append(list_box_label(name))
    list_box.set_hexpand(True)
    list_box.set_selection_mode(Gtk.SelectionMode.BROWSE)
    list_box.set_vexpand(True)
    return list_box


def mode_selector(settings: dict[str, Group]):
    vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 5)

    mod_group = settings["modulators"]
    play_group = settings["misc"]

    frame = Gtk.Frame()
    frame.set_label(mod_group.long)
    setting = mod_group.content[0]
    list_box_mod = list_box_setting(modulators(settings))
    list_box_mod.select_row(list_box_mod.get_row_at_index(0))
    list_box_mod.add_css_class("mod")
    frame.set_child(list_box_mod)
    vbox.append(frame)

    frame = Gtk.Frame()
    setting = next(s for s in play_group.content if s.name == "mode")
    frame.set_label(setting.long)
    list_box_play = list_box_setting(setting.labels)
    frame.set_child(list_box_play)
    vbox.append(frame)

    return vbox, { "modulators.selector": list_box_mod
                 , "misc.mode": list_box_play }


def on_activate(app, qs):
    q_in, q_out = qs
    win = Gtk.ApplicationWindow(application=app, title="NymphesCC")
    css_provider = Gtk.CssProvider()
    with resources.path(__package__, "gtk-style.css") as path:
        css_provider.load_from_path(str(path))
    win.get_style_context().add_provider_for_display(
        Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    win.set_default_size(1500, 1000)
    header_bar = Gtk.HeaderBar()
    header_bar.set_show_title_buttons(True)
    side_bar_button = Gtk.Button()
    win.set_titlebar(header_bar)
    grid = Gtk.Grid()
    grid.add_css_class("mod-baseline")
    controls = {}

    def set_ui_value(ctrl, value):
        match controls[ctrl]:
            case Gtk.Scale():
                controls[ctrl].set_value(value)
            case Gtk.ComboBoxText():
                controls[ctrl].set_active(value)

    def read_input_queue():
        while True:
            ctrl, value = q_in.get()
            if ctrl == "quit":
                return
            GLib.idle_add(set_ui_value, ctrl, value)
            q_in.task_done()

    def write_output_queue(ctrl, value):
        q_out.put_nowait((ctrl, value))

    def on_changed(widget, *args):
        match widget:
            case Gtk.ComboBoxText():
                (ctrl,) = args
                write_output_queue(ctrl, widget.get_active())
            case Gtk.Scale():
                (ctrl,) = args
                write_output_queue(ctrl, int(widget.get_value()))
            case Gtk.ListBox():
                row, ctrl = args
                write_output_queue(ctrl, row.get_index())

    def on_mod_change(widget, row):
        value = row.get_child().get_label().lower().replace(" ", "-")
        css_classes = [re.sub("mod-.*", f"mod-{value}", c)
                       for c in grid.get_css_classes()]
        print(css_classes)
        grid.set_css_classes(css_classes)
        q_out.put_nowait(("select-mod", row.get_index()))

    settings = read_settings()
    layout = [("oscillator", 0, 0, 5, 1), 
              ("filter", 5, 0, 3, 1),
              ("envelope.filter", 0, 1, 2, 1),
              ("envelope.amplitude", 2, 1, 2, 1),
              ("lfo.lfo-1", 4, 1, 2, 1),
              ("lfo.lfo-2", 6, 1, 2, 1),
              ("reverb", 8, 1, 2, 1)]
    grid.set_column_spacing(5)
    grid.set_row_spacing(5)
    grid.set_column_homogeneous(True)
    grid.set_row_homogeneous(True)

    for s, x, y, w, h in layout:
        frame, s_controls = slider_group(settings[s], on_changed)
        grid.attach(frame, x, y, w, h)
        controls.update(s_controls)

    mode_box, mode_controls = mode_selector(settings)
    mode_controls["misc.mode"].connect("row-selected", on_changed, "misc.mode")
    mode_controls["modulators.selector"].connect("row-selected", on_mod_change)
    controls.update(mode_controls)
    grid.attach(mode_box, 8, 0, 2, 1)
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

    Thread(target=read_input_queue).start()
    win.present()


def spawn(q_in: Queue, q_out: Queue):
    app = Gtk.Application(application_id='org.nymphescc')

    def stop_threads(_):
        q_in.put_nowait(("quit", 0))
        q_out.put_nowait(("quit", 0))

    app.connect('activate', on_activate, (q_in, q_out))
    app.connect('shutdown', stop_threads)
    app.run(None)


def main():
    q_in = Queue()
    q_out = Queue()

    def print_messages():
        while True:
            ctrl, value = q_out.get()
            if ctrl == "quit":
                return
            print(ctrl, value)
            q_out.task_done()

    Thread(target=print_messages).start()
    spawn(q_in, q_out)
# ~\~ end
