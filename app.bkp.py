from flask import Flask, render_template, request, jsonify
import subprocess
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

app = Flask(__name__)

LOCAL_NODE = "68751"


# ============================================================
# RUN ASTERISK
# ============================================================

def run_asterisk(command):

    result = subprocess.run(
        [
            "sudo",
            "-n",
            "/usr/sbin/asterisk",
            "-rx",
            command
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None, result.stderr.strip()

    return result.stdout.strip(), None


# ============================================================
# GET CONNECTED NODES
# ============================================================

def get_connected_nodes():

    output, error = run_asterisk(
        f"rpt nodes {LOCAL_NODE}"
    )

    if error:
        return [], error

    if not output:
        return [], None

    if "<NONE>" in output:
        return [], None

    nodes = []

    matches = re.findall(
        r"\b[TR](\d+)\b",
        output
    )

    for node in matches:

        if node != LOCAL_NODE and node not in nodes:
            nodes.append(node)

    return nodes, None


# ============================================================
# PI TEMPERATURE
# ============================================================

def get_pi_temperature():

    try:

        with open(
            "/sys/class/thermal/thermal_zone0/temp",
            "r"
        ) as f:

            temp = int(
                f.read().strip()
            ) / 1000.0

        return round(temp, 1)

    except Exception:

        return None


# ============================================================
# TELEMETRY
# ============================================================

@app.route("/api/telemetry")
def telemetry():

    now_utc = datetime.now(timezone.utc)

    # India
    ist = now_utc.astimezone(
        ZoneInfo("Asia/Kolkata")
    )

    # US Eastern Time
    # Automatically changes between EST and EDT
    eastern = now_utc.astimezone(
        ZoneInfo("America/New_York")
    )

    return jsonify({

        "success": True,

        # ----------------------------------------------------
        # DATE / DAY
        # ----------------------------------------------------

        "day": ist.strftime("%A"),

        "date": ist.strftime("%Y-%m-%d"),

        # ----------------------------------------------------
        # INDIA
        # ----------------------------------------------------

        "local_time": ist.strftime("%H:%M:%S"),

        "local_timezone": "IST",

        # ----------------------------------------------------
        # UTC
        # ----------------------------------------------------

        "utc_time": now_utc.strftime("%H:%M:%S"),

        "utc_date": now_utc.strftime("%Y-%m-%d"),

        # ----------------------------------------------------
        # US EASTERN
        # ----------------------------------------------------

        "eastern_time": eastern.strftime("%H:%M:%S"),

        "eastern_date": eastern.strftime("%Y-%m-%d"),

        "eastern_timezone": eastern.tzname(),

        # ----------------------------------------------------
        # RASPBERRY PI
        # ----------------------------------------------------

        "pi_temperature": get_pi_temperature()
    })


# ============================================================
# WEB PAGE
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html",
        local_node=LOCAL_NODE
    )


# ============================================================
# STATUS API
# ============================================================

@app.route("/api/status")
def status():

    nodes, error = get_connected_nodes()

    if error:

        return jsonify({
            "success": False,
            "error": error
        }), 500

    return jsonify({

        "success": True,

        "local_node": LOCAL_NODE,

        "nodes": nodes
    })


# ============================================================
# CONNECT
# ============================================================

@app.route("/api/connect", methods=["POST"])
def connect():

    data = request.get_json(
        silent=True
    ) or {}

    target = str(
        data.get("node", "")
    ).strip()

    if not target.isdigit():

        return jsonify({
            "success": False,
            "error": "Invalid node number"
        }), 400

    output, error = run_asterisk(
        f"rpt cmd {LOCAL_NODE} ilink 3 {target}"
    )

    if error:

        return jsonify({
            "success": False,
            "error": error
        }), 500

    return jsonify({

        "success": True,

        "node": target,

        "output": output
    })


# ============================================================
# DISCONNECT
# ============================================================

@app.route("/api/disconnect", methods=["POST"])
def disconnect():

    data = request.get_json(
        silent=True
    ) or {}

    target = str(
        data.get("node", "")
    ).strip()

    if not target.isdigit():

        return jsonify({
            "success": False,
            "error": "Invalid node number"
        }), 400

    output, error = run_asterisk(
        f"rpt cmd {LOCAL_NODE} ilink 1 {target}"
    )

    if error:

        return jsonify({
            "success": False,
            "error": error
        }), 500

    return jsonify({

        "success": True,

        "node": target,

        "output": output
    })


# ============================================================
# DISCONNECT ALL
# ============================================================

@app.route("/api/disconnect-all", methods=["POST"])
def disconnect_all():

    output, error = run_asterisk(
        f"rpt cmd {LOCAL_NODE} ilink 6"
    )

    if error:

        return jsonify({
            "success": False,
            "error": error
        }), 500

    return jsonify({

        "success": True,

        "output": output
    })


# ============================================================
# REBOOT SYSTEM
# ============================================================

@app.route("/api/reboot", methods=["POST"])
def reboot():

    subprocess.Popen(
        [
            "sudo",
            "-n",
            "/usr/bin/systemctl",
            "reboot"
        ]
    )

    return jsonify({

        "success": True,

        "message": "System reboot initiated"
    })


# ============================================================
# SHUTDOWN SYSTEM
# ============================================================

@app.route("/api/shutdown", methods=["POST"])
def shutdown():

    subprocess.Popen(
        [
            "sudo",
            "-n",
            "/usr/bin/systemctl",
            "poweroff"
        ]
    )

    return jsonify({

        "success": True,

        "message": "System shutdown initiated"
    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )