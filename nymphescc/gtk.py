# ~\~ language=Python filename=nymphescc/gtk.py
# ~\~ begin <<lit/gtk.md|nymphescc/gtk.py>>[0]
from __future__ import annotations
from dataclasses import dataclass, field
import logging
import queue
from queue import Queue
import threading
from threading import Thread
from importlib import resources
import re
from collections import OrderedDict
from datetime import datetime
import functools

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import GObject, Gtk, GLib, Gdk, Gio

from alsa_midi import SequencerClient
from .messages import read_settings, Group, modulators
from .core import Register, AlsaPort, BytesPort
from .db import NymphesDB


class Interface:
    def __init__(self):
        self.q_out = Queue()
        self.set_ui_value = None
        self.register = Register.new()
        client = SequencerClient("NymphesCC")
        self.nymphes_in_port = AlsaPort(client, "device-in", "in")
        self.nymphes_out_port = AlsaPort(client, "device-out", "out")
        self.through_port = AlsaPort(client, "through", "in")
        self.quit_event = threading.Event()
        self.db = NymphesDB()

        self.nymphes_in_port.auto_connect()
        self.nymphes_out_port.auto_connect()

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

    def read_port(self, port, forward=False):
        for chan, param, value in port.read_cc(self.quit_event):
            if forward:
                self.nymphes_out_port.send_cc(chan, param, value)
            if param not in self.register.midi_map:
                logging.warn("msg %u %u %u unknown", chan, param, value)
                continue
            kind, ctrl = self.register.midi_map[param]
            logging.debug("msg %u %u %u, read as %s:%s", chan, param, value, kind, ctrl)
            if kind == "mod":
                self.register.values[port.selected_mod][ctrl] = value
                self.set_ui(ctrl, port.selected_mod, value)
            elif ctrl == "modulators.selector":
                port.selected_mod = value + 1
            else:
                self.register.values[0][ctrl] = value
                self.set_ui(ctrl, 0, value)

    def read_nymphes(self):
        self.read_port(self.nymphes_in_port, forward=False)

    def load_snapshot(self, snap_id):
        midi = self.db.snapshot(snap_id).midi
        port = BytesPort(midi)
        self.read_port(port, forward=True)

    def get_midi(self):
        port = BytesPort()
        self.register.send_all(port)
        return port.bytes


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
    label.set_name(name.lower().replace(" ", "-"))
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
    list_box_play = list_box_setting(setting.labels or [])
    frame.set_child(list_box_play)
    vbox.append(frame)

    return vbox, { "modulators.selector": list_box_mod
                 , "misc.mode": list_box_play }


def icon_button(icon_name: str) -> Gtk.Button:
    button = Gtk.Button()
    button.set_icon_name(icon_name)
    return button


def tool_bar(**icon_names) -> tuple[Gtk.Box, dict[str, Gtk.Button]]:
    box = Gtk.Box()
    buttons = OrderedDict((k, icon_button(v)) for k, v in icon_names.items())
    for button in buttons.values():
        button.set_has_frame(False)
        box.append(button)
    return box, buttons


class GGroupInfo(GObject.GObject):
    key = GObject.property(type=int)
    name = GObject.property(type=str)
    description = GObject.property(type=str)

    def __init__(self):
        super(GGroupInfo, self).__init__()

    @staticmethod
    def new(key: int, name: str, description: str) -> GGroupInfo:
        obj = GGroupInfo()
        obj.key = key
        obj.name = name
        obj.description = description
        return obj


class GSnapshotInfo(GObject.GObject):
    key = GObject.property(type=int)
    timestamp = GObject.property(type=float)

    def __init__(self):
        super(GSnapshotInfo, self).__init__()

    @staticmethod
    def new(key: int, timestamp: float) -> GSnapshotInfo:
        obj = GSnapshotInfo()
        obj.key = key
        obj.timestamp = timestamp
        return obj


class DeletableRow(Gtk.Box):
    def __init__(self):
        super(DeletableRow, self).__init__()

    @staticmethod
    def new(text: str):
        box = DeletableRow()
        box._label = Gtk.Label.new(text)
        box._label.set_hexpand(True)
        box._label.set_justify(Gtk.Justification.LEFT)
        box._label.set_halign(Gtk.Align.START)
        box._label.set_margin_top(10)
        box._label.set_margin_bottom(10)
        box._label.set_margin_start(5)
        box.append(box._label)
        box._delete_button = icon_button("edit-delete-symbolic")
        box._delete_button.set_has_frame(False)
        box.append(box._delete_button)
        box.hide_delete_button()
        return box

    def show_delete_button(self):
        self._delete_button.set_visible(True)

    def hide_delete_button(self):
        self._delete_button.set_visible(False)

    def set_label(self, text: str):
        self._label.set_label(text)

    @property
    def delete_button(self):
        return self._delete_button


