# SPDX-License-Identifier: MIT
$ErrorActionPreference = 'Stop'
$framework = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$compiler = Join-Path $framework 'csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw '.NET Framework 4.x x64 compiler is required.' }
$destination = Join-Path $PSScriptRoot 'bin'
New-Item -ItemType Directory -Force -Path $destination | Out-Null
& $compiler /nologo /target:exe /platform:x64 ('/out:'+(Join-Path $destination 'XqCompileRunner.exe')) ('/r:'+(Join-Path $framework 'WPF\UIAutomationClient.dll')) ('/r:'+(Join-Path $framework 'WPF\UIAutomationTypes.dll')) ('/r:'+(Join-Path $framework 'WPF\WindowsBase.dll')) /r:System.Web.Extensions.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll (Join-Path $PSScriptRoot 'src\Desktop.cs')
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Write-Output 'Build complete. Binary has NOT been launched, signed, or approved.'
