# Vision – Gemensam projektplan

Senast uppdaterad: 2025-07-15

Det här dokumentet är den *gemensamma* planen för projektet i den här repot.
Äldre/idé-dokument (t.ex. "stora arkitekturvisioner") hör hemma i separata filer.

## Mål

Bygga ett CPU-first system för bildinferens (YOLO via ONNX Runtime) med:

- En Runner (FastAPI) som kan inferera uppladdade bilder och filer i en input-mapp.
- En enkel UI (Next.js) som använder Runnerns endpoints.
- En portabel “model bundle”-kontrakt (modell + labels + meta) som går att flytta till Raspberry Pi senare.
- Docker Compose-flöde som gör att projektet fungerar “direkt” på en ny maskin.

## Vad som finns idag (status)

### Klart (Summering)

- **Core**: CPU Runner (FastAPI + ONNX Runtime) med stöd för robust bild-decode och HEIC.
- **Architecture**: Docker Compose fullstack (Runner + UI), Model Bundle-format (ONNX+Meta), och one-shot model prep.
- **Workflow**: Server-side upload persistens, demo-läge, och "Watch folder" för automatisk inferens.
- **UI**: Modern Next.js frontend med PWA-förberedelser, dark mode, och bounding box visualisering.
- **Integration**: OPC UA Server (40100-1), MQTT Client, och Webhook-stöd.
- **Ops**: Health checks, loggning, "Model Registry" API, samt förbättrat build-flöde i `vision.bat`.
- **Training**: Dataset management API, tränings-UI, annoteringsverktyg och YOLO-export.
- **Privacy**: Ansikts-anonymisering (ULFD, MIT-licens) med blur/pixelate, API-status, frontend-integration och i18n.

### Viktiga designbeslut

- **CPU först**: Vi prioriterar stabilt API + filflöde + model bundle-kontrakt.
- **Builder vs Runner**: Träning/export hör hemma på devmaskin (x86), Runner ska kunna köras på Pi.
- **Säkerhet runt radering**: all destruktiv rensning är avstängd som default.

## Nästa steg (Roadmap)

### P11 – Privacy & Anonymization (Done ✅)
>
> **Goal**: Stödja integritetskrav (GDPR) via automatisk anonymisering.

- [x] **Research**: Utvärdera `Ultra-Light-Fast-Generic-Face-Detector-1MB` vs YOLOv8n-face.
  - ULFD vald (MIT-licens, kommersiellt fri). YOLOv8-face = AGPL-3.0, SCRFD = icke-kommersiell.
- [x] **Implementation**:
  - [x] `PrivacyEngine` klass för sekundär ONNX-inferens.
  - [x] Pillow-baserad `GaussianBlur` eller `Pixelate`.
  - [x] Config: `VISION_PRIVACY_FACE_BLUR=1`.
  - [x] Buggfixar: prior-avkodning, preprocessing `(pixel-127)/128`, default min_score=0.15 för ULFD.
- [x] **Integration**:
  - [x] Inject `anonymize_faces()` före huvud-inferensen i `routes.py`.
  - [x] `privacy_applied` och `privacy_faces` i API-respons (`InferResponse`).
  - [x] `/api/v1/privacy` endpoint för status.
  - [x] Frontend: Privacy-sektion i Inställningar (status, modell, läge).
  - [x] Frontend: Privacy-badge i inferensresultat ("🔒 X ansikten anonymiserade").
  - [x] i18n: Översättningar för alla 7 språk (sv, en, nl, sk, zh, fr, es).
  - [ ] Stöd för att sudda registreringsskyltar (License Plates) i framtiden.

#### PI-plan för P11 (Privacy & Anonymization)

**PI-mål (2 veckor)**
Leverera ansikts-anonymisering som kan slås på via env-flagga, med fallback-modell, loggning och enkel QA.

**Spår & Stories**

1) **Research & Validering** ✅
- [x] Benchmarka face-detectors (ULFD-1MB vs YOLOv8n-face) på CPU.
- [x] Dokumentera precision, latency och modellstorlek.
- [x] Välj standardmodell + fallback.
  - **Resultat**: ULFD (MIT) vald. 240×320 input, ~1MB, CPU-vänlig. YOLOv8-face (AGPL), SCRFD (icke-kommersiell) ej lämpliga.

