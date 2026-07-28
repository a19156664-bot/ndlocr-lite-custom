import os
import json
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from custom_gui.batch_ocr import plan_batch, run_batch, BatchResult
from custom_gui.ocr_cache import save_cache, cache_dir_for, is_cached

@pytest.fixture
def temp_images(tmp_path):
    img1 = tmp_path / "img1.jpg"
    img2 = tmp_path / "img2.jpg"
    img3 = tmp_path / "img3.jpg"
    
    for img in [img1, img2, img3]:
        Image.new('RGB', (10, 10)).save(str(img))
        
    return [str(img1), str(img2), str(img3)]


def test_plan_batch(temp_images):
    # (i) plan_batch splits correctly when some images are already cached
    img1, img2, img3 = temp_images
    
    # Cache img2
    save_cache(img2, [{"text": "t", "bbox": (0,0,1,1), "confidence": 1.0, "is_vertical": False, "source_image": "img2.jpg"}])
    
    to_ocr, already_cached = plan_batch([img1, img2, img3])
    
    assert to_ocr == [img1, img3]
    assert already_cached == [img2]

class FakePopen:
    def __init__(self, expected_images, should_fail=False, stderr_file=None):
        self.expected_images = expected_images
        self.should_fail = should_fail
        self.poll_count = 0
        self.returncode = None
        self.is_terminated = False
        self.is_killed = False
        
        if self.should_fail and stderr_file:
            stderr_file.write("fake stderr")
            stderr_file.flush()

    def poll(self):
        if self.is_terminated or self.is_killed:
            return self.returncode
            
        self.poll_count += 1
        if self.poll_count > 2:
            self.returncode = 1 if self.should_fail else 0
            return self.returncode
        return None
        
    def terminate(self):
        self.is_terminated = True
        
    def kill(self):
        self.is_killed = True

def write_fake_output(output_dir, images):
    for img in images:
        bn = os.path.basename(img)
        stem = os.path.splitext(bn)[0]
        json_path = os.path.join(output_dir, f"{stem}.json")
        data = {
            "contents": [[{
                "boundingBox": [[0,0], [0,10], [10,0], [10,10]],
                "text": f"text_{stem}",
                "confidence": 0.99
            }]]
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

@patch("custom_gui.batch_ocr.subprocess.Popen")
def test_run_batch_success(mock_popen, temp_images):
    # (j) run_batch with a FAKE subprocess that writes plausible <stem>.json files
    # (k) src/ocr.py is invoked EXACTLY ONCE for N images
    # (l) the command line contains --sourcedir, --output and --json-only and NOT --sourcepdf or --viz
    
    def mock_popen_side_effect(cmd, **kwargs):
        # Assert (l)
        assert "src/ocr.py" in cmd
        assert "--sourcedir" in cmd
        assert "--output" in cmd
        assert "--json-only" in cmd
        assert "--sourcepdf" not in cmd
        assert "--viz" not in cmd
        
        output_dir = cmd[cmd.index("--output") + 1]
        write_fake_output(output_dir, temp_images)
        
        return FakePopen(temp_images)
        
    mock_popen.side_effect = mock_popen_side_effect
    
    result = run_batch(temp_images)
    
    # Assert (k): EXACTLY ONCE
    assert mock_popen.call_count == 1
    
    assert len(result.ok) == 3
    assert result.failed == []
    assert result.skipped == []
    assert not result.cancelled
    
    for img in temp_images:
        assert is_cached(img)


@patch("custom_gui.batch_ocr.subprocess.Popen")
def test_run_batch_cancel(mock_popen, temp_images):
    # (m) CANCEL: should_cancel returns True after some outputs exist. Assert cancelled is True...
    # (q) both temporary directories are gone when run_batch returns on the cancel path
    
    temp_dirs = []
    
    def mock_popen_side_effect(cmd, **kwargs):
        staging_dir = cmd[cmd.index("--sourcedir") + 1]
        output_dir = cmd[cmd.index("--output") + 1]
        temp_dirs.extend([staging_dir, output_dir])
        
        # Write output for ONLY the first image
        write_fake_output(output_dir, [temp_images[0]])
        
        return FakePopen(temp_images)
        
    mock_popen.side_effect = mock_popen_side_effect
    
    def should_cancel():
        return True # Cancel immediately
        
    result = run_batch(temp_images, should_cancel=should_cancel)
    
    assert result.cancelled is True
    assert temp_images[0] in result.ok
    assert is_cached(temp_images[0])
    
    assert len(result.failed) == 2
    for path, reason in result.failed:
        assert reason == "Cancelled before completion"
        
    # Assert (q): temporary directories are gone
    for d in temp_dirs:
        assert not os.path.exists(d)

@patch("custom_gui.batch_ocr.subprocess.Popen")
def test_progress(mock_popen, temp_images):
    # (n) progress is called with increasing done values and a correct total
    progress_calls = []
    
    def mock_popen_side_effect(cmd, **kwargs):
        output_dir = cmd[cmd.index("--output") + 1]
        write_fake_output(output_dir, temp_images)
        return FakePopen(temp_images)
        
    mock_popen.side_effect = mock_popen_side_effect
    
    def progress_cb(done, total):
        progress_calls.append((done, total))
        
    run_batch(temp_images, progress=progress_cb)
    
    assert len(progress_calls) > 0
    # Should at least see the final count
    assert progress_calls[-1] == (3, 3)
    
def test_duplicate_basenames(tmp_path):
    # (o) duplicate basenames from two different folders are reported in failed and do not overwrite
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    
    img1 = dir1 / "dup.jpg"
    img2 = dir2 / "dup.jpg"
    Image.new('RGB', (10, 10)).save(str(img1))
    Image.new('RGB', (10, 10)).save(str(img2))
    
    result = run_batch([str(img1), str(img2)])
    
    assert len(result.ok) == 0
    assert len(result.failed) == 2
    assert "Duplicate basename" in result.failed[0][1]
    assert "Duplicate basename" in result.failed[1][1]

@patch("custom_gui.batch_ocr.os.link")
@patch("custom_gui.batch_ocr.subprocess.Popen")
def test_fallback_copy(mock_popen, mock_link, temp_images):
    # (p) staging copy fallback: force os.link to raise and assert batch completes through shutil.copy2
    mock_link.side_effect = OSError("Cross-device link")
    
    def mock_popen_side_effect(cmd, **kwargs):
        staging_dir = cmd[cmd.index("--sourcedir") + 1]
        output_dir = cmd[cmd.index("--output") + 1]
        
        # Verify files were copied to staging
        for img in temp_images:
            assert os.path.exists(os.path.join(staging_dir, os.path.basename(img)))
            
        write_fake_output(output_dir, temp_images)
        return FakePopen(temp_images)
        
    mock_popen.side_effect = mock_popen_side_effect
    
    result = run_batch(temp_images)
    assert len(result.ok) == 3
    
@patch("custom_gui.batch_ocr.subprocess.Popen")
def test_nonzero_exit_no_output(mock_popen, temp_images):
    # (r) non-zero exit with no output JSON puts images in failed with reason, does not raise
    
    def mock_popen_side_effect(cmd, **kwargs):
        # Do NOT write fake output
        return FakePopen(temp_images, should_fail=True, stderr_file=kwargs.get('stderr'))
        
    mock_popen.side_effect = mock_popen_side_effect
    
    result = run_batch(temp_images)
    
    assert len(result.ok) == 0
    assert len(result.failed) == 3
    for path, reason in result.failed:
        assert "OCR process failed with code 1" in reason
        assert "fake stderr" in reason
