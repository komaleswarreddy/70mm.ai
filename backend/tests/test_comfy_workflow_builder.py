from app.comfy_workflow_builder import build_flux_workflow, USO_MAX_REFERENCE_IMAGES


def test_plain_workflow_has_no_character_nodes():
    wf = build_flux_workflow("a quiet street at dusk", "blurry", consistency_params=None)
    assert "unet_loader" in wf
    assert wf["ksampler"]["inputs"]["model"] == ["unet_loader", 0]
    assert wf["ksampler"]["inputs"]["positive"] == ["flux_guidance", 0]
    assert "checkpoint_loader" not in wf
    assert "multiref_method" not in wf


def test_plain_workflow_with_controlnet_wraps_conditioning():
    wf = build_flux_workflow(
        "close-up", "blurry", consistency_params=None, controlnet_image_path="/static/refs/pose.png",
    )
    assert wf["controlnet_apply"]["inputs"]["positive"] == ["flux_guidance", 0]
    assert wf["ksampler"]["inputs"]["positive"] == ["controlnet_apply", 0]
    assert wf["ksampler"]["inputs"]["negative"] == ["controlnet_apply", 1]


def test_uso_workflow_single_character():
    params = {
        "engine": "USO", "characters": ["Vasanth"],
        "identities": [{"name": "Vasanth", "reference_image_paths": ["/static/character_refs/c1_0.png"]}],
    }
    wf = build_flux_workflow("two-shot", "blurry", consistency_params=params)

    # Standard core nodes only -- no third-party custom node class_type.
    assert wf["checkpoint_loader"]["class_type"] == "CheckpointLoaderSimple"
    assert wf["lora_loader"]["class_type"] == "LoraLoaderModelOnly"
    assert wf["lora_loader"]["inputs"]["model"] == ["checkpoint_loader", 0]

    # One reference image -> one chained ReferenceLatent call off the text conditioning.
    assert wf["uso_ref_load_1"]["inputs"]["image"] == "/static/character_refs/c1_0.png"
    assert wf["uso_ref_encode_1"]["inputs"]["pixels"] == ["uso_ref_scale_1", 0]
    assert wf["uso_ref_cond_1"]["inputs"]["conditioning"] == ["positive_text", 0]
    assert wf["uso_ref_cond_1"]["inputs"]["latent"] == ["uso_ref_encode_1", 0]

    # Multi-reference combination method is applied once, after the chain.
    assert wf["multiref_method"]["inputs"]["conditioning"] == ["uso_ref_cond_1", 0]
    assert wf["multiref_method"]["inputs"]["reference_latents_method"] == "uxo/uno"
    assert wf["flux_guidance"]["inputs"]["conditioning"] == ["multiref_method", 0]

    # KSampler runs on the LoRA-patched model, not the raw checkpoint model.
    assert wf["ksampler"]["inputs"]["model"] == ["lora_loader", 0]
    # Negative prompt is a REAL CLIPTextEncode node (not ConditioningZeroOut)
    # -- regression test for the confirmed bug where NEGATIVE_PROMPT_BASE
    # never reached the USO graph at all.
    assert wf["ksampler"]["inputs"]["negative"] == ["negative_text", 0]
    assert wf["negative_text"]["class_type"] == "CLIPTextEncode"
    assert wf["negative_text"]["inputs"]["text"] == "blurry"


def test_uso_workflow_negative_prompt_is_second_cliptextencode_node():
    """comfy_client.generate_image() finds the negative node by scanning for
    the SECOND CLIPTextEncode node in insertion order -- confirm that still
    holds after adding a real negative-text node to this graph."""
    params = {
        "engine": "USO", "characters": ["Vasanth"],
        "identities": [{"name": "Vasanth", "reference_image_paths": ["/static/character_refs/c1_0.png"]}],
    }
    wf = build_flux_workflow("two-shot", "blurry, cartoon", consistency_params=params)
    clip_text_nodes = [nid for nid, node in wf.items() if node["class_type"] == "CLIPTextEncode"]
    assert clip_text_nodes == ["positive_text", "negative_text"]


