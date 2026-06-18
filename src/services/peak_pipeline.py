# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: src/services/peak_pipeline.py
# Author: Gabriel Moraes
# Date: 2026-04-26

import os
import json
import logging
import gc
import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.mixture import GaussianMixture
from typing import Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.distilroberta import DistilRobertaSemanticExtractor

logger = logging.getLogger(__name__)


class ColumnDiscovery:
    """
    Single Responsibility: Semantic column matching using NLP embeddings.
    
    Uses DistilRoBERTa to match dataset columns to traffic concepts
    (volume/flow vs speed/velocity) by cosine similarity.
    """

    VOLUME_CONCEPT = ["traffic volume, vehicle count, vehicle flow, intensity, amount of cars"]
    SPEED_CONCEPT = ["traffic speed, vehicle velocity, average speed, km/h, mph"]

    def __init__(self):
        self._extractor: Optional['DistilRobertaSemanticExtractor'] = None

    def _ensure_extractor(self):
        if self._extractor is None:
            from src.models.distilroberta import DistilRobertaSemanticExtractor
            logger.info("Loading DistilRobertaSemanticExtractor for Column Discovery...")
            self._extractor = DistilRobertaSemanticExtractor()

    def discover(self, columns: list) -> Tuple[str, str]:
        """
        Discovers which columns map to volume/flow and speed/velocity.
        
        Returns:
            Tuple of (volume_column, speed_column).
        """
        self._ensure_extractor()

        vol_emb = self._get_embedding(self.VOLUME_CONCEPT)
        spd_emb = self._get_embedding(self.SPEED_CONCEPT)
        col_embs = self._get_embedding(columns)

        vol_scores = F.cosine_similarity(vol_emb.expand_as(col_embs), col_embs, dim=1)
        spd_scores = F.cosine_similarity(spd_emb.expand_as(col_embs), col_embs, dim=1)

        best_vol_col = columns[torch.argmax(vol_scores).item()]
        best_spd_col = columns[torch.argmax(spd_scores).item()]

        return best_vol_col, best_spd_col

    def _get_embedding(self, texts: list) -> torch.Tensor:
        embeddings = []
        for text in texts:
            emb = self._extractor._get_embedding([text])
            embeddings.append(emb)
        return torch.cat(embeddings, dim=0)


class PeakPipeline:
    """
    Single Responsibility: Peak classification pipeline.
    
    Orchestrates the full ADAGIO pipeline:
    1. Neural feature extraction (iTransformer + TimesNet) in chunks
    2. Canonical week aggregation (168 hourly blocks)
    3. GMM probabilistic classification
    4. JSON schedule export
    """

    DAY_MAP = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
        4: "Friday", 5: "Saturday", 6: "Sunday"
    }

    def __init__(self, itransformer, timesnet, device: torch.device, chunk_size: int = 2048):
        self.itransformer = itransformer
        self.timesnet = timesnet
        self.device = device
        self.chunk_size = chunk_size
        self.gmm = GaussianMixture(n_components=2, covariance_type='full', random_state=42)

    def run(self, df: pd.DataFrame, vol_col: str, spd_col: str, output_path: str) -> dict:
        """
        Executes the full peak classification pipeline.
        
        Returns:
            Dict with the 168-block schedule.
        """
        # 1. Prepare tensors
        volume_tensor = torch.tensor(df[vol_col].values, dtype=torch.float32).unsqueeze(0)
        speed_tensor = torch.tensor(df[spd_col].values, dtype=torch.float32).unsqueeze(0)

        # 2. Neural feature extraction
        logger.info("Extracting neural features via iTransformer + TimesNet...")
        neural_scores = self._extract_features(volume_tensor, speed_tensor)

        # 3. Canonical week
        logger.info("Building canonical week (168 blocks)...")
        canonical_week = self._build_canonical_week(df, neural_scores)

        # 4. GMM classification
        logger.info("Applying GMM classification...")
        scores_matrix = canonical_week['neural_score'].values.reshape(-1, 1)
        self.gmm.fit(scores_matrix)
        cluster_labels = self.gmm.predict(scores_matrix)

        cluster_means = self.gmm.means_.flatten()
        peak_cluster_index = np.argmax(cluster_means)
        is_peak = (cluster_labels == peak_cluster_index)

        # 5. Export
        schedule = self._generate_schedule(canonical_week, is_peak)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schedule, f, indent=4)

        logger.info(f"Peak schedule saved to: {output_path}")
        return schedule

    def _extract_features(self, volume: torch.Tensor, speed: torch.Tensor) -> np.ndarray:
        """Chunked neural feature extraction to prevent VRAM overflow."""
        all_features = []
        total_len = volume.shape[1]

        for i in range(0, total_len, self.chunk_size):
            vol_chunk = volume[:, i:i + self.chunk_size]
            spd_chunk = speed[:, i:i + self.chunk_size]
            current_len = vol_chunk.shape[1]

            if current_len < self.chunk_size:
                pad_len = self.chunk_size - current_len
                vol_chunk = F.pad(vol_chunk, (0, pad_len), mode='constant', value=0.0)
                spd_chunk = F.pad(spd_chunk, (0, pad_len), mode='constant', value=0.0)

            with torch.no_grad():
                multivariate = torch.stack((vol_chunk, spd_chunk), dim=-1).to(self.device)
                stress = self.itransformer(multivariate)
                features = self.timesnet(stress)
                chunk_result = features.mean(dim=-1).cpu().numpy().flatten()

                if current_len < self.chunk_size:
                    chunk_result = chunk_result[:current_len]
                all_features.append(chunk_result)

            del multivariate, stress, features
            torch.cuda.empty_cache()
            gc.collect()

        return np.concatenate(all_features)

    @staticmethod
    def _build_canonical_week(df: pd.DataFrame, neural_scores: np.ndarray) -> pd.DataFrame:
        """Groups neural scores by day-of-week and hour."""
        df = df.copy()
        df['neural_score'] = neural_scores

        time_col = 'timestamp' if 'timestamp' in df.columns else 'event_timestamp'
        df[time_col] = pd.to_datetime(df[time_col])
        df['day_of_week'] = df[time_col].dt.dayofweek
        df['hour'] = df[time_col].dt.hour

        return df.groupby(['day_of_week', 'hour'])['neural_score'].mean().reset_index()

    @classmethod
    def _generate_schedule(cls, canonical_week: pd.DataFrame, predictions: np.ndarray) -> dict:
        """Formats the 168 blocks into JSON structure."""
        canonical_week['is_peak'] = predictions
        schedule = {day: {} for day in cls.DAY_MAP.values()}

        for day_name in cls.DAY_MAP.values():
            for h in range(24):
                schedule[day_name][f"{h:02d}:00"] = False

        for _, row in canonical_week.iterrows():
            day_name = cls.DAY_MAP[int(row['day_of_week'])]
            schedule[day_name][f"{int(row['hour']):02d}:00"] = bool(row['is_peak'])

        return schedule
