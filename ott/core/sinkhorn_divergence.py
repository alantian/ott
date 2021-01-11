# coding=utf-8
# Copyright 2021 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Implements the sinkhorn divergence."""
import collections
from typing import Optional, Type, Dict, Any
from jax import numpy as np
from ott.core import sinkhorn

from ott.core.ground_geometry import geometry

SinkhornDivergence = collections.namedtuple(
    'SinkhornDivergence', ['divergence', 'potentials', 'geoms', 'errors'])


def sinkhorn_divergence_wrapper(
    geom: Type[geometry.Geometry],
    a: np.ndarray,
    b: np.ndarray,
    *args,
    sinkhorn_kwargs: Optional[Dict[str, Any]] = None,
    static_b: bool = False,
    **kwargs):
  """Computes the sinkhorn divergence.

  Args:
    geom: A class of geometry.
    a: np.ndarray<float>[n]: the weight of each input point. The sum of
      all elements of b must match that of a to converge.
    b: np.ndarray<float>[m]: the weight of each target point. The sum of
      all elements of b must match that of a to converge.
    *args: arguments to the prepare_divergences method that is specific to each
      geometry.
    sinkhorn_kwargs: Optionally a dict containing the keywords arguments for
      the sinkhorn_divergence function.
    static_b: whether to compute the regularised sinkhorn cost for the second
      view (b).
    **kwargs: keywords arguments to the generic class. This is specific to each
      geometry.

  Returns:
    tuple: (sinkhorn divergence value, three pairs of potentials, three costs)
  """
  geometries = geom.prepare_divergences(*args, static_b=static_b, **kwargs)
  geometries = (geometries + (None,) * max(0, 3 - len(geometries)))[:3]
  div_kwargs = {} if sinkhorn_kwargs is None else sinkhorn_kwargs
  return sinkhorn_divergence(*geometries, a, b, **div_kwargs)


def sinkhorn_divergence(
    geometry_xy: geometry.Geometry,
    geometry_xx: geometry.Geometry,
    geometry_yy: Optional[geometry.Geometry],
    a: np.ndarray,
    b: np.ndarray,
    **kwargs):
  """Computes the sinkhorn divergence for the wrapper function.

  Args:
    geometry_xy: a Cost object able to apply kernels with a certain epsilon,
    between the views X and Y.
    geometry_xx: a Cost object able to apply kernels with a certain epsilon,
    between elements of the view X.
    geometry_yy: a Cost object able to apply kernels with a certain epsilon,
    between elements of the view Y.
    a: np.ndarray<float>[n]: the weight of each input point. The sum of
     all elements of b must match that of a to converge.
    b: np.ndarray<float>[m]: the weight of each target point. The sum of
     all elements of b must match that of a to converge.
    **kwargs: Arguments to sinkhorn_iterations.
  Returns:
    tuple: (sinkhorn divergence value, three pairs of potentials)
  """
  geoms = (geometry_xy, geometry_xx, geometry_yy)
  out = [
      sinkhorn.SinkhornOutput(None, None, 0, None) if geom is None
      else sinkhorn.sinkhorn(geom, marginals[0], marginals[1], **kwargs)
      for (geom, marginals) in zip(geoms, [[a, b], [a, a], [b, b]])
  ]
  div = out[0].reg_ot_cost - 0.5 * (out[1].reg_ot_cost + out[2].reg_ot_cost)
  return SinkhornDivergence(div, tuple([s.f, s.g] for s in out),
                            geoms, tuple(s.errors for s in out))