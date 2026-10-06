"""
Stage 7 — ComfyUI workflow (node graph) builder for Flux.1-dev generation.

Two genuinely different graph shapes, not one graph with optional injected
pieces:

  - No named characters: the standard ComfyUI-native Flux graph (UNETLoader/
    DualCLIPLoader/VAELoader/CLIPTextEncode/EmptySD3LatentImage/KSampler/
    VAEDecode/SaveImage). VERIFIED against a live ComfyUI instance (Kaggle
    T4) via its own /object_info introspection API.

  - 1+ named characters (engine="USO"): ByteDance's USO ([CVPR 2026],
    Apache 2.0), built entirely from standard ComfyUI CORE nodes — no
    third-party custom node install at all. This replaced an earlier UNO
    integration (via the jax-explorer/ComfyUI-UNO community custom node):
    live GPU testing found UNO's reference-image conditioning path produced
    a reproducible, near-flat/degenerate output with ANY reference image
    (synthetic or real photo), on an otherwise healthy instance, while
    UNO's own reference-free path worked fine — a genuine third-party bug,
    not something in this codebase. USO does the same job (subject-
    consistent generation, same "uxo/uno" multi-reference method — USO is
    ByteDance's own successor covering UNO's use case) but through core
    nodes only, removing that whole class of risk. This graph is reverse-
    engineered from ComfyUI's own official workflow template
    (Comfy-Org/workflow_templates: flux1_dev_uso_reference_image_gen.json,
    the "USO Character Reference" subgraph) — not a guess — reduced to the
    minimal subject-consistency path: the template's optional CLIP-Vision/
    ModelPatchLoader "USOStyleReference" chain is for STYLE transfer, which
    this build doesn't need, and is dropped (the template's own note
    confirms style references are optional and can be disabled, leaving
    pure subject-driven generation). Each pooled reference image is
    VAE-encoded and chained through its own ReferenceLatent call, then
    FluxKontextMultiReferenceLatentMethod (mode "uxo/uno") is applied once
    — the standard pattern for stacking multiple Flux Kontext references.
    Identity is ALSO conveyed via the prompt text itself (shot_prompt_builder.py
    already names each character), same as the earlier UNO integration.

PhotoMaker V2 was dropped from this build entirely (see uso_client.py) —
USO covers both single- and multi-character shots on its own.

ControlNet is only wired for the plain (no-character) path.

Reference images must exist in ComfyUI's own input/ folder before a
LoadImage node can reference them by filename — comfy_client.py's
upload_image() handles pushing the bytes there first.
"""
from typing import Any, Dict, List, Optional

# Centralized so a real ComfyUI install's actual node/input names can be
# corrected here in one place. All entries below are standard ComfyUI core
# nodes, verified against a live instance's /object_info (see module
# docstring) — no third-party custom node is required for either path.
NODE_TYPES = {
    "unet_loader": "UNETLoader",
    "dual_clip_loader": "DualCLIPLoader",
    "vae_loader": "VAELoader",
    "clip_text_encode": "CLIPTextEncode",
    "flux_guidance": "FluxGuidance",
    "empty_latent": "EmptySD3LatentImage",
    "ksampler": "KSampler",
    "vae_decode": "VAEDecode",
    "save_image": "SaveImage",
    "load_image": "LoadImage",
    "controlnet_loader": "ControlNetLoader",
    "controlnet_apply": "ControlNetApplyAdvanced",
    "checkpoint_loader": "CheckpointLoaderSimple",
    "lora_loader_model_only": "LoraLoaderModelOnly",
    "conditioning_zero_out": "ConditioningZeroOut",
    "image_scale_to_max_dimension": "ImageScaleToMaxDimension",
    "vae_encode": "VAEEncode",
    "reference_latent": "ReferenceLatent",
    "flux_kontext_multi_ref_method": "FluxKontextMultiReferenceLatentMethod",
    "image_scale": "ImageScale",
    "load_image_mask": "LoadImageMask",
    "set_latent_noise_mask": "SetLatentNoiseMask",
}

DEFAULT_CHECKPOINTS = {
    "unet_name": "flux1-dev.safetensors",
    "clip_name1": "clip_l.safetensors",
    "clip_name2": "t5xxl_fp8_e4m3fn.safetensors",
    "vae_name": "ae.safetensors",
}

