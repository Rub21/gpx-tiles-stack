#!/usr/bin/env python3
"""Convert the 2013 GPX planet dump to the planet-dump-ng GPX format.

The 2013 dump (https://planet.openstreetmap.org/gps/) is a tar with
metadata.xml and one GPX file per trace in public/, identifiable/ and
trackable/ folders. planet-dump-ng writes one GPX file with a <trk> per
identifiable trace, with the trace id and tags inside. gpxtiler import
reads that format.

Reads the tar from stdin, writes the GPX to stdout. Only the identifiable
traces are written. Nothing is stored on disk:

    xz -dc gpx-planet-2013-04-09.tar.xz | convert-2013.py | bzip2 > gpx-planet-2013-04-09.gpx.bz2
    xz -dc gpx-planet-2013-04-09.tar.xz | convert-2013.py | gpxtiler import -

The 2013 dump has no upload file name, so <name> is the name of the file
in the tar.
"""

import argparse
import sys
import tarfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

GPX_NS = "{http://www.topografix.com/GPX/1/0}"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--max-traces", type=int, default=0, help="stop after this many traces (0 = all)")
    p.add_argument("--bbox", help="only traces whose first point is in minlon,minlat,maxlon,maxlat")
    return p.parse_args()


def read_metadata(f):
    """Return {id: (description, tags)} of the identifiable traces, and the
    dump timestamp."""
    traces = {}
    stamp = None
    for event, el in ET.iterparse(f, events=("start", "end")):
        if event == "start" and el.tag == "gpxFiles":
            stamp = el.get("timestamp")
        elif event == "end" and el.tag == "gpxFile":
            if el.get("visibility") == "identifiable":
                desc = el.findtext("description") or ""
                tags = [t.text for t in el.iter("tag") if t.text]
                traces[int(el.get("id"))] = (desc, tags)
            el.clear()
    return traces, stamp


def read_points(f):
    """Return the <trkseg>s of one trace file as lists of (lat, lon, time)."""
    segs = []
    for event, el in ET.iterparse(f, events=("start", "end")):
        if event == "start" and el.tag == GPX_NS + "trkseg":
            segs.append([])
        elif event == "end" and el.tag == GPX_NS + "trkpt":
            segs[-1].append((el.get("lat"), el.get("lon"), el.findtext(GPX_NS + "time")))
            el.clear()
    return [s for s in segs if s]


def in_bbox(bbox, segs):
    if not bbox:
        return True
    lat, lon = float(segs[0][0][0]), float(segs[0][0][1])
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def write_trace(out, gpx_id, name, desc, tags, segs):
    out.write(" <trk>\n")
    out.write("  <name>%s</name>\n" % escape(name))
    out.write("  <desc>%s</desc>\n" % escape(desc))
    out.write("  <osm:id>%d</osm:id>\n" % gpx_id)
    for t in tags:
        out.write("  <osm:tag>%s</osm:tag>\n" % escape(t))
    for seg in segs:
        out.write("  <trkseg>\n")
        for lat, lon, time in seg:
            if time:
                out.write('   <trkpt lat="%s" lon="%s"><time>%s</time></trkpt>\n' % (lat, lon, time))
            else:
                out.write('   <trkpt lat="%s" lon="%s"/>\n' % (lat, lon))
        out.write("  </trkseg>\n")
    out.write(" </trk>\n")


def main():
    args = parse_args()
    bbox = [float(v) for v in args.bbox.split(",")] if args.bbox else None
    out = sys.stdout
    tar = tarfile.open(fileobj=sys.stdin.buffer, mode="r|")
    traces = None
    written = skipped = 0
    for member in tar:
        if not member.isfile():
            continue
        parts = member.name.split("/")
        if parts[-1] == "metadata.xml":
            traces, stamp = read_metadata(tar.extractfile(member))
            print("metadata: %d identifiable traces" % len(traces), file=sys.stderr)
            out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            out.write('<gpx version="1.0" creator="convert-2013.py" '
                      'xmlns="http://www.topografix.com/GPX/1/0" '
                      'xmlns:osm="https://www.openstreetmap.org/gpx/0.1">\n')
            out.write(" <author>OpenStreetMap and contributors</author>\n")
            out.write(" <url>http://opendatacommons.org/licenses/odbl/1-0/</url>\n")
            out.write(" <time>%s</time>\n" % escape(stamp))
            continue
        if traces is None:
            sys.exit("metadata.xml must come before the traces in the tar")
        if len(parts) < 5 or parts[-4] != "identifiable" or not parts[-1].endswith(".gpx"):
            continue
        gpx_id = int(parts[-1][:-4])
        if gpx_id not in traces:
            skipped += 1
            continue
        segs = read_points(tar.extractfile(member))
        if not segs or not in_bbox(bbox, segs):
            skipped += 1
            continue
        desc, tags = traces[gpx_id]
        write_trace(out, gpx_id, parts[-1], desc, tags, segs)
        written += 1
        if written % 1000 == 0:
            print("%d traces written" % written, file=sys.stderr)
        if args.max_traces and written >= args.max_traces:
            break
    out.write("</gpx>\n")
    print("done: %d traces written, %d skipped" % (written, skipped), file=sys.stderr)


if __name__ == "__main__":
    main()
