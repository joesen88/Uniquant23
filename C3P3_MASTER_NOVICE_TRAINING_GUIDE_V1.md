# C3P3 Master/Novice — Guide vom Modelldownload bis zum Training

Version V1 · 06.09.2026 · Linux/Ubuntu · zwei lokale Rechner

## 1. Was du jetzt hast und was für Training noch fehlt

Du hast die vier Lehrermodelle heruntergeladen. Dieser Guide führt durch deren lokalen Betrieb, die Einrichtung des Schülerrechners, den notwendigen CODE-Integrationsschritt und die anschließenden Trainingsläufe.

**Entscheidender Befund aus der Quellprüfung:** Das verfügbare `C3P3_MEMORY_CORE_ATLAS_PAKET_A_IMPLEMENTIERT_V1.zip` enthält noch keinen Coding-Trainer. `src/code_learning/`, `TASK_DOMAIN` und die CODE-Registry fehlen. Im vorhandenen `start.py` ist die Trading-Registry fest importiert. **`PHASE=7` startet darin Trading-Memory-RL. Das Eintragen eines ungenutzten `TASK_DOMAIN="CODE"` ändert das nicht.**

Deshalb sind die Abschnitte ausdrücklich gekennzeichnet:

| Abschnitt | Status / Ergebnis |
|---|---|
| 2–7 | Jetzt ausführbare Einrichtung: Modelle, llama.cpp, GPU, LAN und Containergrundlage |
| 8 | Notwendiger Implementierungsauftrag für deinen C3P3-Coding-Pfad |
| 9–12 | Konkrete Startfolge und Abnahme nach dieser Integration |
| 13–15 | Fehlerbehebung, Lieferumfang und Quellen |

Der Guide liefert drei ausführbare Hilfsskripte. Er liefert **keinen bereits integrierten C3P3-Coding-Trainer**. Die vorhandene Projektbasis und die bisherigen Implementierungsverträge sind im Begleitpaket enthalten; der fehlende Code wird nicht durch erfundene Startbefehle ersetzt.

## 2. Rollen und Verzeichnisse

| Rechner | Hardware | Arbeit |
|---|---|---|
| PC 1 — Master | RTX 4080, 16 GB VRAM, 32 GB RAM | Jeweils ein eingefrorenes Lehrermodell, HTTP-Server |
| PC 2 — Novice | RTX 5070, 12 GB VRAM, 96 GB RAM | Eigene C3P3-Fibre-Gewichte trainieren, Python ausführen, Aufgaben und Erfahrungen verwalten |

Das LAN überträgt Aufgaben und Antworten. Die GPUs werden nicht zu einem gemeinsamen Speicher zusammengelegt. In der Evaluation arbeitet der Schüler ohne Lehrerhilfe.

**Erstes Lernziel:** Kleine Python-Funktionen reparieren. Der Schüler bewertet aus dem sichtbaren Code erzeugte Patchkandidaten, sagt deren Wirkung voraus und lernt aus tatsächlich ausgeführten Versuchen. Freie Codegenerierung benötigt später einen eigenen Decoder.

Referenz ist natives Ubuntu/Linux. Die Installationsschritte brauchen zunächst Internet. Nach vollständiger Bereitstellung kann der Betrieb lokal erfolgen. Für das CODE-AST-Schema verwenden wir wie im Entwurf Python **3.11**.

Entpacke das Guide-Paket auf beiden PCs, beispielsweise:

```bash
sudo apt update
sudo apt install -y unzip
mkdir -p "$HOME/c3p3-guide"
unzip "$HOME/Downloads/C3P3_MASTER_NOVICE_TRAINING_GUIDE_V1.zip" -d "$HOME/c3p3-guide"
export C3P3_GUIDE="$HOME/c3p3-guide/C3P3_MASTER_NOVICE_TRAINING_GUIDE_V1"
cd "$C3P3_GUIDE"
```

Wenn dein Download woanders liegt, ersetze ausschließlich diesen Pfad. Auf einem neuen Terminal `C3P3_GUIDE` erneut setzen. Die folgenden Shellvariablen bezeichnen Installationspfade; sie sind keine zweite Trainingskonfiguration.

## 3. PC 1: Modelle und CUDA-Runtime

### 3.1 Dateien zuordnen

Lege die bereits heruntergeladenen Dateien in einen gemeinsamen Ordner, etwa `$HOME/c3p3-teachers/models`. Bei bereits bestehendem Modellordner verwende dessen tatsächlichen Pfad.

| Auswahl im Hilfsskript | Exakter Dateiname | Serveralias | Q4_K_M-Dateigröße |
|---|---|---|---:|
| `qwen` | `qwen2.5-coder-14b-instruct-q4_k_m.gguf` | `c3p3-qwen` | ca. 8,99 GB |
| `phi` | `Phi-4-reasoning-plus-Q4_K_M.gguf` | `c3p3-phi` | ca. 9,05 GB |
| `ministral` | `Ministral-3-14B-Instruct-2512-Q4_K_M.gguf` | `c3p3-ministral` | ca. 8,24 GB |
| `gemma` | `gemma-4-12b-it-Q4_K_M.gguf` | `c3p3-gemma` | ca. 7,12 GB |

