# Vision – Gemensam projektplan

Senast uppdaterad: 2026-01-31

Det här dokumentet är den *gemensamma* planen för projektet i den här repot.
Äldre/idé-dokument (t.ex. "stora arkitekturvisioner") hör hemma i separata filer.

## Mål

Bygga ett CPU-first system för bildinferens (YOLO via ONNX Runtime) med:

- En Runner (FastAPI) som kan inferera uppladdade bilder och filer i en input-mapp.
- En enkel UI (Next.js) som använder Runnerns endpoints.
- En portabel “model bundle”-kontrakt (modell + labels + meta) som går att flytta till Raspberry Pi senare.
- Docker Compose-flöde som gör att projektet fungerar “direkt” på en ny maskin.

## Vad som finns idag (status)

### Klart

- [x] CPU Runner: FastAPI + ONNX Runtime (Swagger på `/docs`).
- [x] Model bundle-format: `model.onnx` + `labels.txt` + `meta.json` (ligger under `./models/...`).
- [x] Docker Compose: Full stack med UI + runner + en one-shot `modelprep` som genererar demo-modell om den saknas.
- [x] UI: Next.js-sida för inferens (upload + demo “infer input”).
- [x] Robust bild-decode: Pillow-decode istället för att lita på content-type, EXIF-orientering, samt HEIC/HEIF-stöd.
- [x] Upload-kompat: `/api/v1/infer` accepterar fält `image` (nytt) och `file` (legacy).
- [x] Valfri persist av uploads till `/input/_uploads` med `VISION_SAVE_UPLOADS=1`.
- [x] Säker “töm input”-funktion:
  - CLI: `vision.bat clear-uploads` och `vision.bat clear-input`.
  - API: `POST /api/v1/demo/clear` (kräver `VISION_DEMO_ALLOW_MUTATIONS=1`).
- [x] Settings-sida i UI:
  - API base i localStorage.
  - Backend settings via `GET/POST /api/v1/settings` (runtime update kräver `VISION_ALLOW_RUNTIME_SETTINGS=1`).
- [x] Valfri OpenVINO acceleration via ONNX Runtime EP + compose override.

### Viktiga designbeslut

- **CPU först**: Vi prioriterar stabilt API + filflöde + model bundle-kontrakt.
- **Builder vs Runner**: Träning/export hör hemma på devmaskin (x86), Runner ska kunna köras på Pi.
- **Säkerhet runt radering**: all destruktiv rensning är avstängd som default.

## Nästa steg (tydlig TODO)

### P0 – Nästa commit (små men viktiga)

- [x] Visa “file counts” i Settings:
  - antal filer i `/input` (exkl. `_uploads`)
  - antal filer i `/input/_uploads`
  - gärna även “senast ändrad” eller storlek (om det är lätt)
- [x] Förbättra “build”-flöde i `vision.bat`:
  - se över varför `vision.bat build` kan ge exit code 1 (om det fortfarande händer)
  - ge tydligare felmeddelanden och tips

### P1 – Stabilitet & kvalitet (MVP hårdning)

- [x] “Health + readiness”:
  - behåll `/health`, lägg till modell-ready status (modell laddad + providers)
- [x] Loggning:
  - strukturera loggar (request-id, latency, model version)
- [x] Begränsningar i upload:
  - max filstorlek, tydliga felkoder och feltexter
- [x] Smoke-test script (ingen full test-suite krävs):
  - curl-test som kör infer på en testbild och verifierar JSON-format

### P2 – Model lifecycle (lite mer “riktig produkt”)

- [x] “Model registry” i API:
  - lista bundles i `./models`, visa version, input_size och export-info
  - endpoint för att byta aktiv modell (guarded)
- [x] “Bundle export/import”:
  - exportera zip med `model.onnx/labels.txt/meta.json`
  - importera zip (validera innehåll)

### P3 – Raspberry Pi (Runner)

- [x] Dokumentera Pi-run med `docker-compose.runner.yml`:
  - ARM64 krav + hur man mountar `/input` på Pi