2) **Core Implementation** ✅
- [x] Skapa `PrivacyEngine` med ONNX-session, pre/post-process.
- [x] Implementera `anonymize_faces()` med `GaussianBlur`/`Pixelate`.
- [x] Lägg till `VISION_PRIVACY_FACE_BLUR=1` (default off).
- [x] Säkerställ no-op när ingen modell finns.
- [x] Fix: Prior-avkodning kördes ej (output "boxes" tolkades felaktigt som avkodade koordinater).
- [x] Fix: Preprocessing använde `/255` istället för `(pixel-127)/128` som ULFD kräver.
- [x] Fix: Default min_score sänkt till 0.15 för ULFD (producerar lägre scores).

3) **Integration** ✅
- [x] Hook i `routes.py` före huvud-inferens.
- [x] Flagga i API-respons att anonymisering körts.
- [x] Logga latency & antal ansikten.
- [x] Frontend-integration (Settings-sida + resultat-badge).

4) **QA & Docs** ✅
- [x] Testbilder + smoke test (1 detected, 1 anonymized — korrekt).
- [x] Uppdatera README/plan.md med usage.
- [ ] Kolla Docker-build med modellen.

**Definition of Done**
- [x] Env-flagga aktiverar anonymisering.
- [x] Inga krascher när privacy-modell saknas.
- [x] Latency loggas.
- [x] Dokumentation uppdaterad.

### P12 – Advanced Hardware Support

- [ ] Coral TPU (Edge TPU) integration.
- [ ] Hailo-8 integration (via ONNX EP).

### P13 – Video Mode
>
> **Goal**: Stödja vanliga videoformat (MP4, AVI, MOV, MKV, WebM) utöver enstaka bilder.

- [ ] **Backend**:
  - [ ] Video-ingest via OpenCV (`cv2.VideoCapture`) — extrahera frames.
  - [ ] Nytt endpoint `POST /api/v1/infer/video` som tar emot videofil.
  - [ ] Frame sampling-strategi: alla frames, var N:te, eller FPS-baserat (konfigurerbart).
  - [ ] Batch-inferens per frame med bounding box-resultat.
  - [ ] Valfritt: returnera annoterad video (bounding boxes inritade) som nedladdning.
  - [ ] Privacy-stöd: anonymisera ansikten per frame innan detektion.
  - [ ] Config: `VISION_VIDEO_FRAME_INTERVAL`, `VISION_VIDEO_MAX_FRAMES`.
- [ ] **API-respons**:
  - [ ] `VideoInferResponse` med per-frame detektioner + sammanfattning.
  - [ ] Streaming-progress (SSE eller polling) under lång videobearbetning.
- [ ] **Frontend**:
  - [ ] Video-uppladdning (drag-and-drop, filväljare med video-MIME).
  - [ ] Progress-bar under bearbetning.
  - [ ] Frame-navigator: bläddra mellan frames och se detektioner per frame.
  - [ ] Video-preview med annoterade bounding boxes.
- [ ] **Watch Folder**:
  - [ ] Stöd för videofiler i watch-mappen (auto-process).
  - [ ] JSON-output per video (sammanfattning + per-frame).

#### PI-plan för P13 (Video Mode)

**PI-mål (3 veckor)**
Stödja vanliga videoformat i hela flödet: upload, inferens, preview, watch folder.

**Spår & Stories**

1) **Video Ingest & Frame Extraction (3–4 dagar)**
- [ ] Lägg till `opencv-python-headless` i requirements.
- [ ] Hjälparklass `VideoFrameExtractor` (öppna, sampla frames, stäng).
- [ ] Konfigurerbart: var N:te frame, max antal frames, FPS-target.

2) **Backend API (3–4 dagar)**
- [ ] `POST /api/v1/infer/video` endpoint.
- [ ] `VideoInferResponse` schema (frames, detektioner per frame, total summary).
- [ ] Streaming progress via SSE (`/api/v1/infer/video/status/{job_id}`).
- [ ] Bakgrundsjobb (async task) för längre videor.

