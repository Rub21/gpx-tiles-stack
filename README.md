# gpx-tiles-stack

Runs the GPS traces tiles on one server with Docker Compose:

- PostGIS
- [gpxtiler](https://github.com/Rub21/gpxtiler): import, updates (RSS and id list), PNG tiles and the low zoom render
- [Tilekiln](https://github.com/pnorman/tilekiln) with the config of [gpx-vector-tiles](https://github.com/Rub21/gpx-vector-tiles): vector tiles
- a viewer for both

Start the services one by one, in this order. `up -d` starts a service that keeps running. `run` starts a job that runs once: add `-d --name` for long jobs, so they keep running when you close the terminal (`docker logs -f <name>` to follow them).

### 1. Code and settings

```sh
git clone https://github.com/Rub21/gpx-tiles-stack
cd gpx-tiles-stack
git clone https://github.com/Rub21/gpxtiler
git clone https://github.com/Rub21/gpx-vector-tiles
cp .env.example .env            # set the password and the URLs
docker compose build
```

### 2. Database and import

```sh
# once: make the GPX dump from the 2013 planet dump (hours)
docker compose run -d --name convert convert-2013

# PostGIS. The first start of a new volume restarts once: wait about 10 seconds
docker compose up -d db

# load the dump (about 25 minutes for the 2013 dump)
docker compose run -d --name import import
docker logs -f import
docker rm import 
```

### 3. PNG tiles

```sh
# serve: PNG tiles on /lines/{z}/{x}/{y}.png, drawn on the first request
# and kept on disk up to GPXTILER_CACHE_ZOOM (14)
docker compose up -d serve

# once: draw the PNG tiles of GPXTILER_PRERENDER_ZOOMS (0-9) in advance (about 50 minutes)
docker compose run -d render-all

# Every GPXTILER_RENDER_EXPIRED_EVERY seconds (300 = 5 min), read the expire
# files that update-rss writes when traces are added or deleted. Each line is
# a tile (zoom/x/y):
#   9/259/176     zoom 6-9 (GPXTILER_EXPIRED_ZOOMS): draw it again and save it
#   12/2074/1409  zoom 10-14: delete it from disk, serve draws it on the next request
#   3/4/2         zoom 0-5: nothing, render-daily draws them
docker compose up -d render-expired

# Every GPXTILER_RENDER_DAILY_EVERY seconds (86400 = 1 day), draw all the
# tiles of GPXTILER_DAILY_ZOOMS (0-5) again
docker compose up -d render-daily
```

### 4. Updates

```sh
# Every GPXTILER_RSS_EVERY seconds (300 = 5 min), load the new traces from the
# RSS feed of the website and write the expire files for the PNG and vector tiles
docker compose up -d update-rss

# optional: every day, sync with the list of identifiable trace ids (set GPXTILER_IDS)
docker compose up -d update-ids
```

### 5. Vector tiles (Tilekiln)

```sh
# once: create the tile storage in the database (schema tilekiln)
docker compose run --rm tilekiln-init

# tilekiln: vector tiles on /gps/{z}/{x}/{y}.mvt, drawn on the first request and kept in the database
docker compose up -d tilekiln

# optional, once: draw the vector tiles of zoom 0-9 in advance (hours)
docker compose run -d tilekiln-zooms

# like render-expired and render-daily, for the vector tiles
docker compose up -d tilekiln-expired
docker compose up -d tilekiln-daily
```

### 6. Viewer and HTTPS

```sh
# viewer: a map to look at the PNG and vector tiles
docker compose up -d viewer

# Traefik: HTTPS on GPX_TILES_HOST, with a Let's Encrypt certificate (ACME_EMAIL)
docker compose up -d traefik
```

### Check

```sh
docker ps                                                      # all the services "Up"
docker exec gpx-tiles-db-1 psql -U gpxtiler -c "SELECT count(*), max(gpx_id) FROM traces"
docker logs -f gpx-tiles-update-rss-1                          # new traces from the RSS
```

All the services at once, instead of steps 3 to 6: `docker compose --profile web up -d`.

The PNG tiles and the vector tiles follow the same plan, like ops does on vector.openstreetmap.org: the low zooms are drawn in advance (`render-all`, `tilekiln-zooms`), the other zooms on the first request and kept (on disk for PNG, in the database for Tilekiln), the expire files written by import and update are applied every few minutes (`render-expired`, `tilekiln-expired`) and the lowest zooms are drawn again once a day (`render-daily`, `tilekiln-daily`).

| URL | What |
|---|---|
| `http://localhost:8090/` | viewer, PNG or vector |
| `http://localhost:8080/lines/{z}/{x}/{y}.png` | PNG tiles |
| `http://localhost:8081/gps/tilejson.json` | vector tiles |

With a domain pointing to the server, Traefik serves everything on it with HTTPS: the viewer on `/`, the PNG tiles on `/lines/`, the vector tiles on `/gps/` (compressed). Set `GPX_TILES_HOST`, `GPX_TILES_URL` and `ACME_EMAIL` in `.env` and run `docker compose --profile web up -d`.

Data (database, tiles, expire files) stays in `./data` and the `db-data` volume. To update the code: `git pull` in `gpxtiler` or `gpx-vector-tiles`, then `docker compose up -d --build`. Name the services when a long job (`import`, `render-all`, `tilekiln-zooms`) is running, for example `docker compose up -d --build serve tilekiln`: without names, `db` is recreated too and the job loses its connection.

`GPXTILER_SRC` and `GPX_VECTOR_TILES_SRC` in `.env` can point to any checkout, for development.

## The 2013 dump

The last public GPX dump (https://planet.openstreetmap.org/gps/, 2013) is a tar with one file per trace. `tools/convert-2013.py` turns it into the planet-dump-ng format that gpxtiler reads, identifiable traces only. The `convert-2013` service downloads, unpacks and converts it in one stream (hours, nothing else is stored) and writes `data/gpx-planet-2013.gpx.bz2`:

```
docker compose run --rm convert-2013
```

Then run the import: `GPXTILER_DUMP` points to that file by default.
