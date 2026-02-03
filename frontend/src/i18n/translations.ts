export type Locale = 'sv' | 'en';

export type TranslationKey = keyof typeof translations.sv;

export const translations = {
    sv: {
        // Navigation
        'nav.home': 'Hem',
        'nav.settings': 'Inställningar',
        'nav.back': 'Tillbaka',

        // Header
        'header.title': 'Vision',
        'header.subtitle': 'Bildinferens',

        // Status
        'status.connected': 'Ansluten',
        'status.disconnected': 'Ej ansluten',
        'status.loading': 'Laddar...',
        'status.modelLoaded': 'Modell laddad',
        'status.modelNotLoaded': 'Ingen modell',

        // Upload
        'upload.title': 'Ladda upp bild',
        'upload.dropHere': 'Släpp bild här',
        'upload.orClick': 'eller klicka för att bläddra',
        'upload.dragActive': 'Släpp för att ladda upp',
        'upload.supportedFormats': 'Stöder: JPG, PNG, HEIC, WebP',

        // Demo files
        'demo.title': 'Demofiler',
        'demo.selectFile': 'Välj fil från ./input',
        'demo.noFiles': 'Inga filer tillgängliga',
        'demo.refresh': 'Uppdatera',
        'demo.fileCount': '{count} filer',

        // Inference
        'infer.run': 'Kör inferens',
        'infer.running': 'Kör...',
        'infer.runUpload': 'Kör på uppladdad',
        'infer.runDemo': 'Kör på demofil',

        // Results
        'results.title': 'Detektioner',
        'results.noResults': 'Kör inferens för att se resultat',
        'results.noDetections': 'Inga objekt detekterade',
        'results.confidence': 'Konfidens',
        'results.objects': '{count} objekt',

        // Preview
        'preview.title': 'Förhandsvisning',
        'preview.noImage': 'Välj en bild för förhandsvisning',
        'preview.zoom': 'Zoom',
        'preview.fit': 'Anpassa',
        'preview.zoomIn': 'Zooma in',
        'preview.zoomOut': 'Zooma ut',

        // Settings
        'settings.title': 'Inställningar',
        'settings.ui': 'Gränssnitt',
        'settings.backend': 'Backend',
        'settings.models': 'Modeller',
        'settings.dangerZone': 'Farozonen',

        'settings.apiBase': 'API-adress',
        'settings.apiBasePlaceholder': 'http://localhost:8000',
        'settings.saveApiBase': 'Spara',
        'settings.savedInBrowser': 'Sparad i webbläsaren',

        'settings.theme': 'Tema',
        'settings.themeDark': 'Mörkt',
        'settings.themeLight': 'Ljust',
        'settings.themeSystem': 'System',

        'settings.language': 'Språk',
        'settings.languageSv': 'Svenska',
        'settings.languageEn': 'English',

        'settings.saveUploads': 'Spara uppladdningar',
        'settings.saveUploadsDesc': 'Spara uppladdade bilder till /input/_uploads',
        'settings.uploadsSubdir': 'Undermapp',
        'settings.allowMutations': 'Tillåt destruktiva åtgärder',
        'settings.allowMutationsWarning': 'Farligt om /input pekar på OneDrive/Desktop',

        'settings.runtimeSettings': 'Runtime-inställningar',
        'settings.runtimeEnabled': 'Aktiverad',
        'settings.runtimeDisabled': 'Inaktiverad',
        'settings.applyRuntime': 'Tillämpa på backend',
        'settings.copyEnv': 'Kopiera .env',

        'settings.inputFiles': 'Input-filer',
        'settings.uploads': 'Uppladdningar',
        'settings.totalSize': 'Total storlek',

        'settings.clearUploads': 'Rensa uppladdningar',
        'settings.clearAll': 'Rensa ALLT',
        'settings.clearConfirm': 'Skriv CLEAR för att bekräfta',
        'settings.cancelled': 'Avbrutet',

        'settings.modelsDir': 'Modellmapp',
        'settings.noModels': 'Inga modeller hittades',
        'settings.activate': 'Aktivera',
        'settings.active': 'Aktiv',
        'settings.inputSize': 'Inputstorlek',

        'settings.refresh': 'Uppdatera',
        'settings.refreshBackend': 'Uppdatera backend',
        'settings.refreshModels': 'Uppdatera modeller',

        'settings.uploadModel': 'Ladda upp modell',
        'settings.modelFile': 'ONNX-modell (.onnx)',
        'settings.labelsFile': 'Etiketter (labels.txt)',
        'settings.bundleName': 'Bundle-namn',

        // Notifications
        'notify.success': 'Klart!',
        'notify.error': 'Fel',
        'notify.warning': 'Varning',
        'notify.info': 'Info',

        'notify.apiBaseSaved': 'API-adress sparad i webbläsaren',
        'notify.settingsApplied': 'Inställningar tillämpade på backend',
        'notify.modelActivated': 'Modell aktiverad: {name}',
        'notify.cleared': 'Rensat {scope}: {files} filer, {dirs} mappar',
        'notify.copiedEnv': 'Kopierade .env till urklipp',
        'notify.inferenceComplete': 'Inferens klar: {count} objekt',
        'notify.uploadFailed': 'Uppladdning misslyckades',
        'notify.requestFailed': 'Begäran misslyckades ({status})',

        // Common
        'common.loading': 'Laddar...',
        'common.save': 'Spara',
        'common.cancel': 'Avbryt',
        'common.confirm': 'Bekräfta',
        'common.delete': 'Ta bort',
        'common.close': 'Stäng',
        'common.yes': 'Ja',
        'common.no': 'Nej',
        'common.ok': 'OK',
        'common.files': 'filer',
        'common.version': 'Version',

        // Filters
        'filters.title': 'Filter',
        'filters.edit': 'Redigera filter',
        'filters.newName': 'Nytt filternamn',
        'filters.minConfidence': 'Min konfidens',
        'filters.classes': 'Klasser',
        'filters.include': 'Inkludera',
        'filters.exclude': 'Exkludera',
        'filters.allClasses': 'Alla klasser',
        'filters.noLabels': 'Inga etiketter laddade',

        // Watcher
        'watcher.title': 'Auto-detektion',
        'watcher.loading': 'Laddar status...',
        'watcher.unavailable': 'Watcher ej tillgänglig',
        'watcher.active': 'Aktiv',
        'watcher.inactive': 'Inaktiv',
        'watcher.pending': 'Väntande',
        'watcher.processedToday': 'Bearbetade idag',
        'watcher.mode': 'Läge',
        'watcher.autoMove': 'Auto-flytt',
        'watcher.folders': 'Visa mappsökvägar',
        'watcher.enableHint': 'Ställ in VISION_WATCH=1 för att aktivera',
    },

    en: {
        // Navigation
        'nav.home': 'Home',
        'nav.settings': 'Settings',
        'nav.back': 'Back',

        // Header
        'header.title': 'Vision',
        'header.subtitle': 'Image Inference',

        // Status
        'status.connected': 'Connected',
        'status.disconnected': 'Disconnected',
        'status.loading': 'Loading...',
        'status.modelLoaded': 'Model loaded',
        'status.modelNotLoaded': 'No model',

        // Upload
        'upload.title': 'Upload Image',
        'upload.dropHere': 'Drop image here',
        'upload.orClick': 'or click to browse',
        'upload.dragActive': 'Drop to upload',
        'upload.supportedFormats': 'Supports: JPG, PNG, HEIC, WebP',

        // Demo files
        'demo.title': 'Demo Files',
        'demo.selectFile': 'Select file from ./input',
        'demo.noFiles': 'No files available',
        'demo.refresh': 'Refresh',
        'demo.fileCount': '{count} files',

        // Inference
        'infer.run': 'Run Inference',
        'infer.running': 'Running...',
        'infer.runUpload': 'Run on upload',
        'infer.runDemo': 'Run on demo file',

        // Results
        'results.title': 'Detections',
        'results.noResults': 'Run inference to see results',
        'results.noDetections': 'No objects detected',
        'results.confidence': 'Confidence',
        'results.objects': '{count} objects',

        // Preview
        'preview.title': 'Preview',
        'preview.noImage': 'Select an image to preview',
        'preview.zoom': 'Zoom',
        'preview.fit': 'Fit',
        'preview.zoomIn': 'Zoom in',
        'preview.zoomOut': 'Zoom out',

        // Settings
        'settings.title': 'Settings',
        'settings.ui': 'Interface',
        'settings.backend': 'Backend',
        'settings.models': 'Models',
        'settings.dangerZone': 'Danger Zone',

        'settings.apiBase': 'API Base URL',
        'settings.apiBasePlaceholder': 'http://localhost:8000',
        'settings.saveApiBase': 'Save',
        'settings.savedInBrowser': 'Saved in browser',

        'settings.theme': 'Theme',
        'settings.themeDark': 'Dark',
        'settings.themeLight': 'Light',
        'settings.themeSystem': 'System',

        'settings.language': 'Language',
        'settings.languageSv': 'Svenska',
        'settings.languageEn': 'English',

        'settings.saveUploads': 'Save uploads',
        'settings.saveUploadsDesc': 'Save uploaded images to /input/_uploads',
        'settings.uploadsSubdir': 'Subdirectory',
        'settings.allowMutations': 'Allow destructive actions',
        'settings.allowMutationsWarning': 'Dangerous if /input points to OneDrive/Desktop',

        'settings.runtimeSettings': 'Runtime settings',
        'settings.runtimeEnabled': 'Enabled',
        'settings.runtimeDisabled': 'Disabled',
        'settings.applyRuntime': 'Apply to backend',
        'settings.copyEnv': 'Copy .env',

        'settings.inputFiles': 'Input files',
        'settings.uploads': 'Uploads',
        'settings.totalSize': 'Total size',

        'settings.clearUploads': 'Clear uploads',
        'settings.clearAll': 'Clear ALL',
        'settings.clearConfirm': 'Type CLEAR to confirm',
        'settings.cancelled': 'Cancelled',

        'settings.modelsDir': 'Models directory',
        'settings.noModels': 'No models found',
        'settings.activate': 'Activate',
        'settings.active': 'Active',
        'settings.inputSize': 'Input size',

        'settings.refresh': 'Refresh',
        'settings.refreshBackend': 'Refresh backend',
        'settings.refreshModels': 'Refresh models',

        'settings.uploadModel': 'Upload model',
        'settings.modelFile': 'ONNX model (.onnx)',
        'settings.labelsFile': 'Labels (labels.txt)',
        'settings.bundleName': 'Bundle name',

        // Notifications
        'notify.success': 'Success!',
        'notify.error': 'Error',
        'notify.warning': 'Warning',
        'notify.info': 'Info',

        'notify.apiBaseSaved': 'API base URL saved in browser',
        'notify.settingsApplied': 'Settings applied to backend',
        'notify.modelActivated': 'Model activated: {name}',
        'notify.cleared': 'Cleared {scope}: {files} files, {dirs} directories',
        'notify.copiedEnv': 'Copied .env to clipboard',
        'notify.inferenceComplete': 'Inference complete: {count} objects',
        'notify.uploadFailed': 'Upload failed',
        'notify.requestFailed': 'Request failed ({status})',

        // Common
        'common.loading': 'Loading...',
        'common.save': 'Save',
        'common.cancel': 'Cancel',
        'common.confirm': 'Confirm',
        'common.delete': 'Delete',
        'common.close': 'Close',
        'common.yes': 'Yes',
        'common.no': 'No',
        'common.ok': 'OK',
        'common.files': 'files',
        'common.version': 'Version',

        // Filters
        'filters.title': 'Filter',
        'filters.edit': 'Edit filter',
        'filters.newName': 'New filter name',
        'filters.minConfidence': 'Min confidence',
        'filters.classes': 'Classes',
        'filters.include': 'Include',
        'filters.exclude': 'Exclude',
        'filters.allClasses': 'All classes',
        'filters.noLabels': 'No labels loaded',

        // Watcher
        'watcher.title': 'Auto-Detection',
        'watcher.loading': 'Loading status...',
        'watcher.unavailable': 'Watcher unavailable',
        'watcher.active': 'Active',
        'watcher.inactive': 'Inactive',
        'watcher.pending': 'Pending',
        'watcher.processedToday': 'Processed today',
        'watcher.mode': 'Mode',
        'watcher.autoMove': 'Auto-move',
        'watcher.folders': 'Show folder paths',
        'watcher.enableHint': 'Set VISION_WATCH=1 to enable',
    }
} as const;

export const defaultLocale: Locale = 'sv';

export const localeNames: Record<Locale, string> = {
    sv: 'Svenska',
    en: 'English'
};

export const localeFlags: Record<Locale, string> = {
    sv: '🇸🇪',
    en: '🇬🇧'
};
