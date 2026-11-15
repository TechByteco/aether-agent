param(
    [string]$ImagePath
)

try {
    Add-Type -AssemblyName System.Drawing
    [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
    [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
    [Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

    $absPath = [System.IO.Path]::GetFullPath($ImagePath)
    $fileAsync = [Windows.Storage.StorageFile]::GetFileFromPathAsync($absPath)
    while ($fileAsync.Status -eq 'Started') { Start-Sleep -Milliseconds 15 }
    $file = $fileAsync.GetResults()

    $streamAsync = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
    while ($streamAsync.Status -eq 'Started') { Start-Sleep -Milliseconds 15 }
    $stream = $streamAsync.GetResults()

    $decoderAsync = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
    while ($decoderAsync.Status -eq 'Started') { Start-Sleep -Milliseconds 15 }
    $decoder = $decoderAsync.GetResults()

    $softBmpAsync = $decoder.GetSoftwareBitmapAsync()
    while ($softBmpAsync.Status -eq 'Started') { Start-Sleep -Milliseconds 15 }
    $softBmp = $softBmpAsync.GetResults()

    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if (-not $engine) {
        $lang = [Windows.Globalization.Language]::new("en-US")
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    }

    $ocrAsync = $engine.RecognizeAsync($softBmp)
    while ($ocrAsync.Status -eq 'Started') { Start-Sleep -Milliseconds 15 }
    $ocrResult = $ocrAsync.GetResults()

    $lines = @()
    foreach ($line in $ocrResult.Lines) {
        $lines += $line.Text
    }
    $lines -join "`n"
} catch {
    Write-Error $_.Exception.Message
}
