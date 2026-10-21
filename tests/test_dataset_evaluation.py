"""Owned procedural CAD verifies evaluation mechanics, never industrial accuracy."""
import hashlib
import json
import subprocess
import pytest
from backend.evaluate_dataset import LABELS, run_evaluation, summarize


def row(label):
    return [1.0 if key == label else 0.0 for key in LABELS]


def test_metrics_have_hand_checked_error_and_calibration_values():
    result = summarize(['Planar', 'Cylindrical'], ['Planar', 'Planar'], [row('Planar'), row('Planar')])
    assert result['accuracy'] == .5 and result['macro_f1_observed'] == pytest.approx(1 / 3)
    assert result['ece_10_bins'] == .5 and result['multiclass_brier'] == 1
    assert result['confusion']['Cylindrical']['Planar'] == 1
    assert result['per_class']['Other']['f1'] is None
    assert result['calibration_bins'][-1]['count'] == 2
    assert result['calibration_bins'][0]['accuracy'] is None
    assert sum(part['count'] for part in result['calibration_bins']) == 2


@pytest.mark.parametrize('probabilities', [[], [[float('nan')] * 6], [[.1] * 6], [[-1, 2, 0, 0, 0, 0]]])
def test_invalid_probability_evidence_is_rejected(probabilities):
    with pytest.raises(ValueError):
        summarize(['Planar'], ['Planar'], probabilities)


def corpus(tmp_path):
    import cadquery as cq
    shape = cq.Solid.makeCylinder(5, 10)
    path = tmp_path / 'owned.step'
    cq.exporters.export(shape, str(path))
    labels = {'PLANE': 'Planar', 'CYLINDER': 'Cylindrical'}
    fixture = {'schema_version': 1, 'name': 'owned procedural unit fixture only', 'source': 'unit test', 'license': 'MIT',
               'rights_evidence': 'generated fixture', 'evaluation_only': True,
               'parts': [{'path': 'owned.step', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'group': 'owned',
                          'faces': [{'face_id': i, 'label': labels[face.geomType()]} for i, face in enumerate(shape.Faces())]}]}
    manifest = tmp_path / 'dataset.json'
    manifest.write_text(json.dumps(fixture))
    return manifest, shape


def test_real_isolated_evaluation_matches_face_counts_and_provenance(tmp_path, monkeypatch):
    manifest, shape = corpus(tmp_path)
    active = tmp_path / 'active'
    active.mkdir()
    monkeypatch.setenv('SHAPEOPS_DATA_DIR', str(active))
    monkeypatch.setenv('SHAPEOPS_REPORT_DIR', str(active))
    output = tmp_path / 'evaluation.json'
    report = run_evaluation(manifest, output)
    assert report == json.loads(output.read_text())
    assert report['manifest_sha256'] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert len(report['evaluation_source_sha256']) == 64
    assert len(report['models']) == 2
    for model in report['models']:
        metrics = model['metrics']
        assert metrics['observations'] == len(shape.Faces())
        assert sum(sum(row.values()) for row in metrics['confusion'].values()) == len(shape.Faces())
        assert 0 <= metrics['accuracy'] <= 1 and 0 <= metrics['ece_10_bins'] <= 1
        assert model['model']['gates']['security'] is False
        assert len(model['model']['package_id']) == 64
    assert list(active.iterdir()) == []
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        run_evaluation(manifest, output)
    assert output.read_bytes() == before


def test_evaluation_timeout_never_publishes_success_report(tmp_path):
    manifest, _ = corpus(tmp_path)
    output = tmp_path / 'report.json'
    with pytest.raises(subprocess.TimeoutExpired):
        run_evaluation(manifest, output, timeout=.001)
    assert not output.exists()
