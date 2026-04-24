$kvFile = Join-Path $PSScriptRoot 'app/gnnpcsaft.kv'
$versionNumber = Select-String -Path $kvFile -Pattern 'text:\s*"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)"' |
	Select-Object -First 1 |
	ForEach-Object { $_.Matches[0].Groups[1].Value }

if (-not $versionNumber) {
	throw "Could not find version in $kvFile"
}

$version = "v$versionNumber"
$platform='windows'

## create tag and release
git tag $version
git push origin $version
gh release create -d --generate-notes --latest --verify-tag $version

## create package
uv pip install -r requirements.txt
uv run pyinstaller --distpath ./app_pkg/dist --workpath ./app_pkg/build --noconfirm --clean ./gnnpcsaft.spec
cd ./app_pkg/dist/gnnpcsaft
zip -r gnnpcsaft-$version-$platform.zip ./*

## add artifact to release
gh release upload $version gnnpcsaft-$version-$platform.zip