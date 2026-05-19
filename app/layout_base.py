"""Shared layout base class for common inputs and helpers."""

from kivy.clock import mainthread
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.boxlayout import BoxLayout

from app.ui_helpers import (
    fill_pressure_temperature,
    get_npoints,
    get_pressure,
    get_temperatures,
    show_error_alert,
)
from app.utils import show_error_popup


class BaseInputLayout(BoxLayout):
    """Base layout with shared inputs and helpers."""

    temp_min = ObjectProperty(None)
    temp_max = ObjectProperty(None)
    pressure = ObjectProperty(None)
    predicted_parameters = ObjectProperty(None)
    _dropdown_cache = []
    npoints = ObjectProperty(None)

    @mainthread
    def _show_error_alert(self, error):
        show_error_alert(self, error, show_error_popup)

    def _get_temperatures(self, require_max=True):
        return get_temperatures(self, require_max=require_max)

    def _get_pressure(self):
        return get_pressure(self)

    def _get_npoints(self):
        return get_npoints(self)

    def _fill_inputs(self, pressure=None, t_min=None, t_max=None):
        """Helper to populate inputs with clicked values."""
        fill_pressure_temperature(self, pressure=pressure, t_min=t_min, t_max=t_max)
