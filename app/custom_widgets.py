"Custom widgets"

from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label


class ActionLabelCustom(ButtonBehavior, Label):  # type: ignore
    "Label that acts as a button with hover effect"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = "#0d6efd"  # Default link color (Bootstrap Primary)
        self.background_color_normal = (1, 1, 1, 0)  # Transparent
        self.background_color_hover = (0.9, 0.9, 0.9, 1)  # Light Gray

        # Determine initial background logic
        with self.canvas.before:  # type: ignore
            self.bg_color = Color(*self.background_color_normal)
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self._update_rect, pos=self._update_rect)  # type: ignore pylint: disable=no-member

        # Bind mouse position for hover effect
        Window.bind(mouse_pos=self.on_mouse_pos)

    def _update_rect(self, instance, value):  # pylint: disable=unused-argument
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def on_mouse_pos(self, window, pos):  # pylint: disable=unused-argument
        "function for mouse hover effect"
        if not self.get_root_window():
            return

        if self.collide_point(*self.to_widget(*pos)):
            # Hover state
            self.bg_color.rgba = self.background_color_hover
            self.color = "#0a58ca"  # Darker blue
        else:
            # Normal state
            self.bg_color.rgba = self.background_color_normal
            self.color = "#0d6efd"

    def on_press(self):
        self.bg_color.rgba = (0.8, 0.8, 0.8, 1)  # Darker gray on click

    def on_release(self):
        # Return to hover state color since mouse is likely still over it
        self.bg_color.rgba = self.background_color_hover
