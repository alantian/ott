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
"""Plotting utils."""

import base64
from typing import Union, List
import warnings

import jax.numpy as jnp
import matplotlib.pyplot as plt
from ott.tools import transport
import scipy

try:
  from PIL import Image
  PIL_is_importable = True
except ImportError:
  PIL_is_importable = False

try:
  from IPython import display
  IPython_is_importable = True
except ImportError:
  IPython_is_importable = False


def bidimensional(x: jnp.ndarray, y: jnp.ndarray):
  """Applies PCA to reduce to bimensional data."""
  if x.shape[1] < 3:
    return x, y

  u, s, _ = scipy.sparse.linalg.svds(jnp.concatenate([x, y], axis=0), k=2)
  proj = u * s
  k = x.shape[0]
  return proj[:k], proj[k:]


def _couplings(ax,
               x: jnp.ndarray,
               y: jnp.ndarray,
               a: jnp.ndarray,
               b: jnp.ndarray,
               matrix: jnp.ndarray,
               threshold: float = 0.0,
               scale: int = 200,
               cmap: str = 'Purples'):
  """Plots 2-D couplings. Projects via PCA if data is higher dimensional."""
  x, y = bidimensional(x, y)

  sa, sb = jnp.min(a) / scale, jnp.min(b) / scale
  ax.scatter(*x.T, s=a / sa, edgecolors='k', marker='o', label='x')
  ax.scatter(*y.T, s=b / sb, edgecolors='k', marker='X', label='y')

  cmap = plt.get_cmap(cmap)
  u, v = jnp.where(matrix > threshold)
  c = matrix[jnp.where(matrix > threshold)]
  xy = jnp.concatenate([x[u], y[v]], axis=-1)
  for i in range(xy.shape[0]):
    strength = jnp.max(jnp.array(matrix.shape)) * c[i]
    ax.plot(
        xy[i, [0, 2]],
        xy[i, [1, 3]],
        linewidth=0.5 + 4 * strength,
        color=cmap(strength),
        zorder=0,
        alpha=0.7,
    )
  ax.legend(fontsize=15)
  return ax


def couplings(arg: Union[transport.Transport, jnp.ndarray],
              y: jnp.ndarray = None,
              a: jnp.ndarray = None,
              b: jnp.ndarray = None,
              matrix: jnp.ndarray = None,
              ax=None,
              **kwargs):
  """Plots 2D points and the couplings between them."""
  if ax is None:
    _, ax = plt.subplots(1, 1, figsize=(8, 5))

  if isinstance(arg, transport.Transport):
    ot = arg
    return _couplings(ax, ot.geom.x, ot.geom.y, ot.a, ot.b, ot.matrix, **kwargs)

  return _couplings(ax, arg, y, a, b, matrix, **kwargs)


def _barycenters(ax,
                 y: jnp.ndarray,
                 a: jnp.ndarray,
                 b: jnp.ndarray,
                 matrix: jnp.ndarray,
                 scale: int = 200):
  """Plots 2-D sinkhorn barycenters."""
  sa, sb = jnp.min(a) / scale, jnp.min(b) / scale
  ax.scatter(*y.T, s=b / sb, edgecolors='k', marker='X', label='y')
  tx = 1 / a[:, None] * jnp.matmul(matrix, y)
  ax.scatter(*tx.T, s=a / sa, edgecolors='k', marker='X', label='T(x)')
  ax.legend(fontsize=15)


def barycenters(arg: Union[transport.Transport, jnp.ndarray],
                a: jnp.ndarray = None,
                b: jnp.ndarray = None,
                matrix: jnp.ndarray = None,
                ax=None,
                **kwargs):
  """Plots the barycenters, from the Transport object or from arguments."""
  if ax is None:
    _, ax = plt.subplots(1, 1, figsize=(8, 5))

  if isinstance(arg, transport.Transport):
    ot = arg
    return _barycenters(ax, ot.geom.y, ot.a, ot.b, ot.matrix, **kwargs)

  return _barycenters(ax, arg, a, b, matrix, **kwargs)


def animate(image_fns: List[str],
            gif_fn: str,
            duration: int = 250,
            loop: int = 0):
  """Makes an animated GIF from list of images."""
  if not PIL_is_importable:
    warnings.warn(
        'Pillow was not imported successfully. Doing nothing instead.',
        RuntimeWarning,
    )
    return
  images = [Image.open(image_fn) for image_fn in image_fns]
  images[0].save(
      gif_fn,
      save_all=True,
      append_images=images[1:],
      duration=duration,
      loop=0,
  )


def show_gif(gif_fn):
  """Show GIF in a notebook, in an embeded way."""
  if not IPython_is_importable:
    warnings.run(
        'IPython was not imported successfully. Doing nothing instead.',
        RuntimeWarning,
    )
    return

  with open(gif_fn, 'rb') as f:
    base64_encode = base64.b64encode(f.read()).decode('ascii')
  return display.HTML(f'<img src="data:image/gif;base64,{base64_encode}" />')
