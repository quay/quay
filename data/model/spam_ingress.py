import hashlib
import json
import logging
import math
import os
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_INGRESS_THRESHOLD = 0.9
DEFAULT_TOKEN_PATTERN = r"[a-z0-9][a-z0-9_-]*"
DEFAULT_CLASSIFICATION_WINDOW_TOKENS = 128
DEFAULT_CLASSIFICATION_WINDOW_STRIDE = 64
MAX_CLASSIFICATION_WINDOW_TOKENS = 4096
HYPERLINK_PATTERN = re.compile(r"\bhttps?://[^\s<>()]+", re.IGNORECASE)
REQUIRED_ARTIFACT_FIELDS = {
    "version": str,
    "training_corpus_version": str,
    "spam_prior": (int, float),
    "ham_prior": (int, float),
    "token_spam_counts": dict,
    "token_ham_counts": dict,
    "spam_token_total": (int, float),
    "ham_token_total": (int, float),
    "vocabulary_size": (int, float),
    "smoothing": (int, float),
    "ingress_threshold": (int, float),
    "ingress_thresholds": dict,
    "feature_config": dict,
    "training_metrics": dict,
}
ARTIFACT_INTEGER_FIELDS = ("spam_token_total", "ham_token_total", "vocabulary_size")


class SpamIngressUnavailable(Exception):
    """
    Raised when the local classifier cannot be loaded or evaluated.
    """


@dataclass(frozen=True)
class SpamIngressContext:
    namespace: str
    repository: str
    description: str
    visibility: Optional[str] = None
    action: Optional[str] = None


@dataclass(frozen=True)
class SpamIngressDecision:
    allowed: bool
    score: Optional[float] = None
    reason: Optional[str] = None
    classifier_version: Optional[str] = None


class BayesianSpamClassifier:
    def __init__(self, artifact):
        _validate_artifact_schema(artifact)
        self._artifact = artifact
        self.version = artifact.get("version")
        self._spam_counts = artifact.get("token_spam_counts") or {}
        self._ham_counts = artifact.get("token_ham_counts") or {}
        self._spam_total = int(artifact["spam_token_total"])
        self._ham_total = int(artifact["ham_token_total"])
        self._vocabulary_size = int(artifact["vocabulary_size"])
        self._smoothing = float(artifact.get("smoothing", 1.0))
        self._spam_prior = float(artifact.get("spam_prior", 0.5))
        self._ham_prior = float(artifact.get("ham_prior", 0.5))
        self._threshold = float(artifact.get("ingress_threshold", DEFAULT_INGRESS_THRESHOLD))
        self._thresholds = artifact.get("ingress_thresholds") or {}
        feature_config = artifact.get("feature_config") or {}
        token_pattern = feature_config.get("token_pattern", DEFAULT_TOKEN_PATTERN)
        if token_pattern != DEFAULT_TOKEN_PATTERN:
            raise SpamIngressUnavailable("Custom spam classifier token patterns are not supported")
        self._token_pattern = re.compile(token_pattern, re.IGNORECASE)
        self._include_repository_name = feature_config.get("include_repository_name", False)
        self._window_tokens = _feature_config_int(
            feature_config,
            "classification_window_tokens",
            DEFAULT_CLASSIFICATION_WINDOW_TOKENS,
        )
        self._window_stride = _feature_config_int(
            feature_config,
            "classification_window_stride",
            DEFAULT_CLASSIFICATION_WINDOW_STRIDE,
        )
        if self._window_tokens > MAX_CLASSIFICATION_WINDOW_TOKENS:
            raise SpamIngressUnavailable(
                f"classification_window_tokens must be {MAX_CLASSIFICATION_WINDOW_TOKENS} or fewer"
            )
        if self._window_stride > self._window_tokens:
            raise SpamIngressUnavailable(
                "classification_window_stride must not exceed classification_window_tokens"
            )

        if self._spam_total is None:
            self._spam_total = sum(self._spam_counts.values())
        if self._ham_total is None:
            self._ham_total = sum(self._ham_counts.values())
        if self._vocabulary_size is None:
            self._vocabulary_size = len(set(self._spam_counts) | set(self._ham_counts)) or 1

        if self._spam_prior <= 0 or self._ham_prior <= 0:
            raise SpamIngressUnavailable("Classifier priors must be greater than zero")
        if self._smoothing <= 0:
            raise SpamIngressUnavailable("Classifier smoothing must be greater than zero")

    def classify(self, context):
        tokens = self._tokens(context)
        spam_score = max(
            self._posterior_spam_probability(window)
            for _, window in self._classification_windows(tokens)
        )
        threshold = self._threshold_for_visibility(context.visibility)
        allowed = spam_score < threshold

        return SpamIngressDecision(
            allowed=allowed,
            score=spam_score,
            reason="score_below_threshold" if allowed else "score_exceeded_threshold",
            classifier_version=self.version,
        )

    def _tokens(self, context):
        text = context.description or ""
        if self._include_repository_name:
            text = " ".join([text, context.repository or ""])
        return [match.group(0).lower() for match in self._token_pattern.finditer(text)]

    def _posterior_spam_probability(self, tokens):
        log_spam = math.log(self._spam_prior)
        log_ham = math.log(self._ham_prior)
        spam_denominator = self._spam_total + self._smoothing * self._vocabulary_size
        ham_denominator = self._ham_total + self._smoothing * self._vocabulary_size

        for token in tokens:
            spam_count = self._spam_counts.get(token, 0)
            ham_count = self._ham_counts.get(token, 0)
            log_spam += math.log((spam_count + self._smoothing) / spam_denominator)
            log_ham += math.log((ham_count + self._smoothing) / ham_denominator)

        if log_spam >= log_ham:
            return 1 / (1 + math.exp(log_ham - log_spam))
        return math.exp(log_spam - log_ham) / (1 + math.exp(log_spam - log_ham))

    def _classification_windows(self, tokens):
        if len(tokens) <= self._window_tokens:
            return [(0, tokens)]

        last_start = len(tokens) - self._window_tokens
        starts = list(range(0, last_start + 1, self._window_stride))
        if starts[-1] != last_start:
            starts.append(last_start)
        return [(start, tokens[start : start + self._window_tokens]) for start in starts]

    def _threshold_for_visibility(self, visibility):
        if visibility and visibility in self._thresholds:
            return float(self._thresholds[visibility])
        return self._threshold


def _validate_artifact_schema(artifact):
    for field, expected_type in REQUIRED_ARTIFACT_FIELDS.items():
        if field not in artifact:
            raise SpamIngressUnavailable(
                f"Spam classifier artifact missing required field: {field}"
            )
        if not isinstance(artifact[field], expected_type):
            raise SpamIngressUnavailable(
                f"Spam classifier artifact field has invalid type: {field}"
            )

    for field in ARTIFACT_INTEGER_FIELDS:
        value = artifact[field]
        if isinstance(value, bool) or (
            isinstance(value, float) and (not math.isfinite(value) or not value.is_integer())
        ):
            raise SpamIngressUnavailable(
                f"Spam classifier artifact field must be an integer: {field}"
            )

    if artifact["spam_token_total"] < 0 or artifact["ham_token_total"] < 0:
        raise SpamIngressUnavailable("Classifier token totals must be non-negative")
    if artifact["vocabulary_size"] <= 0:
        raise SpamIngressUnavailable("Classifier vocabulary size must be greater than zero")


def _feature_config_int(feature_config, field, default):
    value = feature_config.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SpamIngressUnavailable(f"{field} must be a positive integer")
    return value


_CLASSIFIER_CACHE: Dict[Tuple[str, int, int], BayesianSpamClassifier] = {}


def clear_classifier_cache():
    _CLASSIFIER_CACHE.clear()


def evaluate_description(context, config):
    if not HYPERLINK_PATTERN.search(context.description or ""):
        return SpamIngressDecision(
            allowed=True,
            reason="hyperlink_required",
        )
    classifier = _get_classifier(config)
    return classifier.classify(context)


def _get_classifier(config):
    path = config.get("SPAM_DETECTION_CLASSIFIER_PATH")
    if not path:
        raise SpamIngressUnavailable("SPAM_DETECTION_CLASSIFIER_PATH is not configured")

    try:
        stat = os.stat(path)
    except OSError as exc:
        raise SpamIngressUnavailable("Unable to read spam classifier artifact") from exc

    cache_key = (path, stat.st_mtime_ns, stat.st_size)
    cached = _CLASSIFIER_CACHE.get(cache_key)
    if cached is not None:
        return cached

    artifact_bytes = _read_and_verify_artifact(path, config)
    try:
        artifact = json.loads(artifact_bytes.decode("utf-8"))
        if not isinstance(artifact, dict):
            raise SpamIngressUnavailable("Spam classifier artifact must be a JSON object")
        classifier = BayesianSpamClassifier(artifact)
    except (TypeError, ValueError, re.error) as exc:
        raise SpamIngressUnavailable("Invalid spam classifier artifact") from exc

    expected_version = config.get("SPAM_DETECTION_CLASSIFIER_VERSION")
    if expected_version and classifier.version != expected_version:
        raise SpamIngressUnavailable("Spam classifier artifact version mismatch")

    _CLASSIFIER_CACHE.clear()
    _CLASSIFIER_CACHE[cache_key] = classifier
    return classifier


def _read_and_verify_artifact(path, config):
    try:
        with open(path, "rb") as artifact_file:
            artifact_bytes = artifact_file.read()
    except OSError as exc:
        raise SpamIngressUnavailable("Unable to read spam classifier artifact") from exc

    expected_sha256 = config.get("SPAM_DETECTION_CLASSIFIER_SHA256")
    if expected_sha256:
        actual_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
        if actual_sha256.lower() != expected_sha256.lower():
            raise SpamIngressUnavailable("Spam classifier artifact checksum mismatch")

    return artifact_bytes