# USO's own all-in-one checkpoint (UNET+CLIP+VAE bundled, natively fp8) is a
# SEPARATE file from DEFAULT_CHECKPOINTS above — that all-in-one shape is
# what CheckpointLoaderSimple expects, unlike the plain path's separate
# UNETLoader/DualCLIPLoader/VAELoader files. Both public/ungated on HF.
USO_CHECKPOINT = "flux1-dev-fp8.safetensors"
USO_LORA = "uso-flux1-dit-lora-v1.safetensors"
USO_MAX_REFERENCE_IMAGES = 4


def build_flux_workflow(
    positive_prompt: str,
    negative_prompt: str,
    width: int = 1024,
    height: int = 640,
    steps: int = 28,  # bumped from 20 -- live-tested: 20 steps left faces in
                       # dynamic/action poses (leaning forward, helmet-worn,
                       # mid-motion) visibly distorted (asymmetric eyes,
                       # smudged features) even though static close-ups at
                       # the same step count looked sharp. More steps is the
                       # standard lever for that kind of fine-detail quality.
    guidance: float = 3.5,
    consistency_params: Optional[Dict[str, Any]] = None,
    controlnet_image_path: Optional[str] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Builds a ComfyUI /prompt-ready workflow dict (node_id -> {class_type, inputs}).

    `consistency_params`: output of CharacterConsistencyOrchestrator
    .compile_consistency_params() — None/engine=None for a shot with no
    named characters (plain text-to-image graph); engine="USO" builds the
    reference-conditioned graph instead (reference images must already be
    uploaded to ComfyUI's input/ folder — see comfy_client.upload_image()
    — with `reference_image_paths` in `consistency_params["identities"]`
    holding the ComfyUI-side filenames, not local disk paths, by the time
    this is called).

    `controlnet_image_path`: optional depth/pose reference image (ComfyUI-
    side filename) — plain-path only, see module docstring.
    """
    engine = (consistency_params or {}).get("engine")
    if engine == "USO":
        return _build_uso_workflow(positive_prompt, negative_prompt, width, height, steps, guidance, consistency_params, seed)
    return _build_plain_flux_workflow(positive_prompt, negative_prompt, width, height, steps, guidance, controlnet_image_path, seed)


def _build_plain_flux_workflow(
    positive_prompt: str, negative_prompt: str, width: int, height: int,
    steps: int, guidance: float, controlnet_image_path: Optional[str], seed: Optional[int],
) -> Dict[str, Any]:
    nt = NODE_TYPES
    wf: Dict[str, Any] = {
        "unet_loader": {"class_type": nt["unet_loader"], "inputs": {
            # fp8_e4m3fn loads the full checkpoint at reduced precision in
            # VRAM (~11.5GB vs ~23GB) — needed to fit a single 15GB T4;
            # verified as a real option via this node's own /object_info.
            "unet_name": DEFAULT_CHECKPOINTS["unet_name"], "weight_dtype": "fp8_e4m3fn",
        }},
        "dual_clip_loader": {"class_type": nt["dual_clip_loader"], "inputs": {
            "clip_name1": DEFAULT_CHECKPOINTS["clip_name1"],
            "clip_name2": DEFAULT_CHECKPOINTS["clip_name2"],
            "type": "flux",
        }},
        "vae_loader": {"class_type": nt["vae_loader"], "inputs": {"vae_name": DEFAULT_CHECKPOINTS["vae_name"]}},
        "positive_prompt": {"class_type": nt["clip_text_encode"], "inputs": {
            "text": positive_prompt, "clip": ["dual_clip_loader", 0],
        }},
        "negative_prompt": {"class_type": nt["clip_text_encode"], "inputs": {
            "text": negative_prompt, "clip": ["dual_clip_loader", 0],
        }},
        "flux_guidance": {"class_type": nt["flux_guidance"], "inputs": {
            "conditioning": ["positive_prompt", 0], "guidance": guidance,
        }},
        "empty_latent": {"class_type": nt["empty_latent"], "inputs": {
            "width": width, "height": height, "batch_size": 1,
        }},
        "ksampler": {"class_type": nt["ksampler"], "inputs": {
            "model": ["unet_loader", 0],
            "positive": ["flux_guidance", 0],
            "negative": ["negative_prompt", 0],
            "latent_image": ["empty_latent", 0],
            "seed": seed if seed is not None else 0,  # comfy_client.generate_image also injects a seed if none given
            "steps": steps,
            "cfg": 1.0,  # Flux uses FluxGuidance for guidance strength, not classic CFG
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1.0,
        }},
        "vae_decode": {"class_type": nt["vae_decode"], "inputs": {
            "samples": ["ksampler", 0], "vae": ["vae_loader", 0],
        }},
        "save_image": {"class_type": nt["save_image"], "inputs": {
            "images": ["vae_decode", 0], "filename_prefix": "70mm_shot",
        }},
    }
    if controlnet_image_path:
        _inject_controlnet(wf, controlnet_image_path)
    return wf


def _build_uso_workflow(
    positive_prompt: str, negative_prompt: str, width: int, height: int, steps: int, guidance: float,
    consistency_params: Dict[str, Any], seed: Optional[int],
) -> Dict[str, Any]:
    nt = NODE_TYPES

    # Pool every identity's reference images across all named characters in
    # the shot, capped at USO_MAX_REFERENCE_IMAGES — identity is conveyed
    # through the prompt text (shot_prompt_builder.py already names each
    # character) in addition to the stacked reference latents themselves.
    all_ref_paths: List[str] = []
    for identity in consistency_params.get("identities", []):
        all_ref_paths.extend(identity.get("reference_image_paths", []))
    all_ref_paths = all_ref_paths[:USO_MAX_REFERENCE_IMAGES]

    wf: Dict[str, Any] = {
        "checkpoint_loader": {"class_type": nt["checkpoint_loader"], "inputs": {
            "ckpt_name": USO_CHECKPOINT,
        }},
        "lora_loader": {"class_type": nt["lora_loader_model_only"], "inputs": {
            "model": ["checkpoint_loader", 0],
            "lora_name": USO_LORA,
            "strength_model": 1.0,
        }},
        "positive_text": {"class_type": nt["clip_text_encode"], "inputs": {
            "text": positive_prompt, "clip": ["checkpoint_loader", 1],
        }},
        # Was ConditioningZeroOut(positive_text) -- a zeroed conditioning
        # derived from the positive text, which meant NEGATIVE_PROMPT_BASE
        # (and its style-exclusion terms) never reached the model at all on
        # this path, no matter what negative_prompt text was passed in. A
        # real second CLIPTextEncode node here (a) actually applies the
        # negative prompt and (b) is what comfy_client.generate_image()'s
        # own "second CLIPTextEncode node found = negative" scan expects --
        # that scan was previously a silent no-op on this graph since there
        # was only ever one CLIPTextEncode node (positive_text) to find.
        "negative_text": {"class_type": nt["clip_text_encode"], "inputs": {
            "text": negative_prompt, "clip": ["checkpoint_loader", 1],
        }},
        "empty_latent": {"class_type": nt["empty_latent"], "inputs": {
            "width": width, "height": height, "batch_size": 1,
        }},
    }

    # Chain one ReferenceLatent call per pooled reference image, then apply
    # the multi-reference combination method once at the end — the standard
    # Flux Kontext pattern for stacking more than one reference latent.
    cond_node = "positive_text"
    for i, path in enumerate(all_ref_paths, start=1):
        load_id, scale_id, encode_id, ref_cond_id = (
            f"uso_ref_load_{i}", f"uso_ref_scale_{i}", f"uso_ref_encode_{i}", f"uso_ref_cond_{i}",
        )
        wf[load_id] = {"class_type": nt["load_image"], "inputs": {"image": path}}
        wf[scale_id] = {"class_type": nt["image_scale_to_max_dimension"], "inputs": {
            "image": [load_id, 0], "upscale_method": "area", "largest_size": 512,
        }}
        wf[encode_id] = {"class_type": nt["vae_encode"], "inputs": {
            "pixels": [scale_id, 0], "vae": ["checkpoint_loader", 2],
        }}
        wf[ref_cond_id] = {"class_type": nt["reference_latent"], "inputs": {
            "conditioning": [cond_node, 0], "latent": [encode_id, 0],
        }}
        cond_node = ref_cond_id

    if all_ref_paths:
        wf["multiref_method"] = {"class_type": nt["flux_kontext_multi_ref_method"], "inputs": {
            "conditioning": [cond_node, 0], "reference_latents_method": "uxo/uno",
        }}
        cond_node = "multiref_method"

    # consistency_params["strength"] (from CharacterConsistencyOrchestrator
    # .compile_consistency_params()) was being set and threaded all the way
    # down to here but never actually consumed -- a dead parameter, live-
    # verified by grepping for every read site. FluxGuidance's own strength
    # is the one real lever this graph exposes for "how hard to push toward
    # the conditioning" (text + stacked reference latents together, since
    # they're the same conditioning chain here), so tie it to that: strength
    # 0.5 leaves `guidance` unchanged, 1.0 pushes it up by 1.5, 0.0 pulls it
    # down by 1.5, clamped to Flux's own sane 0-10 range.
    identity_strength = consistency_params.get("strength", 0.7)
    effective_guidance = max(0.0, min(10.0, guidance + (identity_strength - 0.5) * 3.0))
    wf["flux_guidance"] = {"class_type": nt["flux_guidance"], "inputs": {
        "conditioning": [cond_node, 0], "guidance": effective_guidance,
    }}
    wf["ksampler"] = {"class_type": nt["ksampler"], "inputs": {
        "model": ["lora_loader", 0],
        "positive": ["flux_guidance", 0],
        "negative": ["negative_text", 0],
        "latent_image": ["empty_latent", 0],
        "seed": seed if seed is not None else 0,
        "steps": steps,
        "cfg": 1.0,
        "sampler_name": "euler",
        "scheduler": "simple",
        "denoise": 1.0,
    }}
    wf["vae_decode"] = {"class_type": nt["vae_decode"], "inputs": {
        "samples": ["ksampler", 0], "vae": ["checkpoint_loader", 2],
    }}
    wf["save_image"] = {"class_type": nt["save_image"], "inputs": {
        "images": ["vae_decode", 0], "filename_prefix": "70mm_shot",
    }}
    return wf


def _inject_controlnet(wf: Dict[str, Any], control_image_path: str) -> None:
    """Optional depth/pose conditioning when a precise camera angle/blocking
    reference image is available. Plain-path only — see module docstring.
    Best-effort node shape (not verified against a live install, unlike the
    rest of this file) since no upstream stage produces a control image to
    actually exercise this path yet."""
    nt = NODE_TYPES
    wf["controlnet_ref_image"] = {"class_type": nt["load_image"], "inputs": {"image": control_image_path}}
    wf["controlnet_loader"] = {"class_type": nt["controlnet_loader"], "inputs": {"control_net_name": "flux-depth-controlnet.safetensors"}}
    wf["controlnet_apply"] = {
        "class_type": nt["controlnet_apply"],
        "inputs": {
            "positive": wf["ksampler"]["inputs"]["positive"],
            "negative": ["negative_prompt", 0],
            "control_net": ["controlnet_loader", 0],
            "image": ["controlnet_ref_image", 0],
            "strength": 0.6,
        },
    }
    wf["ksampler"]["inputs"]["positive"] = ["controlnet_apply", 0]
    wf["ksampler"]["inputs"]["negative"] = ["controlnet_apply", 1]

# -- Two-pass generation ------------------------------------------------------
# Why the pipeline is split into passes at all:
#
# USO reference conditioning concatenates the reference image's latents into
# the same attention field as the frame being generated, so it reproduces the
# reference's STRUCTURE as well as its identity. Live-observed consequences
# when a single reference-conditioned pass rendered the whole frame: shots
# specified as "Wide Shot" came back as tight face close-ups, two-shots
# rendered only one person, and poses repeated across shots regardless of the
# described action. Identity and composition were fighting, identity always won.
#
# Splitting them removes the conflict:
#   Pass 1  composition, TEXT ONLY (build_flux_workflow with no
#           consistency_params) -- shot size, staging, how many people and the
#           described action all obey the prompt.
#   Pass 1b refinement, img2img at partial denoise -- the standard fix for the
#           hand/finger artefacts that survive a first pass.
#   Pass 2  identity, per face region only (build_uso_face_workflow) -- the
#           reference can only influence the crop it is handed, so it cannot
#           drag the whole frame back into a reference-shaped close-up.


def build_img2img_refine_workflow(
    positive_prompt: str,
    negative_prompt: str,
    init_image_filename: str,
    width: int = 1024,
    height: int = 640,
    steps: int = 28,
    guidance: float = 3.5,
    denoise: float = 0.4,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Refinement pass: re-denoise an existing frame at `denoise` strength.

    `init_image_filename` must already exist in ComfyUI's own input/ folder
    (see comfy_client.upload_image). Runs on the plain Flux graph -- no
    reference conditioning -- so refining can never alter composition.

    A partial denoise (~0.4) rebuilds local detail while leaving the overall
    frame intact, which is what lets it repair malformed hands and fingers
    without re-rolling the whole shot.
    """
    nt = NODE_TYPES
    wf: Dict[str, Any] = {
        "unet_loader": {"class_type": nt["unet_loader"], "inputs": {
            "unet_name": DEFAULT_CHECKPOINTS["unet_name"], "weight_dtype": "fp8_e4m3fn",
        }},
        "dual_clip_loader": {"class_type": nt["dual_clip_loader"], "inputs": {
            "clip_name1": DEFAULT_CHECKPOINTS["clip_name1"],
            "clip_name2": DEFAULT_CHECKPOINTS["clip_name2"],
            "type": "flux",
        }},
        "vae_loader": {"class_type": nt["vae_loader"], "inputs": {"vae_name": DEFAULT_CHECKPOINTS["vae_name"]}},
        "positive_prompt": {"class_type": nt["clip_text_encode"], "inputs": {
            "text": positive_prompt, "clip": ["dual_clip_loader", 0],
        }},
        "negative_prompt": {"class_type": nt["clip_text_encode"], "inputs": {
            "text": negative_prompt, "clip": ["dual_clip_loader", 0],
        }},
        "flux_guidance": {"class_type": nt["flux_guidance"], "inputs": {
            "conditioning": ["positive_prompt", 0], "guidance": guidance,
        }},
        "init_image": {"class_type": nt["load_image"], "inputs": {"image": init_image_filename}},
        "init_scaled": {"class_type": nt["image_scale"], "inputs": {
            "image": ["init_image", 0], "upscale_method": "lanczos",
            "width": width, "height": height, "crop": "disabled",
        }},
        "init_encoded": {"class_type": nt["vae_encode"], "inputs": {
            "pixels": ["init_scaled", 0], "vae": ["vae_loader", 0],
        }},
        "ksampler": {"class_type": nt["ksampler"], "inputs": {
            "model": ["unet_loader", 0],
            "positive": ["flux_guidance", 0],
            "negative": ["negative_prompt", 0],
            "latent_image": ["init_encoded", 0],
            "seed": seed if seed is not None else 0,
            "steps": steps,
            "cfg": 1.0,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": denoise,
        }},
        "vae_decode": {"class_type": nt["vae_decode"], "inputs": {
            "samples": ["ksampler", 0], "vae": ["vae_loader", 0],
        }},
        "save_image": {"class_type": nt["save_image"], "inputs": {
            "images": ["vae_decode", 0], "filename_prefix": "70mm_refine",
        }},
    }
    return wf


def build_uso_face_workflow(
    positive_prompt: str,
    negative_prompt: str,
    init_image_filename: str,
    reference_image_filenames: List[str],
    width: int = 768,
    height: int = 768,
    steps: int = 28,
    guidance: float = 3.5,
    denoise: float = 0.55,
    seed: Optional[int] = None,
    mask_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Identity pass over a single cropped FACE region.

    `mask_filename` (a grayscale image already uploaded to ComfyUI's input/
    folder, white = repaint) restricts denoising to the head via core
    SetLatentNoiseMask, so the crop's surroundings stay pixel-identical and
    the repaint can run at a much higher denoise than a whole-frame pass.

    Same USO reference conditioning as before, but the init latent is the face
    crop rather than empty noise and denoise is partial -- so the reference
    reshapes the face toward the locked identity while the crop's pose, angle
    and lighting (all inherited from the composition pass) survive.

    Because this graph only ever sees the crop, the reference cannot impose its
    own framing on the finished frame, which is the entire reason composition
    is generated separately first.
    """
    nt = NODE_TYPES
    refs = reference_image_filenames[:USO_MAX_REFERENCE_IMAGES]

    wf: Dict[str, Any] = {
        "checkpoint_loader": {"class_type": nt["checkpoint_loader"], "inputs": {
            "ckpt_name": USO_CHECKPOINT,
        }},
        "lora_loader": {"class_type": nt["lora_loader_model_only"], "inputs": {
            "model": ["checkpoint_loader", 0],
            "lora_name": USO_LORA,
            "strength_model": 1.0,
        }},
        "positive_text": {"class_type": nt["clip_text_encode"], "inputs": {
            "text": positive_prompt, "clip": ["checkpoint_loader", 1],
        }},
        "negative_text": {"class_type": nt["clip_text_encode"], "inputs": {
            "text": negative_prompt, "clip": ["checkpoint_loader", 1],
        }},
        "init_image": {"class_type": nt["load_image"], "inputs": {"image": init_image_filename}},
        "init_scaled": {"class_type": nt["image_scale"], "inputs": {
            "image": ["init_image", 0], "upscale_method": "lanczos",
            "width": width, "height": height, "crop": "disabled",
        }},
        "init_encoded": {"class_type": nt["vae_encode"], "inputs": {
            "pixels": ["init_scaled", 0], "vae": ["checkpoint_loader", 2],
        }},
    }

    cond_node = "positive_text"
    for i, ref_path in enumerate(refs, start=1):
        load_id = "face_ref_load_%d" % i
        scale_id = "face_ref_scale_%d" % i
        encode_id = "face_ref_encode_%d" % i
        ref_cond_id = "face_ref_cond_%d" % i
        wf[load_id] = {"class_type": nt["load_image"], "inputs": {"image": ref_path}}
        wf[scale_id] = {"class_type": nt["image_scale_to_max_dimension"], "inputs": {
            "image": [load_id, 0], "upscale_method": "area", "largest_size": 512,
        }}
        wf[encode_id] = {"class_type": nt["vae_encode"], "inputs": {
            "pixels": [scale_id, 0], "vae": ["checkpoint_loader", 2],
        }}
        wf[ref_cond_id] = {"class_type": nt["reference_latent"], "inputs": {
            "conditioning": [cond_node, 0], "latent": [encode_id, 0],
        }}
        cond_node = ref_cond_id

    if refs:
        wf["multiref_method"] = {"class_type": nt["flux_kontext_multi_ref_method"], "inputs": {
            "conditioning": [cond_node, 0], "reference_latents_method": "uxo/uno",
        }}
        cond_node = "multiref_method"

    latent_node = "init_encoded"
    if mask_filename:
        wf["face_mask"] = {"class_type": nt["load_image_mask"], "inputs": {
            "image": mask_filename, "channel": "red",
        }}
        wf["masked_latent"] = {"class_type": nt["set_latent_noise_mask"], "inputs": {
            "samples": ["init_encoded", 0], "mask": ["face_mask", 0],
        }}
        latent_node = "masked_latent"

    wf["flux_guidance"] = {"class_type": nt["flux_guidance"], "inputs": {
        "conditioning": [cond_node, 0], "guidance": guidance,
    }}
    wf["ksampler"] = {"class_type": nt["ksampler"], "inputs": {
        "model": ["lora_loader", 0],
        "positive": ["flux_guidance", 0],
        "negative": ["negative_text", 0],
        "latent_image": [latent_node, 0],
        "seed": seed if seed is not None else 0,
        "steps": steps,
        "cfg": 1.0,
        "sampler_name": "euler",
        "scheduler": "simple",
        "denoise": denoise,
    }}
    wf["vae_decode"] = {"class_type": nt["vae_decode"], "inputs": {
        "samples": ["ksampler", 0], "vae": ["checkpoint_loader", 2],
    }}
    wf["save_image"] = {"class_type": nt["save_image"], "inputs": {
        "images": ["vae_decode", 0], "filename_prefix": "70mm_face",
    }}
    return wf
