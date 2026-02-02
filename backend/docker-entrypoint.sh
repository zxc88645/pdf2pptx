#!/bin/sh
# Run as root: ensure /data is writable by app (1000:1000), then exec as app
if [ -d /data ]; then
  chown -R 1000:1000 /data 2>/dev/null || true
fi
exec gosu app "$@"
