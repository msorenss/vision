# Vision Smoke Test
# Tests health, settings, and infer endpoints

param(
    [string]$ApiBase = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$passed = 0
$failed = 0

function Test-Endpoint {
    param([string]$Name, [string]$Url, [scriptblock]$Validate)
    
    Write-Host "`n[$Name]" -ForegroundColor Cyan
    try {
        $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 10
        if (& $Validate $response) {
            Write-Host "  PASS" -ForegroundColor Green
            $script:passed++
            return $true
        }
        else {
            Write-Host "  FAIL: validation failed" -ForegroundColor Red
            Write-Host "  Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
            $script:failed++
            return $false
        }
    }
    catch {
        Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
        return $false
    }
}

function Test-InferEndpoint {
    param([string]$ApiBase, [string]$ImagePath)
    
    Write-Host "`n[Infer: $ImagePath]" -ForegroundColor Cyan
    
    if (-not (Test-Path $ImagePath)) {
        Write-Host "  SKIP: image not found at $ImagePath" -ForegroundColor Yellow
        return $null
    }
    
    try {
        # Use .NET for multipart form data (compatible with PS 5.1+)
        $uri = "$ApiBase/api/v1/infer"
        $fileBytes = [System.IO.File]::ReadAllBytes($ImagePath)
        $fileName = [System.IO.Path]::GetFileName($ImagePath)
        
        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        
        $bodyLines = @(
            "--$boundary",
            "Content-Disposition: form-data; name=`"image`"; filename=`"$fileName`"",
            "Content-Type: image/jpeg",
            "",
            [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($fileBytes),
            "--$boundary--"
        )
        $body = $bodyLines -join $LF
        
        $response = Invoke-RestMethod -Uri $uri -Method Post -ContentType "multipart/form-data; boundary=$boundary" -Body $body -TimeoutSec 30
        
        if ($null -ne $response.detections -and $response.image_width -gt 0) {
            Write-Host "  PASS: detected $($response.detections.Count) objects" -ForegroundColor Green
            $script:passed++
            return $true
        }
        else {
            Write-Host "  FAIL: invalid response format" -ForegroundColor Red
            $script:failed++
            return $false
        }
    }
    catch {
        Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
        return $false
    }
}

Write-Host "==================================="
Write-Host "  Vision Smoke Test"
Write-Host "  API: $ApiBase"
Write-Host "==================================="

# Test 1: Health
Test-Endpoint -Name "Health" -Url "$ApiBase/health" -Validate {
    param($r) $r.ok -eq $true
}

# Test 2: Health Ready
Test-Endpoint -Name "Health Ready" -Url "$ApiBase/health/ready" -Validate {
    param($r) $r.ready -eq $true
}

# Test 3: Settings
Test-Endpoint -Name "Settings" -Url "$ApiBase/api/v1/settings" -Validate {
    param($r) $null -ne $r.demo_input_dir
}

# Test 4: Models
Test-Endpoint -Name "Models" -Url "$ApiBase/api/v1/models" -Validate {
    param($r) $r.loaded -eq $true
}

# Test 5: Demo files
Test-Endpoint -Name "Demo Files" -Url "$ApiBase/api/v1/demo/files" -Validate {
    param($r) $null -ne $r.files
}

# Test 6: Infer via demo endpoint (simpler, no file upload)
$demoFiles = (Invoke-RestMethod -Uri "$ApiBase/api/v1/demo/files").files
if ($demoFiles.Count -gt 0) {
    $testFile = $demoFiles[0]
    Write-Host "`n[Demo Infer: $testFile]" -ForegroundColor Cyan
    try {
        $response = Invoke-RestMethod -Uri "$ApiBase/api/v1/demo/infer?name=$testFile" -Method Get -TimeoutSec 30
        if ($null -ne $response.detections) {
            Write-Host "  PASS: detected $($response.detections.Count) objects" -ForegroundColor Green
            $passed++
        }
        else {
            Write-Host "  FAIL: no detections field" -ForegroundColor Red
            $failed++
        }
    }
    catch {
        Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}
else {
    Write-Host "`n[Demo Infer]" -ForegroundColor Cyan
    Write-Host "  SKIP: no demo files available" -ForegroundColor Yellow
}

# Summary
Write-Host "`n==================================="
Write-Host "  Results: $passed passed, $failed failed"
Write-Host "==================================="

if ($failed -gt 0) {
    exit 1
}
exit 0
