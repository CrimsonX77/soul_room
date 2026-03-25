# Soul Room

**Multi-model AI collaboration framework. Multiple AI cores — different architectures, different reasoning — in one room, cooperating in real time.**

This isn't a chatbot with personas. This is Mistral, Llama3, Qwen, Grok, and any other model you want, each running as an independent participant in a shared conversation space. The human is an *optional participant*, not a mandatory operator.

```
┌─────────────────────────────────────────────────┐
│                  SOUL ROOM (port 7700)          │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Mistral  │  │ Llama3   │  │  Qwen    │     │
│  │ :7710    │  │ :7711    │  │ :7712    │     │
│  │ analyst  │  │ creative │  │ coder    │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │              │              │           │
│       └──────────────┼──────────────┘           │
│                      │                          │
│              ┌───────┴────────┐                 │
│              │  Human (opt.)  │                 │
│              └────────────────┘                 │
└─────────────────────────────────────────────────┘
```

## What Makes This Different

- **Multi-model, not multi-persona.** Each participant runs on a genuinely different AI architecture. Different training data. Different reasoning patterns. Different blind spots. When they collaborate, you get cognitive diversity that a single model can never achieve.
- **Soul YAML identity system.** Each AI loads a structured identity file that defines personality, ethics, capabilities, and communication style — not a hardcoded system prompt, but a living schema that any model can inhabit.
- **Human-optional.** The room runs with or without a human present. Set a topic, let the AIs discuss it, come back to a synthesized result. Or jump in and steer. Your choice.
- **Drop-in connector.** Any interface can join the room with a single import. Build your own frontend, connect an existing tool, or use the included PyQt6 GUI.
- **Self-healing infrastructure.** Automatic port scanning, heartbeat monitoring, stale connection cleanup, diagnostic tooling built in.

## Quick Start

### 1. Install

```bash
git clone https://github.com/YOUR_REPO/soul-room.git
cd soul-room
pip install -r requirements.txt
```

### 2. Start the Room Server

```bash
python -m soul_room.server.room_server
# Room available at http://localhost:7700
```

### 3. Connect a Participant

```python
from soul_room.connector import RoomConnector

# Create a connector for any model
connector = RoomConnector(
    participant_name="Analyst",
    endpoint_port=7710,
    room_url="http://127.0.0.1:7700"
)

# Wire up your LLM response function
def my_llm_respond(message, context, participants):
    # Call Ollama, OpenAI, Anthropic, Grok, local model — anything
    return your_model.generate(message)

connector.set_response_handler(my_llm_respond)
connector.connect()
```

### 4. Load a Soul (Optional)

```python
from soul_room.engine.soul_parser import load_soul_yaml

soul = load_soul_yaml("examples/souls/analyst.yaml")
# The soul gets flattened into a rich system prompt
# Feed it to whatever model backend you're using
```

### 5. Connect More Participants

Repeat step 3 with different models, different ports, different souls.
They'll all hear each other. They'll all respond. The room orchestrates.

## Architecture

```
soul_room/
├── server/
│   └── room_server.py      # Central room — message routing, participant registry
├── engine/
│   ├── chat_engine.py       # Multi-backend LLM interface (Ollama, Grok, OpenAI, etc.)
│   └── soul_parser.py       # Soul YAML loader, auto-repair, system prompt generator
├── connector.py             # Drop-in module — any interface can join the room
├── db/
│   ├── conversation_db.py   # SQLite conversation persistence
│   └── media_db.py          # Shared media gallery storage
└── ui/
    └── main_window.py       # PyQt6 GUI (optional — room works headless too)

examples/
├── souls/
│   ├── analyst.yaml         # Example: analytical reasoning specialist
│   ├── creative.yaml        # Example: creative/divergent thinker
│   └── coder.yaml           # Example: code-focused problem solver
└── configs/
    └── three_model_room.json  # Example: room with 3 different model backends
```

## Soul YAML Format

Souls are flexible — the parser auto-detects schema variations and handles common YAML formatting issues automatically.

```yaml
identity:
  designation: "Analyst"
  soul_type: "reasoning_specialist"
  core_directive: |
    Prioritize logical analysis and evidence-based reasoning.
    Challenge assumptions. Identify blind spots.

expression:
  voice: "precise, measured, occasionally dry humor"
  style: "structured arguments with clear evidence chains"

capabilities:
  strengths:
    - "pattern recognition across large datasets"
    - "identifying logical fallacies"
    - "synthesizing competing viewpoints"
  
ethics:
  holds_sacred: ["intellectual honesty", "evidence over ideology"]
  refuses: ["confirmation bias", "appeals to authority without evidence"]
```

## Configuration

### Environment Variables

```bash
# .env file (auto-encrypted with Fernet)
OLLAMA_HOST=http://localhost:11434
XAI_API_KEY=sk-...          # For Grok backend
OPENAI_API_KEY=sk-...       # For OpenAI backend
DEFAULT_MODEL=llama3:latest
ROOM_PORT=7700
```

### Port Assignments

The room server runs on port 7700 by default. Participants auto-scan the range 7710-7749 for free ports, or you can assign them explicitly.

## Backends

Soul Room works with any LLM backend:

| Backend | Setup | Notes |
|---------|-------|-------|
| **Ollama** | `ollama serve` | Best for local models — Llama3, Mistral, Qwen, Phi, etc. |
| **Grok (xAI)** | API key in .env | Cloud-based, good for high-capability tasks |
| **OpenAI** | API key in .env | GPT-4, GPT-4o, etc. |
| **Anthropic** | API key in .env | Claude models |
| **Custom** | Implement response handler | Any HTTP endpoint, local or remote |

Mix and match. Put Llama3 on analysis, Mistral on creative writing, Grok on fact-checking — all in the same room, all hearing each other.

## Use Cases

- **Research synthesis** — Multiple models analyze a paper from different angles, debate findings, produce a synthesized summary
- **Code review** — One model writes, another reviews, a third tests edge cases
- **Creative collaboration** — Different models contribute different creative styles to a shared project  
- **Decision support** — Models argue different sides of a decision, human makes the final call
- **Autonomous agents** — Set a goal, let the room self-organize toward it

## Credits

Built by Crimson Valentine / RedstruckSolo550.
Born from the RedVerse project — two years of building AI companion infrastructure from scratch.

## License

MIT
