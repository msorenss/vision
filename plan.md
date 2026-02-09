# Vision – Gemensam projektplan

Senast uppdaterad: 2026-02-09

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
- **Video**: Video-inferens (MP4/AVI/MOV/MKV/WebM) med annoterad export, interpolering och H.264-preview.
- **Integration**: OPC UA Server (40100-1), MQTT Client, och Webhook-stöd — även för video.
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

### P13 – Video Mode (Done ✅)
>
> **Goal**: Stödja vanliga videoformat (MP4, AVI, MOV, MKV, WebM) utöver enstaka bilder.

- [x] **Backend**:
  - [x] Video-ingest via OpenCV (`cv2.VideoCapture`) — extrahera frames.
  - [x] Nytt endpoint `POST /api/v1/infer/video` som tar emot videofil.
  - [x] Frame sampling-strategi: alla frames, var N:te, eller FPS-baserat (konfigurerbart).
  - [x] Batch-inferens per frame med bounding box-resultat.
  - [x] Valfritt: returnera annoterad video (bounding boxes inritade) som nedladdning.
  - [x] Privacy-stöd: anonymisera ansikten per frame innan detektion.
  - [x] Config: `VISION_VIDEO_FRAME_INTERVAL`, `VISION_VIDEO_MAX_FRAMES`.
- [x] **API-respons**:
  - [x] `VideoInferResponse` med per-frame detektioner + sammanfattning.
  - [x] Streaming-progress (SSE eller polling) under lång videobearbetning.
- [x] **Frontend**:
  - [x] Video-uppladdning (drag-and-drop, filväljare med video-MIME).
  - [x] Progress-bar under bearbetning.
  - [x] Frame-navigator: bläddra mellan frames och se detektioner per frame.
  - [x] Video-preview med annoterade bounding boxes.
- [x] **Watch Folder**:
  - [x] Stöd för videofiler i watch-mappen (auto-process).
  - [x] JSON-output per video (sammanfattning + per-frame).

#### PI-plan för P13 (Video Mode)

**PI-mål (3 veckor)**
Stödja vanliga videoformat i hela flödet: upload, inferens, preview, watch folder.

**Spår & Stories**

1) **Video Ingest & Frame Extraction (3–4 dagar)**
- [x] Lägg till `opencv-python-headless` i requirements.
- [x] Hjälparklass `VideoFrameExtractor` (öppna, sampla frames, stäng).
- [x] Konfigurerbart: var N:te frame, max antal frames, FPS-target.

2) **Backend API (3–4 dagar)**
- [x] `POST /api/v1/infer/video` endpoint.
- [x] `VideoInferResponse` schema (frames, detektioner per frame, total summary).
- [x] Streaming progress via SSE (`/api/v1/infer/video/status/{job_id}`).
- [x] Bakgrundsjobb (async task) för längre videor.

3) **Frontend (4–5 dagar)**
- [x] Utöka uppladdning till att acceptera video.
- [x] Progress-indikator under bearbetning.
- [x] Frame-navigering (slider/timeline) med detektionsresultat per frame.
- [x] Video-export: nedladdning av annoterad video.

4) **Watch Folder & Integration (2 dagar)**
- [x] Watcher känner igen videofiler.
- [x] JSON-output med per-frame-resultat.
- [x] MQTT/Webhook-notifiering vid klar video.

**Definition of Done**
- [x] MP4/AVI/MOV kan laddas upp och infereras.
- [x] Per-frame-resultat visas i UI.
- [x] Privacy fungerar även på video (blur per frame).
- [x] Watch folder hanterar videofiler.

### P14 – Valbar Detektionsfunktion
>
> **Goal**: Låta användaren välja vilken typ av detektion som ska utföras — t.ex. person, fordon, registreringsskylt, ansikte — istället för att alltid köra alla klasser.

- [x] **Funktionsväljare i UI**:
  - [x] Dropdown/chip-selector på huvudsidan för att välja aktiva detektionsklasser.
  - [x] Spara senaste val i `localStorage`.
  - [x] Snabbval-profiler: "Alla", "Personer", "Fordon", "Anpassat".
- [x] **Backend**:
  - [x] Utöka filter-API med predefined profiler (person, vehicle, all).
  - [x] Ny query-param `?classes=person,bus,car` på infer-endpoints.
  - [x] Stöd för att filtrera redan vid inferens (NMS-nivå) eller post-filter.
