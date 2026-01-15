"# main.py"

import os

import kivy
import kivy_matplotlib_widget  # pylint: disable=unused-import
from kivy.app import App
from kivy.properties import (  # pylint: disable=no-name-in-module
    ObjectProperty,
    StringProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from mixture_screen import MixtureLayout, MixtureScreen  # pylint: disable=unused-import
from pure_screen import PureLayout, PureScreen  # pylint: disable=unused-import

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

    icon = os.path.join(application_path, "512.png")


if __name__ == "__main__":
    GNNPCSAFT().run()
