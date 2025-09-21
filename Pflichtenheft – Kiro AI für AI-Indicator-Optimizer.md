Hier ist das detaillierte **Pflichtenheft** für „**Kiro AI**“ zur Mitarbeit an deinem Projekt, mit besonderem Fokus auf **MiniCPM-4.1-8B-Marlin**, **Fine-Tuning** und **Implementierung** inklusive **CPM.cu**-Pfad. Ich liefere das maximal präzise aus meinem Stand heraus. (Hinweis: Da Web-Suche hier deaktiviert ist, markiere ich an kritischen Stellen „**VERIFY**“, wo ihr die exakten Details in der jeweiligen HuggingFace-Repo/README bitte noch gegenprüft.)

---

# Pflichtenheft – Kiro AI für AI-Indicator-Optimizer

## 1. Ziel & Scope

**Ziel:**  
Kiro AI soll ein produktionsreifes, multimodales KI-Subsystem mit **MiniCPM-4.1** aufbauen, das:

1. **Textaufgaben** (Strategie-Erklärung, Pine-Script-Generierung, Entscheidungs-Begründung) mit **MiniCPM-4.1-8B-Marlin** performant ausführt.

2. **Visuelle Chartanalyse** (Pattern aus Chart-Bildern) mit einem **Vision-Pendant** von MiniCPM-4.1 (z. B. „4.1-V“ / „Vision“) erledigt.

3. **Beide Pfade** sauber orchestriert (Vision→Features→Textmodell) und in die bestehende Trading-Pipeline (Backtesting, Position-Sizing, NautilusTrader-Integration) integriert.

**Out-of-Scope:**  
Kein persönliches Finanz-Advisory; keine Trade-Ausführung ohne explizite Freigabe.

---

## 2. Stakeholder & Verantwortlichkeiten

- **Owner/Tech Lead (du):** Architektur, Priorisierung, finale Freigaben.

- **Kiro AI (dieses Pflichtenheft):** Umsetzungsvorschläge, Code-Gerüste, Evaluations-/Test-Pläne, Dokumentation.

- **Ops/Infra:** GPU-Cluster (RTX 5090), Storage, CI/CD, Monitoring.

- **Quant-Support:** Metriken, Backtests, Datenkuration.

---

## 3. Systemübersicht (High-Level)

```
        ┌───────────── Data Layer ─────────────┐
        │  Dukascopy (Tick/Bar)  •  Images     │
        └───────────────────────────────────────┘
                       │
             Feature/Chart Pipeline
                       │
        ┌──── Vision Path ───┐     ┌── Text Path (Marlin) ──┐
        │ MiniCPM-4.1-Vision │ ==> │ MiniCPM-4.1-8B-Marlin  │
        └──────────┬─────────┘     └──────────┬─────────────┘
                   │ features/json            │ prompts
                   └─────────► Orchestrator ◄─┘
                                   │
                           Strategy Builder
                                   │
                         NautilusTrader Adapter
```

---

## 4. Technologiewahl & Begründung

### 4.1 MiniCPM-4.1-8B-Marlin (Text)

- **Warum?** Sehr gutes **Speed/Latency-Profil** dank Marlin-Kernels (quant./weight-only-Beschleunigung; **VERIFY**: Marlin-Format & Runtimes der Repo), ausreichend Qualität für Reasoning, Code-Gen und „Chain-of-Thought-Light“.

- **Stärken:** Niedrige Latenz, guter Throughput, stabile 8B-Qualität für Textaufgaben.

- **Trade-offs:** Marlin-spezifische Pipelines (z. B. vLLM/Triton) – **kein** direkter Mix mit **CPM.cu** in derselben Pipeline (zwei getrennte Inferenzpfade).

### 4.2 MiniCPM-4.1-Vision (Bild/Chart)

- **Warum?** Chart-Erkennung benötigt ein Vision-Encoder-gekoppeltes LLM aus demselben Ökosystem.

- **Stärken:** Natives Vision+Text, reduziert Glue-Code.

- **Trade-offs:** Evtl. nicht als „Marlin“ erhältlich → Standard-HF/FP16/8-bit-Pfad.

### 4.3 CPM.cu (Custom CUDA-Inferenz von OpenBMB)

