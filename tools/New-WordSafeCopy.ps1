[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]] $InputPath,

    [string] $ReviewRoot,

    [string] $BackupRoot,

    [switch] $PlanOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $ReviewRoot) {
    $ReviewRoot = Join-Path $projectRoot '.docx-review'
}
if (-not $BackupRoot) {
    $BackupRoot = Join-Path $projectRoot '.docx-backups'
}

$reviewRootFull = [System.IO.Path]::GetFullPath($ReviewRoot)
$backupRootFull = [System.IO.Path]::GetFullPath($BackupRoot)
$projectPrefix = $projectRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

function Test-IsUnderPath {
    param(
        [Parameter(Mandatory = $true)][string] $Candidate,
        [Parameter(Mandatory = $true)][string] $Parent
    )

    $candidateFull = [System.IO.Path]::GetFullPath($Candidate)
    $parentPrefix = [System.IO.Path]::GetFullPath($Parent).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    return $candidateFull.StartsWith($parentPrefix, [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-RepositoryRelativePath {
    param([Parameter(Mandatory = $true)][string] $FullName)

    $absolute = [System.IO.Path]::GetFullPath($FullName)
    if (-not $absolute.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "拒绝处理项目目录之外的文件：$absolute"
    }
    return [System.IO.Path]::GetRelativePath($projectRoot, $absolute)
}

function Test-IsExcludedSourcePath {
    param([Parameter(Mandatory = $true)][string] $FullName)

    $absolute = [System.IO.Path]::GetFullPath($FullName)
    if ((Test-IsUnderPath -Candidate $absolute -Parent $reviewRootFull) -or
        (Test-IsUnderPath -Candidate $absolute -Parent $backupRootFull)) {
        return $true
    }

    $relative = Get-RepositoryRelativePath -FullName $absolute
    $segments = $relative -split '[\\/]'
    foreach ($segment in $segments) {
        if ($segment -match '(?i)backup' -or
            $segment -match '^\.codex(?:[-_].*)?$' -or
            $segment -in @('.qa', 'outputs')) {
            return $true
        }
    }
    return $false
}

function Test-GitTracked {
    param([Parameter(Mandatory = $true)][string] $RelativePath)

    $gitPath = $RelativePath.Replace([System.IO.Path]::DirectorySeparatorChar, '/')
    & git -C $projectRoot ls-files --error-unmatch -- ":(literal)$gitPath" *> $null
    return $LASTEXITCODE -eq 0
}

$candidates = [System.Collections.Generic.List[System.IO.FileInfo]]::new()
foreach ($requestedPath in $InputPath) {
    $resolvedItems = @(Get-Item -LiteralPath $requestedPath -ErrorAction Stop)
    foreach ($item in $resolvedItems) {
        if ($item.PSIsContainer) {
            foreach ($file in Get-ChildItem -LiteralPath $item.FullName -File -Recurse -Filter '*.docx') {
                $candidates.Add($file)
            }
        }
        elseif ($item.Extension -ieq '.docx') {
            $candidates.Add($item)
        }
        else {
            throw "仅接受 .docx 文件或包含 .docx 的目录：$($item.FullName)"
        }
    }
}

$files = @(
    $candidates |
        Where-Object {
            -not $_.Name.StartsWith('~$') -and
            -not (Test-IsExcludedSourcePath -FullName $_.FullName)
        } |
        Sort-Object FullName -Unique
)

if ($files.Count -eq 0) {
    throw '没有找到可处理的 Word 文档。备份、工作副本和 Word 临时文件会被自动排除。'
}

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$reviewSession = Join-Path $reviewRootFull $timestamp
$backupSession = Join-Path $backupRootFull $timestamp

$manifest = foreach ($file in $files) {
    $relative = Get-RepositoryRelativePath -FullName $file.FullName
    $relativeDirectory = Split-Path $relative -Parent
    $reviewDirectory = if ($relativeDirectory) { Join-Path $reviewSession $relativeDirectory } else { $reviewSession }
    $backupDirectory = if ($relativeDirectory) { Join-Path $backupSession $relativeDirectory } else { $backupSession }
    $reviewName = '{0}_REVIEW{1}' -f $file.BaseName, $file.Extension

    [pscustomobject]@{
        SourcePath       = $file.FullName
        RelativePath     = $relative
        GitTracked       = Test-GitTracked -RelativePath $relative
        SourceSha256     = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        BackupPath       = Join-Path $backupDirectory $file.Name
        ReviewPath       = Join-Path $reviewDirectory $reviewName
    }
}

if ($PlanOnly) {
    $manifest | Format-Table RelativePath, GitTracked, SourceSha256 -AutoSize
    Write-Host "只读预检完成：$($manifest.Count) 个文件；未创建、复制、覆盖或删除任何文件。"
    return
}

foreach ($entry in $manifest) {
    foreach ($destination in @($entry.BackupPath, $entry.ReviewPath)) {
        if (Test-Path -LiteralPath $destination) {
            throw "目标已存在，已停止以防覆盖：$destination"
        }
        $parent = Split-Path $destination -Parent
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    Copy-Item -LiteralPath $entry.SourcePath -Destination $entry.BackupPath
    Copy-Item -LiteralPath $entry.SourcePath -Destination $entry.ReviewPath

    $backupHash = (Get-FileHash -LiteralPath $entry.BackupPath -Algorithm SHA256).Hash
    $reviewHash = (Get-FileHash -LiteralPath $entry.ReviewPath -Algorithm SHA256).Hash
    if ($backupHash -ne $entry.SourceSha256 -or $reviewHash -ne $entry.SourceSha256) {
        throw "复制后哈希校验失败，已停止：$($entry.SourcePath)"
    }
}

$manifestPath = Join-Path $backupSession 'manifest.csv'
$manifest | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8

Write-Host "安全副本已创建：$($manifest.Count) 个文件"
Write-Host "备份目录：$backupSession"
Write-Host "工作副本：$reviewSession"
Write-Host "审计清单：$manifestPath"
Write-Host '原始 Word 文件未被修改。后续格式操作只能针对工作副本。'
