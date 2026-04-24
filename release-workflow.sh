script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
kv_file="$script_dir/app/gnnpcsaft.kv"
version_number="$(sed -nE 's/^[[:space:]]*text:[[:space:]]*"Version:[[:space:]]*([0-9]+\.[0-9]+\.[0-9]+)".*/\1/p' "$kv_file" | head -n 1)"

if [ -z "$version_number" ]; then
	echo "Could not find version in $kv_file" >&2
	exit 1
fi

version="v$version_number"
platform=ubuntu

## create tag and release
# git tag $version
# git push origin $version
# gh release create -d --generate-notes --latest --verify-tag $version

## create package
uv pip install -r requirements.txt
uv run pyinstaller --distpath ./app_pkg/dist --workpath ./app_pkg/build --noconfirm --clean ./gnnpcsaft.spec
cd ./app_pkg/dist/gnnpcsaft
zip -r gnnpcsaft-$version-$platform.zip ./*

## add artifact to release
gh release upload $version gnnpcsaft-$version-$platform.zip