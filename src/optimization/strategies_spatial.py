# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# File: src/optimization/strategies_spatial.py
# Author: Gabriel Moraes
# Date: 2026-03-08

"""
Optuna Strategies for the Cartographer Agent (Spatial Alignment).

Adheres strictly to SOLID:
- Single Responsibility Principle (SRP): Isolates hyperparameter search and
  convergence orchestration; delegates sampling to BfsGraphSampler, mutation
  to SpatialGraphMutator, and neural training to CartographerTrainer.
- Open/Closed Principle (OCP): Components (sampler, mutator, trainer) are injectable
  and extensible without modifying this orchestrator.
- Dependency Inversion Principle (DIP): Relies on IGraphSampler, ISpatialGraphMutator,
  and ICartographerTrainer protocols.
"""

import logging
import torch
from typing import Any, List, Tuple, Optional, Callable

try:
    from torch_geometric.data import Data
    PYG_AVAILABLE = True
except ImportError:
    PYG_AVAILABLE = False

from src.models.sinkhorn_cross_attention import SinkhornCrossAttention
from src.services.line_graph_builder import LineGraphBuilder
from src.services.graph_sampler import BfsGraphSampler
from src.services.spatial_graph_mutator import SpatialGraphMutator
from src.trainer.cartographer_trainer import CartographerTrainer
from src.domain.entities import MapEdge, MapNode
from src.domain.model_contracts import IGraphSampler, ISpatialGraphMutator
from src.utils.convergence_tracker import MarginalConvergenceTracker

logger = logging.getLogger("Synapse.Strategies.Spatial")