- [x] Säker “watch-folder mode” på Pi:
  - robusthet vid trasiga filer, partial writes, och stora mappar
- [x] Pull model bundle från “builder maskin”:
  - script eller endpoint för att hämta senaste bundle

### P4 – Acceleration (valfritt)

- [x] OpenVINO (redan valfritt): verifiera i README med tydliga krav och felsökning.
- [x] Coral/Hailo: endast när CPU-pipelinen är stabil.

### P5 – Professionell GUI (polish)

- [x] Modern design:
  - dark mode / light mode toggle
  - konsekvent färgpalett och typografi
  - responsiv layout (mobil + desktop)
- [x] Förbättrad inferens-vy:
  - bounding boxes med labels direkt på bilden
  - confidence score-visning
  - zoombar bild
- [ ] Dashboard-vy:
  - statistik (antal inferenser, senaste aktivitet)
  - modellinfo prominent visad
- [x] Förbättrad UX:
  - drag-and-drop upload
  - loading spinners och progress
  - toast-notifikationer
- [x] Settings-polish:
  - bättre gruppering
  - visuell feedback vid ändringar
- [x] Internationalisering:
  - Svenska och Engelska
  - Språkväljare i header

### P6 – Automatisk inferens-mapp

- [x] Watch-folder med auto-move:
  - `VISION_WATCH_INPUT` för inkommande bilder
  - `VISION_WATCH_PROCESSED` för färdigbehandlade
  - `VISION_WATCH_MODE` (json/move/both)
  - Kör automatiskt inferens på nya bilder

### P7 – Docker Hub Publishing

- [x] Push till `marcussorensson218/volvo-vision:latest`
- [x] Versionstaggar (v1.0.0)
- [x] `docker-compose.production.yml` för enkel deployment
- [x] `INSTALL.md` installationsguide med:
  - Alla volume-mappningar (input/output/models)
  - Alla miljövariabler dokumenterade
  - Användningsexempel för Windows/Linux/Pi

### P8 – Model Management & Detection Filters

- [x] Model Upload:
  - `POST /api/v1/models/upload` endpoint
  - Sparar ONNX + labels.txt som bundle
- [x] Detection Filters:
  - `filters.json` konfigurationsfil
  - `GET/POST/DELETE /api/v1/filters` endpoints
  - `POST /api/v1/infer/filtered` med filterparameter
  - `FilterSelector` UI-komponent
- [x] Auto-Detection Status:
  - `GET /api/v1/watcher/status` endpoint
  - `WatcherStatusCard` UI-komponent

> [!NOTE]
> **Release v1.1.0** publicerad till Docker Hub 2026-02-01. Innehåller Model Upload, Filters och Industrial Theme.

### P9 – Integration & Connectivity (Completed)

- [x] **REST API Push (Webhook)**
  - Konfiguration för URL, method, headers
  - Skicka inferensresultat JSON till externt system
- [x] **MQTT Client (Internal & External)**
  - Inbyggd Mosquitto broker (port 1883)
  - Konfigurerbar topic/auth
- [x] **OPC UA Server (Industriell Standard)**
  - **40100-1 Compliance**: Machine Vision Companion Spec
  - **Events**: `ResultReadyEventType` (Push-baserad integration)
  - **Methods**: `Start`, `Stop`, `SelectModel` (Styrning från PLC)
  - **Alarms**: `SystemErrorAlarm`
  - **Legacy Support**: Förenklade noder för äldre PLC:er

### P10 – Training Pipeline (Future)

- [ ] Dataset management API
- [ ] Träningssida med parametrar
- [ ] Annotationsverktyg
- [ ] YOLO export-format

## Definition of Done (för MVP)

- UI kan inferera upload och visa boxes.
- Demo-läge kan lista filer i `/input` och inferera på vald fil.
- Projektet kan startas på ny maskin med `docker compose -f docker-compose.full.yml up --build`.
- Säkerhets-guardrails: radering och runtime-settings är opt-in.

## Anteckningar

- [plan.md](plan.md) är källan för status + TODO.
