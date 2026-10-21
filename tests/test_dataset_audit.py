"""Owned procedural fixtures exercise corpus input audit, not industrial evaluation."""
import hashlib
import json
import os
import pytest
from pydantic import ValidationError
from backend.dataset_audit import audit_dataset, load_dataset, read_regular


def fixture(tmp_path, data=b'unit fixture; not actual CAD'):
    part = tmp_path / 'owned.step'
    part.write_bytes(data)
    payload = {'schema_version': 1, 'name': 'explicit owned unit fixture', 'source': 'unit test',
               'license': 'MIT', 'rights_evidence': 'generated within unit test', 'evaluation_only': True,
               'parts': [{'path': 'owned.step', 'sha256': hashlib.sha256(data).hexdigest(),
                          'group': 'owned-group', 'faces': [{'face_id': 0, 'label': 'Planar'}]}]}
    manifest = tmp_path / 'dataset.json'
    manifest.write_text(json.dumps(payload))
    return manifest, payload


def test_actual_step_audit_preserves_original_face_annotations(tmp_path):
    import cadquery as cq
    shape = cq.Solid.makeCylinder(5, 10)
    step = tmp_path / 'owned.step'
    cq.exporters.export(shape, str(step))
    manifest, payload = fixture(tmp_path, step.read_bytes())
    labels = {'PLANE': 'Planar', 'CYLINDER': 'Cylindrical'}
    payload['parts'][0]['faces'] = [{'face_id': i, 'label': labels[face.geomType()]} for i, face in enumerate(shape.Faces())]
    manifest.write_text(json.dumps(payload))
    report = audit_dataset(manifest)
    assert report['total_faces'] == len(shape.Faces())
    assert report['parts'][0]['sha256'] == payload['parts'][0]['sha256']
    assert report['manifest_sha256'] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    payload['parts'][0]['faces'].pop()
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='parsed face IDs'):
        audit_dataset(manifest)


@pytest.mark.parametrize('field,value', [('path', '../escape.step'), ('path', '/absolute.step'), ('path', 'part.obj'),
                                         ('sha256', 'invalid'), ('faces', [{'face_id': 1, 'label': 'Planar'}])])
def test_invalid_part_contract(tmp_path, field, value):
    manifest, payload = fixture(tmp_path)
    payload['parts'][0][field] = value
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValidationError):
        load_dataset(manifest)


def test_rights_evaluation_scope_and_duplicate_content_are_required(tmp_path):
    manifest, payload = fixture(tmp_path)
    for field, value in [('rights_evidence', ''), ('evaluation_only', False), ('parts', payload['parts'] * 2)]:
        invalid = {**payload, field: value}
        manifest.write_text(json.dumps(invalid))
        with pytest.raises(ValidationError):
            load_dataset(manifest)


def test_checksum_mismatch_is_rejected_before_cad_parsing(tmp_path):
    manifest, _ = fixture(tmp_path)
    (tmp_path / 'owned.step').write_bytes(b'changed fixture')
    with pytest.raises(ValueError, match='checksum'):
        audit_dataset(manifest)


def test_symlink_parent_and_fifo_inputs_are_rejected_without_blocking(tmp_path):
    manifest, payload = fixture(tmp_path)
    external = tmp_path / 'actual'
    external.mkdir()
    (external / 'owned.step').write_bytes(b'fixture')
    (tmp_path / 'alias').symlink_to(external, target_is_directory=True)
    payload['parts'][0]['path'] = 'alias/owned.step'
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='symlink'):
        audit_dataset(manifest)
    fifo = tmp_path / 'fifo'
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match='regular'):
        read_regular(fifo, 10)


def test_input_and_aggregate_budgets(tmp_path, monkeypatch):
    import backend.dataset_audit as audit
    manifest, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match='byte budget'):
        read_regular(manifest, 1)
    monkeypatch.setattr(audit, 'MAX_TOTAL_BYTES', 1)
    with pytest.raises(ValueError, match='aggregate'):
        audit_dataset(manifest)
