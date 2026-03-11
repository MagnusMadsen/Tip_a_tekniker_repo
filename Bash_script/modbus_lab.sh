#!/usr/bin/env bash
set -euo pipefail

# =========================
# Konfiguration
# =========================
BASE_DIR="/home/magnus/Ship_pentest/venv"

SLAVE_PY="$BASE_DIR/Slave_venv/bin/python"
MASTER_PY="$BASE_DIR/Master_venv/bin/python"
CAPTURE_PY="$BASE_DIR/Slave_venv/bin/python"

SLAVE_SCRIPT="$BASE_DIR/SLAVE_VIRKER_PEN3.py"
MASTER_SCRIPT="$BASE_DIR/MASTER_VIRKER_PEN3.py"
CAPTURE_SCRIPT="$BASE_DIR/capture_modbus_state.py"

NS_SLAVE="mb0"
NS_MASTER="mb1"

IF_SLAVE="eth0"
IF_MASTER="eth1"

BRIDGE_NAME="br0"

SLAVE_IPS=(
  "192.168.61.20/24"
  "192.168.61.22/24"
  "192.168.61.71/24"
  "192.168.61.191/24"
)

MASTER_IP="192.168.61.151/24"

MODBUS_PORT="502"

RUN_DIR="/tmp/modbus_lab"
SLAVE_PIDFILE="$RUN_DIR/slave.pid"
MASTER_PIDFILE="$RUN_DIR/master.pid"
SNIFF_MB0_PIDFILE="$RUN_DIR/sniff_mb0.pid"
SNIFF_MB1_PIDFILE="$RUN_DIR/sniff_mb1.pid"
BRIDGE_SNIFF_PIDFILE="$RUN_DIR/bridge_sniff.pid"

SLAVE_LOG="$RUN_DIR/slave.log"
MASTER_LOG="$RUN_DIR/master.log"
SNIFF_MB0_LOG="$RUN_DIR/mb0_tcpdump.log"
SNIFF_MB1_LOG="$RUN_DIR/mb1_tcpdump.log"
BRIDGE_SNIFF_LOG="$RUN_DIR/bridge_tcpdump.log"

CAPTURE_PCAP="$RUN_DIR/modbus_bridge_capture.pcap"
STATE_JSON="$RUN_DIR/state.json"

# =========================
# Hjælpefunktioner
# =========================
need_root() {
  if [ "${EUID}" -ne 0 ]; then
    echo "[FAIL] Kør scriptet med sudo"
    exit 1
  fi
}

prepare_dirs() {
  mkdir -p "$RUN_DIR"
  touch "$SLAVE_LOG" "$MASTER_LOG" "$SNIFF_MB0_LOG" "$SNIFF_MB1_LOG" "$BRIDGE_SNIFF_LOG"
}

check_files() {
  [ -x "$SLAVE_PY" ] || { echo "[FAIL] Mangler slave python: $SLAVE_PY"; exit 1; }
  [ -x "$MASTER_PY" ] || { echo "[FAIL] Mangler master python: $MASTER_PY"; exit 1; }
  [ -x "$CAPTURE_PY" ] || { echo "[FAIL] Mangler capture python: $CAPTURE_PY"; exit 1; }

  [ -f "$SLAVE_SCRIPT" ] || { echo "[FAIL] Mangler slave script: $SLAVE_SCRIPT"; exit 1; }
  [ -f "$MASTER_SCRIPT" ] || { echo "[FAIL] Mangler master script: $MASTER_SCRIPT"; exit 1; }
  [ -f "$CAPTURE_SCRIPT" ] || { echo "[FAIL] Mangler capture script: $CAPTURE_SCRIPT"; exit 1; }
}

wait_for_root_ifaces() {
  echo "[INFO] Venter på at $IF_SLAVE og $IF_MASTER findes i root namespace"
  for _ in $(seq 1 30); do
    if ip link show "$IF_SLAVE" >/dev/null 2>&1 && ip link show "$IF_MASTER" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
  done

  echo "[FAIL] Interfaces kom ikke tilbage i root namespace"
  ip -br link || true
  return 1
}

