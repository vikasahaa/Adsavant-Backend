"""
ML Model Service — loads the trained pipeline and handles inference.

This module encapsulates all ML logic: feature extraction, prediction,
confidence estimation, and classification. The FastAPI routes call
this service without needing to know ML internals.
"""

import logging
import re
from typing import Optional, Tuple, List

import joblib
import numpy as np
import pandas as pd
import torch
import open_clip
import torchvision.transforms as TF
from PIL import Image, ImageStat
from textblob import TextBlob
import emoji

from app.core.config import settings


class ConfidenceEstimator:
    """Estimate prediction confidence based on proximity to training data."""

    def __init__(self, k: int = 5):
        self.k = k
        self.nn = NearestNeighbors(n_neighbors=k)
        self._fitted = False

    def fit(self, X_train_processed: np.ndarray):
        self.nn.fit(X_train_processed)
        dists, _ = self.nn.kneighbors(X_train_processed)
        self.train_mean_dists = dists.mean(axis=1)
        self._fitted = True
        return self

    def predict_confidence(self, X_processed: np.ndarray) -> List[str]:
        """Return confidence labels: High / Moderate / Low."""
        dists, _ = self.nn.kneighbors(X_processed)
        mean_dists = dists.mean(axis=1)

        p50 = np.percentile(self.train_mean_dists, 50)
        p85 = np.percentile(self.train_mean_dists, 85)

        labels = []
        for d in mean_dists:
            if d <= p50:
                labels.append("High")
            elif d <= p85:
                labels.append("Moderate")
            else:
                labels.append("Low")
        return labels

import sys
import app.ml.model_service
sys.modules['__main__'].ConfidenceEstimator = ConfidenceEstimator

logger = logging.getLogger(__name__)


class CLIPFeatureExtractor:
    """Extract image embeddings using OpenCLIP ViT-B/32 with multi-crop TTA."""

    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "laion2b_s34b_b79k",
        n_views: int = 5,
    ):
        self.n_views = n_views
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer(model_name)

        self.tta_transforms = [
            self.preprocess,
            TF.Compose([
                TF.Resize(224, interpolation=TF.InterpolationMode.BICUBIC),
                TF.CenterCrop(224),
                TF.RandomHorizontalFlip(p=1.0),
                TF.ToTensor(),
                TF.Normalize(
                    mean=(0.48145466, 0.4578275, 0.40821073),
                    std=(0.26862954, 0.26130258, 0.27577711),
                ),
            ]),
            TF.Compose([
                TF.Resize(224, interpolation=TF.InterpolationMode.BICUBIC),
                TF.CenterCrop(224),
                TF.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
                TF.ToTensor(),
                TF.Normalize(
                    mean=(0.48145466, 0.4578275, 0.40821073),
                    std=(0.26862954, 0.26130258, 0.27577711),
                ),
            ]),
            TF.Compose([
                TF.RandomResizedCrop(
                    224,
                    scale=(0.75, 1.0),
                    interpolation=TF.InterpolationMode.BICUBIC,
                ),
                TF.ToTensor(),
                TF.Normalize(
                    mean=(0.48145466, 0.4578275, 0.40821073),
                    std=(0.26862954, 0.26130258, 0.27577711),
                ),
            ]),
            TF.Compose([
                TF.RandomRotation(degrees=10),
                TF.Resize(224, interpolation=TF.InterpolationMode.BICUBIC),
                TF.CenterCrop(224),
                TF.ToTensor(),
                TF.Normalize(
                    mean=(0.48145466, 0.4578275, 0.40821073),
                    std=(0.26862954, 0.26130258, 0.27577711),
                ),
            ]),
        ]

    @torch.no_grad()
    def extract_single(self, image: Image.Image, use_tta: bool = True) -> np.ndarray:
        """Extract CLIP embedding, optionally averaging over TTA views."""
        if use_tta:
            embeddings = []
            for transform in self.tta_transforms[: self.n_views]:
                tensor = transform(image).unsqueeze(0)
                features = self.model.encode_image(tensor)
                features = features / features.norm(dim=-1, keepdim=True)
                embeddings.append(features.squeeze().numpy())
            return np.mean(embeddings, axis=0)
        else:
            tensor = self.preprocess(image).unsqueeze(0)
            features = self.model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)
            return features.squeeze().numpy()

    @torch.no_grad()
    def image_caption_similarity(self, image: Image.Image, caption: str) -> float:
        """Compute CLIP cosine similarity between image and caption."""
        img_tensor = self.preprocess(image).unsqueeze(0)
        text_tokens = self.tokenizer([caption])

        img_features = self.model.encode_image(img_tensor)
        text_features = self.model.encode_text(text_tokens)

        img_features = img_features / img_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        similarity = (img_features @ text_features.T).item()
        return float(similarity)


