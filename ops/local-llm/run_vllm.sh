#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
fi

if [[ "${EUID}" -eq 0 ]]; then
  echo "Refusing to run vLLM as root. Use a non-root service account." >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
QWEN_PROFILE="${QWEN_PROFILE:-safe_profile}"
QWEN_SAFE_PROFILE_MODEL="${QWEN_SAFE_PROFILE_MODEL:-Qwen/Qwen3-14B-AWQ}"
QWEN_BIG_PROFILE_MODEL="${QWEN_BIG_PROFILE_MODEL:-Qwen/Qwen3-30B-A3B-Instruct-2507}"
QWEN_EXPERIMENTAL_DENSE_PROFILE_MODEL="${QWEN_EXPERIMENTAL_DENSE_PROFILE_MODEL:-Qwen/Qwen3-32B-AWQ}"

case "${QWEN_PROFILE}" in
  safe_profile)
    PROFILE_MODEL="${QWEN_SAFE_PROFILE_MODEL}"
    ;;
  big_profile)
    PROFILE_MODEL="${QWEN_BIG_PROFILE_MODEL}"
    ;;
  experimental_dense_profile)
    PROFILE_MODEL="${QWEN_EXPERIMENTAL_DENSE_PROFILE_MODEL}"
    ;;
  *)
    echo "Unknown QWEN_PROFILE=${QWEN_PROFILE}. Use safe_profile, big_profile, or experimental_dense_profile." >&2
    exit 1
    ;;
esac

QWEN_MODEL="${QWEN_MODEL:-${PROFILE_MODEL}}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-${QWEN_MODEL}}"
LLM_HOST="${LLM_HOST:-127.0.0.1}"
VLLM_PORT="${VLLM_PORT:-8000}"
MODEL_CACHE_DIR="${MODEL_CACHE_DIR:-/srv/local-llm/models}"
LOG_DIR="${LOG_DIR:-/var/log/local-llm}"
RUN_DIR="${RUN_DIR:-/var/run/local-llm}"
SERVICE_LOG_FILE="${SERVICE_LOG_FILE:-${LOG_DIR}/vllm.log}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-24576}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.82}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-1}"
DTYPE="${DTYPE:-auto}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
ALLOW_MODEL_DOWNLOAD="${ALLOW_MODEL_DOWNLOAD:-false}"
INSTALL_DEPS="${INSTALL_DEPS:-false}"
REASONING_PARSER="${REASONING_PARSER:-qwen3}"
ENABLE_AUTO_TOOL_CHOICE="${ENABLE_AUTO_TOOL_CHOICE:-false}"
TOOL_CALL_PARSER="${TOOL_CALL_PARSER:-hermes}"

if [[ "${QWEN_MODEL}" == *"Qwen3-32B-AWQ"* && "${QWEN_PROFILE}" != "experimental_dense_profile" ]]; then
  echo "Qwen3-32B-AWQ is allowed only through QWEN_PROFILE=experimental_dense_profile." >&2
  exit 1
fi

mkdir -p "${MODEL_CACHE_DIR}" "${LOG_DIR}" "${RUN_DIR}"

echo "== Environment probe =="
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found. Install/configure the NVIDIA driver in WSL/Ubuntu first." >&2
  exit 1
fi
nvidia-smi --query-gpu=name,driver_version,cuda_version,memory.total --format=csv,noheader

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

"${PYTHON_BIN}" - <<'PY'
import importlib.util
import sys

print("python=", sys.version.replace("\n", " "))
if importlib.util.find_spec("torch") is None:
    print("torch=not-installed")
else:
    import torch
    print("torch=", torch.__version__)
    print("torch_cuda_available=", torch.cuda.is_available())
    print("torch_cuda_version=", torch.version.cuda)
    print("torch_gpu_count=", torch.cuda.device_count())
    if torch.cuda.is_available():
        print("torch_gpu_name=", torch.cuda.get_device_name(0))
PY

if [[ "${INSTALL_DEPS}" == "true" ]]; then
  "${PYTHON_BIN}" -m pip install -U pip wheel
  "${PYTHON_BIN}" -m pip install "vllm>=0.8.5"
fi

if ! command -v vllm >/dev/null 2>&1; then
  echo "vllm command not found. Install vLLM in the active environment or set INSTALL_DEPS=true." >&2
  exit 1
fi

if [[ ! -d "${QWEN_MODEL}" && "${ALLOW_MODEL_DOWNLOAD}" != "true" ]]; then
  cat >&2 <<EOF
QWEN_MODEL is not a local directory and ALLOW_MODEL_DOWNLOAD is not true:
  ${QWEN_MODEL}

Download/cache the model during the install phase, then set QWEN_MODEL to the
local snapshot directory. To allow Hugging Face/ModelScope download during this
start, explicitly set ALLOW_MODEL_DOWNLOAD=true.
EOF
  exit 1
fi

if [[ "${ALLOW_MODEL_DOWNLOAD}" == "true" ]]; then
  export HF_HOME="${MODEL_CACHE_DIR}/huggingface"
  export HF_HUB_OFFLINE=0
  export TRANSFORMERS_OFFLINE=0
else
  export HF_HOME="${MODEL_CACHE_DIR}/huggingface"
  export HF_HUB_OFFLINE=1
  export TRANSFORMERS_OFFLINE=1
fi

VLLM_ARGS=(
  serve "${QWEN_MODEL}"
  --host "${LLM_HOST}"
  --port "${VLLM_PORT}"
  --served-model-name "${SERVED_MODEL_NAME}"
  --dtype "${DTYPE}"
  --tensor-parallel-size "${TENSOR_PARALLEL_SIZE}"
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}"
  --max-model-len "${MAX_MODEL_LEN}"
  --max-num-seqs "${MAX_NUM_SEQS}"
)

if [[ -n "${REASONING_PARSER}" ]]; then
  VLLM_ARGS+=(--enable-reasoning --reasoning-parser "${REASONING_PARSER}")
fi

if [[ "${ENABLE_AUTO_TOOL_CHOICE}" == "true" ]]; then
  VLLM_ARGS+=(--enable-auto-tool-choice --tool-call-parser "${TOOL_CALL_PARSER}")
fi

echo "== Starting vLLM =="
echo "profile=${QWEN_PROFILE}"
echo "model=${QWEN_MODEL}"
echo "served_model_name=${SERVED_MODEL_NAME}"
echo "max_num_seqs=${MAX_NUM_SEQS}"
echo "endpoint=http://${LLM_HOST}:${VLLM_PORT}/v1"
echo "log=${SERVICE_LOG_FILE}"

exec vllm "${VLLM_ARGS[@]}" 2>&1 | tee -a "${SERVICE_LOG_FILE}"
