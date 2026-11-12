# JSON-line stdin/stdout server. Each request carries an image as JPEG base64.
# No screenshots or disk reads: the parent supplies decoded video pixels.
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.DataWriter,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null=[Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
$asTaskGeneric=([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetGenericArguments().Count -eq 1 })[0]
function Await($taskLike,$resultType) {
    $netTask=$asTaskGeneric.MakeGenericMethod($resultType).Invoke($null,@($taskLike))
    $netTask.Wait()
    return $netTask.Result
}
$engine=[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))
if ($null -eq $engine) { throw 'English Windows OCR is unavailable' }
[Console]::WriteLine('{"ready":true}')
while (($line=[Console]::ReadLine()) -ne $null) {
    $memory=$null; $bitmap=$null; $dataWriter=$null; $request=$null
    try {
        $request=$line | ConvertFrom-Json
        $memory=[Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
        $dataWriter=[Windows.Storage.Streams.DataWriter]::new($memory)
        $dataWriter.WriteBytes([Convert]::FromBase64String($request.image))
        $null=Await ($dataWriter.StoreAsync()) ([uint32])
        $null=$dataWriter.DetachStream()
        $dataWriter.Dispose(); $dataWriter=$null
        $memory.Seek(0)
        $decoder=Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($memory)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $scale=2.0
        if ($request.scale) { $scale=[double]$request.scale }
        $scale=[Math]::Min($scale,[Windows.Media.Ocr.OcrEngine]::MaxImageDimension/[Math]::Max($decoder.PixelWidth,$decoder.PixelHeight))
        $transform=[Windows.Graphics.Imaging.BitmapTransform]::new()
        $transform.ScaledWidth=[uint32][Math]::Round($decoder.PixelWidth*$scale)
        $transform.ScaledHeight=[uint32][Math]::Round($decoder.PixelHeight*$scale)
        $bitmap=Await ($decoder.GetSoftwareBitmapAsync([Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,[Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied,$transform,[Windows.Graphics.Imaging.ExifOrientationMode]::IgnoreExifOrientation,[Windows.Graphics.Imaging.ColorManagementMode]::DoNotColorManage)) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $result=Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $lineNo=0
        $words=@($result.Lines | ForEach-Object {
            foreach ($word in $_.Words) {
                [pscustomobject]@{text=$word.Text;line=$lineNo;x=$word.BoundingRect.X/$scale;y=$word.BoundingRect.Y/$scale;width=$word.BoundingRect.Width/$scale;height=$word.BoundingRect.Height/$scale}
            }
            $lineNo++
        })
        $response=[pscustomobject]@{id=$request.id;text=$result.Text;words=$words;error=$null}
    } catch {
        $response=[pscustomobject]@{id=$request.id;text='';words=@();error=$_.Exception.Message}
    } finally {
        if ($bitmap) {$bitmap.Dispose()}
        if ($dataWriter) {$dataWriter.Dispose()}
        if ($memory) {$memory.Dispose()}
    }
    [Console]::WriteLine(($response | ConvertTo-Json -Depth 5 -Compress))
}