- **Was ist das?** Low-Level-CUDA-Kernels & Engine (Dateien wie `CPM.cu`) für **Max-Performance** mit MiniCPM (**separater** Pfad von Marlin/vLLM).

- **Wann nutzen?** Wenn ihr **OpenBMBs eigene Inferenzlaufzeit** bauen wollt (CMake/nvcc) und **direkt** in Python/C++ bindet.

- **Trade-off:** Build-/Maintenance-Aufwand; HF/vLLM-Kompatibilität eingeschränkt.

- **Konsequenz:** Für **dieses Projekt** empfehlen wir **Primärpfad: Marlin** (Text) + **Standard-Vision-Pfad**, **Sekundärpfad (optional): CPM.cu-Build** als Alternative/Benchmark.

---

## 5. Funktionale Anforderungen

1. **Prompt-→-Pine-Script**: LLM generiert und erklärt Strategien (Ein-/Ausstieg, SL/TP, Parameter).

2. **Chart-→-Pattern**: Vision-Pfad extrahiert Muster/Features (z. B. Double-Top, Range, Volatilität), liefert strukturierte JSON-Features.

3. **Fusion**: Orchestrator baut finalen Prompt für das Marlin-Modell (Features + Historie + Policies).

4. **Erklärbarkeit**: strukturierte Reasoning-Felder (JSON mit `decision`, `confidence`, `assumptions`).

5. **Sichere Ausführung**: Guardrails (z. B. keine gefährlichen Ordergrößen).

6. **Backtesting-Loop**: Generierte Strategien automatisch prüfen (Sharpe, PF, MDD).

7. **NautilusTrader-Adapter**: Echtzeitfähig, idempotente Orders, Slippage/Fees modelliert.

---

## 6. Nicht-funktionale Anforderungen

- **Latenz**: Text-Inference P95 ≤ 400 ms @ 2k tokens; Vision-Pfad P95 ≤ 700 ms (RTX 5090).

- **Durchsatz**: ≥ 8 gleichzeitige Pipelines.

- **Robustheit**: Circuit-Breaker, Retries, Fallback-Modelle.

- **Reproduzierbarkeit**: deterministische Seeds, Versionierung (Model, Tokenizer, Datasets).

- **Compliance**: Lizenz-Check der MiniCPM-Modelle (**VERIFY** Lizenz auf HF).

- **Security**: API-Auth, Prompt sanitization, no secrets im Prompt.

---

## 7. Daten & Prompting

### 7.1 Datenschemata (SFT/DPO-fähig)

```json
// SFT-Beispiel (Text-only, Marlin)
{
  "task": "pine_gen",
  "context": {
    "symbol": "EURUSD",
    "timeframe": "M15",
    "features": {"rsi": 68.2, "bb_width": 1.5, "range_state": "trending"},
    "constraints": {"max_drawdown": 0.1, "max_leverage": 5}
  },
  "instruction": "Erzeuge eine konservative Mean-Reversion-Strategie in Pine v5.",
  "output": {
    "pine": "...",
    "explanation": "..."
  }
}
```

```json
// Vision→JSON (Vorverarbeitung)
{
  "chart_meta": {"tf":"M15","symbol":"EURUSD","ts":"2025-03-01T10:00:00Z"},
  "vision_findings": {
    "pattern":"double_top",
    "strength":0.73,
    "volatility":"elevated",
    "support_resistance":[1.0835,1.0860]
  }
}
```

### 7.2 Prompt-Template (Fusion)

```text
SYSTEM:
Du bist ein Trading-Assistent. Befolge strikt die Policies und gib JSON zurück.

USER:
Kontext:
{context_json}

Vision-Analyse:
{vision_json}

Aufgabe:
Erzeuge Pine Script v5 mit konservativem Risikomanagement.
Gib zurück:
{
 "pine": "...",
 "rationale": "...",
 "risk": {"max_dd": ..., "sl": ..., "tp": ...}
}
```

---

## 8. Modell-Setups (drei Pfade)

### 8.1 Primär: **MiniCPM-4.1-8B-Marlin** via vLLM (empfohlen)

**Assumption/VERIFY:** Repo nennt exakten Weight-/Runtime-Pfad.

**Inferenz-Server (vLLM):**

```bash
# VERIFY: korrekter Modellbezeichner lt. HuggingFace
pip install vllm==<compatible> transformers accelerate
python -m vllm.entrypoints.api_server \
  --model openbmb/MiniCPM-4.1-8B-Marlin \
  --dtype half --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --port 8000
```

