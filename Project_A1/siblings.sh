#!/usr/bin/env bash
# Prints pairs of thread siblings from sysfs if available
for cpu in /sys/devices/system/cpu/cpu[0-9]*; do
  id=$(basename "$cpu" | sed 's/cpu//')
  f="$cpu/topology/thread_siblings_list"
  if [ -f "$f" ]; then
    echo -n "cpu$id siblings: "
    cat "$f"
  fi
done
