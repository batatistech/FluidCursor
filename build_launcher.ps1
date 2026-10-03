# Rebuild the one launcher executable in place.
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$compilerCandidates = @(
    (Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'),
    (Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe')
)
$compiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compiler) { throw 'The Windows .NET Framework C# compiler was not found.' }
$compilerArgs = @(
    '/nologo', '/target:winexe', '/optimize+',
    '/reference:System.Windows.Forms.dll',
    ('/win32icon:' + (Join-Path $projectRoot 'assets\icon.ico')),
    ('/win32manifest:' + (Join-Path $projectRoot 'app.manifest')),
    ('/out:' + (Join-Path $projectRoot 'FluidCursor.exe')),
    (Join-Path $projectRoot 'launcher.cs')
)
& $compiler @compilerArgs
if ($LASTEXITCODE -ne 0) { throw "Launcher compilation failed with exit code $LASTEXITCODE." }
Write-Output 'Built FluidCursor.exe'
