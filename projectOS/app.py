from flask import Flask, render_template, jsonify
from influxdb import InfluxDBClient

app = Flask(__name__)

# InfluxDB configuration
HOST = 'localhost'
PORT = 8086
DATABASE = 'linuxperform'
client = InfluxDBClient(host=HOST, port=PORT, database=DATABASE)

def get_latest_metrics():
    metrics = {}
    # CPU overall
    result = client.query('SELECT last("percent") FROM "cpu_usage_overall"')
    metrics['cpu_overall'] = list(result.get_points())[0]['last'] if result else 0

    # Memory
    result = client.query('SELECT last("percent") FROM "memory_usage"')
    metrics['memory_percent'] = list(result.get_points())[0]['last'] if result else 0

    # Disk usage (root partition as example)
    result = client.query('SELECT last("percent") FROM "disk_usage" WHERE "partition" = \'/\'')
    metrics['disk_percent'] = list(result.get_points())[0]['last'] if result else 0

    # Network usage (eth0 as example, adjust interface name as needed)
    result = client.query('SELECT last("bytes_sent_per_sec"), last("bytes_recv_per_sec") FROM "network_usage" WHERE "interface" = \'eth0\'')
    metrics['network'] = list(result.get_points())[0] if result else {"last_bytes_sent_per_sec": 0, "last_bytes_recv_per_sec": 0}

    return metrics

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/metrics')
def api_metrics():
    return jsonify(get_latest_metrics())

if __name__ == '__main__':
    app.run(debug=True)
