"""
Stage 6 tests — character reference locking. image_service/embedding_service
calls are mocked so these stay fast and don't depend on ComfyUI or a real
CLIP model load; embedding_service.py and image_service.py's placeholder
path are exercised for real elsewhere (test_embedding_service.py, and the
live smoke test against the actual route).
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.character_asset_service import lock_character_reference


@pytest.fixture(autouse=True)
def isolated_refs_dir(tmp_path):
    """The upload path writes real bytes to disk (by design — locked
    references must persist). Redirect that to a temp dir for every test in
    this file so the suite never pollutes the app's real static folder."""
    with patch("app.character_asset_service.CHARACTER_REFS_DIR", str(tmp_path)):
        yield tmp_path


@pytest.mark.asyncio
async def test_lock_with_uploaded_images_skips_generation(isolated_refs_dir):
    fake_embedding = [0.1, 0.2, 0.3]
    with patch("app.character_asset_service.compute_image_embedding", return_value=fake_embedding), \
         patch("app.character_asset_service.image_service.generate_character_portrait", new=AsyncMock()) as gen_mock:
        result = await lock_character_reference(
            character_id="char-1", character_name="Vasanth", character_description="A young man.",
            uploaded_images=[b"fake-png-bytes-1", b"fake-png-bytes-2"],
        )
    gen_mock.assert_not_called()  # user-supplied refs must never trigger auto-generation
    assert len(result["reference_image_paths"]) == 2
    assert result["locked_seed"] is None  # no seed for user-supplied references
    assert result["embedding_vector"] == fake_embedding
    assert (isolated_refs_dir / "char-1_0.png").exists()

@pytest.mark.asyncio
async def test_lock_without_images_generates_and_freezes_a_seed(isolated_refs_dir):
    with patch("app.character_asset_service.compute_image_embedding", return_value=None), \
         patch("app.character_asset_service.image_service.generate_character_portrait",
               new=AsyncMock(side_effect=lambda cid, idx, *a, **kw: f"/static/character_refs/{cid}_{idx}.png")) as gen_mock:
        result = await lock_character_reference(
            character_id="char-2", character_name="Rukhmika", character_description=None, uploaded_images=None,
        )
    # One reference per head angle, not one per character: USO conditions on up
    # to 4 references, and a single fixed-angle reference left identity weakest
    # on exactly the frames whose head angle differed from it (a clean profile
    # measured 0.500 identity before an identity pass, 0.607 after).
    from app.character_asset_service import REFERENCE_ANGLES

    assert gen_mock.call_count == len(REFERENCE_ANGLES)
    assert result["locked_seed"] is not None
    assert isinstance(result["locked_seed"], int)
    assert len(result["reference_image_paths"]) == len(REFERENCE_ANGLES)

    # indices must be distinct (they become _0/_1/_2 filenames) and each angle
    # needs its own seed, otherwise every "angle" renders the same image
    indices = [call.args[1] for call in gen_mock.call_args_list]
    seeds = [call.args[3] for call in gen_mock.call_args_list]
    assert indices == list(range(len(REFERENCE_ANGLES)))
    assert len(set(seeds)) == len(REFERENCE_ANGLES)
    # all seeds derive from the one stored locked_seed, so the set stays reproducible
    assert all(s - result["locked_seed"] == i for i, s in enumerate(seeds))

@pytest.mark.asyncio
async def test_lock_caps_uploaded_images_at_four(isolated_refs_dir):
    with patch("app.character_asset_service.compute_image_embedding", return_value=None), \
         patch("app.character_asset_service.image_service.generate_character_portrait", new=AsyncMock()):
        result = await lock_character_reference(
            character_id="char-3", character_name="Group", character_description=None,
            uploaded_images=[b"1", b"2", b"3", b"4", b"5", b"6"],
        )
    assert len(result["reference_image_paths"]) == 4

@pytest.mark.asyncio
async def test_lock_handles_embedding_unavailable_gracefully(isolated_refs_dir):
    with patch("app.character_asset_service.compute_image_embedding", return_value=None), \
         patch("app.character_asset_service.image_service.generate_character_portrait", new=AsyncMock()):
        result = await lock_character_reference(
            character_id="char-4", character_name="X", character_description=None, uploaded_images=[b"img"],
        )
    assert result["embedding_vector"] is None  # never raises — degrades gracefully
