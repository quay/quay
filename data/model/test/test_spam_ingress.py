import hashlib
import json

import pytest

from data.model import spam_ingress


def _artifact(**overrides):
    artifact = {
        "version": "test-v1",
        "training_corpus_version": "2-test",
        "spam_prior": 0.5,
        "ham_prior": 0.5,
        "token_spam_counts": {"casino": 100},
        "token_ham_counts": {"project": 100},
        "spam_token_total": 100,
        "ham_token_total": 100,
        "vocabulary_size": 2,
        "smoothing": 1.0,
        "ingress_threshold": 0.9,
        "ingress_thresholds": {"public": 0.9, "private": 0.98},
        "feature_config": {
            "token_pattern": spam_ingress.DEFAULT_TOKEN_PATTERN,
            "include_repository_name": False,
        },
        "training_metrics": {
            "example_count": 2,
            "spam_examples": 1,
            "ham_examples": 1,
            "validation_status": "not_available",
        },
    }
    artifact.update(overrides)
    return artifact


def _write_artifact(tmp_path, artifact):
    artifact_path = tmp_path / "classifier.json"
    artifact_bytes = json.dumps(artifact).encode("utf-8")
    artifact_path.write_bytes(artifact_bytes)
    return artifact_path, hashlib.sha256(artifact_bytes).hexdigest()


def test_bayesian_classifier_rejects_matching_spam_artifact(tmp_path):
    spam_ingress.clear_classifier_cache()
    artifact_path, artifact_sha = _write_artifact(
        tmp_path,
        _artifact(),
    )
    context = spam_ingress.SpamIngressContext(
        namespace="devtable",
        repository="spamrepo",
        description="casino casino bonus",
        visibility="public",
        action="create",
    )

    decision = spam_ingress.evaluate_description(
        context,
        {
            "SPAM_DETECTION_CLASSIFIER_PATH": str(artifact_path),
            "SPAM_DETECTION_CLASSIFIER_VERSION": "test-v1",
            "SPAM_DETECTION_CLASSIFIER_SHA256": artifact_sha,
        },
    )

    assert not decision.allowed
    assert decision.score > 0.9
    assert decision.classifier_version == "test-v1"


def test_classifier_version_mismatch_raises_unavailable(tmp_path):
    spam_ingress.clear_classifier_cache()
    artifact_path, artifact_sha = _write_artifact(
        tmp_path,
        _artifact(),
    )
    context = spam_ingress.SpamIngressContext(
        namespace="devtable",
        repository="spamrepo",
        description="casino",
    )

    with pytest.raises(spam_ingress.SpamIngressUnavailable):
        spam_ingress.evaluate_description(
            context,
            {
                "SPAM_DETECTION_CLASSIFIER_PATH": str(artifact_path),
                "SPAM_DETECTION_CLASSIFIER_VERSION": "other-version",
                "SPAM_DETECTION_CLASSIFIER_SHA256": artifact_sha,
            },
        )


def test_classifier_checksum_mismatch_raises_unavailable(tmp_path):
    spam_ingress.clear_classifier_cache()
    artifact_path, _ = _write_artifact(
        tmp_path,
        _artifact(),
    )
    context = spam_ingress.SpamIngressContext(
        namespace="devtable",
        repository="spamrepo",
        description="casino",
    )

    with pytest.raises(spam_ingress.SpamIngressUnavailable):
        spam_ingress.evaluate_description(
            context,
            {
                "SPAM_DETECTION_CLASSIFIER_PATH": str(artifact_path),
                "SPAM_DETECTION_CLASSIFIER_SHA256": "0" * 64,
            },
        )


def test_custom_token_pattern_raises_unavailable(tmp_path):
    spam_ingress.clear_classifier_cache()
    artifact_path, artifact_sha = _write_artifact(
        tmp_path,
        _artifact(feature_config={"token_pattern": "(a+)+", "include_repository_name": False}),
    )
    context = spam_ingress.SpamIngressContext(
        namespace="devtable",
        repository="spamrepo",
        description="casino",
    )

    with pytest.raises(spam_ingress.SpamIngressUnavailable):
        spam_ingress.evaluate_description(
            context,
            {
                "SPAM_DETECTION_CLASSIFIER_PATH": str(artifact_path),
                "SPAM_DETECTION_CLASSIFIER_SHA256": artifact_sha,
            },
        )


def test_missing_required_artifact_field_raises_unavailable(tmp_path):
    spam_ingress.clear_classifier_cache()
    artifact = _artifact()
    del artifact["training_corpus_version"]
    artifact_path, artifact_sha = _write_artifact(tmp_path, artifact)
    context = spam_ingress.SpamIngressContext(
        namespace="devtable",
        repository="spamrepo",
        description="casino",
    )

    with pytest.raises(spam_ingress.SpamIngressUnavailable):
        spam_ingress.evaluate_description(
            context,
            {
                "SPAM_DETECTION_CLASSIFIER_PATH": str(artifact_path),
                "SPAM_DETECTION_CLASSIFIER_SHA256": artifact_sha,
            },
        )