3) **Frontend (4–5 dagar)**
- [ ] Utöka uppladdning till att acceptera video.
- [ ] Progress-indikator under bearbetning.
- [ ] Frame-navigering (slider/timeline) med detektionsresultat per frame.
- [ ] Video-export: nedladdning av annoterad video.

4) **Watch Folder & Integration (2 dagar)**
- [ ] Watcher känner igen videofiler.
- [ ] JSON-output med per-frame-resultat.
- [ ] MQTT/Webhook-notifiering vid klar video.

**Definition of Done**
- [ ] MP4/AVI/MOV kan laddas upp och infereras.
- [ ] Per-frame-resultat visas i UI.
- [ ] Privacy fungerar även på video (blur per frame).
- [ ] Watch folder hanterar videofiler.

### P14 – Valbar Detektionsfunktion
>
> **Goal**: Låta användaren välja vilken typ av detektion som ska utföras — t.ex. person, fordon, registreringsskylt, ansikte — istället för att alltid köra alla klasser.

- [ ] **Funktionsväljare i UI**:
  - [ ] Dropdown/chip-selector på huvudsidan för att välja aktiva detektionsklasser.
  - [ ] Spara senaste val i `localStorage`.
  - [ ] Snabbval-profiler: "Alla", "Personer", "Fordon", "Anpassat".
- [ ] **Backend**:
  - [ ] Utöka filter-API med predefined profiler (person, vehicle, all).
  - [ ] Ny query-param `?classes=person,bus,car` på infer-endpoints.
  - [ ] Stöd för att filtrera redan vid inferens (NMS-nivå) eller post-filter.
- [ ] **Multi-modell**:
  - [ ] Stöd för att byta modell beroende på uppgift (t.ex. YOLO-general vs face-only vs LPR).
  - [ ] Task-baserad modellväxling: "person detection" → yolov8n, "face" → ULFD, "license plate" → LPR-modell.
  - [ ] UI: Välj uppgift → system laddar rätt modell automatiskt.
- [ ] **Kombinerade pipelines**:
  - [ ] Kör flera modeller i sekvens (t.ex. YOLO + Privacy + LPR).
  - [ ] Sammanslagna resultat i en `InferResponse`.
- [ ] **Frontend**:
  - [ ] Funktionsväljare (task picker) med ikoner.
  - [ ] Visa vilka klasser som är aktiva i resultat-panelen.
  - [ ] i18n för alla funktionsnamn.

#### PI-plan för P14 (Valbar Detektionsfunktion)

**PI-mål (2 veckor)**
Ge användaren kontroll över vilken detektion som körs, med snabbval-profiler och framtidssäkrad multi-modell-arkitektur.

**Spår & Stories**

1) **Klass-filter i UI (2–3 dagar)**
- [ ] Chip-selector komponent med tillgängliga klasser (hämtade från aktiv modells `labels.txt`).
- [ ] Snabbval-knappar: "Alla", "Personer", "Fordon".
- [ ] Spara val i `localStorage`, skicka som query-param.

2) **Backend Profiler (2–3 dagar)**
- [ ] Predefined profiler i `filters.json`: `all`, `persons`, `vehicles`.
- [ ] Endpoint `GET /api/v1/tasks` — lista tillgängliga uppgifter.
- [ ] Infer-endpoint accepterar `?classes=...` för inline-filtrering.

3) **Multi-modell Arkitektur (3–4 dagar)**
- [ ] `TaskRegistry` som mappar uppgift → modell.
- [ ] Auto-switch modell vid task-byte.
- [ ] Config: `VISION_TASKS` JSON-definition.

4) **Frontend Task Picker (2–3 dagar)**
- [ ] Task-picker komponent med ikoner (🧑 Person, 🚌 Fordon, 🔒 Ansikte, 🔤 Skylt).
- [ ] Visa aktiv task + klasser i resultat.
- [ ] i18n: sv, en + övriga språk.

**Definition of Done**
- [ ] Användaren kan välja detektionstyp i UI.
- [ ] Rätt modell/filter tillämpas automatiskt.
- [ ] Profiler möjliga att konfigurera.
- [ ] Kombinerade pipelines fungerar (detektion + privacy).