Das sind Dateigrößen. Kontextcache und Rechenpuffer benötigen zusätzlich VRAM. Die vier Dateien werden auf der SSD gesammelt; in der GPU liegt jeweils ein Lehrer. Siehe die [Qwen-Dateien](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF/tree/main), [Phi-Dateien](https://huggingface.co/unsloth/Phi-4-reasoning-plus-GGUF/tree/main), [Ministral-Dateien](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512-GGUF/tree/main) und [Gemma-Dateien](https://huggingface.co/unsloth/gemma-4-12b-it-GGUF/tree/main).

```bash
export C3P3_MODELS="$HOME/c3p3-teachers/models"
python3 "$C3P3_GUIDE/tools/teacher.py" inventory --models-dir "$C3P3_MODELS"
```

Die Inventur prüft Vorhandensein und GGUF-Kennung. Eine einmalige eigene Dateihash-Inventur ist zusätzlich möglich:

```bash
python3 "$C3P3_GUIDE/tools/teacher.py" inventory --models-dir "$C3P3_MODELS" --sha256
```

Das liest alle vier Dateien vollständig und kann dauern. Ein selbst berechneter Hash fixiert deine Dateiidentität; er ist ohne Vergleich mit einer veröffentlichten Prüfsumme noch keine unabhängige Bestätigung des Downloads.

### 3.2 Treiber und Compiler unterscheiden

```bash
nvidia-smi
nvcc --version
```

`nvidia-smi` muss die RTX 4080 zeigen. Dessen CUDA-Zeile beschreibt die Treiberunterstützung. `nvcc` weist den tatsächlich installierten CUDA-Compiler nach. Für den folgenden Quellbuild brauchst du beide. [NVIDIA-Dokumentation](https://docs.nvidia.com/deploy/nvidia-smi/index.html)

Falls `nvcc` fehlt: Nutze die [NVIDIA-CUDA-Auswahl](https://developer.nvidia.com/cuda-downloads), wähle **Linux → x86_64 → Ubuntu → deine tatsächlich installierte Version**, und installiere das dazu passende Toolkit. Die Ubuntu-Version zeigt `cat /etc/os-release`. Toolkit- und Treiberversion gemäß [NVIDIA-Linux-Anleitung](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/) abstimmen. Dieser Guide errät deine Ubuntu-Version nicht.

### 3.3 llama.cpp mit CUDA bauen

```bash
sudo apt update
sudo apt install -y git cmake build-essential curl libssl-dev python3

mkdir -p "$HOME/c3p3-teachers/runtime"
cd "$HOME/c3p3-teachers/runtime"
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
cd llama.cpp

cmake -S . -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=89

cmake --build build --config Release --target llama-server -j 8

./build/bin/llama-server --version
./build/bin/llama-server --list-devices

mkdir -p "$HOME/c3p3-teachers/metadata"
git rev-parse HEAD > "$HOME/c3p3-teachers/metadata/llama_cpp_commit.txt"
sha256sum build/bin/llama-server > "$HOME/c3p3-teachers/metadata/llama_server.sha256"
```

`89` ist die Compute Capability der RTX 4080. Dieses Binary ist für PC 1 gebaut. Die RTX 5070 verwendet für den Schüler PyTorch. `-j 8` ist eine einstellbare Zahl paralleler Compilerjobs. Nach erfolgreicher Einrichtung den llama.cpp-Commit während eines Versuchs beibehalten. [Buildanleitung](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md), [GPU-Tabelle](https://developer.nvidia.com/cuda/gpus)

Bei einem bereits vorhandenen Checkout direkt in dessen Ordner wechseln. Wenn CMake `nvcc` nicht findet, dessen tatsächlichen Pfad explizit mit `-DCMAKE_CUDA_COMPILER=/tatsaechlicher/pfad/nvcc` setzen.

## 4. PC 1: Ersten Lehrer starten

### 4.1 Schlüssel einmalig erstellen

Der schon bestehende Dual-PC-Entwurf verwendet einen lokalen Zugriffsschlüssel. Er bleibt eine Datei außerhalb von Prompts, Trainingsdaten und Checkpoints.

```bash
python3 - <<'PY'
from pathlib import Path
import os
import secrets

folder = Path.home() / "c3p3-teachers" / "secrets"
folder.mkdir(parents=True, exist_ok=True)
folder.chmod(0o700)
path = folder / "teacher.key"
if not path.exists():
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(secrets.token_urlsafe(32) + "\n")
print("Schlüsseldatei vorhanden:", path)
PY
```

Kopiere **diese Datei** auf PC 2 nach `$HOME/c3p3-teachers/secrets/teacher.key`, zum Beispiel per USB oder über deine vorhandene lokale Dateifreigabe. Auf PC 2 keinen abweichenden Schlüssel erzeugen.

### 4.2 Qwen im Vordergrund starten

```bash
export C3P3_SERVER="$HOME/c3p3-teachers/runtime/llama.cpp/build/bin/llama-server"
export C3P3_MODELS="$HOME/c3p3-teachers/models"

python3 "$C3P3_GUIDE/tools/teacher.py" serve \
  --teacher qwen \
  --server "$C3P3_SERVER" \
  --models-dir "$C3P3_MODELS" \
  --host 0.0.0.0 --port 8080 \
  --ctx 4096 --parallel 1 \
  --gpu-layers 99 --batch 256 --ubatch 128 \
  --key-file "$HOME/c3p3-teachers/secrets/teacher.key"
```

Dieses Terminal bleibt offen. Ein erstmaliger Modellstart kann dauern. Im Serverlog müssen CUDA-Gerät und die tatsächlich auf die GPU ausgelagerten Layer erkennbar sein. Die Einstellungen sind Startwerte; es gibt hier keine gemessene Tok/s-Zusage.

Das Hilfsskript nutzt die im GGUF vorhandene Chatvorlage mit `--jinja` und reinen Textbetrieb mit `--no-mmproj`. Es installiert nichts und lädt keine Modelle aus dem Netz nach.

### 4.3 Antwort lokal prüfen

In einem zweiten Terminal auf PC 1:

```bash
export C3P3_GUIDE="$HOME/c3p3-guide/C3P3_MASTER_NOVICE_TRAINING_GUIDE_V1"

python3 "$C3P3_GUIDE/tools/teacher.py" probe \
  --teacher qwen \
  --base-url http://127.0.0.1:8080/v1 \
  --key-file "$HOME/c3p3-teachers/secrets/teacher.key" \
  --timeout 180 --max-tokens 256
```

Die Probe prüft Bereitschaft, Modellalias und eine echte Textantwort. Sie sendet nur eine einfache Rechenfrage. Prüfe auch den Antwortinhalt. Ein erfolgreicher HTTP-Aufruf belegt noch keine brauchbaren Coding-Demonstrationen.

`finish_reason=length`, leere Endantworten und Netzwerkfehler gelten als fehlgeschlagene Probe. Reasoningtext wird nicht als fertige Lösung ausgegeben. Siehe [llama.cpp-Serververtrag](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

## 5. PC 2: GPU und Python einrichten

### 5.1 NVIDIA prüfen

```bash
nvidia-smi
```

Erwartet: RTX 5070, ungefähr 12 GB VRAM. Für Blackwell verwenden wir den im Entwurf festgelegten PyTorch-Build **2.8.0 mit CUDA 12.8**. Dies ist eine gepinnte Referenzversion, keine Behauptung über die aktuell neueste Version. Blackwell-Unterstützung kam mit PyTorch 2.7. [PyTorch-Versionen](https://pytorch.org/get-started/previous-versions/), [Blackwell-Unterstützung](https://pytorch.org/blog/pytorch-2-7/)

### 5.2 Python 3.11 in einer eigenen Umgebung

Wenn `python3.11` bereits vorhanden ist:

```bash
mkdir -p "$HOME/venvs"
python3.11 -m venv "$HOME/venvs/c3p3-code"
```

Wenn Python 3.11 fehlt, ist dieser Weg über eine separate uv-Installation möglich:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip

mkdir -p "$HOME/venvs"
python3 -m venv "$HOME/venvs/c3p3-bootstrap"
"$HOME/venvs/c3p3-bootstrap/bin/python" -m pip install uv

"$HOME/venvs/c3p3-bootstrap/bin/uv" python install 3.11
"$HOME/venvs/c3p3-bootstrap/bin/uv" venv --python 3.11 --seed "$HOME/venvs/c3p3-code"
```

[Python-Verwaltung mit uv](https://docs.astral.sh/uv/guides/install-python/), [Umgebungen mit uv](https://docs.astral.sh/uv/pip/environments/)

Danach:

```bash
export C3P3_PY="$HOME/venvs/c3p3-code/bin/python"
"$C3P3_PY" --version
"$C3P3_PY" -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
"$C3P3_PY" -m pip check
```

Für diesen Hardwaretest sind `torchvision` und `torchaudio` unnötig. Die später tatsächlich importierten Projektpakete kommen bei der CODE-Integration hinzu; nur Torch zu installieren macht den alten Trading-Projektbaum nicht automatisch startfähig. PyTorch-Wheels bringen CUDA-Laufzeitbibliotheken mit; für diese Nutzung ist kein eigener `nvcc`-Build auf PC 2 erforderlich. Ein geeigneter NVIDIA-Treiber bleibt Voraussetzung.

### 5.3 Einen echten GPU-Optimizerschritt testen

```bash
"$C3P3_PY" "$C3P3_GUIDE/tools/runtime_check.py" \
  --device cuda --precision bf16 --steps 3 \
  --report "$HOME/c3p3-code-runtime-check.json"
```

Der Test führt aus:

1. Matrixoperationen und Forward auf der GPU.
2. Loss und Backward mit endlichen Gradienten.
3. Drei tatsächliche AdamW-Updates; Gewichtsänderung muss größer als null sein.
4. Speichern und Reload von Modell sowie Optimierer; Ausgaben und Updatezähler werden verglichen.

Im Bericht müssen `device=cuda`, die RTX 5070 und Capability `[12, 0]` stehen. Es gibt keine stille CPU-Ausweichroute. `PASS` bedeutet nur: Diese kleine PyTorch-Rechenkette funktioniert. Es ist **kein Training des Coding-Schülers und kein Nachweis seines Speicherbedarfs**.

Falls BF16 Probleme verursacht, denselben kurzen Test ausdrücklich mit `--precision fp32` wiederholen. Funktioniert nur FP32, wird später diese Änderung in der Modellconfig dokumentiert. Kein automatischer Wechsel in einem laufenden Versuch.

## 6. PC 2: Lehrer über LAN erreichen

Auf PC 1:

```bash
hostname -I
```

Verwende dessen tatsächliche private LAN-IPv4-Adresse. Auf PC 2:

```bash
export C3P3_TEACHER_IP="192.168.178.20"
```

**Die Beispieladresse ersetzen.** `127.0.0.1` bezeichnet auf PC 2 immer PC 2.

```bash
python3 "$C3P3_GUIDE/tools/teacher.py" probe \
  --teacher qwen \
  --base-url "http://$C3P3_TEACHER_IP:8080/v1" \
  --key-file "$HOME/c3p3-teachers/secrets/teacher.key" \
  --timeout 180 --max-tokens 256
```

Falls PC 1 eine aktive UFW-Firewall verwendet, den Zugriff nur von der tatsächlichen PC-2-Adresse freigeben. Beispiel auf PC 1, mit vorher angepasster Adresse:

```bash
export C3P3_NOVICE_IP="192.168.178.21"
sudo ufw allow from "$C3P3_NOVICE_IP" to any port 8080 proto tcp
```

Keine Router-Portfreigabe wird benötigt. Funktioniert die lokale Probe auf PC 1, aber die LAN-Probe nicht, zuerst Adresse, Serverbindung und Firewall prüfen.

## 7. PC 2: Grundlage für isolierte Python-Ausführung

Der Schüler muss vorgeschlagene Programme ausführen können. Der vertrauenswürdige Controller behält Referenzen und verborgene Tests. Kandidatencode erhält nur den zu prüfenden Funktionsinput. Diese Trennung ist Teil des bestehenden C3P3-CODE-Entwurfs.

Für den vorgesehenen CPU-Worker verwenden wir im Guide rootless Podman:

```bash
sudo apt update
sudo apt install -y podman uidmap

podman info
podman pull docker.io/library/python:3.11-slim

mkdir -p "$HOME/c3p3-worker"
podman image inspect docker.io/library/python:3.11-slim \
  --format '{{.Id}}' > "$HOME/c3p3-worker/python_image_id.txt"

export C3P3_WORKER_IMAGE="$(cat "$HOME/c3p3-worker/python_image_id.txt")"

podman run --rm --pull=never \
  --network=none --read-only \
  --user=10000:10000 --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=64 --memory=512m --cpus=1 \
  --tmpfs=/tmp:rw,nosuid,nodev,noexec,size=64m \
  "$C3P3_WORKER_IMAGE" python -I -B -c 'print(sum([2, 3]))'
```

Erwartete Ausgabe: `5`. Der Pull findet nur bei der Einrichtung statt. Die lokale Image-ID fixiert anschließend die Bytes. Dieser bekannte Einzeiler testet die Containergrundlage; er ist noch nicht der Kandidatenrunner. [Podman run](https://docs.podman.io/en/latest/markdown/podman-run.1.html)

Der zu implementierende Runner ergänzt insbesondere: endliches Walltime-Limit, Beenden der ganzen Ausführung bei Timeout, begrenzte Ausgabe, frischen Zustand je unabhängiger Ausführung, typisierte Rückgaben und getrennte Infrastrukturfehler. Die entsprechenden Ressourcenwerte kommen aus `DATA_PARAMS`. Weder GPU noch Projekt-/Testverzeichnis werden in den Kandidatenworker durchgereicht. Eine AST-Prüfung ergänzt diese Ausführung, ersetzt sie aber nicht.

## 8. Der notwendige Entwicklungsschritt: CODE produktiv anschließen

### 8.1 Geprüfte Ausgangsbasis

Im Paket unter `referenzen/` liegen:

- Die unveränderte Paket-A-ZIP samt Prüfbericht.
- `C3P3_CODE_FIBRE_DUAL_PC_UMSETZUNGSSKRIPT_V1.md`: ausführliche Aufgaben-, Architektur-, Loss- und Phasenverträge.
- `C3P3_CODE_SEMANTIK_MEMORY_ATLAS_GESAMTKONZEPT_V2.md`: verbindliche Korrekturen für die Integration.
- `C3P3_CODE_SEMANTIK_LOGIK_TRANSFER_V1.md`: Semantik- und Operationsvertrag.

Paket-A-SHA256: `ae3d1c0e04eb3f423fccda200ea26dbfd792ac3e268ac134610fbb023ceaf752`.

Die Referenzbasis kann auf PC 2 in eine Arbeitskopie entpackt werden:

```bash
mkdir -p "$HOME/c3p3-code"
unzip "$C3P3_GUIDE/referenzen/C3P3_MEMORY_CORE_ATLAS_PAKET_A_IMPLEMENTIERT_V1.zip" \
  -d "$HOME/c3p3-code"

export C3P3_PROJECT="$HOME/c3p3-code/C3P3_MEMORY_CORE_ATLAS_PAKET_A_IMPLEMENTIERT_V1/PROJECT"

python3 "$C3P3_GUIDE/tools/project_status.py" \
  --project "$C3P3_PROJECT" \
  --report "$HOME/c3p3-code-source-status.json"
```

Im unveränderten Paket lautet der Status erwartungsgemäß `CODE_NOT_READY` und der Exitcode ist 2. Das ist ein lesender Bestandsbericht, keine Änderung oder neue Trainingssperre. Bei deiner bereits weiterentwickelten Arbeitskopie setze `C3P3_PROJECT` auf deren tatsächliche Wurzel.

Auch ein späterer Status `CODE_INTEGRATION_INDICATORS_PRESENT` belegt nur Dateien und Configangaben. Die produktive Verdrahtung und ein echter Lernschritt müssen separat nachgewiesen werden.

### 8.2 Arbeitsaufträge in ausführbarer Entwicklungsreihenfolge

Diese Tabelle bezeichnet **noch zu implementierende** Teile; neue Dateinamen sind Sollpfade innerhalb `PROJECT/`.

| Auftrag | Konkrete Umsetzung | Abnahme |
|---|---|---|
| I01 | `start.py` auf eine Domain-Registry umstellen; `src/code_learning/registry.py` und `phases.py` hinzufügen | `TASK_DOMAIN="CODE"` ruft nachweislich CODE-Funktionen auf; Trading bleibt eigene Registry |
| I02 | `schema.py`, `runtime.py`: Task, Patch, Observation, Outcome und Teacherjob typisieren; CODE-Payload-Codec sowie minimalen gemeinsamen Writer/Reader mit vorhandener Identität, Herkunft und Artefaktverwaltung anbinden | Persistieren/Reload und reproduzierbare Hashes |
| I03 | `runner.py` und `workers/code_runner/`: tatsächliche isolierte Ausführung | Richtige Lösung, falsche Lösung, Exception und Timeout getrennt; Containerfehler erzeugt kein negatives Programmlabel |
| I04 | `tasks.py` und `actions.py`: acht Familien, Strukturgruppen, AST-Kandidaten | Referenz-/Mutationswissen erscheint nicht im Zustand oder Kandidatengenerator |
| I05 | `teacher_client.py`: asynchrone Requests, Modellhash, Alias, Prompt-/Samplingprofil, Idempotenz | Echtes Qwen-Resultat wird ausgeführt; falscher Lehrerpatch bleibt falsch |
| I06 | Gemeinsame bilineare Operation aus `src/v150_model.py` nach `src/fibre_ops.py` auslagern; `encoder.py`, `model.py` ergänzen | Trading-Parität; CODE-Forward/Backward mit gültigen Masken |
| I07 | `losses.py` und `train.py`: überwachte Vorhersage-/Rankingziele auf ausgeführten Kandidaten | Optimizer verändert eigene Schülergewichte; unbeobachtete Aktionen erhalten keine erfundenen Labels |
| I08 | `evaluate.py`, `export.py`: lehrerfreie Basis-Auswertung und Reload bereits für ersten Versuch | Getrennte Strukturgruppen, gleicher Ausführungs-/Editetat, reproduzierbare Ausgaben |
| I09 | `semantic_ir.py`, `transfer_rules.py` und erweiterte CODE-Scope-/Branch-Authority auf dem Writer/Reader aus I02 | Aussagen tragen Programmscope, Revision und Evidenz; unbekannt bleibt unbekannt |
| I10 | Gemeinsamer Zykluscontroller, Core und Atlas gemäß V2; `episodes.py` und spätere `tensor_tasks.py` | Konsistenter Wake/Sleep-Übergang, Wiederaufnahme, Retention, Mehrschrittlernen und vollständige Phasen 1–12 |

Die Details stehen bereits in V1, Abschnitte 6–15, und V2, Abschnitte 4–16. Es wird kein paralleler generischer Trainer angelegt. Insbesondere werden Markt-Geo-Tensoren nicht mit Codebytes befüllt und Trading-Checkpoints nicht als Programmierwissen umgedeutet.

**Praktischer erster Abschluss:** I01–I08 liefern den integrierten Fibre-Basisversuch bis zu echtem Vortraining und einer lehrerfreien Basis-Auswertung. Die gemeinsame Herkunfts-/Writer-Hülle wird dabei schon verwendet. Dieser Versuch ist ausdrücklich der Basis-/Vergleichsarm; er beansprucht noch keinen vollständigen Memory-/Atlas-Lifecycle. I09–I10 vervollständigen den V2-Zyklus. In diesem Zyklus sind Gewichte während der Erfahrungsphase gepinnt; Updates und Veröffentlichung erfolgen in der Konsolidierung.

### 8.3 Was der erste Schüler konkret lernt

Acht Familien: ACCUMULATE, FILTER, BOUNDARY, INDEX, REDUCE, COUNT, RANGE, RETURN. Der Controller erzeugt unabhängige Strukturgruppen für TRAIN/VAL/TEST. Unterschiedliche Variablennamen allein sind keine ausreichende strukturelle Trennung.

Der Schüler sieht Anforderung, fehlerhaften Code, Public-Ergebnisse, bisherige Edits und Restbudget. Referenzcode, richtige Mutationsstelle, korrekter Aktionsindex und verborgene Assessmentfälle bleiben außerhalb der Beobachtung.

Startarchitektur aus V1:

| Größe | Anfangswert |
|---|---:|
| Bytevokabular | 260 einschließlich vier Sondertokens |
| Transformer | 4 Schichten, Breite 192, 6 Köpfe, FFN 768 |
| AST-Aggregation | 3 Runden |
| Public-Trace-Merkmale | 32 |
| State-/Fibre-Dimension | jeweils 128 |
| Bilinearer Rang | 16 |
| Kandidatenlimit | 32 |
| Microbatch × Akkumulation | 2 × 8 = 16 Entscheidungen |
| Vortraining | 3 Epochen, Standardmaximum 10 |

Die Zahlen sind Entwurfsdefaults. Der reale Speicherbedarf wird auf PC 2 gemessen.

Die Lernziele sind getrennt: Passwahrscheinlichkeit, Ausführungsfehler, Ranking und gemessener Ein-Schritt-Nutzen. Lehrerhinweise sind ein schwach gewichtetes Zusatzsignal. **Die primären Targets stammen aus Ausführung, nicht aus Lehrerzustimmung.**

### 8.4 Woran tatsächliches Training erkennbar ist

Ein Trainingsreport muss mindestens ausweisen:

- Tatsächliches Gerät, Schülerparameterzahl und konfigurierte Phase.
- Mindestens einen Optimizerschritt mit endlichen Gradienten und geänderten Gewichten.
- Verifizierte TRAIN-Aufgaben und tatsächlich ausgeführte Kandidaten.
- Vorhergesagte Werte vor Ausführung sowie danach beobachtete Ergebnisse.
- Eigene Schülercheckpoints einschließlich Optimierer, Schrittzähler, RNG und Herkunft.
- Reload desselben Checkpoints und lehrerfreie Auswertung.

Ein GGUF-Server, ein Dataset, ein Dummycheckpoint oder der kleine Hardwaretest erfüllt diese Kriterien nicht.

## 9. Nach Integration: Start bis zum ersten tatsächlichen Training

**Die Befehle in diesem Abschnitt gelten erst für die integrierte CODE-Arbeitskopie.** Im mitgelieferten unveränderten Paket A sind diese Domainfunktionen nicht vorhanden.

### 9.1 Einzige Trainingskonfiguration

Die bestehenden fünf Gruppen in `PROJECT/config.py` erweitern. Den vorhandenen Dateiinhalt nicht durch dieses kurze Beispiel ersetzen.

Am Dateianfang:

```python
# PHASENABLAUF — CODE
# Phase 1: Runtime und Hardware
# Phase 2: Python-Runner und Referenzen
# Phase 3: Aufgaben und Splits
# Phase 4: Lehrer-Demonstrationen
# Phase 5: Repräsentation und Fibre-Modell
# Phase 6: Überwachtes Vortraining — START HIER erste echte Gewichtsupdates
# Phase 7: Eigene Reparaturversuche und Alternativen
# Phase 8: Gemeinsame Konsolidierung, Memory, Core und Atlas
# Phase 9: Mehrstufige Reparaturen
# Phase 10: PyTorch-Curriculum
# Phase 11: Lehrerfreie Evaluation
# Phase 12: Export und Reload — START HIER vollständiger Aufbau
# Ziel N besucht 1..N; gültige Vorstufen werden wiederverwendet.
PHASE = 6
TASK_DOMAIN = "CODE"
OVERWRITE = False
```

In den bestehenden Gruppen die bereits im Entwurf definierten Schlüssel setzen:

```python
DATA_PARAMS["run_profile"] = "smoke"
DATA_PARAMS["code_root"] = "artifacts/code/run_v1"
DATA_PARAMS["teacher_base_url"] = "http://192.168.178.20:8080/v1"
DATA_PARAMS["teacher_key_file"] = "/tatsaechlicher/pfad/teacher.key"
DATA_PARAMS["teacher_model_alias"] = "c3p3-qwen"
DATA_PARAMS["teacher_context_tokens"] = 4096

MODEL_PARAMS["device"] = "cuda"
MODEL_PARAMS["precision"] = "bf16"
MODEL_PARAMS["compile"] = False
MODEL_PARAMS["microbatch"] = 2
MODEL_PARAMS["gradient_accumulation"] = 8

PRETRAIN_PARAMS["epochs"] = 3
PRETRAIN_PARAMS["max_epochs"] = 10

RL_PARAMS["smoke_updates_per_phase"] = 20
RL_PARAMS["smoke_episodes_per_phase"] = 16
RL_PARAMS["smoke_walltime_s"] = 300
RL_PARAMS["resume"] = True
```

Adresse und Schlüsselpfad ersetzen. Das endgültige Implementierungspaket muss alle übrigen V1-Parameter und deren V2-Korrekturen mit tatsächlich aufrufenden Funktionen liefern. Die obigen Zeilen alleine implementieren diese Funktionen nicht.

Für Lehrer-Temperatur, Top-p, Top-k, Min-p und Wiederholungsstrafe gilt das aktive Modellprofil aus Abschnitt 10. Neue Profilfelder müssen ebenfalls in `DATA_PARAMS` mit produktivem Consumer und Fingerprint angebunden werden. Ein unbeachteter Configkey ist kein Feature.

### 9.2 Phase 6: Erstes echtes Vortraining

Qwen auf PC 1 laufen lassen. Auf PC 2:

```bash
cd "$C3P3_PROJECT"
"$HOME/venvs/c3p3-code/bin/python" start.py
```

Erwarteter Ablauf: Domain CODE → 1 Runtime → 2 Runner → 3 Tasks/Splits → 4 echte Lehrerantworten und deren Ausführung → 5 Schüler → 6 Optimizerupdates.

Der kurze erste Lauf dient der technischen Abnahme. Ein Zeitbudgetende wird als `INCOMPLETE` protokolliert. 300 Sekunden sind ein Abnahmelimit, keine Laufzeitzusage für Datenaufbau und lange Lehrerantworten.

Danach den eigenen Schüler laden und auf zurückgehaltenen Basisaufgaben prüfen. Für den frühen Basisarm muss I08 diesen Aufruf produktiv an die Phase-6-Abnahme anbinden; ein isoliertes, nie aufgerufenes `evaluate.py` genügt nicht.

### 9.3 Phase 7 und V2-Konsolidierung

Im ausdrücklich benannten Basisarm kann Phase 7 Ein-Schritt-Reparaturen und ausgeführte Alternativen ergänzen. Sobald der V2-Zyklus aktiviert ist:

1. Veröffentlichtes Schüler-/Memory-Bundle pinnen.
2. Kleine Erfahrungsgruppe sammeln; Prognosen vor Ausführung sichern.
3. Hauptaktion und bis zu zwei Alternativen aus demselben Vorher-Code prüfen.
4. Ergebnisse journalisieren.
5. Phase 8 beziehungsweise den gemeinsamen Lifecycle-Dienst konsolidieren lassen.
6. Neues vollständiges Bundle veröffentlichen und mit diesem weiterarbeiten.

**Für den zusammengeführten V2-Versuch daher Ziel `PHASE=8` wählen.** Phase 7 allein beschreibt dort das Sammeln; sie darf nicht unbemerkt wieder zu sofortigen Gewichtsupdates während des gepinnten Wake-Abschnitts werden. Die Phase ist kein Zykluszähler.

### 9.4 Erster Lernpilot und spätere Ziele

Nach erfolgreicher technischer Abnahme `DATA_PARAMS["run_profile"]="pilot"` setzen. V1-Defaults: 500 Updates pro entsprechender Phase und 256 Episoden; Vortraining bleibt bei 3 Epochen mit Standardmaximum 10. Alle tatsächlichen Budgets werden in der aufgelösten Config ausgegeben.

| Ziel | Ergebnis |
|---:|---|
| 6 | Überwachtes Vortraining des Fibre-Basisarms |
| 8 | Eigene Erfahrungen plus konsolidierter V2-Memory-Zyklus |
| 9 | Mehrere aufeinanderfolgende Reparaturen |
| 11 | Formale lehrerfreie Evaluation einschließlich vorheriger freigegebener Phasen |
| 12 | Gesamtaufbau, Export und Offline-Reload |

V1/V2 Phase 11 zieht im vollständigen Aufbau auch Phase 10 nach sich. Für eine kleine frühe Auswertung wird deshalb die Basis-Auswertung aus I08 verwendet; nicht versehentlich alle Ausbaustufen starten.

Sinkender TRAIN-Loss allein belegt kein Lernen über Aufgaben hinweg. Berichte getrennt: Candidate Coverage, Lösungsrate auf neuen Strukturgruppen, Fehlervorhersage, frühere Fähigkeiten, Rechenzeit und Lehrerwarteanteil.

## 10. Die anderen drei Lehrer in Betrieb nehmen

Vor jedem Wechsel den bisherigen Server mit **Strg+C** beenden. Dann denselben `serve`-Aufruf aus Abschnitt 4.2 verwenden und `--teacher` ändern.

| Lehrer | `--teacher` | Kontext als Startversuch | Probetokens / Timeout |
|---|---|---:|---|
| Qwen | `qwen` | 4096 | 256 / 180 s |
| Phi | `phi` | 8192 | 4096 / 600 s |
| Ministral | `ministral` | 4096 | 256 / 180 s |
| Gemma | `gemma` | 4096 | 512 / 180 s |

Die höheren Phi-Werte sind endliche Startbudgets, keine Erfolgsgarantie. Kontext umfasst Eingabe und Ausgabe gemeinsam. Bei Speicherproblemen die dokumentierten Werte reduzieren; bei abgeschnittener Antwort nicht trotzdem einen gültigen Lehrerjob speichern.

Beispiel Phi auf PC 1:

```bash
python3 "$C3P3_GUIDE/tools/teacher.py" serve \
  --teacher phi \
  --server "$C3P3_SERVER" --models-dir "$C3P3_MODELS" \
  --host 0.0.0.0 --port 8080 \
  --ctx 8192 --parallel 1 \
  --gpu-layers 99 --batch 256 --ubatch 128 \
  --key-file "$HOME/c3p3-teachers/secrets/teacher.key"
```

PC 2:

```bash
python3 "$C3P3_GUIDE/tools/teacher.py" probe \
  --teacher phi \
  --base-url "http://$C3P3_TEACHER_IP:8080/v1" \
  --key-file "$HOME/c3p3-teachers/secrets/teacher.key" \
  --timeout 600 --max-tokens 4096
```

Für Ministral und Gemma entsprechend `--teacher ministral` beziehungsweise `--teacher gemma` verwenden und die Budgets aus der Tabelle setzen.

### Modellprofile und Chatvorlagen

| Profil | Temperatur | top_p | top_k | Weitere Festlegung |
|---|---:|---:|---:|---|
| Qwen | 0,7 | 0,8 | 20 | repeat_penalty 1,05 |
| Phi | 0,8 | 0,95 | 50 | repeat_penalty 1,0; Aufgabenanweisung in user |
| Ministral Instruct | 0,05 | 1,0 | 0 | repeat_penalty 1,0 |
| Gemma | 1,0 | 0,95 | 64 | repeat_penalty 1,0; Thinking für kurze Proben aus |

Min-p wird auf 0 gesetzt. Qwen/Phi/Gemma orientieren sich an ihren veröffentlichten Profilen. Bei Ministral stammen Temperatur unter 0,1 vom Hersteller und die neutralen Top-p-/Top-k-Werte aus diesem Guide. Alle sind Startprofile, keine für deinen Datensatz optimierten Einstellungen. [Qwen-Profil](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct/blob/main/generation_config.json), [Phi-Profil](https://huggingface.co/microsoft/Phi-4-reasoning-plus), [Ministral-Profil](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512), [Gemma-Profil](https://huggingface.co/google/gemma-4-12B-it)

Die Probe deaktiviert bei Gemma Thinking mit `chat_template_kwargs.enable_thinking=false`. Phi behält seine eigene Reasoning-Vorlage; ein zu kleines Tokenbudget kann eine Endantwort verhindern. Ein zusätzliches Systemprompt wird im veröffentlichten Phi-Template nicht wie bei Qwen verarbeitet. Aufgaben-/Ausgabeanweisungen deshalb in der user-Nachricht führen und das Modelltemplate bewahren. [Phi-Template](https://huggingface.co/microsoft/Phi-4-reasoning-plus/blob/main/tokenizer_config.json)

Die vier vorhandenen GGUF-Dateien genügen für die hier verwendeten Textaufgaben. Spätere Bildverarbeitung in llama.cpp benötigt passende mmproj-Artefakte und einen entsprechenden Schüler-Eingabepfad. Der jetzige Guide aktiviert das nicht. [Multimodaler Betrieb](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)

## 11. Nacheinander lernen, ohne den Schüler neu zu beginnen

**Serverwechsel und Trainingsfortsetzung sind zwei verschiedene Operationen.** Die Hilfsskripte können Server wechseln. Die erforderliche Mehrlehrer-Fortsetzung muss in den CODE-Trainer integriert werden.

Eine bloße Änderung von `teacher_model_alias` in einem fingerprintgesteuerten Erstaufbau kann Phase 4 und nachfolgende Artefakte invalidieren. Wenn der Dispatcher anschließend einen neuen Initialschüler baut, wurde kein Wissen von Lehrer zu Lehrer weitergetragen.

Der zu implementierende Fortsetzungsvertrag lautet:

1. Die erste Runde startet mit frischen CODE-Gewichten und Qwen.
2. Jede weitere Runde bindet den tatsächlich gewählten vorherigen Schülercheckpoint als Parent. Optimierer-/Schedulerbehandlung wird explizit protokolliert; bei unverändertem Trainingsverfahren werden sie fortgesetzt.
3. Neue Lehrerjobs erhalten Modellhash, Prompt-/Schema-/Samplingversion und eine eigene Rundenidentität.
4. Alte verifizierte Beispiele bleiben nur soweit gültig, wie die aktuelle Retention-Autorität sie zulässt.
5. Ein neuer Lehrer wird auf ungelöste TRAIN-Aufgaben und relevante Fehlertypen angesetzt.
6. Nach jeder Runde werden neue Aufgaben sowie zuvor beherrschte Aufgaben ohne Lehrer ausgewertet.
7. Ein fehlender Parent führt zu einer verständlichen technischen Fehlermeldung; kein stiller Neustart.

Alle Einstellungen gehören in die vorhandenen fünf Gruppen. Rundenstatus, Parent und Datenherkunft gehören in die vorhandene Artefakt-/Generationenverwaltung. Ein zweites Trainingssystem oder eine zweite kanonische Memory-Datenbank ist nicht erforderlich.

Für den **ersten Vergleich** sollen alle vier Lehrer denselben begrenzten Python-Patchvertrag bedienen. So lässt sich deren zusätzlicher Nutzen messen. Phi kann mathematische Randfälle erklären; Ministral Anweisungen und strukturierte Aktionen prüfen; Gemma alternative Formulierungen liefern. Tool-Use oder Bildverständnis entstehen im Schüler erst, wenn dessen Aufgaben, Beobachtungen und Aktionen sie tatsächlich abbilden.

Ein Mischversuch mit 70 % neuem Schwerpunkt und 30 % zulässiger Wiederholung ist ein möglicher erster Curriculumvergleich. Diese Quote ist weder eine nachgewiesene optimale Mischung noch die Memory-Löschquote.

### V2-Memory-Regel beibehalten

Im vollständigen Zyklus wird zuerst konsolidiert, dann werden **50–80 %** der bisherigen eindeutigen Bank-Erfahrungen zufällig gelöscht, anschließend wird das neue Bundle atomar aktiviert. Core besitzt zuvor bewusst gesicherte eigene Belege. Die genaue Rundungs-/Populationsregel steht unverändert in V2, Abschnitt 10.1.

Eine gelöschte Erfahrung darf nicht aus dem alten Teacher-Cache als scheinbar neue Erfahrung wieder eingespeist werden. Neue echte Ausführungen sind neue Ereignisse. Das ungefähr 2/3-zu-1/3-Verhältnis von Erfahrung und Konsolidierung bleibt eine Zeitbudget-Hypothese.

## 12. Training abschließen, exportieren und offline prüfen

Nach vollständiger CODE-Integration:

1. `TASK_DOMAIN="CODE"` und `PHASE=12` wählen.
2. Vorhandene gültige Phasenartefakte wiederverwenden; nur fachlich veraltete Abhängigkeiten neu aufbauen.
3. Schülercheckpoint, Architektur-/Byte-/AST-Vertrag, tatsächlich wirksame Config und Runner-/Modellversionen exportieren.
4. Bei aktivem Memory vollständige erlaubte TRAIN-Payloads mit exportieren; der Atlas ist nur ein rekonstruierbarer Index.
5. Teacher-Server abschalten und exportierten Schüler erneut auf den festen Auswertungsaufgaben ausführen.
6. Internetzugang trennen und denselben Reload-/Auswertungspfad erneut ausführen.

Das endgültige Paket muss die konkreten Export- und Reload-Entrypoints tatsächlich enthalten. Die vorhandene Trading-Exportphase ist kein Ersatz.

Die einmal eingerichtete Python-Umgebung dokumentieren:

```bash
mkdir -p "$HOME/c3p3-code-environment"
"$HOME/venvs/c3p3-code/bin/python" --version \
  > "$HOME/c3p3-code-environment/python-version.txt"
"$HOME/venvs/c3p3-code/bin/python" -m pip freeze \
  > "$HOME/c3p3-code-environment/requirements-resolved.txt"
```

Das ist eine Versionsinventur, noch kein vollständiges Offline-Installationspaket. Für Neuinstallation ohne Internet müssen zusätzlich passende Wheels samt Hashes, Python-Runtime, llama.cpp samt benötigten Bibliotheken, CUDA-/Treiberpakete bei Bedarf und Workerimage bereitliegen. Der Trainingsstart darf keine Downloads nachholen.

## 13. Häufige Fehler

| Beobachtung | Bedeutung / nächster Schritt |
|---|---|
| `Could not find nvcc` | Auf PC 1 fehlt das Toolkit oder dessen Compilerpfad; `nvidia-smi` allein reicht für den Build nicht |
| `no kernel image is available` auf PC 2 | PyTorch-Build/GPU-Unterstützung und tatsächlich verwendeten Interpreter prüfen; für die Referenz den cu128-Build verwenden |
| `torch.cuda.is_available() == False` | Treiber, GPU-Sichtbarkeit und installierte Torch-Variante prüfen; nicht still auf CPU trainieren |
| Lokal funktioniert HTTP, per LAN nicht | Richtige PC-1-IP, `--host`-Bindung und Firewall prüfen |
| HTTP 401 | Schlüsseldateien auf beiden PCs stimmen nicht überein |
| Falscher Modellalias | Alter Lehrer läuft noch oder Clientprofil passt nicht zum aktuellen Server |
| HTTP 503 beim Laden | Modell ist noch nicht bereit; später erneut prüfen |
| Phi liefert keine Endantwort | Reasoning hat das Token-/Kontextbudget verbraucht; mehr Budget oder kleinere Aufgabe |
| Gemma liefert nur Reasoning | Für kurze Proben Thinking ausschalten; eigenes Endantwortfeld prüfen |
| GPU-OOM | Kontext, Batch oder Microbatch explizit reduzieren und geänderte Werte dokumentieren |
| `CODE_NOT_READY` beim Originalpaket | Erwarteter Quellenstand; I01–I08 beziehungsweise I09–I10 fehlen |
| `PHASE=7` zeigt `MEMORY_RL_V17_FROZEN` | Es läuft der Trading-Dispatcher, nicht CODE |
| TRAIN wird besser, getrennte Aufgaben nicht | Mögliche Überanpassung, geringe Candidate Coverage oder ungeeignete Repräsentation untersuchen |
| Nach Lehrerwechsel plötzlich Initialcheckpoint | Curriculum-Fortsetzung/Parentbindung fehlt; nicht als fortgesetztes Lernen ausweisen |

## 14. Gelieferte Dateien und Prüfgrenzen

| Datei | Zweck |
|---|---|
| Dieses Markdown-Dokument | Einrichtung, Integrationsauftrag, Trainingsfolge |
| `tools/teacher.py` | Vorhandene GGUFs inventarisieren, llama.cpp starten, echte HTTP-Antwort prüfen |
| `tools/runtime_check.py` | Kleine echte PyTorch-Optimierung und Reload auf dem gewählten Gerät testen |
| `tools/project_status.py` | CODE-Integrationsindikatoren lesen, ohne das Projekt zu importieren/starten |
| `tests/test_setup_tools.py` | Wiederholbare lokale Prüfungen mit HTTP-Testdouble |
| `referenzen/` | Unveränderte Projektbasis und bisherige Implementierungsverträge |
| `PRUEFBERICHT_V1.md` | Tatsächlich hier ausgeführte Prüfungen und offene lokale Abnahme |

Der Guide wurde gegen den verfügbaren Projektstand und Primärdokumentation geprüft. Die vier großen GGUF-Dateien befinden sich auf deinen PCs; sie wurden hier nicht gestartet. Die lokalen NVIDIA-Karten und das LAN wurden hier nicht gemessen. Ein aufgeführter GPU-Befehl ist eine Anleitung für deine Abnahme, kein bereits bestandener GPU-Test.

## 15. Maßgebliche Quellen

Projektgrundlagen sind die mitgelieferten Originale in `referenzen/`. Bei Konflikten gelten die V2-Korrekturen gegenüber V1. Onlinequellen sind unmittelbar bei den jeweiligen technischen Aussagen verlinkt.

Für den ersten tatsächlichen Trainingsstart ist die nächste Entwicklungsarbeit eindeutig: **den CODE-Pfad I01–I08 in die vorhandene Projektbasis integrieren und auf deiner RTX 5070 bis zu echten Schülerupdates plus Reload abnehmen.** Die vier Lehrermodelle sind dafür die Daten-/Hinweisgeber; das trainierte Modell bleibt deine C3P3-Fibre-Architektur.