# =========================
# Cleanup
# =========================
cleanup_standard() {
  echo "[INFO] Standard cleanup starter"
  echo "[INFO] Overblik før cleanup"
  ip -br link || true
  ip netns list || true

  pkill -f "$SLAVE_SCRIPT" 2>/dev/null || true
  pkill -f "$MASTER_SCRIPT" 2>/dev/null || true
  pkill -f "$CAPTURE_SCRIPT" 2>/dev/null || true

  pkill -f "tcpdump -l -nn -i $IF_SLAVE" 2>/dev/null || true
  pkill -f "tcpdump -l -nn -i $IF_MASTER" 2>/dev/null || true
  pkill -f "tcpdump -l -nn -i $BRIDGE_NAME" 2>/dev/null || true
  pkill -f "tcpdump -nn -i $IF_SLAVE" 2>/dev/null || true
  pkill -f "tcpdump -nn -i $IF_MASTER" 2>/dev/null || true
  pkill -f "tcpdump -nn -i $BRIDGE_NAME" 2>/dev/null || true

  ip -all netns delete 2>/dev/null || true
  wait_for_root_ifaces || true

  ip link set "$IF_SLAVE" nomaster 2>/dev/null || true
  ip link set "$IF_MASTER" nomaster 2>/dev/null || true
  ip link set "$BRIDGE_NAME" down 2>/dev/null || true
  ip link delete "$BRIDGE_NAME" type bridge 2>/dev/null || true

  for dev in "$IF_SLAVE" "$IF_MASTER"; do
    if ip link show "$dev" >/dev/null 2>&1; then
      ip link set "$dev" down 2>/dev/null || true
      ip addr flush dev "$dev" 2>/dev/null || true
      ip route flush dev "$dev" 2>/dev/null || true
      ip neigh flush dev "$dev" 2>/dev/null || true
      ip link set "$dev" up 2>/dev/null || true
    fi
  done

  for i in $(ip -o link show | awk -F': ' '{print $2}' | sed 's/@.*//' | grep -E '^(br|veth|dummy)' || true); do
    [ "$i" = "$IF_SLAVE" ] && continue
    [ "$i" = "$IF_MASTER" ] && continue
    ip link set "$i" down 2>/dev/null || true
    ip link delete "$i" 2>/dev/null || true
  done

  sysctl -w net.ipv4.ip_forward=0 >/dev/null 2>&1 || true
  echo "[INFO] Standard cleanup færdig"
}

cleanup_brutal() {
  echo "[WARN] Brutal cleanup starter"
  cleanup_standard
  echo "[WARN] Flusher nftables/iptables"
  nft flush ruleset 2>/dev/null || true
  iptables -F 2>/dev/null || true
  iptables -t nat -F 2>/dev/null || true
  iptables -t mangle -F 2>/dev/null || true
  iptables -X 2>/dev/null || true
  echo "[WARN] Brutal cleanup færdig"
}

# =========================
# Bridge mode
# =========================
restore_bridge() {
  echo "[INFO] Lægger $IF_SLAVE og $IF_MASTER tilbage på bridge $BRIDGE_NAME"

  ip -all netns delete 2>/dev/null || true
  wait_for_root_ifaces

  ip link set "$IF_SLAVE" nomaster 2>/dev/null || true
  ip link set "$IF_MASTER" nomaster 2>/dev/null || true

  ip link set "$BRIDGE_NAME" down 2>/dev/null || true
  ip link delete "$BRIDGE_NAME" type bridge 2>/dev/null || true

  ip addr flush dev "$IF_SLAVE" 2>/dev/null || true
  ip addr flush dev "$IF_MASTER" 2>/dev/null || true

  ip link add name "$BRIDGE_NAME" type bridge
  ip link set "$BRIDGE_NAME" up

  ip link set "$IF_SLAVE" up
  ip link set "$IF_MASTER" up

  ip link set "$IF_SLAVE" master "$BRIDGE_NAME"
  ip link set "$IF_MASTER" master "$BRIDGE_NAME"

  echo "[OK] Bridge $BRIDGE_NAME oprettet"
  bridge link 2>/dev/null || true
  ip -br link show dev "$BRIDGE_NAME" || true
  ip -br link show dev "$IF_SLAVE" || true
  ip -br link show dev "$IF_MASTER" || true
}

