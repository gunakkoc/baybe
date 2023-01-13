"""
Functionality for data scaling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, Tuple, Type

import pandas as pd
import torch
from torch import Tensor

from .utils import to_tensor

ScaleFun = Callable[[Tensor], Tensor]


class Scaler(ABC):
    """Abstract base class for all scalers."""

    type: str
    SUBCLASSES: Dict[str, Type[Scaler]] = {}

    def __init__(self, searchspace: pd.DataFrame):
        self.searchspace = searchspace
        self.fitted = False
        self.scale_x: ScaleFun
        self.scale_y: ScaleFun
        self.unscale_x: ScaleFun
        self.unscale_y: ScaleFun
        self.unscale_m: ScaleFun
        self.unscale_s: ScaleFun

    @abstractmethod
    def fit_transform(self, x: Tensor, y: Tensor) -> Tuple[Tensor, Tensor]:
        """Fits the scaler using the given training data and transforms the data."""

    def transform(self, x: Tensor) -> Tensor:
        """Scales a given input."""
        if not self.fitted:
            raise RuntimeError("Scaler object must be fitted first.")
        return self.scale_x(x)

    def untransform(self, mean: Tensor, variance: Tensor) -> Tuple[Tensor, Tensor]:
        """Transforms mean values and variances back to the original domain."""
        if not self.fitted:
            raise RuntimeError("Scaler object must be fitted first.")
        return self.unscale_m(mean), self.unscale_s(variance)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Registers new subclasses dynamically."""
        super().__init_subclass__(**kwargs)
        cls.SUBCLASSES[cls.type] = cls


class DefaultScaler(Scaler):
    """A scaler that normalizes inputs to the unit cube and standardizes targets."""

    type = "DEFAULT"

    def fit_transform(self, x: Tensor, y: Tensor) -> Tuple[Tensor, Tensor]:
        """See base class."""

        # Get the searchspace boundaries
        searchspace = to_tensor(self.searchspace)
        bounds = torch.vstack(
            [torch.min(searchspace, dim=0)[0], torch.max(searchspace, dim=0)[0]]
        )

        # Compute the mean and standard deviation of the training targets
        mean = torch.mean(y, dim=0)
        std = torch.std(y, dim=0)

        # Functions for input and target scaling
        self.scale_x = lambda l: (l - bounds[0]) / (bounds[1] - bounds[0])
        self.scale_y = lambda l: (l - mean) / std

        # Functions for inverse input and target scaling
        self.unscale_x = lambda l: l * (bounds[1] - bounds[0]) + bounds[0]
        self.unscale_y = lambda l: l * std + mean

        # Functions for inverse mean and variance scaling
        self.unscale_m = lambda l: l * std + mean
        self.unscale_s = lambda l: l * std**2

        # Flag that the scaler has been fitted
        self.fitted = True

        return self.scale_x(x), self.scale_y(y)