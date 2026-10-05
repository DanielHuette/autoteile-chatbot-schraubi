#!/bin/bash
# Startet den Testserver abgekoppelt von der aufrufenden Shell.
# Beendet wird ueber eine PID-Datei, nicht ueber Mustersuche in
# Prozesslisten - sonst trifft das Muster die eigene Shell.
cd /home/claude/teilethuns
PIDFILE=logs/server.pid
# setsid legt eine eigene Prozessgruppe an; beendet wird die ganze
# Gruppe, sonst ueberlebt uvicorn als Kindprozess und haelt den Port.
if [ -f "$PIDFILE" ]; then kill -TERM -- "-$(cat $PIDFILE)" 2>/dev/null; sleep 2; fi
fuser -k 8099/tcp 2>/dev/null; sleep 1
mkdir -p logs
APPLY_SCHEMA=0 setsid nohup python3 scripts/mitenv.py .env.test \
  python3 -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8099 \
  > logs/server.log 2>&1 < /dev/null &
echo $! > "$PIDFILE"
disown
for i in $(seq 1 45); do
  sleep 1
  if curl -sf http://127.0.0.1:8099/api/health -m 2 >/dev/null 2>&1; then echo "bereit nach ${i}s"; exit 0; fi
done
echo "START FEHLGESCHLAGEN"; tail -20 logs/server.log; exit 1