- [ ] **Multi-modell**:
  - [ ] Stöd för att byta modell beroende på uppgift (t.ex. YOLO-general vs face-only vs LPR).
  - [ ] Task-baserad modellväxling: "person detection" → yolov8n, "face" → ULFD, "license plate" → LPR-modell.
  - [ ] UI: Välj uppgift → system laddar rätt modell automatiskt.
- [ ] **Kombinerade pipelines**:
  - [ ] Kör flera modeller i sekvens (t.ex. YOLO + Privacy + LPR).
  - [ ] Sammanslagna resultat i en `InferResponse`.
- [x] **Frontend**:
  - [x] Funktionsväljare (task picker) med ikoner.
  - [x] Visa vilka klasser som är aktiva i resultat-panelen.
  - [x] i18n för alla funktionsnamn.

#### PI-plan för P14 (Valbar Detektionsfunktion)

**PI-mål (2 veckor)**
Ge användaren kontroll över vilken detektion som körs, med snabbval-profiler och framtidssäkrad multi-modell-arkitektur.

**Spår & Stories**

1) **Klass-filter i UI (2–3 dagar)** ✅
- [x] Chip-selector komponent med tillgängliga klasser (hämtade från aktiv modells `labels.txt`).
- [x] Snabbval-knappar: "Alla", "Personer", "Fordon".
- [x] Spara val i `localStorage`, skicka som query-param.

2) **Backend Profiler (2–3 dagar)** ✅
- [x] Predefined profiler i `filters.json`: `all`, `persons`, `vehicles`.
- [x] Endpoint `GET /api/v1/tasks` — lista tillgängliga uppgifter.
- [x] Infer-endpoint accepterar `?classes=...` för inline-filtrering.

3) **Multi-modell Arkitektur (3–4 dagar)**
- [x] `TaskRegistry` som mappar uppgift → modell.
- [ ] Auto-switch modell vid task-byte.
- [ ] Config: `VISION_TASKS` JSON-definition.

4) **Frontend Task Picker (2–3 dagar)** ✅
- [x] Task-picker komponent med ikoner (🧑 Person, 🚌 Fordon, 🔒 Ansikte, 🔤 Skylt).
- [x] Visa aktiv task + klasser i resultat.
- [x] i18n: sv, en + övriga språk.

**Definition of Done**
- [x] Användaren kan välja detektionstyp i UI.
- [ ] Rätt modell/filter tillämpas automatiskt.
- [x] Profiler möjliga att konfigurera.
- [ ] Kombinerade pipelines fungerar (detektion + privacy).

### P15 – Export av Bearbetade Bilder & Video
>
> **Goal**: Låta användaren ladda ner bearbetade resultat — annoterade bilder (med bounding boxes), anonymiserade bilder, och annoterade/anonymiserade videor.

- [x] **Bild-export**:
  - [x] Endpoint `GET /api/v1/export/image` — returnera bild med inritade bounding boxes.
  - [x] Valfritt: med eller utan privacy-blur (query-param `?privacy=1`).
  - [x] Valfritt: bara anonymiserad bild (utan bounding boxes) via `?mode=privacy_only`.
  - [x] Konfigurerbar box-stil: färg, tjocklek, labels on/off.
  - [x] Nedladdningsknapp i UI bredvid preview.
- [x] **Video-export** (kräver P13):
  - [x] Endpoint `POST /api/v1/infer/video/export/{job_id}` — rendera annoterad video.
  - [x] Bounding boxes inritade per frame med smooth interpolering.
  - [x] Privacy-blur per frame (om aktiverat).
  - [x] Format: MP4 (H.264) via ffmpeg, browser-kompatibelt.
  - [x] Asynkron bearbetning med progress (polling).
  - [x] Preview-endpoint `GET /api/v1/infer/video/preview/{job_id}`.
  - [x] Download-endpoint `GET /api/v1/infer/video/export/{job_id}`.
- [x] **Batch-export**:
  - [x] Exportera alla bilder i en mapp som ZIP med annoterade versioner.
  - [x] Endpoint `POST /api/v1/export/batch` — ta emot lista med filnamn.
  - [x] Watch folder: valfri output av annoterade bilder (inte bara JSON).
  - [x] Config: `VISION_EXPORT_ANNOTATED=1`, `VISION_EXPORT_FORMAT=jpg|png`.