start_bridge_capture() {
  echo "[INFO] Starter bridge capture på $BRIDGE_NAME"
  : >"$BRIDGE_SNIFF_LOG"
  rm -f "$CAPTURE_PCAP"

  nohup tcpdump -i "$BRIDGE_NAME" -nn -s 0 -w "$CAPTURE_PCAP" "tcp port $MODBUS_PORT" >"$BRIDGE_SNIFF_LOG" 2>&1 &
  echo $! > "$BRIDGE_SNIFF_PIDFILE"
  sleep 1
  echo "[OK] Bridge capture startet"
  echo "[INFO] pcap: $CAPTURE_PCAP"
}

stop_bridge_capture() {
  if [ -f "$BRIDGE_SNIFF_PIDFILE" ]; then
    kill "$(cat "$BRIDGE_SNIFF_PIDFILE")" 2>/dev/null || true
    rm -f "$BRIDGE_SNIFF_PIDFILE"
    echo "[INFO] Bridge capture stoppet"
  fi

  pkill -f "tcpdump -i $BRIDGE_NAME" 2>/dev/null || true
  pkill -f "tcpdump -nn -s 0 -w $CAPTURE_PCAP" 2>/dev/null || true
}

parse_bridge_capture() {
  if [ ! -f "$CAPTURE_PCAP" ]; then
    echo "[FAIL] Ingen pcap fundet: $CAPTURE_PCAP"
    return 1
  fi

  echo "[INFO] Parser pcap til state.json"
  "$CAPTURE_PY" "$CAPTURE_SCRIPT" \
    --pcap "$CAPTURE_PCAP" \
    --out "$STATE_JSON" \
    --targets 192.168.61.20,192.168.61.22,192.168.61.71,192.168.61.191 \
    --pretty

  echo "[OK] State skrevet til $STATE_JSON"
}

bridge_mode() {
  need_root
  prepare_dirs
  check_files
  cleanup_standard
  restore_bridge
  echo "[OK] Bridge mode aktiv"
  echo "[INFO] Brug '$0 capture-start' for at begynde at lære trafik"
}

# =========================
# mb0 slave mode
# =========================
create_slave_namespace() {
  echo "[INFO] Opretter namespace $NS_SLAVE"
  ip netns add "$NS_SLAVE"
}

move_slave_interface() {
  echo "[INFO] Flytter $IF_SLAVE til $NS_SLAVE"
  ip link set "$IF_SLAVE" netns "$NS_SLAVE"
}

setup_slave_net() {
  echo "[INFO] Sætter slave-net op i $NS_SLAVE"
  ip netns exec "$NS_SLAVE" ip link set lo up
  ip netns exec "$NS_SLAVE" ip link set "$IF_SLAVE" up
  ip netns exec "$NS_SLAVE" ip addr flush dev "$IF_SLAVE"

  for ipaddr in "${SLAVE_IPS[@]}"; do
    ip netns exec "$NS_SLAVE" ip addr add "$ipaddr" dev "$IF_SLAVE"
  done
}

start_slave() {
  echo "[INFO] Starter slave i $NS_SLAVE"
  : >"$SLAVE_LOG"

  ip netns exec "$NS_SLAVE" env MODBUS_STATE_JSON="$STATE_JSON" nohup "$SLAVE_PY" "$SLAVE_SCRIPT" >"$SLAVE_LOG" 2>&1 &
  echo $! > "$SLAVE_PIDFILE"
  sleep 1
  echo "[OK] Slave startet. Log: $SLAVE_LOG"

  if [ ! -f "$STATE_JSON" ]; then
    echo "[WARN] $STATE_JSON findes ikke endnu"
    echo "[WARN] Slaven starter, men uden lært state"
  fi
}

start_mb0_sniffer() {
  echo "[INFO] Starter tcpdump i $NS_SLAVE"
  : >"$SNIFF_MB0_LOG"
  ip netns exec "$NS_SLAVE" nohup tcpdump -l -nn -i "$IF_SLAVE" "tcp port $MODBUS_PORT" >"$SNIFF_MB0_LOG" 2>&1 &
  echo $! > "$SNIFF_MB0_PIDFILE"
  sleep 1
  echo "[OK] Tcpdump mb0 startet"
}

# =========================
# mb1 master mode
# =========================
create_master_namespace() {
  echo "[INFO] Opretter namespace $NS_MASTER"
  ip netns add "$NS_MASTER"
}

