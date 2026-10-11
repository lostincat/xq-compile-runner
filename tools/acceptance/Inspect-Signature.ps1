# SPDX-License-Identifier: MIT
param([Parameter(Mandatory=$true)][string]$Executable)
$ErrorActionPreference = 'Stop'
try {
    $file = Get-Item -LiteralPath $Executable
    if ($file.PSIsContainer) { throw 'Not a file' }
    $before = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    $signature = Get-AuthenticodeSignature -LiteralPath $file.FullName
    $after = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    if ($before -ne $after) { throw 'File changed during inspection' }
    [ordered]@{
        status = $signature.Status.ToString()
        sha256 = $after.ToLowerInvariant()
        signer_subject = $(if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { '' })
        signer_thumbprint = $(if ($signature.SignerCertificate) { $signature.SignerCertificate.Thumbprint } else { '' })
        timestamp_present = ($null -ne $signature.TimeStamperCertificate)
    } | ConvertTo-Json -Compress
} catch {
    @{ status='INSPECTION_FAILED'; error=$_.Exception.Message } | ConvertTo-Json -Compress
    exit 1
}