class TextFeatureExtractor:
    """Extract NLP features from Instagram captions."""

    CTA_PATTERNS = [
        r"\bshop\b", r"\bbuy\b", r"\blink in bio\b", r"\bavailable\b",
        r"\border\b", r"\bget yours\b", r"\blimited\b", r"\bnow live\b",
        r"\brestocking\b", r"\bdm\b", r"\bswipe\b", r"\btap\b",
    ]

    @classmethod
    def extract(cls, caption: str) -> dict:
        """Extract all text features from a single caption string."""
        text = caption or ""
        blob = TextBlob(text) if text.strip() else None

        return {
            "caption_length": len(text),
            "word_count": len(text.split()),
            "hashtag_count": len(re.findall(r"#\w+", text)),
            "mention_count": len(re.findall(r"@\w+", text)),
            "emoji_count": emoji.emoji_count(text),
            "cta_count": sum(
                1 for p in cls.CTA_PATTERNS if re.search(p, text.lower())
            ),
            "newline_count": text.count("\n"),
            "has_question": int("?" in text),
            "exclamation_count": text.count("!"),
            "sentiment_polarity": blob.sentiment.polarity if blob else 0.0,
            "sentiment_subjectivity": blob.sentiment.subjectivity if blob else 0.0,
        }


class ModelService:
    """Orchestrates the full prediction pipeline.

    Loaded once at application startup via the FastAPI lifespan.
    Thread-safe for concurrent requests (all state is read-only after load).
    """

    def __init__(self):
        self._artifacts = None
        self._clip_extractor = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, model_path: str) -> None:
        """Load all model artifacts from the serialized .pkl file."""
        logger.info(f"Loading model from {model_path}")
        self._artifacts = joblib.load(model_path)

        cfg = self._artifacts["config"]
        logger.info(f"Model config: {cfg}")

        # Initialize CLIP extractor
        self._clip_extractor = CLIPFeatureExtractor(
            model_name=cfg.get("clip_model", settings.CLIP_MODEL),
            pretrained=cfg.get("clip_pretrained", settings.CLIP_PRETRAINED),
            n_views=cfg.get("n_augment_views", settings.N_AUGMENT_VIEWS),
        )

        self._loaded = True
        logger.info("All artifacts loaded.")

    def _extract_image_features(
        self, image: Optional[Image.Image], caption: str
    ) -> dict:
        """Extract all image-derived features (CLIP + metadata)."""
        cfg = self._artifacts["config"]
        n_components = cfg.get("image_pca_components", 0)

        if image is not None and cfg.get("use_image_features", False):
            # CLIP embedding with TTA
            clip_emb = self._clip_extractor.extract_single(image, use_tta=True)
            clip_pca = self._artifacts["image_pca"].transform(
                clip_emb.reshape(1, -1)
            )

            features = {
                f"img_pca_{i}": float(clip_pca[0, i]) for i in range(n_components)
            }

            # Image-caption similarity
            features["clip_similarity"] = self._clip_extractor.image_caption_similarity(
                image, caption
            )

            # Image metadata
            stat = ImageStat.Stat(image)
            features["img_brightness"] = sum(stat.mean[:3]) / 3 / 255
            features["img_contrast"] = sum(stat.stddev[:3]) / 3 / 255
            features["img_colorfulness"] = (
                max(stat.mean[:3]) - min(stat.mean[:3])
            ) / 255
            features["img_aspect_ratio"] = image.width / image.height
            features["img_is_square"] = int(abs(image.width - image.height) < 20)
            features["img_dominant_warm"] = int(stat.mean[0] > stat.mean[2])
        else:
            features = {f"img_pca_{i}": 0.0 for i in range(n_components)}
            features.update({
                "clip_similarity": 0.0,
                "img_brightness": 0.0,
                "img_contrast": 0.0,
                "img_colorfulness": 0.0,
                "img_aspect_ratio": 1.0,
                "img_is_square": 1,
                "img_dominant_warm": 0,
            })

        return features

    def _build_feature_row(
        self,
        caption: str,
        brand_type: str,
        followers: int,
        image: Optional[Image.Image] = None,
    ) -> pd.DataFrame:
        """Assemble the full feature vector for a single prediction."""
        cfg = self._artifacts["config"]

        # Text features
        text_feats = TextFeatureExtractor.extract(caption)

        # Metadata features
        log_followers = float(np.log1p(followers))
        follower_tier = (
            "nano" if followers <= 5000
            else "micro" if followers <= 20000
            else "small" if followers <= 80000
            else "medium" if followers <= 150000
            else "large"
        )

        # Image features
        img_feats = self._extract_image_features(image, caption)

        # Combine
        feature_row = {
            **text_feats,
            "log_followers": log_followers,
            "brand_type": brand_type.lower().strip(),
            "follower_tier": follower_tier,
            **img_feats,
        }

        return pd.DataFrame([feature_row])[cfg["feature_order"]]

    @staticmethod
    def classify_engagement(er: float) -> str:
        """Map engagement rate to category."""
        if er >= settings.ER_HIGH_THRESHOLD:
            return "High"
        elif er >= settings.ER_AVG_THRESHOLD:
            return "Average"
        return "Low"

    def predict(
        self,
        caption: str,
        brand_type: str,
        followers: int,
        image: Optional[Image.Image] = None,
    ) -> dict:
        """Run the full dual-head prediction pipeline.

        Returns:
            dict with predicted_er, regression_classification,
            direct_classification, confidence, and feature_summary.
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        cfg = self._artifacts["config"]
        input_df = self._build_feature_row(caption, brand_type, followers, image)

        # --- Regression head ---
        reg_model = self._artifacts["reg_model"]
        reg_prediction = reg_model.predict(input_df)[0]
        if cfg.get("log_transform_target", True):
            predicted_er = float(np.expm1(reg_prediction))
        else:
            predicted_er = float(reg_prediction)
        predicted_er = max(0.0, predicted_er)

        reg_class = self.classify_engagement(predicted_er)

        # --- Classification head ---
        clf_model = self._artifacts.get("clf_model")
        le = self._artifacts.get("label_encoder")
        if clf_model is not None and le is not None:
            clf_prediction = clf_model.predict(input_df)[0]
            direct_class = le.inverse_transform([clf_prediction])[0]
        else:
            direct_class = reg_class  # Fallback if classifier not available

        # --- Confidence ---
        confidence_est = self._artifacts.get("confidence_estimator")
        if confidence_est is not None:
            try:
                preprocessor = reg_model.named_steps["preprocessor"]
                processed = preprocessor.transform(input_df)
                confidence_labels = confidence_est.predict_confidence(processed)
                confidence = confidence_labels[0]
            except Exception:
                confidence = "Moderate"
        else:
            confidence = "Moderate"

        # --- Feature summary for transparency ---
        text_feats = TextFeatureExtractor.extract(caption)
        feature_summary = {
            "caption_length": text_feats["caption_length"],
            "word_count": text_feats["word_count"],
            "hashtag_count": text_feats["hashtag_count"],
            "emoji_count": text_feats["emoji_count"],
            "cta_keywords_found": text_feats["cta_count"],
            "sentiment": round(text_feats["sentiment_polarity"], 3),
            "followers": followers,
            "image_provided": image is not None,
        }

        if image is not None:
            img_feats = self._extract_image_features(image, caption)
            feature_summary["clip_similarity"] = round(
                img_feats.get("clip_similarity", 0.0), 3
            )
            feature_summary["image_brightness"] = round(
                img_feats.get("img_brightness", 0.0), 3
            )

        return {
            "predicted_engagement_rate": round(predicted_er, 4),
            "regression_classification": reg_class,
            "direct_classification": direct_class,
            "confidence": confidence,
            "feature_summary": feature_summary,
        }
