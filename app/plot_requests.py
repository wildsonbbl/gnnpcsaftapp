"""Dataclasses for plot requests."""

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple, Union

from numpy import float64
from numpy.typing import NDArray

NumericSeq = Sequence[float]


@dataclass
class PlotRequest:
    """Parameters for a standard 2D plot."""

    x_data: Union[NumericSeq, Sequence[NumericSeq]]
    y_data: Union[NumericSeq, Sequence[NumericSeq]]
    title: str
    x_label: str
    y_label: str
    legends: Optional[Sequence[str]] = None
    exp_data: Optional[Tuple[NDArray[float64], NDArray[float64], str]] = None


@dataclass
class TernaryPlotRequest:
    """Parameters for a ternary plot."""

    a: Sequence[NumericSeq]
    b: Sequence[NumericSeq]
    title: str
    a_label: str
    b_label: str
    legends: Optional[Sequence[str]] = None
    exp_data: Optional[Tuple[NDArray[float64], NDArray[float64], str]] = None
