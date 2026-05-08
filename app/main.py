"""App entrypoint for the Kivy UI."""

import os
import threading
import webbrowser
from json import JSONDecodeError
from urllib.error import HTTPError, URLError

import kivy
import kivy_matplotlib_widget  # pylint: disable=unused-import
from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.properties import (  # pylint: disable=no-name-in-module
    BooleanProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager

from app._version import __version__
from app.about_screen import AboutLayout, AboutScreen  # pylint: disable=unused-import
from app.mixture_screen import (  # pylint: disable=unused-import
    MixtureLayout,
    MixtureScreen,
)
from app.pure_screen import PureLayout, PureScreen  # pylint: disable=unused-import
from app.update_check import fetch_latest_release, is_newer_version

kivy.require("2.3.1")  # replace with your current kivy version

application_path = os.path.dirname(os.path.abspath(__file__))


class WindowManager(ScreenManager):
    "Window manager for multiple screens"


class PlotScreen(Screen):
    "Plot screen"


class PlotLayout(BoxLayout):
    "Plot Layout"

    previous_screen = StringProperty("pure_screen")
    matplot_figure = ObjectProperty(None)


class NavBar(BoxLayout):
    "Navigation Bar"


class GNNPCSAFT(App):
    "Main app class"

    version = __version__
    update_available = BooleanProperty(False)
    update_tag = StringProperty("")
    update_url = StringProperty("")

    icon = os.path.join(application_path, "512.png")

    def on_start(self):
        self.check_for_updates()

    def check_for_updates(self):
        """Start a background check for the latest release."""

        threading.Thread(target=self._check_for_updates, daemon=True).start()

    def open_update_release(self):
        """Open the latest release page if an update is available."""

        if self.update_url:
            webbrowser.open(self.update_url)

    def _check_for_updates(self):
        try:
            latest_release = fetch_latest_release()
            Logger.debug("Latest release: %s", latest_release)
        except (HTTPError, URLError, TimeoutError, JSONDecodeError) as e:
            Logger.error("Failed to fetch latest release: %s", e)
            return

        if not latest_release.tag_name:
            Logger.debug("No valid tag found for the latest release")
            return

        if is_newer_version(latest_release.tag_name, self.version):
            Logger.debug("A newer version is available")
            Clock.schedule_once(
                lambda _dt: self._show_update_available(latest_release),
                0,
            )

    def _show_update_available(self, release):
        self.update_available = True
        self.update_tag = release.tag_name
        self.update_url = release.html_url

        content = BoxLayout(orientation="vertical", spacing=10, padding=12)
        title = Label(
            text=f"A new version is available: {release.tag_name}",
            color=(0, 0, 0, 1),
            bold=True,
            size_hint_y=None,
            height=30,
            halign="center",
        )
        message = Label(
            text=(
                f"Current version: {self.version}\n"
                f"Latest version: {release.tag_name}"
            ),
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=54,
            halign="center",
        )
        open_button = Button(
            text="Open release notes",
            size_hint_y=None,
            height=40,
        )
        dismiss_button = Button(
            text="Later",
            size_hint_y=None,
            height=40,
        )

        content.add_widget(title)
        content.add_widget(message)
        content.add_widget(open_button)
        content.add_widget(dismiss_button)

        popup = Popup(
            title="",
            content=content,
            background="",
            background_color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(420, 300),
            auto_dismiss=False,
        )

        def open_release_notes(_btn):
            webbrowser.open(release.html_url)
            popup.dismiss()

        def dismiss_popup(_btn):
            popup.dismiss()

        open_button.bind(on_release=open_release_notes)  # type: ignore pylint: disable=no-member
        dismiss_button.bind(on_release=dismiss_popup)  # type: ignore pylint: disable=no-member
        popup.open()


if __name__ == "__main__":
    GNNPCSAFT().run()