**Client (Python):**

```python
import requests, json

def generate(prompt: str):
    payload = {
        "model": "openbmb/MiniCPM-4.1-8B-Marlin",  # VERIFY
        "prompt": prompt,
        "max_tokens": 1024,
        "temperature": 0.2
    }
    r = requests.post("http://localhost:8000/generate", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["text"]

print(generate("Erzeuge Pine v5 für Mean-Reversion auf EURUSD M15."))
```

### 8.2 Vision-Pfad: **MiniCPM-4.1-Vision** (HF Transformers)

```python
from transformers import AutoProcessor, AutoModelForVision2Seq  # VERIFY exact classes
import torch, PIL.Image as Image

device = "cuda" if torch.cuda.is_available() else "cpu"
proc = AutoProcessor.from_pretrained("openbmb/MiniCPM-4.1-V", trust_remote_code=True)  # VERIFY
model = AutoModelForVision2Seq.from_pretrained(
    "openbmb/MiniCPM-4.1-V", torch_dtype=torch.float16, device_map="auto", trust_remote_code=True
)

img = Image.open("chart.png").convert("RGB")
inputs = proc(images=img, text="Analysiere Pattern und liefere JSON.", return_tensors="pt").to(device)
with torch.inference_mode():
    out = model.generate(**inputs, max_new_tokens=512)
vision_json = proc.batch_decode(out, skip_special_tokens=True)[0]
```

### 8.3 Alternativ/Benchmark: **CPM.cu** (OpenBMB-Custom Engine)

**Build (High-Level, VERIFY konkrete Schritte in Repo):**

```bash
git clone https://github.com/OpenBMB/<cpm_engine_repo>.git  # VERIFY
cd cpm_engine && pip install -r requirements.txt
python setup.py build_ext --inplace  # oder: ./build.sh (VERIFY)
```

**Python-Binding (hypothetisches Beispiel):**

```python
from cpm_engine import CPMEngine  # VERIFY Modulname
engine = CPMEngine(model_path="/weights/minicpm-4.1-8b", dtype="fp16", device="cuda")
text = engine.generate("Erkläre Double-Top in JSON.")
```

**Hinweis:** **Marlin** und **CPM.cu** sind **separate** Beschleunigungswege. Eine Pipeline nutzt **entweder** vLLM/Marlin **oder** CPM.cu.

---

## 9. Fine-Tuning – detaillierter Ablauf (PEFT/QLoRA)

### 9.1 Ziele

- SFT (Supervised Fine-Tuning) für **Domänen-Sprache**, **Pine-Gen-Stil**, **Risikopolicies**.

- Optional **DPO/ORPO** (Bevorzugungs-Feintuning) auf Vergleichspaaren (gute vs. schlechte Strategien).

- Vision-Pfad: Light-Adapter (LoRA auf Text-Decoder) für Chart-Spezifika.

### 9.2 Datenaufbereitung (Schritte)

1. **Sammlung**: Eigene Prompt→Pine Beispiele, Backtest-Ergebnisse, Erklärtexte.

2. **Normalisierung**: Einheitliche JSON-Schemas (oben).

3. **Filter**: Entferne leaky/unstete Beispiele; ent-dupliziere.

4. **Splits**: train/val/test (70/15/15), „by time“ splitten.

5. **Eval-Sets**: „Hard“ Sätze (Low-Vol, News-Spikes, Range vs Trend).

### 9.3 Training (Text, Marlin-Pfad; LoRA/QLoRA)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType
import bitsandbytes as bnb
import torch, datasets

model_id = "openbmb/MiniCPM-4.1-8B-Marlin"  # VERIFY
tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

base = AutoModelForCausalLM.from_pretrained(
    model_id,
    load_in_8bit=True,  # QLoRA
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)

lconf = LoraConfig(
    r=64, lora_alpha=16, lora_dropout=0.05,
    target_modules=["q_proj","k_proj","v_proj","o_proj"],  # VERIFY module names
    task_type=TaskType.CAUSAL_LM
)
model = get_peft_model(base, lconf)

train = datasets.load_from_disk("data/sft_train")
val   = datasets.load_from_disk("data/sft_val")

def collate(batch):
    # tokenize to input_ids/labels with EOS; apply truncation to 4k
    ...

