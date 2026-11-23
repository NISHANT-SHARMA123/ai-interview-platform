# =============================================================================
# MediaPipe Self-Hosted Assets Downloader
# Fetches official Google MediaPipe Tasks vision WASM binaries and models
# =============================================================================

$wasmDir = "static/vendor/mediapipe/wasm"
$modelsDir = "static/vendor/mediapipe/models"

New-Item -ItemType Directory -Force -Path $wasmDir | Out-Null
New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null

$version = "0.10.14"
$wasmBaseUrl = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@$version/wasm"

$wasmFiles = @(
    "vision_wasm_internal.js",
    "vision_wasm_internal.wasm",
    "vision_wasm_nosimd_internal.js",
    "vision_wasm_nosimd_internal.wasm"
)

Write-Host ">>> Downloading MediaPipe Tasks Vision WASM assets ($version)..." -ForegroundColor Cyan
foreach ($file in $wasmFiles) {
    $target = Join-Path $wasmDir $file
    if (-not (Test-Path $target)) {
        Write-Host "  Downloading $file..."
        Invoke-WebRequest -Uri "$wasmBaseUrl/$file" -OutFile $target
    } else {
        Write-Host "  $file already exists." -ForegroundColor Gray
    }
}

$modelUrls = @{
    "pose_landmarker_lite.task" = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    "face_landmarker.task" = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
    "efficientdet_lite0.tflite" = "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/latest/efficientdet_lite0.tflite"
}

Write-Host ">>> Downloading MediaPipe Model Task Binaries..." -ForegroundColor Cyan
foreach ($item in $modelUrls.GetEnumerator()) {
    $target = Join-Path $modelsDir $item.Key
    if (-not (Test-Path $target)) {
        Write-Host "  Downloading $($item.Key)..."
        Invoke-WebRequest -Uri $item.Value -OutFile $target
    } else {
        Write-Host "  $($item.Key) already exists." -ForegroundColor Gray
    }
}

Write-Host ">>> All MediaPipe self-hosted assets downloaded into /static/vendor/mediapipe/!" -ForegroundColor Green