def maybe(f):
    @functools.wraps(f)
    def maybe_f(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AttributeError:
            return None
    return maybe_f


@dataclass
class SessionPane:
    iface: Interface
    search_entry: Gtk.SearchEntry
    session_list: Gtk.ListBox
    add_session_button: Gtk.Button

    info_box: Gtk.Box
    name: Gtk.Entry
    description: Gtk.TextView
    snapshot_list: Gtk.ListBox
    add_snapshot_button: Gtk.Button

    session_list_store: Gio.ListStore \
        = field(default_factory=lambda: Gio.ListStore.new(GGroupInfo))
    snapshot_list_store: Gio.ListStore \
        = field(default_factory=lambda: Gio.ListStore.new(GSnapshotInfo))

    def __post_init__(self):
        self.session_list.bind_model(self.session_list_store, self.session_list_row)
        self.snapshot_list.bind_model(self.snapshot_list_store, self.snapshot_list_row)
        self.session_list.connect("row-selected", self.select_group_event)
        self.snapshot_list.connect("row-selected", self.select_snapshot_event)
        self.add_session_button.connect("clicked", self.add_session_event)
        self.add_snapshot_button.connect("clicked", self.add_snapshot_event)
        self.name.connect("changed", self.name_changed_event)
        self.description.get_buffer().connect("changed", self.description_changed_event)
        self.name.connect("editing-done", self.focus_description)
        self.load_groups()
        self._selected_row = None

    @maybe
    def group_id(self):
        idx = self.session_list.get_selected_row().get_index()
        return self.session_list_store.get_item(idx).key

    @maybe
    def group_info(self):
        idx = self.session_list.get_selected_row().get_index()
        return self.session_list_store.get_item(idx)

    @maybe
    def snapshot_id(self):
        idx = self.snapshot_list.get_selected_row().get_index()
        return self.snapshot_list_store.get_item(idx).key

    def session_list_row(self, group_info: GGroupInfo) -> DeletableRow:
        x = DeletableRow.new(group_info.name)
        x.delete_button.connect("clicked", self.delete_session)
        return x

    def focus_description(self, _):
        self.description.grab_focus()

    def delete_session(self, _):
        idx = self.session_list.get_selected_row().get_index()
        self.iface.db.delete_group(self.group_id())
        self._selected_row = None
        self.session_list_store.remove(idx)

    def snapshot_list_row(self, snapshot_info: GSnapshotInfo) -> Gtk.Label:
        return Gtk.Label.new(datetime.fromtimestamp(snapshot_info.timestamp).strftime("%c"))

    def load_groups(self):
        self.session_list_store.remove_all()
        for g in self.iface.db.groups():
            self.session_list_store.append(GGroupInfo.new(g.key, g.name, g.description))

    def load_snapshots(self, group_id):
        self.snapshot_list_store.remove_all()
        for s in self.iface.db.snapshots(group_id):
            self.snapshot_list_store.append(GSnapshotInfo.new(s.key, s.timestamp.timestamp()))

    def select_group_event(self, _1, row):
        if row is None:
            self.info_box.set_sensitive(False)
            self.name.set_text("")
            self.description.get_buffer().set_text("", -1)
            self.snapshot_list_store.remove_all()
            return

        row.get_child().show_delete_button()
        if self._selected_row:
            self._selected_row.get_child().hide_delete_button()
        self._selected_row = row

        info = self.iface.db.group_info(self.group_id())
        self.info_box.set_sensitive(True)
        self.name.set_text(info.name)
        self.description.get_buffer().set_text(info.description or "", -1)
        self.load_snapshots(info.key)

    def select_snapshot_event(self, _1, _2):
        if self.snapshot_id() is None:
            return
        self.iface.load_snapshot(self.snapshot_id())

    def add_session_event(self, _):
        group_id = self.iface.db.new_group("New Group")
        info = self.iface.db.group_info(group_id)
        self.session_list_store.append(GGroupInfo.new(info.key, info.name, info.description))
        idx = self.session_list_store.get_n_items() - 1
        self.session_list.select_row(self.session_list.get_row_at_index(idx))
        self.name.select_region(0, -1)
        self.name.grab_focus()

    def add_snapshot_event(self, _):
        snap_id = self.iface.db.new_snapshot(self.group_info().key, self.iface.get_midi())
        s = self.iface.db.snapshot(snap_id)
        self.snapshot_list_store.append(GSnapshotInfo.new(s.key, s.timestamp.timestamp()))
        idx = self.snapshot_list_store.get_n_items() - 1
        self.snapshot_list.select_row(self.snapshot_list.get_row_at_index(idx))

    def name_changed_event(self, _):
        if self.group_id() is None:
            return
        name = self.name.get_text()
        self.iface.db.set_name(self.group_id(), name)
        self.group_info().name = name
        self.session_list.get_selected_row().get_child().set_label(name)

    def description_changed_event(self, buffer):
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        self.iface.db.set_description(self.group_id(), buffer.get_text(start, end, True))


def session_pane(iface):
    search_bar = Gtk.SearchEntry()

    session_overlay = Gtk.Overlay()
    session_list = Gtk.ListBox()
    list_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 5)
    list_box.append(session_list)
    list_box.append(list_box_label(""))
    # session_list.set_vexpand(True)
    scroll = Gtk.ScrolledWindow()
    scroll.set_child(list_box)
    scroll.set_vexpand(True)
    session_overlay.set_child(scroll)

    ctrl = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    ctrl.append(search_bar)
    ctrl.append(session_overlay)

    new_group_button = icon_button("list-add-symbolic")
    session_overlay.add_overlay(new_group_button)
    new_group_button.set_property("halign", Gtk.Align.CENTER)
    new_group_button.set_property("valign", Gtk.Align.END)
    new_group_button.set_margin_bottom(5)
    session_list.set_margin_bottom(new_group_button.get_height() + 10)

    info = Gtk.Box.new(Gtk.Orientation.VERTICAL, 5)
    info.set_margin_start(5)
    info.set_margin_end(5)
    info.set_margin_top(5)
    info.set_margin_bottom(5)
    title = Gtk.Entry()
    title.set_name("session-title")
    title.set_has_frame(False)
    info.append(title)

    descr_frame = Gtk.Frame()
    descr_frame.set_label("Description")
    descr_scroll = Gtk.ScrolledWindow()
    descr = Gtk.TextView()
    descr.set_wrap_mode(Gtk.WrapMode.WORD)
    descr_scroll.set_child(descr)
    descr_scroll.set_size_request(-1, 100)
    descr_frame.set_child(descr_scroll)
    info.append(descr_frame)

    snaps_overlay = Gtk.Overlay()
    new_snapshot_button = icon_button("list-add-symbolic")
    new_snapshot_button.set_property("halign", Gtk.Align.CENTER)
    new_snapshot_button.set_property("valign", Gtk.Align.END)
    new_snapshot_button.set_margin_bottom(5)
    snaps_frame = Gtk.Frame()
    snaps_frame.set_label("Snapshots")
    snaps_scroll = Gtk.ScrolledWindow()
    snaps = Gtk.ListBox()
    snaps_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    snaps_box.append(snaps)
    snaps_box.append(list_box_label(""))
    snaps_scroll.set_child(snaps_box)
    snaps_frame.set_child(snaps_overlay)
    snaps_frame.set_vexpand(True)
    snaps_overlay.set_child(snaps_scroll)
    snaps_overlay.add_overlay(new_snapshot_button)
    info.append(snaps_frame)
    info.set_sensitive(False)

    vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 5)
    vbox.append(ctrl)
    vbox.append(info)
    vbox.set_homogeneous(True)

    pane = SessionPane(
        iface=iface,
        search_entry=search_bar,
        session_list=session_list,
        add_session_button=new_group_button,
        info_box=info,
        name=title,
        description=descr,
        snapshot_list=snaps,
        add_snapshot_button=new_snapshot_button)

    return vbox, pane


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

    side, _ = session_pane(iface)

    scrolled_main = Gtk.ScrolledWindow()
    scrolled_main.set_child(grid)
    paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
    paned.set_start_child(side)
    paned.set_end_child(scrolled_main)
    paned.set_position(300)

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

# ~\~ end
