#!/usr/bin/env bash
set -euo pipefail

# =========================
# Konfiguration
# =========================
BASE_DIR="/home/magnus/Ship_pentest/venv"

SLAVE_PY="$BASE_DIR/Slave_venv/bin/python"
MASTER_PY="$BASE_DIR/Master_venv/bin/python"

SLAVE_SCRIPT="$BASE_DIR/SLAVE_VIRKER_PEN3.py"
MASTER_SCRIPT="$BASE_DIR/MASTER_VIRKER_PEN3.py"

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

SLAVE_LOG="$RUN_DIR/slave.log"
MASTER_LOG="$RUN_DIR/master.log"
SNIFF_MB0_LOG="$RUN_DIR/mb0_tcpdump.log"
SNIFF_MB1_LOG="$RUN_DIR/mb1_tcpdump.log"

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
  touch "$SLAVE_LOG" "$MASTER_LOG" "$SNIFF_MB0_LOG" "$SNIFF_MB1_LOG"
}

check_files() {
  [ -x "$SLAVE_PY" ] || { echo "[FAIL] Mangler slave python: $SLAVE_PY"; exit 1; }
  [ -x "$MASTER_PY" ] || { echo "[FAIL] Mangler master python: $MASTER_PY"; exit 1; }
  [ -f "$SLAVE_SCRIPT" ] || { echo "[FAIL] Mangler slave script: $SLAVE_SCRIPT"; exit 1; }
  [ -f "$MASTER_SCRIPT" ] || { echo "[FAIL] Mangler master script: $MASTER_SCRIPT"; exit 1; }
}

# =========================
# Cleanup
# =========================
cleanup_standard() {
  echo "[INFO] Standard cleanup starter"
  echo "[INFO] Overblik før cleanup"
  ip -br link || true
  ip netns list || true

  # Stop evt. kendte gamle processer, også hvis PID-filer mangler
  pkill -f "$SLAVE_SCRIPT" 2>/dev/null || true
  pkill -f "$MASTER_SCRIPT" 2>/dev/null || true
  pkill -f "tcpdump -l -nn -i $IF_SLAVE" 2>/dev/null || true
  pkill -f "tcpdump -l -nn -i $IF_MASTER" 2>/dev/null || true
  pkill -f "tcpdump -nn -i $IF_SLAVE" 2>/dev/null || true
  pkill -f "tcpdump -nn -i $IF_MASTER" 2>/dev/null || true

  # Slet namespaces først, så fysiske interfaces kommer tilbage
  ip -all netns delete 2>/dev/null || true

  # Fjern bridge hvis den findes
  ip link set "$IF_SLAVE" nomaster 2>/dev/null || true
  ip link set "$IF_MASTER" nomaster 2>/dev/null || true
  ip link set "$BRIDGE_NAME" down 2>/dev/null || true
  ip link delete "$BRIDGE_NAME" type bridge 2>/dev/null || true

  # Reset eth0/eth1
  for dev in "$IF_SLAVE" "$IF_MASTER"; do
    ip link set "$dev" down 2>/dev/null || true
    ip addr flush dev "$dev" 2>/dev/null || true
    ip route flush dev "$dev" 2>/dev/null || true
    ip neigh flush dev "$dev" 2>/dev/null || true
    ip link set "$dev" up 2>/dev/null || true
  done

  # Slet lab-artefakter
  for i in $(ip -o link show | awk -F': ' '{print $2}' | sed 's/@.*//' | grep -E '^(br|veth|dummy)'); do
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
# Bridge restore
# =========================
restore_bridge() {
  echo "[INFO] Lægger $IF_SLAVE og $IF_MASTER tilbage på bridge $BRIDGE_NAME"

  ip -all netns delete 2>/dev/null || true

  echo "[INFO] Venter på at interfaces vender tilbage til root namespace"
  for _ in $(seq 1 20); do
    if ip link show "$IF_SLAVE" >/dev/null 2>&1 && ip link show "$IF_MASTER" >/dev/null 2>&1; then
      break
    fi
    sleep 0.2
  done

  if ! ip link show "$IF_SLAVE" >/dev/null 2>&1; then
    echo "[FAIL] Interface $IF_SLAVE findes ikke i root namespace"
    ip -br link || true
    return 1
  fi

  if ! ip link show "$IF_MASTER" >/dev/null 2>&1; then
    echo "[FAIL] Interface $IF_MASTER findes ikke i root namespace"
    ip -br link || true
    return 1
  fi

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

# =========================
# Namespace / net setup
# =========================
create_namespaces() {
  echo "[INFO] Opretter namespaces"
  ip netns add "$NS_SLAVE"
  ip netns add "$NS_MASTER"
}

move_interfaces() {
  echo "[INFO] Flytter interfaces til namespaces"
  ip link set "$IF_SLAVE" netns "$NS_SLAVE"
  ip link set "$IF_MASTER" netns "$NS_MASTER"
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

setup_master_net() {
  echo "[INFO] Sætter master-net op i $NS_MASTER"
  ip netns exec "$NS_MASTER" ip link set lo up
  ip netns exec "$NS_MASTER" ip link set "$IF_MASTER" up
  ip netns exec "$NS_MASTER" ip addr flush dev "$IF_MASTER"
  ip netns exec "$NS_MASTER" ip addr add "$MASTER_IP" dev "$IF_MASTER"
}

show_status() {
  echo
  echo "=== Host ==="
  ip -br addr || true
  ip route || true
  echo

  echo "=== Namespaces ==="
  ip netns list || true
  echo

  echo "=== $NS_SLAVE ==="
  ip netns exec "$NS_SLAVE" ip -br addr || true
  ip netns exec "$NS_SLAVE" ip route || true
  echo

  echo "=== $NS_MASTER ==="
  ip netns exec "$NS_MASTER" ip -br addr || true
  ip netns exec "$NS_MASTER" ip route || true
  echo
}

# =========================
# Processer
# =========================
start_slave() {
  echo "[INFO] Starter slave i $NS_SLAVE"
  : >"$SLAVE_LOG"
  ip netns exec "$NS_SLAVE" nohup "$SLAVE_PY" "$SLAVE_SCRIPT" >"$SLAVE_LOG" 2>&1 &
  echo $! > "$SLAVE_PIDFILE"
  sleep 1
  echo "[OK] Slave startet. Log: $SLAVE_LOG"
}

start_master() {
  echo "[INFO] Starter master i $NS_MASTER"
  : >"$MASTER_LOG"
  ip netns exec "$NS_MASTER" nohup "$MASTER_PY" "$MASTER_SCRIPT" >"$MASTER_LOG" 2>&1 &
  echo $! > "$MASTER_PIDFILE"
  sleep 1
  echo "[OK] Master startet. Log: $MASTER_LOG"
}

start_sniffers() {
  echo "[INFO] Starter tcpdump i $NS_SLAVE og $NS_MASTER"

  : >"$SNIFF_MB0_LOG"
  : >"$SNIFF_MB1_LOG"

  ip netns exec "$NS_SLAVE" nohup tcpdump -l -nn -i "$IF_SLAVE" "tcp port $MODBUS_PORT" >"$SNIFF_MB0_LOG" 2>&1 &
  echo $! > "$SNIFF_MB0_PIDFILE"

  ip netns exec "$NS_MASTER" nohup tcpdump -l -nn -i "$IF_MASTER" "tcp port $MODBUS_PORT" >"$SNIFF_MB1_LOG" 2>&1 &
  echo $! > "$SNIFF_MB1_PIDFILE"

  sleep 1
  echo "[OK] Tcpdump startet"
}

stop_processes() {
  # PID-filer først
  if [ -f "$SLAVE_PIDFILE" ]; then
    kill "$(cat "$SLAVE_PIDFILE")" 2>/dev/null || true
    rm -f "$SLAVE_PIDFILE"
    echo "[INFO] Slave stoppet via pidfile"
  fi

  if [ -f "$MASTER_PIDFILE" ]; then
    kill "$(cat "$MASTER_PIDFILE")" 2>/dev/null || true
    rm -f "$MASTER_PIDFILE"
    echo "[INFO] Master stoppet via pidfile"
  fi

  # Fallback: dræb kendte scriptnavne
  pkill -f "$SLAVE_SCRIPT" 2>/dev/null || true
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

destroy_all() {
  stop_sniffers
  stop_processes
  destroy_namespaces
  restore_bridge
}

logs() {
  echo "=== slave log ==="
  tail -n 50 "$SLAVE_LOG" 2>/dev/null || true
  echo
  echo "=== master log ==="
  tail -n 50 "$MASTER_LOG" 2>/dev/null || true
  echo
  echo "=== mb0 tcpdump ==="
  tail -n 30 "$SNIFF_MB0_LOG" 2>/dev/null || true
  echo
  echo "=== mb1 tcpdump ==="
  tail -n 30 "$SNIFF_MB1_LOG" 2>/dev/null || true
}

follow_logs() {
  echo "[INFO] Følger slave/master logs live. Ctrl+C for at stoppe."
  tail -f "$SLAVE_LOG" "$MASTER_LOG"
}

show_packets() {
  echo "[INFO] Følger tcpdump live for mb0 og mb1. Ctrl+C for at stoppe."
  tail -f "$SNIFF_MB0_LOG" "$SNIFF_MB1_LOG"
}

status() {
  echo "=== Processer ==="
  [ -f "$SLAVE_PIDFILE" ] && echo "slave pid: $(cat "$SLAVE_PIDFILE")" || echo "slave: ingen pidfile"
  [ -f "$MASTER_PIDFILE" ] && echo "master pid: $(cat "$MASTER_PIDFILE")" || echo "master: ingen pidfile"
  [ -f "$SNIFF_MB0_PIDFILE" ] && echo "tcpdump mb0 pid: $(cat "$SNIFF_MB0_PIDFILE")" || echo "tcpdump mb0: ingen pidfile"
  [ -f "$SNIFF_MB1_PIDFILE" ] && echo "tcpdump mb1 pid: $(cat "$SNIFF_MB1_PIDFILE")" || echo "tcpdump mb1: ingen pidfile"
  echo
  ip netns list || true
  echo
  ip -br link || true
  ip -br addr || true
  bridge link 2>/dev/null || true
}

# =========================
# Hovedflow
# =========================
start_all() {
  need_root
  prepare_dirs
  check_files
  cleanup_standard
  create_namespaces
  move_interfaces
  setup_slave_net
  setup_master_net
  show_status
  start_slave
  start_master
  start_sniffers
  echo "[OK] Hele labben er oppe"
}

restart_all() {
  need_root
  stop_sniffers
  stop_processes
  cleanup_standard
  create_namespaces
  move_interfaces
  setup_slave_net
  setup_master_net
  show_status
  start_slave
  start_master
  start_sniffers
  echo "[OK] Hele labben er genstartet"
}

stop_all() {
  need_root
  stop_sniffers
  stop_processes

  pkill -f "$SLAVE_SCRIPT" 2>/dev/null || true
  pkill -f "$MASTER_SCRIPT" 2>/dev/null || true
  pkill -f tcpdump 2>/dev/null || true

  destroy_namespaces
  restore_bridge
  echo "[OK] Alt stoppet, namespaces fjernet, bridge genskabt"
}

nuke_all() {
  need_root
  stop_sniffers
  stop_processes
  cleanup_brutal
  restore_bridge
  echo "[OK] Hard reset færdig, bridge genskabt"
}

# =========================
# CLI
# =========================
case "${1:-}" in
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    restart_all
    ;;
  destroy)
    stop_all
    ;;
  nuke)
    nuke_all
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
  pcap)
    need_root
    show_packets
    ;;
  *)
    echo "Brug: sudo $0 {start|stop|restart|destroy|nuke|status|logs|follow|pcap}"
    exit 1
    ;;
esac