class SpatialStrategies:
    """Optimization strategies for the Cartographer Agent."""

    @staticmethod
    def cartographer_strategy(
        trial,
        graph_data: Any,
        device: torch.device,
        max_epochs: int = 50,
        min_epochs: int = 4,
        n_subgraphs_per_epoch: int = 10,
        sampler: Optional[IGraphSampler] = None,
        mutator: Optional[ISpatialGraphMutator] = None,
        trainer_factory: Optional[Callable[[SinkhornCrossAttention, float, torch.device], CartographerTrainer]] = None,
    ) -> float:
        """
        Optuna trial for the SinkhornCrossAttention model with Dynamic Marginal Convergence.

        Args:
            trial: Optuna trial object.
            graph_data: Dict with 'edges' (List[MapEdge]) and 'nodes' (List[MapNode]).
            device: Torch device.
            max_epochs: Max safety epochs per trial.
            min_epochs: Min warm-up epochs.
            n_subgraphs_per_epoch: Random subgraphs per epoch.
            sampler: Optional injected graph sampler (defaults to BfsGraphSampler).
            mutator: Optional injected graph mutator (defaults to SpatialGraphMutator).
            trainer_factory: Optional factory callable for trainer (DIP).

        Returns:
            Final best loss (lower is better).
        """
        if not PYG_AVAILABLE:
            logger.error("[Spatial] PyTorch Geometric not available.")
            return float('inf')

        edges = graph_data.get('edges', []) if isinstance(graph_data, dict) else getattr(graph_data, 'edges', [])
        nodes = graph_data.get('nodes', []) if isinstance(graph_data, dict) else getattr(graph_data, 'nodes', [])

        if len(edges) < 10:
            logger.error(f"[Spatial] Not enough edges: {len(edges)}")
            return float('inf')

        # Dependency resolution (Default to solid services if not injected)
        graph_sampler = sampler or BfsGraphSampler()
        graph_mutator = mutator or SpatialGraphMutator()

        # ── Hyperparameters (Optuna Search Space) ──
        d_model = trial.suggest_categorical("cart_d_model", [32, 64, 128])
        n_heads = trial.suggest_categorical("cart_n_heads", [2, 4, 8])
        n_gat_layers = trial.suggest_int("cart_n_gat_layers", 2, 4)
        dropout = trial.suggest_float("cart_dropout", 0.05, 0.3)
        sinkhorn_iters = trial.suggest_int("cart_sinkhorn_iters", 5, 20)
        lr = trial.suggest_float("cart_lr", 1e-4, 1e-2, log=True)
        noise_scale = trial.suggest_float("cart_noise_scale", 5.0, 50.0)
        temperature = trial.suggest_float("cart_temperature", 0.05, 0.5, log=True)

        logger.info(
            f"[Spatial] 🌐 Trial {trial.number} starting | "
            f"d_model={d_model}, n_heads={n_heads}, layers={n_gat_layers}, "
            f"sinkhorn={sinkhorn_iters}, lr={lr:.5f}"
        )

        # ── Model & Trainer Instantiation (DIP) ──
        model = SinkhornCrossAttention(
            raw_dim=11,
            d_model=d_model,
            n_heads=n_heads,
            n_gat_layers=n_gat_layers,
            sinkhorn_iters=sinkhorn_iters,
            dropout=dropout,
            temperature=temperature,
        ).to(device)

        if trainer_factory is not None:
            trainer = trainer_factory(model, lr, device)
        else:
            trainer = CartographerTrainer(model=model, learning_rate=lr, device=device)

        # ── Dynamic Training Loop ──
        tracker = MarginalConvergenceTracker(
            min_epochs=min_epochs,
            max_epochs=max_epochs,
            patience=3,
            min_delta=1e-4,
            optuna_trial=trial
        )

        try:
            for epoch in range(tracker.max_epochs):
                batch_losses: List[float] = []

                for _ in range(n_subgraphs_per_epoch):
                    try:
                        # 1. Connected Subgraph Extraction (Delegated to IGraphSampler)
                        sub_edges, sub_nodes = graph_sampler.sample_subgraph(
                            edges, nodes, min_edges=5, max_edges=30
                        )
                        if len(sub_edges) < 3:
                            continue

                        # 2. Build Source Line Graph
                        source = LineGraphBuilder.build_from_edges(sub_edges, sub_nodes)
                        if source is None:
                            continue

                        # 3. Mutant Synthesis (Delegated to ISpatialGraphMutator)
                        mut_edges, perm = graph_mutator.mutate(
                            sub_edges, noise_scale=noise_scale
                        )
                        mutant = LineGraphBuilder.build_from_edges(mut_edges, sub_nodes)
                        if mutant is None:
                            continue

                        # 4. Ground Truth Permutation Matrix
                        n_s, n_m = source.num_nodes, mutant.num_nodes
                        gt = torch.zeros(n_s, n_m)
                        for src_idx, mut_idx in enumerate(perm):
                            if src_idx < n_s and mut_idx < n_m:
                                gt[src_idx, mut_idx] = 1.0

                        # 5. Forward + Loss + Optimization (Delegated to ICartographerTrainer)
                        loss_val = trainer.train_step(source, mutant, gt)
                        batch_losses.append(loss_val)

                    except Exception as e:
                        logger.debug(f"[Spatial] Subgraph error: {e}")
                        continue

                if batch_losses:
                    mean_loss = sum(batch_losses) / len(batch_losses)
                    
                    if epoch % 10 == 0:
                        logger.info(
                            f"[Spatial] Trial {trial.number} | "
                            f"Epoch {epoch+1} | Loss: {mean_loss:.4f}"
                        )

                    if tracker.step(epoch, mean_loss, model=model):
                        break

            if not tracker.loss_history:
                return float('inf')

            logger.info(
                f"[Spatial] Trial {trial.number} finished with value: {tracker.best_loss:.6f} "
                f"at epoch {tracker.best_epoch+1} and parameters: {trial.params}"
            )

            return tracker.best_loss

        except Exception as e:
            # Check if it was optuna TrialPruned
            if hasattr(e, '__class__') and e.__class__.__name__ == 'TrialPruned':
                raise
            logger.warning(f"[Spatial] Trial failed: {e}")
            return float('inf')
        finally:
            del model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    # ─── Backward-compatible delegates ───────────────────────────────────────

    @staticmethod
    def _random_subgraph(
        edges: List[MapEdge],
        nodes: List[MapNode],
        min_edges: int = 5,
        max_edges: int = 30,
    ) -> Tuple[List[MapEdge], List[MapNode]]:
        """Delegates to BfsGraphSampler for backward compatibility."""
        return BfsGraphSampler().sample_subgraph(edges, nodes, min_edges, max_edges)

    @staticmethod
    def _create_mutation(
        edges: List[MapEdge],
        noise_scale: float = 20.0,
        drop_prob: float = 0.1,
    ) -> Tuple[List[MapEdge], List[int]]:
        """Delegates to SpatialGraphMutator for backward compatibility."""
        return SpatialGraphMutator().mutate(edges, noise_scale, drop_prob)