def test_uso_workflow_multi_character_chains_references_in_order():
    params = {
        "engine": "USO", "characters": ["Vasanth", "Rukhmika"],
        "identities": [
            {"name": "Vasanth", "reference_image_paths": ["/static/refs/vasanth_1.png"]},
            {"name": "Rukhmika", "reference_image_paths": ["/static/refs/rukhmika_1.png"]},
        ],
    }
    wf = build_flux_workflow("two-shot", "", consistency_params=params)

    # Second reference chains off the first, not off the raw text conditioning.
    assert wf["uso_ref_cond_1"]["inputs"]["conditioning"] == ["positive_text", 0]
    assert wf["uso_ref_cond_2"]["inputs"]["conditioning"] == ["uso_ref_cond_1", 0]
    assert wf["multiref_method"]["inputs"]["conditioning"] == ["uso_ref_cond_2", 0]


def test_uso_workflow_pools_and_caps_reference_images():
    identities = [
        {"name": f"Char{i}", "reference_image_paths": [f"/static/refs/char{i}.png"]}
        for i in range(USO_MAX_REFERENCE_IMAGES + 2)
    ]
    params = {"engine": "USO", "characters": [c["name"] for c in identities], "identities": identities}
    wf = build_flux_workflow("crowd shot", "", consistency_params=params)

    assert f"uso_ref_load_{USO_MAX_REFERENCE_IMAGES}" in wf
    assert f"uso_ref_load_{USO_MAX_REFERENCE_IMAGES + 1}" not in wf


def test_uso_workflow_with_no_reference_images_skips_multiref_method():
    # Defensive case -- compile_consistency_params always requires locked
    # (and therefore reference-image-bearing) characters in practice, but
    # the builder itself shouldn't emit a reference-conditioning node chain
    # with nothing to condition on.
    params = {"engine": "USO", "characters": ["Vasanth"], "identities": [{"name": "Vasanth", "reference_image_paths": []}]}
    wf = build_flux_workflow("two-shot", "", consistency_params=params)
    assert "multiref_method" not in wf
    assert wf["flux_guidance"]["inputs"]["conditioning"] == ["positive_text", 0]


# ── Two-pass generation graphs ─────────────────────────────────────────────
from app.comfy_workflow_builder import build_img2img_refine_workflow, build_uso_face_workflow


def test_refine_workflow_is_img2img_with_no_reference_conditioning():
    """The refinement pass must not be able to change composition -- so it runs
    on the plain graph and starts from the encoded init image, not empty noise."""
    wf = build_img2img_refine_workflow("a frame", "blurry", "init.png", denoise=0.4)
    assert wf["ksampler"]["inputs"]["latent_image"] == ["init_encoded", 0]
    assert wf["ksampler"]["inputs"]["denoise"] == 0.4
    assert wf["init_image"]["inputs"]["image"] == "init.png"
    assert not any("ref" in node_id for node_id in wf)
    assert "checkpoint_loader" not in wf          # plain path, not the USO bundle

def test_face_workflow_conditions_a_crop_on_references():
    wf = build_uso_face_workflow("RAM face", "blurry", "crop.png", ["r1.png", "r2.png"], denoise=0.55)
    assert wf["ksampler"]["inputs"]["latent_image"] == ["init_encoded", 0]
    assert wf["ksampler"]["inputs"]["denoise"] == 0.55
    # references chain in order, then combine once
    assert wf["face_ref_cond_1"]["inputs"]["conditioning"] == ["positive_text", 0]
    assert wf["face_ref_cond_2"]["inputs"]["conditioning"] == ["face_ref_cond_1", 0]
    assert wf["multiref_method"]["inputs"]["reference_latents_method"] == "uxo/uno"
    # real negative text encode, not ConditioningZeroOut
    assert wf["negative_text"]["class_type"] == "CLIPTextEncode"
    assert wf["ksampler"]["inputs"]["negative"] == ["negative_text", 0]

def test_face_workflow_without_references_skips_multiref():
    wf = build_uso_face_workflow("a face", "blurry", "crop.png", [])
    assert "multiref_method" not in wf
    assert wf["flux_guidance"]["inputs"]["conditioning"] == ["positive_text", 0]

def test_face_workflow_caps_references():
    wf = build_uso_face_workflow("a face", "", "crop.png", [f"r{i}.png" for i in range(8)])
    assert f"face_ref_load_{USO_MAX_REFERENCE_IMAGES}" in wf
    assert f"face_ref_load_{USO_MAX_REFERENCE_IMAGES + 1}" not in wf
