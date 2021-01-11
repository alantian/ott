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

# Lint as: python3
"""Tests for the Sinkhorn divergence."""

from absl.testing import absltest
import jax
import jax.numpy as np
import jax.test_util

from ott.core import sinkhorn_divergence
from ott.core.ground_geometry import geometry
from ott.core.ground_geometry import pointcloud


class SinkhornDivergenceTest(jax.test_util.JaxTestCase):

  def setUp(self):
    super().setUp()
    self.rng = jax.random.PRNGKey(0)
    self._dim = 4
    self._num_points = 60, 70
    self.rng, *rngs = jax.random.split(self.rng, 3)
    a = jax.random.uniform(rngs[0], (self._num_points[0],))
    b = jax.random.uniform(rngs[1], (self._num_points[1],))
    self._a = a / np.sum(a)
    self._b = b / np.sum(b)

  def test_euclidean_point_cloud(self):
    rngs = jax.random.split(self.rng, 2)
    x = jax.random.uniform(rngs[0], (self._num_points[0], self._dim))
    y = jax.random.uniform(rngs[1], (self._num_points[1], self._dim))
    geometry_xx = pointcloud.PointCloudGeometry(x, x, epsilon=0.1)
    geometry_xy = pointcloud.PointCloudGeometry(x, y, epsilon=0.1)
    geometry_yy = pointcloud.PointCloudGeometry(y, y, epsilon=0.1)
    div = sinkhorn_divergence.sinkhorn_divergence(
        geometry_xy,
        geometry_xx,
        geometry_yy,
        self._a,
        self._b,
        threshold=1e-1,
        max_iterations=20)
    # div.divergence = 2.0
    self.assertGreater(div.divergence, 0.0)
    self.assertLen(div.potentials, 3)

  def test_euclidean_point_cloud_wrapper(self):
    rngs = jax.random.split(self.rng, 2)
    cloud_a = jax.random.uniform(rngs[0], (self._num_points[0], self._dim))
    cloud_b = jax.random.uniform(rngs[1], (self._num_points[1], self._dim))
    div = sinkhorn_divergence.sinkhorn_divergence_wrapper(
        pointcloud.PointCloudGeometry, self._a, self._b,
        cloud_a, cloud_b, epsilon=0.1,
        sinkhorn_kwargs=dict(threshold=1e-2))
    self.assertGreater(div.divergence, 0.0)
    self.assertLen(div.potentials, 3)
    self.assertLen(div.geoms, 3)

  def test_generic_point_cloud_wrapper(self):
    rngs = jax.random.split(self.rng, 2)
    x = jax.random.uniform(rngs[0], (self._num_points[0], self._dim))
    y = jax.random.uniform(rngs[1], (self._num_points[1], self._dim))

    # Tests with 3 cost matrices passed as args
    cxy = np.sum(np.abs(x[:, np.newaxis] - y[np.newaxis, :])**2, axis=2)
    cxx = np.sum(np.abs(x[:, np.newaxis] - x[np.newaxis, :])**2, axis=2)
    cyy = np.sum(np.abs(y[:, np.newaxis] - y[np.newaxis, :])**2, axis=2)
    div = sinkhorn_divergence.sinkhorn_divergence_wrapper(
        geometry.Geometry, self._a, self._b,
        cxy, cxx, cyy, epsilon=0.1, sinkhorn_kwargs=dict(threshold=1e-2))
    self.assertIsNotNone(div.divergence)
    self.assertLen(div.potentials, 3)
    self.assertLen(div.geoms, 3)

    # Tests with 2 cost matrices passed as args
    div = sinkhorn_divergence.sinkhorn_divergence_wrapper(
        geometry.Geometry, self._a, self._b,
        cxy, cxx, epsilon=0.1, sinkhorn_kwargs=dict(threshold=1e-2))
    self.assertIsNotNone(div.divergence)
    self.assertLen(div.potentials, 3)
    self.assertLen(div.geoms, 3)

    # Tests with 3 cost matrices passed as kwargs
    div = sinkhorn_divergence.sinkhorn_divergence_wrapper(
        geometry.Geometry, self._a, self._b,
        cost_matrix=(cxy, cxx, cyy), epsilon=0.1,
        sinkhorn_kwargs=dict(threshold=1e-2))
    self.assertIsNotNone(div.divergence)
    self.assertLen(div.potentials, 3)
    self.assertLen(div.geoms, 3)

  def test_gradient_generic_point_cloud_wrapper(self):
    rngs = jax.random.split(self.rng, 3)
    x = jax.random.uniform(rngs[0], (self._num_points[0], self._dim))
    y = jax.random.uniform(rngs[1], (self._num_points[1], self._dim))

    def loss_fn(cloud_a, cloud_b):
      div = sinkhorn_divergence.sinkhorn_divergence_wrapper(
          pointcloud.PointCloudGeometry, self._a, self._b,
          cloud_a, cloud_b, epsilon=0.5,
          sinkhorn_kwargs=dict(threshold=1e-2))
      return div.divergence

    delta = jax.random.normal(rngs[2], x.shape)
    eps = 1e-3  # perturbation magnitude

    # first calculation of gradient
    loss_and_grad = jax.jit(jax.value_and_grad(loss_fn))
    loss_value, grad_loss = loss_and_grad(x, y)
    custom_grad = np.sum(delta * grad_loss)

    self.assertIsNot(loss_value, np.nan)
    self.assertEqual(grad_loss.shape, x.shape)
    self.assertFalse(np.any(np.isnan(grad_loss)))

    # second calculation of gradient
    loss_delta_plus = loss_fn(x + eps * delta, y)
    loss_delta_minus = loss_fn(x - eps * delta, y)
    finite_diff_grad = (loss_delta_plus - loss_delta_minus) / (2 * eps)

    self.assertAllClose(custom_grad, finite_diff_grad, rtol=1e-02, atol=1e-02)

if __name__ == '__main__':
  absltest.main()