
from flask import Flask, render_template, request, jsonify
import subprocess
import re

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

    data = request.get_json(silent=True) or {}

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

    data = request.get_json(silent=True) or {}

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

    # Schedule reboot after a short delay so the HTTP response
    # has a chance to reach the phone.

    result = subprocess.Popen(
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
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )