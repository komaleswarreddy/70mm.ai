"""Per-face identity pass: face -> character assignment, mask-confined
blending, and the masked ComfyUI graph. Pure logic -- no GPU, no detector."""
import numpy as np
from PIL import Image

from app import face_identity as fi
from app.comfy_workflow_builder import build_uso_face_workflow


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def _face(x, w, feature):
    return fi.FaceBox(x=x, y=100, w=w, h=int(w * 1.2), score=0.9, feature=_unit(feature))


def test_each_character_gets_its_own_best_matching_face():
    ram_ref, sita_ref = _unit([1, 0, 0]), _unit([0, 1, 0])
    faces = [_face(100, 120, [0.1, 1, 0]), _face(600, 110, [1, 0.1, 0])]   # SITA-like left, RAM-like right
    got = dict((n, f["x"]) for n, f in fi.assign_faces(faces, {"RAM": [ram_ref], "SITA": [sita_ref]}, ["RAM", "SITA"]))
    assert got == {"RAM": 600, "SITA": 100}


def test_two_characters_never_claim_the_same_face():
    refs = {"RAM": [_unit([1, 0, 0])], "ANWAR": [_unit([0.9, 0.1, 0])]}
    pairs = fi.assign_faces([_face(100, 120, [1, 0, 0])], refs, ["RAM", "ANWAR"])
    assert len(pairs) == 1 and pairs[0][0] == "RAM"        # focal character wins the only face


def test_no_faces_means_no_assignment():
    assert fi.assign_faces([], {"RAM": [_unit([1, 0, 0])]}, ["RAM"]) == []


def test_paste_only_changes_pixels_inside_the_head_mask():
    frame = Image.new("RGB", (1024, 640), (10, 20, 30))
    face = fi.FaceBox(x=450, y=200, w=120, h=150, score=0.9, feature=None)
    box = fi.crop_box(face, 1024, 640)
    mask = fi.head_mask(face, box)
    out = np.asarray(fi.paste_crop(frame, Image.new("RGB", (768, 768), (250, 250, 250)), box, mask))
    assert tuple(out[0, 0]) == (10, 20, 30) and tuple(out[639, 1023]) == (10, 20, 30)   # far outside
    cy, cx = face["y"] + face["h"] // 2, face["x"] + face["w"] // 2
    assert out[cy, cx].min() > 200                                                     # face centre repainted


def test_masked_face_workflow_confines_denoise_with_core_nodes():
    wf = build_uso_face_workflow("RAM face", "blurry", "crop.png", ["r1.png"], denoise=0.62, mask_filename="mask.png")
    assert wf["face_mask"]["class_type"] == "LoadImageMask"
    assert wf["masked_latent"]["class_type"] == "SetLatentNoiseMask"
    assert wf["ksampler"]["inputs"]["latent_image"] == ["masked_latent", 0]
    assert wf["ksampler"]["inputs"]["denoise"] == 0.62


def test_unmasked_face_workflow_is_unchanged():
    wf = build_uso_face_workflow("a face", "blurry", "crop.png", ["r1.png"])
    assert "masked_latent" not in wf
    assert wf["ksampler"]["inputs"]["latent_image"] == ["init_encoded", 0]


def test_stored_static_url_resolves_under_backend_root(tmp_path, monkeypatch):
    """Regression: on Windows os.path.isabs("/static/...") is True, so the
    stored reference URL resolved to the drive root and no references loaded."""
    ref = tmp_path / "static" / "character_refs" / "c_0.png"
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"x")
    monkeypatch.setattr(fi, "BACKEND_ROOT", str(tmp_path))
    import os
    assert os.path.samefile(fi.resolve_local_path("/static/character_refs/c_0.png"), ref)
    assert os.path.samefile(fi.resolve_local_path("static/character_refs/c_0.png"), ref)