move_master_interface() {
  echo "[INFO] Flytter $IF_MASTER til $NS_MASTER"
  ip link set "$IF_MASTER" netns "$NS_MASTER"
}

setup_master_net() {
  echo "[INFO] Sætter master-net op i $NS_MASTER"
  ip netns exec "$NS_MASTER" ip link set lo up
  ip netns exec "$NS_MASTER" ip link set "$IF_MASTER" up
  ip netns exec "$NS_MASTER" ip addr flush dev "$IF_MASTER"
  ip netns exec "$NS_MASTER" ip addr add "$MASTER_IP" dev "$IF_MASTER"
}

start_master() {
  echo "[INFO] Starter master i $NS_MASTER"
  : >"$MASTER_LOG"
  ip netns exec "$NS_MASTER" nohup "$MASTER_PY" "$MASTER_SCRIPT" >"$MASTER_LOG" 2>&1 &
  echo $! > "$MASTER_PIDFILE"
  sleep 1
  echo "[OK] Master startet. Log: $MASTER_LOG"
}

start_mb1_sniffer() {
  echo "[INFO] Starter tcpdump i $NS_MASTER"
  : >"$SNIFF_MB1_LOG"
  ip netns exec "$NS_MASTER" nohup tcpdump -l -nn -i "$IF_MASTER" "tcp port $MODBUS_PORT" >"$SNIFF_MB1_LOG" 2>&1 &
  echo $! > "$SNIFF_MB1_PIDFILE"
  sleep 1
  echo "[OK] Tcpdump mb1 startet"
}

# =========================
# Processer / stop
# =========================
stop_slave() {
  if [ -f "$SLAVE_PIDFILE" ]; then
    kill "$(cat "$SLAVE_PIDFILE")" 2>/dev/null || true
    rm -f "$SLAVE_PIDFILE"
    echo "[INFO] Slave stoppet via pidfile"
  fi
  pkill -f "$SLAVE_SCRIPT" 2>/dev/null || true
}

stop_master() {
  if [ -f "$MASTER_PIDFILE" ]; then
    kill "$(cat "$MASTER_PIDFILE")" 2>/dev/null || true
    rm -f "$MASTER_PIDFILE"
    echo "[INFO] Master stoppet via pidfile"
  fi
  pkill -f "$MASTER_SCRIPT" 2>/dev/null || true
}

stop_sniffers() {
  if [ -f "$SNIFF_MB0_PIDFILE" ]; then
    kill "$(cat "$SNIFF_MB0_PIDFILE")" 2>/dev/null || true
    rm -f "$SNIFF_MB0_PIDFILE"
    echo "[INFO] Tcpdump mb0 stoppet"
  fi

  if [ -f "$SNIFF_MB1_PIDFILE" ]; then
    kill "$(cat "$SNIFF_MB1_PIDFILE")" 2>/dev/null || true
    rm -f "$SNIFF_MB1_PIDFILE"
    echo "[INFO] Tcpdump mb1 stoppet"
  fi

  pkill -f "tcpdump -l -nn -i $IF_SLAVE" 2>/dev/null || true
  pkill -f "tcpdump -l -nn -i $IF_MASTER" 2>/dev/null || true
  pkill -f "tcpdump -nn -i $IF_SLAVE" 2>/dev/null || true
  pkill -f "tcpdump -nn -i $IF_MASTER" 2>/dev/null || true
}

destroy_namespaces() {
  ip -all netns delete 2>/dev/null || true
  echo "[OK] Alle namespaces fjernet"
}

stop_all() {
  need_root
  stop_bridge_capture
  stop_sniffers
  stop_slave
  stop_master
  destroy_namespaces
  restore_bridge
  echo "[OK] Alt stoppet, namespaces fjernet, bridge genskabt"
}

# =========================
# Visning / debug
# =========================
logs() {
  echo "=== slave log ==="
  tail -n 50 "$SLAVE_LOG" 2>/dev/null || true
  echo
  echo "=== master log ==="
  tail -n 50 "$MASTER_LOG" 2>/dev/null || true
  echo
  echo "=== bridge tcpdump log ==="
  tail -n 30 "$BRIDGE_SNIFF_LOG" 2>/dev/null || true
  echo
  echo "=== mb0 tcpdump ==="
  tail -n 30 "$SNIFF_MB0_LOG" 2>/dev/null || true
  echo
  echo "=== mb1 tcpdump ==="
  tail -n 30 "$SNIFF_MB1_LOG" 2>/dev/null || true
}

