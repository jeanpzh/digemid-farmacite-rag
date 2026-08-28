import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
START_SCRIPT = ROOT / "scripts" / "start.sh"


def run_start_script(*, gpu_backend: str | None = None, nvidia_smi: bool = False):
    environment = os.environ.copy()
    environment["PATH"] = "/usr/bin:/bin"
    if gpu_backend is not None:
        environment["GPU_BACKEND"] = gpu_backend

    if nvidia_smi:
        fake_bin = ROOT / ".test-bin"
        fake_bin.mkdir(exist_ok=True)
        fake_nvidia_smi = fake_bin / "nvidia-smi"
        fake_nvidia_smi.write_text("#!/bin/sh\nexit 0\n")
        fake_nvidia_smi.chmod(0o755)
        environment["PATH"] = f"{fake_bin}:/usr/bin:/bin"

    try:
        return subprocess.run(
            ["bash", str(START_SCRIPT), "--print-command"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if nvidia_smi:
            fake_nvidia_smi.unlink(missing_ok=True)
            fake_bin.rmdir()


def test_start_script_selects_cpu_when_no_gpu_is_detected():
    result = run_start_script()

    assert result.returncode == 0
    assert "GPU backend: cpu" in result.stdout
    assert "docker-compose.yml" in result.stdout
    assert "docker-compose.amd.yml" not in result.stdout


def test_start_script_selects_nvidia_when_nvidia_smi_is_available():
    result = run_start_script(nvidia_smi=True)

    assert result.returncode == 0
    assert "GPU backend: nvidia" in result.stdout
    assert "docker-compose.gpu.yml" in result.stdout


def test_start_script_allows_explicit_amd_selection():
    result = run_start_script(gpu_backend="amd")

    assert result.returncode == 0
    assert "GPU backend: amd" in result.stdout
    assert "docker-compose.amd.yml" in result.stdout
