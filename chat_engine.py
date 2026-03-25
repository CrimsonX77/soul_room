"""
chat_engine.py — Multi-Backend LLM Interface

Supports Ollama (local), Grok (xAI), OpenAI, and Anthropic backends.
Handles encrypted API key storage.
Loads soul YAMLs into system prompts automatically.

Part of the Soul Room framework.
"""

import os
import requests
import yaml
from dotenv import load_dotenv
from cryptography.fernet import Fernet

try:
    import ollama as _ollama
except ImportError:
    _ollama = None


# ── Encrypted Environment ────────────────────────────

def load_encrypted_env(env_path=".env", key_path=".env.key"):
    """Load .env, decrypting values that are Fernet-encrypted."""
    load_dotenv(env_path)
    fernet = None
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            fernet = Fernet(f.read().strip())
    env = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if fernet and v.startswith("gAAAA"):
                    try:
                        v = fernet.decrypt(v.encode()).decode()
                    except Exception:
                        pass
                env[k] = v
    return env


def encrypt_value(value, key_path=".env.key"):
    """Encrypt a plaintext value using the Fernet key."""
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        os.chmod(key_path, 0o600)
    with open(key_path, "rb") as f:
        fernet = Fernet(f.read().strip())
    return fernet.encrypt(value.encode()).decode()


def save_env(env_dict, env_path=".env"):
    """Write key=value pairs to .env file."""
    with open(env_path, "w") as f:
        for k, v in env_dict.items():
            f.write(f"{k}={v}\n")
    os.chmod(env_path, 0o600)


# ── Backend Definitions ──────────────────────────────

BACKENDS = {
    "ollama": {
        "name": "Ollama (Local)",
        "requires_key": False,
        "default_model": "llama3:latest",
    },
    "grok": {
        "name": "Grok (xAI)",
        "requires_key": True,
        "env_key": "XAI_API_KEY",
        "api_base": "https://api.x.ai/v1",
        "default_model": "grok-beta",
    },
    "openai": {
        "name": "OpenAI",
        "requires_key": True,
        "env_key": "OPENAI_API_KEY",
        "api_base": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "name": "Anthropic",
        "requires_key": True,
        "env_key": "ANTHROPIC_API_KEY",
        "api_base": "https://api.anthropic.com/v1",
        "default_model": "claude-sonnet-4-20250514",
    },
}


class ChatEngine:
    """
    Multi-backend chat engine. Each participant in a Soul Room
    can use a different engine instance pointed at a different backend/model.
    """

    def __init__(self, backend="ollama", model=None, api_key=None):
        self.backend = backend
        self.api_key = api_key or ""
        self.model = model or BACKENDS.get(backend, {}).get("default_model", "llama3:latest")
        self.system_prompt = ""
        self.soul = None
        self._load_env()

    def _load_env(self):
        """Load API keys from encrypted .env if available."""
        env = load_encrypted_env()
        backend_def = BACKENDS.get(self.backend, {})
        env_key = backend_def.get("env_key", "")
        if env_key and env.get(env_key) and not self.api_key:
            self.api_key = env[env_key]
        if env.get("DEFAULT_MODEL") and not self.model:
            self.model = env["DEFAULT_MODEL"]

    def set_soul(self, soul):
        """Load a soul dict and generate system prompt from it."""
        from soul_room.engine.soul_parser import soul_to_system_prompt
        self.soul = soul
        if 'system_prompt' in soul:
            self.system_prompt = soul['system_prompt']
        else:
            self.system_prompt = soul_to_system_prompt(soul, base_prompt=self.system_prompt)

    def set_system_prompt(self, prompt):
        """Set a raw system prompt (without soul loading)."""
        self.system_prompt = prompt

    def get_local_models(self, refresh=False):
        """List available Ollama models."""
        if _ollama is None:
            return ["(ollama package not installed)"]
        try:
            result = _ollama.list()
            models = result.models if hasattr(result, 'models') else []
            return [m.model for m in models] or ["llama3:latest"]
        except Exception:
            return ["(Ollama not running?)"]

    def set_model(self, model_name):
        self.model = model_name

    def set_backend(self, backend):
        self.backend = backend
        self._load_env()

    def test_connection(self):
        """Test the current backend connection."""
        try:
            if self.backend == "ollama":
                if _ollama is None:
                    return False, "ollama package not installed"
                models = _ollama.list()
                return True, f"Connected — {len(models.models)} models available"
            elif self.backend == "grok":
                resp = requests.get(
                    f"{BACKENDS['grok']['api_base']}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10
                )
                return resp.status_code == 200, f"HTTP {resp.status_code}"
            elif self.backend == "openai":
                resp = requests.get(
                    f"{BACKENDS['openai']['api_base']}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10
                )
                return resp.status_code == 200, f"HTTP {resp.status_code}"
            else:
                return False, f"Unknown backend: {self.backend}"
        except Exception as e:
            return False, str(e)

    def generate_response(self, history):
        """
        Generate a response from the current backend.
        
        Args:
            history: list of {"role": "user/assistant/system", "content": str}
        
        Returns:
            str: The model's response text
        """
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        if self.soul and self.soul.get('preamble'):
            messages.append({"role": "system", "content": self.soul['preamble']})
        messages += history

        try:
            if self.backend == "ollama":
                return self._ollama_chat(messages)
            elif self.backend in ("grok", "openai"):
                return self._openai_compatible_chat(messages)
            elif self.backend == "anthropic":
                return self._anthropic_chat(messages)
            else:
                return f"[Error] Unknown backend: {self.backend}"
        except Exception as e:
            return f"[Error] {self.backend}: {str(e)}"

    def _ollama_chat(self, messages):
        if _ollama is None:
            return "[Error] ollama package not installed"
        resp = _ollama.chat(model=self.model, messages=messages, stream=False)
        return resp.message.content

    def _openai_compatible_chat(self, messages):
        """Works with any OpenAI-compatible API (OpenAI, Grok, etc.)."""
        if not self.api_key:
            return f"[Error] No API key set for {self.backend}"
        backend_def = BACKENDS[self.backend]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 1024
        }
        resp = requests.post(
            f"{backend_def['api_base']}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _anthropic_chat(self, messages):
        """Anthropic Messages API."""
        if not self.api_key:
            return "[Error] No API key set for Anthropic"
        # Separate system from conversation messages
        system_parts = []
        conversation = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                conversation.append(msg)

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": conversation,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)

        resp = requests.post(
            f"{BACKENDS['anthropic']['api_base']}/messages",
            json=payload,
            headers=headers,
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(
            block["text"] for block in data["content"]
            if block["type"] == "text"
        )
