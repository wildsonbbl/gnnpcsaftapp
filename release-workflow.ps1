$version='v1.2.0'
$platform='windows'

## create tag and release
git tag $version
git push origin $version
gh release create -d --generate-notes --latest --verify-tag $version

## create package
uv run pyinstaller --distpath ./app_pkg/dist --workpath ./app_pkg/build --noconfirm --clean ./gnnpcsaft.spec
cd ./app_pkg/dist/gnnpcsaft
zip -r gnnpcsaft-$version-$platform.zip ./*

## add artifact to release
gh release upload $version gnnpcsaft-$version-$platform.zip