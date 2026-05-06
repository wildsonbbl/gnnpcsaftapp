param(
	[switch]$SkipUpload
)

$kvFile = Join-Path $PSScriptRoot 'app/gnnpcsaft.kv'
$versionNumber = Select-String -Path $kvFile -Pattern 'text:\s*"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)"' |
	Select-Object -First 1 |
	ForEach-Object { $_.Matches[0].Groups[1].Value }

if (-not $versionNumber) {
	throw "Could not find version in $kvFile"
}

$version = "v$versionNumber"
$platform='windows'
$installerName = "gnnpcsaft-$version-$platform.msi"
$appDir = Join-Path $PSScriptRoot 'app'

if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
	$env:PYTHONPATH = $appDir
}
else {
	$env:PYTHONPATH = "$appDir;$($env:PYTHONPATH)"
}

# ## create tag and release
# git tag $version
# git push origin $version
# gh release create -d --generate-notes --latest --verify-tag $version

## create package
uv pip install -r requirements.txt
uv run pyinstaller --distpath ./app_pkg/dist --workpath ./app_pkg/build --noconfirm --clean ./gnnpcsaft.spec

$distDir = Join-Path $PSScriptRoot 'app_pkg/dist/gnnpcsaft'
if (-not (Test-Path $distDir)) {
	throw "Could not find PyInstaller dist directory at $distDir"
}

$installerOutputDir = Join-Path $PSScriptRoot 'app_pkg/dist/installer'
$productWxs = Join-Path $PSScriptRoot 'gnnpcsaft-product.wxs'

Remove-Item -Path $installerOutputDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $installerOutputDir -Force | Out-Null

$installerArtifact = Join-Path $installerOutputDir $installerName
$wixCommand = Get-Command wix.exe -ErrorAction SilentlyContinue | Select-Object -First 1

if ($wixCommand) {
	$wixExe = if ($wixCommand.Source) { $wixCommand.Source } else { $wixCommand.Path }
	& $wixExe build --acceptEula wix7 $productWxs -arch x64 -d "ProductVersion=$versionNumber" -d "SourceDir=$distDir" -d "ProjectDir=$PSScriptRoot" -o $installerArtifact
	if ($LASTEXITCODE -ne 0) {
		throw 'WiX build failed while generating MSI with wix.exe'
	}
}

if (-not (Test-Path $installerArtifact)) {
	throw "Could not find generated installer at $installerArtifact"
}

## add artifact to release
if (-not $SkipUpload) {
	gh release upload $version $installerArtifact
}