- [x] **Frontend**:
  - [x] Nedladdningsknapp (⬇️) på preview-bilden efter inferens.
  - [x] Export-meny: "Original", "Med detektioner", "Anonymiserad", "Anonymiserad + detektioner".
  - [x] Video: progress-bar + nedladdningslänk när klar.
  - [ ] Batch-export: markera flera filer → "Exportera alla".
  - [x] i18n: exportrelaterade strängar för alla språk.

#### PI-plan för P15 (Export)

**PI-mål (2 veckor)**
Ge användaren möjlighet att ladda ner bearbetade bilder och videor direkt från UI:t.

**Spår & Stories**

1) **Bild-export Backend (2–3 dagar)** ✅
- [x] `ImageAnnotator`-klass: rita bounding boxes + labels på PIL-bild.
- [x] Endpoint `GET /api/v1/export/image?name=...&boxes=1&privacy=1`.
- [x] `POST /api/v1/export/image` för uppladdade bilder.
- [x] Returnera JPEG/PNG som `StreamingResponse`.

2) **Video-export Backend (3–4 dagar)** ✅
- [x] OpenCV-baserad video-skrivare (`cv2.VideoWriter`).
- [x] Rita bounding boxes + valfri privacy per frame.
- [x] Bakgrundsjobb med progress-tracking.
- [x] Endpoint `POST /api/v1/export/video` → jobb-ID → `GET /api/v1/export/video/{id}`.

3) **Batch-export (2–3 dagar)** ✅
- [x] ZIP-generator med annoterade bilder.
- [x] Watch folder output-mode: `VISION_WATCH_MODE=annotated`.
- [x] Endpoint `POST /api/v1/export/batch`.

4) **Frontend (3–4 dagar)** ✅
- [x] Nedladdningsknapp-komponent med dropdown-meny.
- [x] Export-alternativ: original, annoterad, anonymiserad, båda.
- [ ] Progress-indikator för video + batch.
- [x] i18n: sv, en + övriga språk.

**Definition of Done**
- [x] Annoterade bilder kan laddas ner med ett klick.
- [x] Anonymiserade bilder kan exporteras separat.
- [x] Video-export fungerar med bounding boxes + privacy.
- [x] Batch-export av hela mappar som ZIP.
- [x] Watch folder kan skriva annoterade bilder.

---

## Implementeringsplan: P14 + P15 (kvarvarande features)

> Skapad: 2026-02-09
> Baserad på analys av befintlig kodbas och gap mot P14/P15 specifikationerna.

### Sammanfattning

| Område | Status | Kvarvarande arbete |
|--------|--------|--------------------|
| P14 – Klass-filter i UI | **Klart ✅** | — |
| P14 – TaskRegistry & multi-modell | Partiell (~50%) | Auto-switch modell vid task-byte, kombinerade pipelines |
| P14 – Task picker i UI | **Klart ✅** | — |
| P15 – Video-export | **Klart ✅** | — |
| P15 – Bild-export | **Klart ✅** | — |
| P15 – Batch-export | **Klart ✅** | Batch-export UI (filvälj + "Exportera alla") kvar |
| P15 – Watch folder annoterad output | **Klart ✅** | — |

### Befintlig bas att bygga vidare på

- **Filtersystem** (från P8): `FilterSelector.tsx`, `filters.json`, `_load_filters()/_save_filters()/_apply_filter()` i `routes.py`, CRUD-endpoints `GET/POST/DELETE /api/v1/filters`.
- **Labels-endpoint**: `GET /api/v1/models/labels` (routes.py L1480) hämtar klasser från aktiv modells `labels.txt`.
- **Video-rendering**: `_draw_boxes_on_frame()` i `video_render.py` L201 — kan återanvändas som bas för `ImageAnnotator`.
- **Privacy-anonymisering**: `POST /api/v1/privacy/anonymize` returnerar anonymiserad bild (utan bboxar).

---

### Sprint 1 (vecka 1): P15 Bild-export + P14 Klass-filter

#### Dag 1–2: ImageAnnotator + Bild-export backend