args = TrainingArguments(
    output_dir="out/minicpm_sft",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    num_train_epochs=2,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=10,
    eval_steps=200,
    save_steps=200,
    bf16=True,
    gradient_checkpointing=True,
    report_to=["wandb"]
)

trainer = Trainer(model=model, args=args, train_dataset=train, eval_dataset=val, data_collator=collate)
trainer.train()
model.save_pretrained("out/minicpm_sft_lora")
tok.save_pretrained("out/minicpm_sft_lora")
```

**Wichtig:**

- **Marlin-Gewichte** sind ggf. **inference-optimiert**; Feintuning erfolgt i. d. R. auf **HF-kompatiblen FP16/8-bit-Pfaden** mit **LoRA-Adaptern** (Adapter separat speichern). **VERIFY** in Repo, ob LoRA auf Marlin-Checkpoint direkt gestützt wird; notfalls **Base-FP16** nehmen und nach dem SFT quantisieren/servieren.

### 9.4 DPO/ORPO (optional)

- Trainiert auf (prompt, response_good, response_bad) → verbessert Präferenzen (z. B. risikoarm statt überheblich).

- **Ablauf:** SFT-Checkpoint → DPO-Trainer (TRL) → kleiner LR, 1–2 Epochen.

### 9.5 Vision-Adapter (Light LoRA)

- Gleiche Vorgehensweise auf dem Decoder-Teil, geringe r-Werte (8–16), kleines Budget; trainiere nur wenige Epochen.

### 9.6 Validierung

- **Text**: Perplexity ↓, Pass@k für Pine-Gen, Policy-Konformität (JSON-Validator).

- **Task-Eval**: Backtests (Sharpe, PF, MDD), Refusals/Guardrails-Rate, Regeltreue.

- **Vision**: Accuracy auf Pattern-Labels, Korrelation mit Backtest-Outcomes.

---

## 10. Serving & Orchestrierung

### 10.1 Text (Marlin)

- **vLLM-Server** (s. oben), **Autoscaling** (GPU Util 80–90%), **token-throughput** Metriken.

- **Request-Schema** (JSON): `context_json`, `vision_json`, `instruction`, Limits (`max_tokens`, `temp`, `stop`).

### 10.2 Vision

- HF-Pipeline per **Triton**/**TorchServe** oder als Python-Microservice (uvicorn).

- Pre/Post-Processing standardisieren (gleiche Chart-Renditions).

### 10.3 Orchestrator

```python
class Orchestrator:
    def run(self, chart_png: bytes, context: dict, instruction: str):
        vision_json = self.vision.analyze(chart_png)
        prompt = self.prompt_builder(context, vision_json, instruction)
        text_out = self.marlin.generate(prompt)
        return self.postprocess(text_out)
