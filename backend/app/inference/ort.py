from __future__ import annotations

import os

import onnxruntime as ort  # type: ignore


def get_ort_providers_from_env() -> tuple[list[str], list[dict], bool]:
    """Return (providers, provider_options, uses_openvino).

    Env vars:
    - VISION_ORT_PROVIDERS: comma-separated provider list.
      Default: CPUExecutionProvider
      Example: OpenVINOExecutionProvider,CPUExecutionProvider
    - VISION_OPENVINO_DEVICE_TYPE: OpenVINO device_type, e.g. CPU, GPU,
        NPU, AUTO:GPU,NPU,CPU
      Default: CPU
    - VISION_OPENVINO_LOAD_CONFIG: optional JSON config path for OpenVINO EP.
    - VISION_OPENVINO_CACHE_DIR: optional cache directory.
    """

    raw = os.getenv("VISION_ORT_PROVIDERS", "CPUExecutionProvider")
    providers = [p.strip() for p in raw.split(",") if p.strip()]
    if not providers:
        providers = ["CPUExecutionProvider"]

    available = set(ort.get_available_providers())
    # Filter to available providers (keeps ordering).
    filtered = [p for p in providers if p in available]
    if not filtered:
        filtered = ["CPUExecutionProvider"]

    uses_openvino = "OpenVINOExecutionProvider" in filtered

    provider_options: list[dict] = []
    for provider in filtered:
        if provider == "OpenVINOExecutionProvider":
            opts: dict[str, str] = {}
            opts["device_type"] = os.getenv(
                "VISION_OPENVINO_DEVICE_TYPE",
                "CPU",
            )

            load_config = os.getenv("VISION_OPENVINO_LOAD_CONFIG")
            if load_config:
                opts["load_config"] = load_config

            cache_dir = os.getenv("VISION_OPENVINO_CACHE_DIR")
            if cache_dir:
                opts["cache_dir"] = cache_dir

            provider_options.append(opts)
        else:
            provider_options.append({})

    return filtered, provider_options, uses_openvino
