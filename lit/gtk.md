# GUI
The GUI is using Gtk 4.0.

``` {.python file=nymphescc/gtk.py}
import logging
import queue
from queue import Queue
import threading
from threading import Thread
from importlib import resources
import re
from datetime import datetime

from xdg import xdg_config_home
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk
from dataclasses import dataclass


from .messages import read_settings, Group, Setting, modulators
from .core import Register, AlsaPort
from .db import NymphesDB


class Interface:
    def __init__(self):
        self.q_out = Queue()
        self.set_ui_value = None
        self.register = Register.new()
        self.nymphes_in_port = AlsaPort("device-in", "in")
        self.nymphes_out_port = AlsaPort("device-out", "out")
        self.through_port = AlsaPort("through", "in")
        self.quit_event = threading.Event()
        self.db = NymphesDB()

        self.nymphes_in_port.auto_connect()
        self.nymphes_in_port.auto_connect()

    def set_ui(self, ctrl, mod, value):
        GLib.idle_add(self.set_ui_value, ctrl, mod, value)

    def send_nymphes(self):
        while True:
            try:
                ctrl, mod, value = self.q_out.get(timeout=0.1)
            except queue.Empty:
                if self.quit_event.is_set():
                    break
                else:
                    continue

            if mod is not None and mod != 0 and self.nymphes_out_port.selected_mod != mod:
                self.nymphes_out_port.send_cc(
                    0, self.register.flat_config["modulators.selector"].cc, mod - 1)
                self.nymphes_out_port.selected_mod = mod
            if mod is not None and mod > 0:
                self.nymphes_out_port.send_cc(
                    0, self.register.flat_config[ctrl].mod, value)
            else:
                self.nymphes_out_port.send_cc(
                    0, self.register.flat_config[ctrl].cc, value)

            self.q_out.task_done()

    def read_nymphes(self):
        for chan, param, value in self.nymphes_in_port.read_cc(self.quit_event):
            if param not in self.register.midi_map:
                logging.warn("msg %u %u %u unknown", chan, param, value)
                continue
            kind, ctrl = self.register.midi_map[param]
            logging.debug("msg %u %u %u, read as %s:%s", chan, param, value, kind, ctrl)
            if kind == "mod":
                self.register.values[self.nymphes_in_port.selected_mod][ctrl] = value
                self.set_ui(ctrl, self.nymphes_in_port.selected_mod, value)
            elif ctrl == "modulators.selector":
                self.nymphes_in_port.selected_mod = value + 1
            else:
                self.register.values[0][ctrl] = value
                self.set_ui(ctrl, 0, value)


def make_tree_store(db: NymphesDB):
    store = Gtk.TreeStore(int, str, str, str)   # name, tag-list, date
    tree = db.tree()
    for grp_id, grp_name, snaps in tree:
        grp = store.append(None, (grp_id, grp_name, None, None))
        for snap_id, name, tags, date in snaps:
            store.append(grp, (snap_id, name, tags, date))
    return store


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


def on_activate(app, iface):
    win = Gtk.ApplicationWindow(application=app, title="NymphesCC")
    css_provider = Gtk.CssProvider()
    with resources.path(__package__, "gtk-style.css") as path:
        css_provider.load_from_path(str(path))
    win.get_style_context().add_provider_for_display(
        Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    win.set_default_size(1600, 1000)
    header_bar = Gtk.HeaderBar()
    header_bar.set_show_title_buttons(True)
    side_bar_button = Gtk.Button()
    win.set_titlebar(header_bar)
    grid = Gtk.Grid()
    grid.add_css_class("mod-baseline")
    controls = {}

    def set_ui_value(ctrl, mod, value):
        if mod != controls["modulators.selector"].get_selected_row().get_index():
            return
        if ctrl not in controls:
            logging.warn("no widget to control %s", ctrl)
            return

        match controls[ctrl]:
            case Gtk.Scale():
                controls[ctrl].set_value(value)
            case Gtk.ComboBoxText():
                controls[ctrl].set_active(value)
            case Gtk.ListBox():
                w = controls[ctrl]
                w.select_row(w.get_row_at_index(value))

    iface.set_ui_value = set_ui_value

    def write_output_queue(ctrl, value):
        mod = controls["modulators.selector"].get_selected_row().get_index()
        if iface.register.flat_config[ctrl].mod is None:
            mod = 0
        if iface.register.gui_msg(ctrl, mod, value):
            iface.q_out.put_nowait((ctrl, mod, value))

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
        index = row.get_index()
        css_classes = [re.sub("mod-.*", f"mod-{value}", c)
                       for c in grid.get_css_classes()]
        grid.set_css_classes(css_classes)
        for name, setting in iface.register.flat_config.items():
            if setting.mod is not None:
                widget = controls[name]
                match widget:
                    case Gtk.Scale():
                        widget.set_value(iface.register.values[index][name])
                    case Gtk.ComboBox():
                        widget.set_active(iface.register.values[index][name])
        iface.q_out.put_nowait(("modulators.selector", None, row.get_index()))

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

    for mod, v in iface.register.values.items():
        for ctrl, value in v.items():
            set_ui_value(ctrl, mod, value)

    side_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    new_snapshot_button = Gtk.Button()
    new_snapshot_button.set_child(Gtk.Image.new_from_icon_name("value-increase-symbolic"))
    tree_store = make_tree_store(iface.db)
    db_tree_view = Gtk.TreeView.new_with_model(tree_store)
    db_col_1 = Gtk.TreeViewColumn()
    db_cell_1 = Gtk.CellRendererText()
    db_cell_1.set_property("editable", True)
    db_cell_2 = Gtk.CellRendererText()
    db_cell_2.set_property("editable", True)
    db_col_1.set_title("Name")
    db_col_1.pack_start(db_cell_1, True)
    db_col_1.add_attribute(db_cell_1, "text", 1)
    db_col_2 = Gtk.TreeViewColumn()
    db_col_2.set_title("Tags")
    db_col_2.pack_start(db_cell_2, True)
    db_col_2.add_attribute(db_cell_2, "text", 2)

    db_tree_view.append_column(db_col_1)
    db_tree_view.append_column(db_col_2)
    db_tree_view.set_vexpand(True)

    scrolled_side = Gtk.ScrolledWindow()
    scrolled_side.set_child(db_tree_view)
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


def spawn(iface: Interface):
    app = Gtk.Application(application_id='org.nymphescc')

    def stop_threads(_):
        iface.quit_event.set()

    app.connect('activate', on_activate, iface)
    app.connect('shutdown', stop_threads)
    app.run(None)


def main():
    logging.getLogger().setLevel(logging.DEBUG)
    iface = Interface()
    # Thread(target=spawn, args=(iface,)).start()
    Thread(target=iface.send_nymphes).start()
    Thread(target=iface.read_nymphes).start()
    spawn(iface)

```