```

---

## 11. Integration in NautilusTrader

- **Signal-Adapter**: JSON→Order-Intents (Buy/Sell/Flat, Size, SL/TP).

- **Risiko-Layer**: Caps (Kelly-max, DD-Guard), Vol-Scaler, Circuit-Breaker.

- **Backtesting**: Walk-forward, Fees/Slippage/Latency, Distribution-Shift-Checks.

- **Echtzeit**: Warm-start der Modelle, identische Feature-Pipeline.

---

## 12. Monitoring & QA

- **Model-Metrics**: latency, tokens/s, OOM-Rate, error classes.

- **Business-Metrics**: Sharpe, PF, MDD, Hit-Rate per Regime.

- **Data-Drift**: Feature-drift Stats, Alerting.

- **A/B-Tests**: neue Adapter vs. alte.

- **Eval Dashboards**: W&B/MLflow + Prometheus/Grafana.

---

## 13. Risiken & Gegenmaßnahmen

- **Lizenz/Compliance (VERIFY)** → Freigabe dokumentieren.

- **Quantization-Mismatch** → LoRA auf Base-FP16 trainieren; Serving quantisiert.

- **CPM.cu Build-Fragilität** → als optionalen Pfad führen, CI-Jobs mit CCache.

- **Prompt-Injection** → Sanitizer, Output-Schema-Validator.

- **Overfitting** → hold-out, „hard“ eval-sets, early-stopping.

---

## 14. Abnahmekriterien

- P95-Latenz (Text) ≤ 400 ms bei 2k Tokens; Vision ≤ 700 ms.

- Pine-Gen JSON valide, Policies eingehalten (≥ 99% gültige Antworten).

- Backtest-Mindestkriterien (projekt-spezifisch definieren).

- Reproduzierbares SFT (Seeded), Versionierung vollständig.

- Monitoring + Alerting produktiv.

---

## 15. Umsetzungsfahrplan (Milestones)

1. **M1 – Infra & Serving (2 Wochen)**: vLLM/Marlin live; Vision-Service; Orchestrator MVP.

2. **M2 – SFT v1 (2–3 Wochen)**: Datensets, LoRA-SFT, erste Eval, Guardrails.

3. **M3 – DPO/ORPO (1–2 Wochen)**: Präferenzfit, Policy-Tuning.

4. **M4 – Backtesting-Harness (1 Woche)**: Auto-Eval, Reports, CI-Gates.

5. **M5 – NautilusTrader (1–2 Wochen)**: Live-Adapter, Safety-Caps, Monitoring.

6. **M6 – Optional CPM.cu (1 Woche)**: Build, Benchmark, Dokumentation.

---

## 16. Beispiel-Code (kompakt)

**Marlin-Client (OpenAI-kompatibel via vLLM, falls aktiviert):**

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="na")

def gen(context_json, vision_json, instruction):
    prompt = f"SYSTEM: ...\nUSER:\nKontext:\n{context_json}\nVision:\n{vision_json}\nAufgabe:\n{instruction}"
    resp = client.chat.completions.create(
        model="openbmb/MiniCPM-4.1-8B-Marlin",  # VERIFY
        messages=[{"role":"user","content":prompt}],
        temperature=0.2, max_tokens=1024
    )
    return resp.choices[0].message.content
```

**SFT-Inference mit LoRA-Adaptern:**

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

base_id = "openbmb/MiniCPM-4.1-8B-Marlin"  # oder Base-FP16, VERIFY
tok = AutoTokenizer.from_pretrained(base_id, trust_remote_code=True)
base = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True)
model = PeftModel.from_pretrained(base, "out/minicpm_sft_lora")

def infer(prompt):
    ids = tok(prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        out = model.generate(**ids, max_new_tokens=512, temperature=0.2)
    return tok.decode(out[0], skip_special_tokens=True)
```

**CPM.cu – nur als Demo-Gerüst (VERIFY in Repo):**

```python
# Achtung: Platzhalter – exakte API im OpenBMB-Repo prüfen
from cpm_engine import CPMEngine
eng = CPMEngine("/weights/minicpm_8b", gpu=0, dtype="fp16")
print(eng.generate("Gib Pine v5 JSON-konform aus."))
```

---

## 17. To-Dos für Kiro AI (konkret)

- **VERIFY**: HF-Repo-Readme (Modell-IDs, Lizenz, Marlin-Serving-Pfad).

- vLLM-Serving für **MiniCPM-4.1-8B-Marlin** auf RTX 5090 aufsetzen, Benchmarks erfassen.

- Vision-Service (MiniCPM-4.1-V) integrieren, JSON-Normalisierung.

- SFT-Dataset finalisieren, LoRA-Trainingslauf (QLoRA) + Eval.

- DPO/ORPO auf Präferenz-Paare (sichere, regelkonforme Strategien).

- Orchestrator-API stabilisieren (Schemas, Contracts, Tests).

- NautilusTrader-Adapter mit Safety-Caps.

- Optional: **CPM.cu** bauen und Latenz/Throughput vs. Marlin vergleichen.

- Vollständige Doku + CI/CD + Monitoring.

---

### Kurzfazit

- **MiniCPM-4.1-8B-Marlin** ist für **Text-Teil** (Strategie-Gen/Erklärung) ideal: **schnell & effizient**.

- **Vision-Pfad** ergänzt für Chart-Verständnis (separate Pipeline).

- **CPM.cu** ist ein **alternativer** High-Performance-Pfad (separat halten, benchmarken).

- Sorgfältiges **SFT (QLoRA) + optional DPO** bringt domänenspezifische Qualität bei vertretbaren Kosten/Latenzen.

Wenn du willst, erstelle ich dir direkt die **vLLM-Startskripte + Dockerfile** und ein **funktionierendes SFT-Template-Repo** mit Datenschemata und Makefile.
