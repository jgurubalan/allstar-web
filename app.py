
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
        text=True,
        timeout=15
    )

    if result.returncode != 0:
        return None, result.stderr.strip() or "Asterisk command failed"

    return result.stdout.strip(), None


# ============================================================
# GET CONNECTED NODES
# ============================================================


def get_connected_nodes():
    output, error = run_asterisk(f"rpt nodes {LOCAL_NODE}")

    if error:
        return [], error

    if not output or "<NONE>" in output:
        return [], None

    # Parse the list after the CONNECTED NODES heading.
    parts = re.split(r"CONNECTED NODES\s*", output, flags=re.IGNORECASE)
    if len(parts) < 2:
        return [], None

    nodes = []
    for token in re.split(r"[\s,]+", parts[1].strip()):
        token = token.strip()

        if not token:
            continue

        # T12345 / R12345 -> 12345.
        # Keep callsign-style entries such as W3ICQ as they are.
        match = re.fullmatch(r"[TR](\d+)", token)
        if match:
            node = match.group(1)
        elif re.fullmatch(r"[A-Za-z0-9-]+", token):
            node = token
        else:
            continue

        if node != LOCAL_NODE and node not in nodes:
            nodes.append(node)

    return nodes, None


# ============================================================
# PI TEMPERATURE
# ============================================================

def get_pi_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read().strip()) / 1000.0
        return round(temp, 1)
    except Exception:
        return None


# ============================================================
# TELEMETRY
# ============================================================

@app.route("/api/telemetry")
def telemetry():
    now_utc = datetime.now(timezone.utc)
    ist = now_utc.astimezone(ZoneInfo("Asia/Kolkata"))
    eastern = now_utc.astimezone(ZoneInfo("America/New_York"))

    return jsonify({
        "success": True,
        "day": ist.strftime("%A"),
        "date": ist.strftime("%Y-%m-%d"),
        "local_time": ist.strftime("%H:%M:%S"),
        "local_timezone": "IST",
        "utc_time": now_utc.strftime("%H:%M:%S"),
        "utc_date": now_utc.strftime("%Y-%m-%d"),
        "eastern_time": eastern.strftime("%H:%M:%S"),
        "eastern_date": eastern.strftime("%Y-%m-%d"),
        "eastern_timezone": eastern.tzname(),
        "pi_temperature": get_pi_temperature()
    })


# ============================================================
# WEB PAGE
# ============================================================

@app.route("/")
def index():
    return render_template("index.html", local_node=LOCAL_NODE)


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
# CONNECT TO AN ALLSTAR NODE
# ============================================================

@app.route("/api/connect", methods=["POST"])
def connect():
    data = request.get_json(silent=True) or {}
    target = str(data.get("node", "")).strip()

    if not target.isdigit() or int(target) <= 0:
        return jsonify({
            "success": False,
            "error": "Invalid node number"
        }), 400

    if target == LOCAL_NODE:
        return jsonify({
            "success": False,
            "error": "Cannot connect to the local node itself"
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
        "message": f"Connection command sent to node {target}",
        "output": output
    })


# ============================================================
# DISCONNECT FROM AN ALLSTAR NODE
# ============================================================

@app.route("/api/disconnect", methods=["POST"])
def disconnect():
    data = request.get_json(silent=True) or {}
    target = str(data.get("node", "")).strip()

    if not target.isdigit() or int(target) <= 0:
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
        "message": f"Disconnection command sent to node {target}",
        "output": output
    })


# ============================================================
# ECHOLINK CONNECT / DISCONNECT
# The web form takes the normal EchoLink node number.
# Based on the supplied command, prefix it with "3" for AllStar.
# Example: 696410 becomes 3696410.
# ============================================================

@app.route("/api/echolink", methods=["POST"])
def echolink():
    data = request.get_json(silent=True) or {}

    action = str(data.get("action", "")).strip().lower()
    target = str(data.get("node", "")).strip()

    if action not in ("connect", "disconnect"):
        return jsonify({
            "success": False,
            "error": "Invalid EchoLink action"
        }), 400

    if not target.isdigit() or int(target) <= 0:
        return jsonify({
            "success": False,
            "error": "Invalid EchoLink node number"
        }), 400

    # Convert the entered EchoLink node to the target format
    # shown in the supplied Asterisk command.
    echolink_target = f"3{target}"

    if action == "connect":
        command = (
            f"rpt cmd {LOCAL_NODE} ilink 3 {echolink_target}"
        )
    else:
        command = (
            f"rpt cmd {LOCAL_NODE} ilink 1 {echolink_target}"
        )

    output, error = run_asterisk(command)

    if error:
        return jsonify({
            "success": False,
            "error": error
        }), 500

    verb = "Connection" if action == "connect" else "Disconnection"

    return jsonify({
        "success": True,
        "node": target,
        "allstar_target": echolink_target,
        "message": (
            f"{verb} command sent for EchoLink node {target}"
        ),
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
        "message": "Disconnect-all command sent",
        "output": output
    })



# ============================================================
# REBOOT SYSTEM
# ============================================================

@app.route("/api/reboot", methods=["POST"])
def reboot():
    try:
        result = subprocess.run(
            ["sudo", "-n", "/usr/bin/systemctl", "reboot"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return jsonify({
                "success": False,
                "error": result.stderr.strip() or
                         "Reboot command failed"
            }), 500

        return jsonify({
            "success": True,
            "message": "Reboot command accepted"
        })

    except Exception as exc:
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# ============================================================
# SHUTDOWN SYSTEM
# ============================================================

@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    try:
        result = subprocess.run(
            ["sudo", "-n", "/usr/bin/systemctl", "poweroff"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return jsonify({
                "success": False,
                "error": result.stderr.strip() or
                         "Shutdown command failed"
            }), 500

        return jsonify({
            "success": True,
            "message": "Shutdown command accepted"
        })

    except Exception as exc:
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
