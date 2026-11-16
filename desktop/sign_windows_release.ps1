param(
    [Parameter(Mandatory=$true)][string]$InputExe,
    [Parameter(Mandatory=$true)][string]$OutputExe,
    [Parameter(Mandatory=$true)][string]$SignTool,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{40}$')][string]$CertificateThumbprint,
    [Parameter(Mandatory=$true)][uri]$TimestampUrl
)
$ErrorActionPreference = 'Stop'
if ($TimestampUrl.Scheme -ne 'https') { throw 'Use the signing provider''s HTTPS RFC 3161 timestamp endpoint.' }
$sourcePath = (Resolve-Path -LiteralPath $InputExe).Path
$toolPath = (Resolve-Path -LiteralPath $SignTool).Path
$destinationPath = [System.IO.Path]::GetFullPath($OutputExe)
if (Test-Path -LiteralPath $destinationPath) { throw 'Choose a new output file; existing releases are preserved.' }
if ([System.IO.Path]::GetExtension($sourcePath) -ne '.exe') { throw 'The input must be an executable.' }
$certificate = Get-Item -LiteralPath "Cert:\CurrentUser\My\$CertificateThumbprint"
if (-not $certificate.HasPrivateKey -or $certificate.NotAfter -le (Get-Date)) { throw 'A current certificate with access to its signing key is required.' }
if (-not ($certificate.EnhancedKeyUsageList.ObjectId.Value -contains '1.3.6.1.5.5.7.3.3')) { throw 'The certificate must permit code signing.' }
$outputFolder = Split-Path -Parent $destinationPath
if (-not (Test-Path -LiteralPath $outputFolder)) { throw 'Create the intended output folder first.' }
$stagingPath = Join-Path $outputFolder ([guid]::NewGuid().ToString() + '.exe')
try {
    Copy-Item -LiteralPath $sourcePath -Destination $stagingPath
    & $toolPath sign /sha1 $CertificateThumbprint /s My /fd SHA256 /tr $TimestampUrl.AbsoluteUri /td SHA256 /d 'USAFE Connect' $stagingPath
    if ($LASTEXITCODE -ne 0) { throw 'Code signing failed.' }
    & $toolPath verify /pa /all /tw $stagingPath
    if ($LASTEXITCODE -ne 0) { throw 'Windows signature verification failed.' }
    $signature = Get-AuthenticodeSignature -LiteralPath $stagingPath
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Thumbprint -ne $CertificateThumbprint -or $null -eq $signature.TimeStamperCertificate) {
        throw 'The signer or trusted timestamp does not match the release policy.'
    }
    Move-Item -LiteralPath $stagingPath -Destination $destinationPath
    Write-Output "Signed and verified: $destinationPath"
} finally {
    if (Test-Path -LiteralPath $stagingPath) { Remove-Item -LiteralPath $stagingPath }
}