**Steg 1: `ImageAnnotator`-klass** (`backend/app/inference/image_export.py`)
- Ny klass som tar en PIL-bild + lista av detektioner → ritar bounding boxes + labels.
- Konfigurerbar box-stil: färg (per klass), tjocklek, labels on/off.
- Återanvänd färglogik från `_draw_boxes_on_frame()` i `video_render.py`.
- Stöd för privacy-overlay (anropa `PrivacyEngine.anonymize_faces()` om `privacy=1`).
- Returnera PIL Image (JPEG/PNG-ready).

**Steg 2: Export-endpoints** (`backend/app/api/routes.py`)
- `GET /api/v1/export/image?name=<filnamn>&boxes=1&privacy=1&mode=annotated|privacy_only`
  - Läser bild från `output/` eller `input/`, applicerar annotation.
  - Returnerar `StreamingResponse` (JPEG).
- `POST /api/v1/export/image` — för uppladdad bild (skicka bild + detektioner i body).
- Schema: `ImageExportRequest`, `ImageExportParams` i `schema.py`.

**Steg 3: Tester**
- Smoke test: ladda upp bild → infera → exportera annoterad → verifiera att bild har bboxar.

#### Dag 2–3: P14 Klass-filter förbättringar

**Steg 4: Inline `?classes=` parameter** (`backend/app/api/routes.py`)
- Lägg till `classes: Optional[str] = Query(None)` på `POST /api/v1/infer` och `POST /api/v1/infer/filtered`.
- Post-filter: om `classes` anges, filtrera detektioner efter klass-namn (case-insensitive).
- Fungerar oberoende av sparade filter-profiler.

**Steg 5: Snabbval-profiler** (`models/filters.json`)
- Lägg till predefined profiler: `"all"` (tomt include = alla), `"persons"` (person), `"vehicles"` (car, bus, truck, motorcycle, bicycle).
- Markera dem som `"builtin": true` så de inte kan raderas via API.
- Uppdatera `_load_filters()` och `DELETE`-endpoint att skydda inbyggda profiler.

**Steg 6: Chip-selector i UI** (`frontend/src/components/FilterSelector.tsx`)
- Refaktorera till chip/toggle-baserad selector som visar top-klasser inline.
- Snabbval-knappar: "Alla", "Personer", "Fordon" som pre-selekterar rätt profil.
- Spara senaste val i `localStorage` med key `vision_active_filter`.

#### Dag 3–4: Frontend bild-export

**Steg 7: Nedladdningsknapp** (`frontend/src/app/page.tsx`)
- Lägg till ⬇️-knapp bredvid preview-bilden efter inferens.
- Export-dropdown-meny:
  - "Original" — ladda ner originalbild.
  - "Med detektioner" — `GET /api/v1/export/image?name=...&boxes=1`
  - "Anonymiserad" — `GET /api/v1/export/image?name=...&privacy=1`
  - "Anonymiserad + detektioner" — `GET /api/v1/export/image?name=...&boxes=1&privacy=1`
- Triggera browser-download via `<a download>` eller `URL.createObjectURL`.

**Steg 8: i18n** (`frontend/src/i18n/translations.ts`)
- Nya nycklar: `export.download`, `export.original`, `export.annotated`, `export.anonymized`, `export.both`, `export.batchExport`, `export.exportAll`.
- Alla 7 språk (sv, en, nl, sk, zh, fr, es).

---

### Sprint 2 (vecka 2): P14 Multi-modell + P15 Batch-export

#### Dag 5–6: P14 TaskRegistry & multi-modell

**Steg 9: `TaskRegistry`** (`backend/app/inference/task_registry.py`)
- Ny klass som mappar task-namn → modell-bundle-path.
- Config via `VISION_TASKS` env-var (JSON) eller `tasks.json` i `models/`.
- Standardtasks:
  - `"detection"` → aktiv YOLO-modell (default).
  - `"face"` → `models/privacy/ulfd/v1/` (om tillgänglig).
- Metod: `get_model_for_task(task: str) → ModelBundle`.
- Metod: `list_tasks() → List[TaskInfo]` med metadata (namn, beskrivning, ikon, tillgängliga klasser).

**Steg 10: `GET /api/v1/tasks` endpoint** (`backend/app/api/routes.py`)
- Returnerar lista av tillgängliga tasks med metadata.
- Schema: `TaskInfo(name, description, icon, model_name, classes)`, `TaskListResponse`.

