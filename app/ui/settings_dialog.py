from enum import Enum

from gi.repository import Gdk

from app.commons import run_task, run_idle
from app.connections import test_telnet, test_ftp, TestException, test_http
from app.properties import write_config, Profile, get_default_settings
from app.ui.dialogs import get_message
from .uicommons import Gtk, UI_RESOURCES_PATH, TEXT_DOMAIN, NEW_COLOR, EXTRA_COLOR
from .main_helper import update_entry_data


def show_settings_dialog(transient, options):
    return SettingsDialog(transient, options).show()


class Property(Enum):
    FTP = "ftp"
    HTTP = "http"
    TELNET = "telnet"


class SettingsDialog:

    def __init__(self, transient, options):
        handlers = {"on_field_icon_press": self.on_field_icon_press,
                    "on_profile_changed": self.on_profile_changed,
                    "on_reset": self.on_reset,
                    "apply_settings": self.apply_settings,
                    "on_connection_test": self.on_connection_test,
                    "on_info_bar_close": self.on_info_bar_close,
                    "on_set_color_switch_state": self.on_set_color_switch_state}

        builder = Gtk.Builder()
        builder.set_translation_domain(TEXT_DOMAIN)
        builder.add_from_file(UI_RESOURCES_PATH + "settings_dialog.glade")
        builder.connect_signals(handlers)

        self._dialog = builder.get_object("settings_dialog")
        self._dialog.set_transient_for(transient)
        self._header_bar = builder.get_object("header_bar")
        # Network
        self._host_field = builder.get_object("host_field")
        self._port_field = builder.get_object("port_field")
        self._login_field = builder.get_object("login_field")
        self._password_field = builder.get_object("password_field")
        self._http_login_field = builder.get_object("http_login_field")
        self._http_password_field = builder.get_object("http_password_field")
        self._http_port_field = builder.get_object("http_port_field")
        self._telnet_login_field = builder.get_object("telnet_login_field")
        self._telnet_password_field = builder.get_object("telnet_password_field")
        self._telnet_port_field = builder.get_object("telnet_port_field")
        self._telnet_timeout_spin_button = builder.get_object("telnet_timeout_spin_button")
        self._settings_stack = builder.get_object("settings_stack")
        # Paths
        self._services_field = builder.get_object("services_field")
        self._user_bouquet_field = builder.get_object("user_bouquet_field")
        self._satellites_xml_field = builder.get_object("satellites_xml_field")
        self._data_dir_field = builder.get_object("data_dir_field")
        self._picons_field = builder.get_object("picons_field")
        self._picons_dir_field = builder.get_object("picons_dir_field")
        self._backup_dir_field = builder.get_object("backup_dir_field")
        # Info bar
        self._info_bar = builder.get_object("info_bar")
        self._message_label = builder.get_object("info_bar_message_label")
        self._test_spinner = builder.get_object("test_spinner")
        # Profile
        self._enigma_radio_button = builder.get_object("enigma_radio_button")
        self._neutrino_radio_button = builder.get_object("neutrino_radio_button")
        self._support_ver5_check_button = builder.get_object("support_ver5_check_button")
        self._support_http_api_check_button = builder.get_object("support_http_api_check_button")
        # Program
        self._before_save_switch = builder.get_object("before_save_switch")
        self._before_downloading_switch = builder.get_object("before_downloading_switch")
        self._program_box = builder.get_object("program_box")
        self._colors_grid = builder.get_object("colors_grid")
        self._set_color_switch = builder.get_object("set_color_switch")
        self._new_color_button = builder.get_object("new_color_button")
        self._extra_color_button = builder.get_object("extra_color_button")
        # Options
        self._options = options
        self._active_profile = options.get("profile")
        self.set_settings()
        self.init_ui_elements(Profile(self._active_profile))

    def init_ui_elements(self, profile):
        is_enigma_profile = profile is Profile.ENIGMA_2
        self._neutrino_radio_button.set_active(profile is Profile.NEUTRINO_MP)
        self._settings_stack.get_child_by_name(Property.HTTP.value).set_visible(is_enigma_profile)
        self._program_box.set_sensitive(is_enigma_profile)
        self.update_subtitle(profile)

    def show(self):
        response = self._dialog.run()
        if response == Gtk.ResponseType.OK:
            self.apply_settings()
        self._dialog.destroy()

        return response

    def on_field_icon_press(self, entry, icon, event_button):
        update_entry_data(entry, self._dialog, self._options.get(self._options.get("profile")))

    def on_profile_changed(self, item):
        profile = Profile.ENIGMA_2 if self._enigma_radio_button.get_active() else Profile.NEUTRINO_MP
        self._active_profile = profile.value
        self.set_settings()
        self.init_ui_elements(profile)

    def update_subtitle(self, profile):
        sub = "{} Enigma2" if profile is Profile.ENIGMA_2 else "{} Neutrino-MP"
        self._header_bar.set_subtitle(sub.format(get_message("Profile:")))

    def set_profile(self, profile):
        self._active_profile = profile.value
        self.set_settings()

    def on_reset(self, item):
        def_settings = get_default_settings()
        for key in def_settings:
            current = self._options.get(key)
            if type(current) is str:
                continue
            default = def_settings.get(key)
            for k in default:
                current[k] = default.get(k)
        self.set_settings()

    def set_settings(self):
        def_settings = get_default_settings().get(self._active_profile)
        options = self._options.get(self._active_profile)
        self._host_field.set_text(options.get("host", def_settings["host"]))
        self._port_field.set_text(options.get("port", def_settings["port"]))
        self._login_field.set_text(options.get("user", def_settings["user"]))
        self._password_field.set_text(options.get("password", def_settings["password"]))
        self._http_login_field.set_text(options.get("http_user", def_settings["http_user"]))
        self._http_password_field.set_text(options.get("http_password", def_settings["http_password"]))
        self._http_port_field.set_text(options.get("http_port", def_settings["http_port"]))
        self._telnet_login_field.set_text(options.get("telnet_user", def_settings["telnet_user"]))
        self._telnet_password_field.set_text(options.get("telnet_password", def_settings["telnet_password"]))
        self._telnet_port_field.set_text(options.get("telnet_port", def_settings["telnet_port"]))
        self._telnet_timeout_spin_button.set_value(options.get("telnet_timeout", def_settings["telnet_timeout"]))
        self._services_field.set_text(options.get("services_path", def_settings["services_path"]))
        self._user_bouquet_field.set_text(options.get("user_bouquet_path", def_settings["user_bouquet_path"]))
        self._satellites_xml_field.set_text(options.get("satellites_xml_path", def_settings["satellites_xml_path"]))
        self._picons_field.set_text(options.get("picons_path", def_settings["picons_path"]))
        self._data_dir_field.set_text(options.get("data_dir_path", def_settings["data_dir_path"]))
        self._picons_dir_field.set_text(options.get("picons_dir_path", def_settings["picons_dir_path"]))
        self._backup_dir_field.set_text(options.get("backup_dir_path", def_settings["backup_dir_path"]))
        self._before_save_switch.set_active(options.get("backup_before_save", def_settings["backup_before_save"]))
        self._before_downloading_switch.set_active(options.get("backup_before_downloading",
                                                               def_settings["backup_before_downloading"]))

        if Profile(self._active_profile) is Profile.ENIGMA_2:
            self._support_ver5_check_button.set_active(options.get("v5_support", False))
            self._support_http_api_check_button.set_active(options.get("http_api_support", False))
            self._set_color_switch.set_active(options.get("use_colors", False))
            new_rgb = Gdk.RGBA()
            new_rgb.parse(options.get("new_color", NEW_COLOR))
            extra_rgb = Gdk.RGBA()
            extra_rgb.parse(options.get("extra_color", EXTRA_COLOR))
            self._new_color_button.set_rgba(new_rgb)
            self._extra_color_button.set_rgba(extra_rgb)

    def apply_settings(self, item=None):
        profile = Profile.ENIGMA_2 if self._enigma_radio_button.get_active() else Profile.NEUTRINO_MP
        self._active_profile = profile.value
        self._options["profile"] = self._active_profile
        options = self._options.get(self._active_profile)
        options["host"] = self._host_field.get_text()
        options["port"] = self._port_field.get_text()
        options["user"] = self._login_field.get_text()
        options["password"] = self._password_field.get_text()
        options["http_user"] = self._http_login_field.get_text()
        options["http_password"] = self._http_password_field.get_text()
        options["http_port"] = self._http_port_field.get_text()
        options["telnet_user"] = self._telnet_login_field.get_text()
        options["telnet_password"] = self._telnet_password_field.get_text()
        options["telnet_port"] = self._telnet_port_field.get_text()
        options["telnet_timeout"] = int(self._telnet_timeout_spin_button.get_value())
        options["services_path"] = self._services_field.get_text()
        options["user_bouquet_path"] = self._user_bouquet_field.get_text()
        options["satellites_xml_path"] = self._satellites_xml_field.get_text()
        options["picons_path"] = self._picons_field.get_text()
        options["data_dir_path"] = self._data_dir_field.get_text()
        options["picons_dir_path"] = self._picons_dir_field.get_text()
        options["backup_dir_path"] = self._backup_dir_field.get_text()
        options["backup_before_save"] = self._before_save_switch.get_active()
        options["backup_before_downloading"] = self._before_downloading_switch.get_active()

        if profile is Profile.ENIGMA_2:
            options["v5_support"] = self._support_ver5_check_button.get_active()
            options["http_api_support"] = self._support_http_api_check_button.get_active()
            options["use_colors"] = self._set_color_switch.get_active()
            options["new_color"] = self._new_color_button.get_rgba().to_string()
            options["extra_color"] = self._extra_color_button.get_rgba().to_string()

        write_config(self._options)

    @run_task
    def on_connection_test(self, item):
        if self._test_spinner.get_state() is Gtk.StateType.ACTIVE:
            return
        self.show_spinner(True)
        current_property = Property(self._settings_stack.get_visible_child_name())
        if current_property is Property.HTTP:
            self.test_http()
        elif current_property is Property.TELNET:
            self.test_telnet()
        elif current_property is Property.FTP:
            self.test_ftp()

    def test_http(self):
        user, password = self._http_login_field.get_text(), self._http_password_field.get_text()
        host, port = self._host_field.get_text(), self._http_port_field.get_text()
        try:
            self.show_info_message(test_http(host, port, user, password), Gtk.MessageType.INFO)
        except TestException as e:
            self.show_info_message(str(e), Gtk.MessageType.ERROR)
        finally:
            self.show_spinner(False)

    def test_telnet(self):
        timeout = int(self._telnet_timeout_spin_button.get_value())
        host, port = self._host_field.get_text(), self._telnet_port_field.get_text()
        user, password = self._telnet_login_field.get_text(), self._telnet_password_field.get_text()
        try:
            self.show_info_message(test_telnet(host, port, user, password, timeout), Gtk.MessageType.INFO)
            self.show_spinner(False)
        except TestException as e:
            self.show_info_message(str(e), Gtk.MessageType.ERROR)
            self.show_spinner(False)

    def test_ftp(self):
        host, port = self._host_field.get_text(), self._port_field.get_text()
        user, password = self._login_field.get_text(), self._password_field.get_text()
        try:
            self.show_info_message("OK.  {}".format(test_ftp(host, port, user, password)), Gtk.MessageType.INFO)
        except TestException as e:
            self.show_info_message(str(e), Gtk.MessageType.ERROR)
        finally:
            self.show_spinner(False)

    @run_idle
    def show_info_message(self, text, message_type):
        self._info_bar.set_visible(True)
        self._info_bar.set_message_type(message_type)
        self._message_label.set_text(text)

    @run_idle
    def show_spinner(self, show):
        self._test_spinner.start() if show else self._test_spinner.stop()
        self._test_spinner.set_state(Gtk.StateType.ACTIVE if show else Gtk.StateType.NORMAL)

    def on_info_bar_close(self, bar=None, resp=None):
        self._info_bar.set_visible(False)

    def on_set_color_switch_state(self, switch, state):
        self._colors_grid.set_sensitive(state)


if __name__ == "__main__":
    pass
