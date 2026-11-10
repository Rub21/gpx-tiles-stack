# gpx-tiles-stack

Runs the GPS traces tiles on one server with Docker Compose:

- PostGIS
- [gpxtiler](https://github.com/Rub21/gpxtiler): import, updates (RSS and id list), PNG tiles and the low zoom render
- [Tilekiln](https://github.com/pnorman/tilekiln) with the config of [gpx-vector-tiles](https://github.com/Rub21/gpx-vector-tiles): vector tiles
- a viewer for both

```
git clone https://github.com/Rub21/gpx-tiles-stack
cd gpx-tiles-stack
git clone https://github.com/Rub21/gpxtiler
git clone https://github.com/Rub21/gpx-vector-tiles
cp .env.example .env            # set the password and the URLs

docker compose run --rm convert-2013   # once: make the GPX dump from the 2013 planet dump (hours)
docker compose up -d db
docker compose run --rm import         # once: load the dump
docker compose run --rm render-all     # once: low zoom PNG tiles
docker compose up -d                   # serve, tilekiln, viewer, updates, render
docker compose --profile ids up -d     # also update-ids, when the id list exists
```

| URL | What |
|---|---|
| `http://localhost:8090/` | viewer, PNG or vector |
| `http://localhost:8080/lines/{z}/{x}/{y}.png` | PNG tiles |
| `http://localhost:8081/gps/tilejson.json` | vector tiles |

Data (database, tiles, expire files) stays in `./data` and the `db-data` volume. To update the code: `git pull` in `gpxtiler` or `gpx-vector-tiles`, then `docker compose up -d --build`.

`GPXTILER_SRC` and `GPX_VECTOR_TILES_SRC` in `.env` can point to any checkout, for development.

## The 2013 dump

The last public GPX dump (https://planet.openstreetmap.org/gps/, 2013) is a tar with one file per trace. `tools/convert-2013.py` turns it into the planet-dump-ng format that gpxtiler reads, identifiable traces only. The `convert-2013` service downloads, unpacks and converts it in one stream (hours, nothing else is stored) and writes `data/gpx-planet-2013.gpx.bz2`:

```
docker compose run --rm convert-2013
```

Then run the import: `GPXTILER_DUMP` points to that file by default.
