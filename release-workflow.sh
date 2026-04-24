script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
kv_file="$script_dir/app/gnnpcsaft.kv"
version_number="$(sed -nE 's/^[[:space:]]*text:[[:space:]]*"Version:[[:space:]]*([0-9]+\.[0-9]+\.[0-9]+)".*/\1/p' "$kv_file" | head -n 1)"

set -euo pipefail

if [ -z "$version_number" ]; then
	echo "Could not find version in $kv_file" >&2
	exit 1
fi

version="v$version_number"
arch="$(dpkg --print-architecture)"
package_name="gnnpcsaft"
deb_file="${package_name}_${version_number}_${arch}.deb"

## create tag and release
# git tag $version
# git push origin $version
# gh release create -d --generate-notes --latest --verify-tag $version

## create package
uv pip install -r requirements.txt
uv run pyinstaller --distpath ./app_pkg/dist --workpath ./app_pkg/build --noconfirm --clean ./gnnpcsaft.spec

dist_dir="$script_dir/app_pkg/dist/gnnpcsaft"
pkg_root="$script_dir/app_pkg/dist/deb_pkg"

rm -rf "$pkg_root"
mkdir -p "$pkg_root/DEBIAN" "$pkg_root/opt/$package_name" "$pkg_root/usr/bin"

cp -a "$dist_dir/." "$pkg_root/opt/$package_name/"
ln -sf "/opt/$package_name/$package_name" "$pkg_root/usr/bin/$package_name"

cat > "$pkg_root/DEBIAN/control" <<EOF
Package: $package_name
Version: $version_number
Section: utils
Priority: optional
Architecture: $arch
Maintainer: Wildson B. B. Lima <wil_bbl@hotmail.com>
Description: GNNPCSAFT desktop application
EOF

dpkg-deb --build "$pkg_root" "$script_dir/app_pkg/dist/$deb_file"

## add artifact to release
gh release upload "$version" "$script_dir/app_pkg/dist/$deb_file"