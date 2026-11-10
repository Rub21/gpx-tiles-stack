#!/bin/sh
# Make /data/gpx-planet-2013.gpx.bz2 from the 2013 dump, in one stream:
# download, xz, convert, bzip2. Nothing else is stored.
#   GPX_2013_SRC   URL of the tar.xz, or a file under /data
#   GPX_2013_OUT   output file (default /data/gpx-planet-2013.gpx.bz2)
set -eu
src=${GPX_2013_SRC:-https://planet.openstreetmap.org/gps/gpx-planet-2013-04-09.tar.xz}
out=${GPX_2013_OUT:-/data/gpx-planet-2013.gpx.bz2}
case "$src" in
  http://*|https://*) read="curl -sSL $src" ;;
  *) read="cat $src" ;;
esac
echo "$(date -u +%FT%TZ) $src -> $out"
# The file is written as .part and renamed at the end, so a half-made file
# is never used by import.
$read | xz -dc | python3 /usr/local/bin/convert-2013.py | pbzip2 > "$out.part"
mv "$out.part" "$out"
echo "$(date -u +%FT%TZ) done: $(du -h "$out" | cut -f1)"
