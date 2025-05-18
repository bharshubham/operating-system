import psutil
from influxdb import InfluxDBClient
import time

# InfluxDB configuration
HOST = 'localhost'
PORT = 8086
DATABASE = 'linuxperfmon'

client = InfluxDBClient(host=HOST, port=PORT)
client.create_database(DATABASE)
client.switch_database(DATABASE)

# Initialize variables for network rate calculation
previous_network_io = None
previous_time = None

while True:
    # Measure CPU usage (single interval, store result)
    cpu_percent_overall = psutil.cpu_percent(interval=1)
    cpu_percent_per_core = psutil.cpu_percent(interval=1, percpu=True)

    current_time = time.time()

    # Collect memory usage
    memory = psutil.virtual_memory()

    # Collect disk usage safely
    disk_partitions = psutil.disk_partitions()
    disk_usage = {}
    for partition in disk_partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_usage[partition.mountpoint] = usage
        except PermissionError:
            continue

    # Collect network I/O
    current_network_io = psutil.net_io_counters(pernic=True)

    # Calculate network rates
    if previous_network_io is not None and previous_time is not None:
        delta_time = current_time - previous_time
        network_rates = {}
        for interface, io in current_network_io.items():
            prev_io = previous_network_io.get(interface)
            if prev_io:
                network_rates[interface] = {
                    "bytes_sent_per_sec": (io.bytes_sent - prev_io.bytes_sent) / delta_time,
                    "bytes_recv_per_sec": (io.bytes_recv - prev_io.bytes_recv) / delta_time,
                    "packets_sent_per_sec": (io.packets_sent - prev_io.packets_sent) / delta_time,
                    "packets_recv_per_sec": (io.packets_recv - prev_io.packets_recv) / delta_time
                }
            else:
                network_rates[interface] = {
                    "bytes_sent_per_sec": 0, "bytes_recv_per_sec": 0,
                    "packets_sent_per_sec": 0, "packets_recv_per_sec": 0
                }
    else:
        network_rates = {
            interface: {
                "bytes_sent_per_sec": 0, "bytes_recv_per_sec": 0,
                "packets_sent_per_sec": 0, "packets_recv_per_sec": 0
            } for interface in current_network_io
        }

    # Update previous values
    previous_network_io = current_network_io
    previous_time = current_time

    # Prepare data for InfluxDB
    json_body = [
        {"measurement": "cpu_usage_overall", "fields": {"percent": cpu_percent_overall}},
        *[
            {"measurement": "cpu_usage_per_core", "tags": {"core_id": str(i)}, "fields": {"percent": percent}}
            for i, percent in enumerate(cpu_percent_per_core)
        ],
        {"measurement": "memory_usage", "fields": {
            "total": memory.total,
            "used": memory.used,
            "free": memory.free,
            "percent": memory.percent
        }},
        *[
            {"measurement": "disk_usage", "tags": {"partition": partition}, "fields": {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent
            }} for partition, usage in disk_usage.items()
        ],
        *[
            {"measurement": "network_usage", "tags": {"interface": interface}, "fields": rates}
            for interface, rates in network_rates.items()
        ]
    ]

    # Write data to InfluxDB
    try:
        client.write_points(json_body)
    except Exception as e:
        print(f"Failed to write to InfluxDB: {e}")