**Steg 11: Task-baserad modellväxling**
- Utöka infer-endpoints: `?task=face` → laddar ULFD-modell automatiskt.
- `OnnxYoloEngine` behöver stödja hot-swap eller hålla flera sessions.
- Fallback: om task-modell saknas → returnera 404 med tydligt meddelande.

**Steg 12: Kombinerade pipelines**
- Utöka `?task=` till att acceptera kommaseparerade tasks: `?task=detection,face`.
- Kör modeller i sekvens, slå samman resultat i en `InferResponse`.
- Privacy-pipeline: om `face` ingår → anonymisera + returnera `privacy_applied=true`.

#### Dag 7–8: P14 Frontend task picker

**Steg 13: Task-picker komponent** (`frontend/src/components/TaskPicker.tsx`)
- Hämta tasks från `GET /api/v1/tasks`.
- Visa som horisontell rad med ikoner: 🧑 Person, 🚌 Fordon, 🔒 Ansikte, 🔤 Skylt.
- Selektera task → skicka `?task=...` vid inferens.
- Visa aktiv task + tillgängliga klasser i resultat-panelen.
- Spara val i `localStorage`.

**Steg 14: i18n för tasks** (`frontend/src/i18n/translations.ts`)
- Nycklar: `tasks.title`, `tasks.detection`, `tasks.face`, `tasks.licensePlate`, `tasks.all`, `tasks.selectTask`.
- Alla 7 språk.

#### Dag 8–9: P15 Batch-export

**Steg 15: Batch-export backend**
- Endpoint `POST /api/v1/export/batch` — tar emot `{ files: ["img1.jpg", "img2.jpg"], boxes: true, privacy: false }`.
- Genererar annoterade bilder → packar i ZIP → returnerar som `StreamingResponse`.
- Bakgrundsjobb om > 10 filer (med progress-tracking).
- Schema: `BatchExportRequest`, `BatchExportStatus`.

**Steg 16: Watch folder annoterad output** (`backend/app/watcher.py`)
- Ny mode: `VISION_WATCH_MODE=annotated` (utöver `json`, `move`, `both`).
- Config: `VISION_EXPORT_ANNOTATED=1`, `VISION_EXPORT_FORMAT=jpg|png`.
- När aktiverat: spara annoterad bild i `output/`-mappen bredvid JSON.
- Återanvänd `ImageAnnotator` från steg 1.

#### Dag 9–10: Frontend batch-export + polish

**Steg 17: Batch-export UI** (`frontend/src/app/page.tsx`)
- Markera flera filer i resultat-listan (checkboxar).
- "Exportera alla"-knapp → `POST /api/v1/export/batch`.
- Progress-bar under generering.
- Nedladdning av ZIP-fil.

**Steg 18: Slutpolering & QA**
- Verifiera alla endpoints med curl/Postman.
- Kontrollera i18n i alla 7 språk.
- Uppdatera `plan.md` — markera klara items.
- Testa Docker-build.

---

### Beroenden & risker

| Risk | Påverkan | Mitigation |
|------|----------|------------|
| Multi-modell hot-swap kan ge minnespress | Hög | Lazy-load modeller, unload inaktiv session |
| `ImageAnnotator` font-rendering i Docker | Låg | Fallback till OpenCV `putText` om PIL font saknas |
| Batch-export av stora mappar (100+ bilder) | Medel | Bakgrundsjobb + fildelstorleksgräns |
| Task-pipeline latency (2+ modeller) | Medel | Parallellisera oberoende modeller, cacha resultat |

### Prioriteringsordning (om tid begränsas)

1. **Bild-export** (P15) — störst användarvärde, enklast att implementera.
2. **Chip-selector + snabbval** (P14) — UX-förbättring med befintlig backend.
3. **`?classes=` inline-filter** (P14) — liten ändring, stor flexibilitet.
4. **Batch-export** (P15) — bra komplement, men kräver ZIP-logik.
5. **TaskRegistry** (P14) — arkitekturförändring, framtidssäkrar.
6. **Watch folder annoterad output** (P15) — nisch-feature, låg prioritet.

---

## Anteckningar

- [plan.md](plan.md) är källan för status + TODO.