follow_logs() {
  echo "[INFO] Følger logs live. Ctrl+C for at stoppe."
  tail -f "$SLAVE_LOG" "$MASTER_LOG" "$BRIDGE_SNIFF_LOG" "$SNIFF_MB0_LOG" "$SNIFF_MB1_LOG"
}

status() {
  echo "=== Processer ==="
  [ -f "$SLAVE_PIDFILE" ] && echo "slave pid: $(cat "$SLAVE_PIDFILE")" || echo "slave: ingen pidfile"
  [ -f "$MASTER_PIDFILE" ] && echo "master pid: $(cat "$MASTER_PIDFILE")" || echo "master: ingen pidfile"
  [ -f "$BRIDGE_SNIFF_PIDFILE" ] && echo "bridge capture pid: $(cat "$BRIDGE_SNIFF_PIDFILE")" || echo "bridge capture: ingen pidfile"
  [ -f "$SNIFF_MB0_PIDFILE" ] && echo "tcpdump mb0 pid: $(cat "$SNIFF_MB0_PIDFILE")" || echo "tcpdump mb0: ingen pidfile"
  [ -f "$SNIFF_MB1_PIDFILE" ] && echo "tcpdump mb1 pid: $(cat "$SNIFF_MB1_PIDFILE")" || echo "tcpdump mb1: ingen pidfile"
  echo

  echo "=== namespaces ==="
  ip netns list || true
  echo

  echo "=== links ==="
  ip -br link || true
  echo

  echo "=== addrs ==="
  ip -br addr || true
  echo

  echo "=== bridge ==="
  bridge link 2>/dev/null || true
  echo

  if ip netns list | grep -q "^$NS_SLAVE"; then
    echo "=== $NS_SLAVE ==="
    ip netns exec "$NS_SLAVE" ip -br addr || true
    ip netns exec "$NS_SLAVE" ip route || true
    echo
  fi

  if ip netns list | grep -q "^$NS_MASTER"; then
    echo "=== $NS_MASTER ==="
    ip netns exec "$NS_MASTER" ip -br addr || true
    ip netns exec "$NS_MASTER" ip route || true
    echo
  fi

  [ -f "$CAPTURE_PCAP" ] && echo "pcap: $CAPTURE_PCAP"
  [ -f "$STATE_JSON" ] && echo "state: $STATE_JSON"
}

# =========================
# Hovedflow
# =========================
start_all() {
  need_root
  prepare_dirs
  check_files

  if [ ! -f "$STATE_JSON" ]; then
    echo "[WARN] $STATE_JSON findes ikke endnu"
    echo "[WARN] Kør bridge -> capture-start -> capture-stop -> capture-parse først"
  fi

  cleanup_standard

  # mb0
  create_slave_namespace
  move_slave_interface
  setup_slave_net
  start_slave
  start_mb0_sniffer

  # mb1
  create_master_namespace
  move_master_interface
  setup_master_net
  start_master
  start_mb1_sniffer

  echo "[OK] Startede både mb0 og mb1"
}

# =========================
# CLI
# =========================
case "${1:-}" in
  bridge)
    bridge_mode
    ;;
  capture-start)
    need_root
    start_bridge_capture
    ;;
  capture-stop)
    need_root
    stop_bridge_capture
    ;;
  capture-parse)
    need_root
    parse_bridge_capture
    ;;
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  nuke)
    need_root
    stop_bridge_capture
    stop_sniffers
    stop_slave
    stop_master
    cleanup_brutal
    restore_bridge
    echo "[OK] Hard reset færdig, bridge genskabt"
    ;;
  status)
    need_root
    status
    ;;
  logs)
    need_root
    logs
    ;;
  follow)
    need_root
    follow_logs
    ;;
  *)
    echo "Brug: sudo $0 {bridge|capture-start|capture-stop|capture-parse|start|stop|nuke|status|logs|follow}"
    exit 1
    ;;
esac