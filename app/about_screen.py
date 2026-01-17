"About screen and layout"

import webbrowser

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen


class AboutScreen(Screen):
    "About screen"


class AboutLayout(BoxLayout):
    "About Layout containing project info"

    def open_link(self, instance, value):
        "Opens the clicked link in the default browser"
        webbrowser.open(value)