### P15 – Export av Bearbetade Bilder & Video
>
> **Goal**: Låta användaren ladda ner bearbetade resultat — annoterade bilder (med bounding boxes), anonymiserade bilder, och annoterade/anonymiserade videor.

- [ ] **Bild-export**:
  - [ ] Endpoint `GET /api/v1/export/image` — returnera bild med inritade bounding boxes.
  - [ ] Valfritt: med eller utan privacy-blur (query-param `?privacy=1`).
  - [ ] Valfritt: bara anonymiserad bild (utan bounding boxes) via `?mode=privacy_only`.
  - [ ] Konfigurerbar box-stil: färg, tjocklek, labels on/off.
  - [ ] Nedladdningsknapp i UI bredvid preview.
- [ ] **Video-export** (kräver P13):
  - [ ] Endpoint `POST /api/v1/export/video` — skicka video, få tillbaka annoterad video.
  - [ ] Bounding boxes inritade per frame.
  - [ ] Privacy-blur per frame (om aktiverat).
  - [ ] Format: MP4 (H.264) som standard, konfigurerbart.
  - [ ] Asynkron bearbetning med progress (SSE/polling).
- [ ] **Batch-export**:
  - [ ] Exportera alla bilder i en mapp som ZIP med annoterade versioner.
  - [ ] Endpoint `POST /api/v1/export/batch` — ta emot lista med filnamn.
  - [ ] Watch folder: valfri output av annoterade bilder (inte bara JSON).
  - [ ] Config: `VISION_EXPORT_ANNOTATED=1`, `VISION_EXPORT_FORMAT=jpg|png`.
- [ ] **Frontend**:
  - [ ] Nedladdningsknapp (⬇️) på preview-bilden efter inferens.
  - [ ] Export-meny: "Original", "Med detektioner", "Anonymiserad", "Anonymiserad + detektioner".
  - [ ] Video: progress-bar + nedladdningslänk när klar.
  - [ ] Batch-export: markera flera filer → "Exportera alla".
  - [ ] i18n: exportrelaterade strängar för alla språk.

#### PI-plan för P15 (Export)

**PI-mål (2 veckor)**
Ge användaren möjlighet att ladda ner bearbetade bilder och videor direkt från UI:t.

**Spår & Stories**

1) **Bild-export Backend (2–3 dagar)**
- [ ] `ImageAnnotator`-klass: rita bounding boxes + labels på PIL-bild.
- [ ] Endpoint `GET /api/v1/export/image?name=...&boxes=1&privacy=1`.
- [ ] `POST /api/v1/export/image` för uppladdade bilder.
- [ ] Returnera JPEG/PNG som `StreamingResponse`.

2) **Video-export Backend (3–4 dagar)**
- [ ] OpenCV-baserad video-skrivare (`cv2.VideoWriter`).
- [ ] Rita bounding boxes + valfri privacy per frame.
- [ ] Bakgrundsjobb med progress-tracking.
- [ ] Endpoint `POST /api/v1/export/video` → jobb-ID → `GET /api/v1/export/video/{id}`.

3) **Batch-export (2–3 dagar)**
- [ ] ZIP-generator med annoterade bilder.
- [ ] Watch folder output-mode: `VISION_WATCH_MODE=annotated`.
- [ ] Endpoint `POST /api/v1/export/batch`.

4) **Frontend (3–4 dagar)**
- [ ] Nedladdningsknapp-komponent med dropdown-meny.
- [ ] Export-alternativ: original, annoterad, anonymiserad, båda.
- [ ] Progress-indikator för video + batch.
- [ ] i18n: sv, en + övriga språk.

**Definition of Done**
- [ ] Annoterade bilder kan laddas ner med ett klick.
- [ ] Anonymiserade bilder kan exporteras separat.
- [ ] Video-export fungerar med bounding boxes + privacy.
- [ ] Batch-export av hela mappar som ZIP.
- [ ] Watch folder kan skriva annoterade bilder.

## Anteckningar

- [plan.md](plan.md) är källan för status + TODO.
