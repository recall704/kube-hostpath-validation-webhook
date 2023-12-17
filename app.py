import logging
import os
import re
import yaml
from flask import Flask, jsonify, request

app = Flask("webhook")
app.logger.addHandler(logging.StreamHandler())
app.logger.setLevel(logging.DEBUG)


rule_name = "rules.yaml"
rule_file = os.path.join(os.path.dirname(__file__), rule_name)
if not os.path.exists(rule_file):
    raise Exception("Rule file %s not found" % rule_file)

hostpath_rules = []
with open(rule_file) as f:
    hostpath_rules = yaml.safe_load(f.read())
    app.logger.debug(f"rules: {hostpath_rules}")


# Default route
@app.route("/", methods=["GET"])
def hello():
    return jsonify({"message": "Hello validation controller"})


# Health check
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "pong"})


def validate_rule(rule, hostpath: str) -> bool:
    if re.search(rule, hostpath):
        return True


@app.route("/validate", methods=["POST"])
def deployment_webhook():
    r = request.get_json()

    req = r.get("request", {})
    # app.logger.debug(f"+ request: {req}")
    try:
        if not req:
            return send_response(
                False, "<no uid>", "Invalid request, no payload.request found"
            )

        uid = req.get("uid", "")
        app.logger.debug(f"+ uid: {uid}")
        if not uid:
            return send_response(
                False, "<no uid>", "Invalid request, no payload.request.uid found"
            )

        # get volumes
        volumes = req.get("object", {}).get("spec", {}).get("volumes")
        app.logger.debug(f"+ volumes: {volumes}")
        for vol in volumes:
            # if vol is hostpath
            if vol.get("hostPath", {}).get("path"):
                # 1. hostpath not allowed
                for disabled_rule in hostpath_rules.get("disabled", []):
                    if re.search(disabled_rule, vol.get("hostPath", {}).get("path")):
                        return send_response(
                            False,
                            uid,
                            f"hostPath {vol.get('hostPath', {}).get('path')} is not allowed",
                        )

                # 2. hostpath allowed, but it must be readOnly
                for readonly_rule in hostpath_rules.get("readonly", []):
                    if re.search(readonly_rule, vol.get("hostPath", {}).get("path")):
                        vol_name = vol.get("name", "")
                        for container in (
                            req.get("object", {})
                            .get("spec", {})
                            .get("template", {})
                            .get("spec", {})
                            .get("containers", [])
                        ):
                            for volumeMount in container.get("volumeMounts", []):
                                if volumeMount.get("name") == vol_name:
                                    # vomlumeMount must be readOnly
                                    if volumeMount.get("readOnly", False) == False:
                                        return send_response(
                                            False,
                                            uid,
                                            f"hostPath {vol.get('hostPath', {}).get('path')} must be readOnly",
                                        )
                                    else:
                                        continue
                        for initContainer in (
                            req.get("object", {})
                            .get("spec", {})
                            .get("template", {})
                            .get("spec", {})
                            .get("initContainers", [])
                        ):
                            for volumeMount in initContainer.get("volumeMounts", []):
                                if volumeMount.get("name") == vol_name:
                                    # vomlumeMount must be readOnly
                                    if volumeMount.get("readOnly", False) == False:
                                        return send_response(
                                            False,
                                            uid,
                                            f"hostPath {vol.get('hostPath', {}).get('path')} must be readOnly",
                                        )
                                    else:
                                        continue

    except Exception as e:
        return send_response(False, uid, f"Webhook exception: {e}")

    # Send OK
    return send_response(True, uid, "Request has required labels")


# Function to respond back to the Admission Controller
def send_response(allowed, uid, message):
    app.logger.debug(f"> response:(allowed={allowed}, uid={uid}, message={message})")
    return jsonify(
        {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "allowed": allowed,
                "uid": uid,
                "status": {"message": message},
            },
        }
    )


if __name__ == "__main__":
    server_crt = "/etc/ssl/server.crt"
    server_key = "/etc/ssl/server.key"
    if os.path.exists(server_crt) and os.path.exists(server_key):
        app.run(
            ssl_context=(server_crt, server_key), port=8080, host="0.0.0.0", debug=True
        )
    else:
        app.run(port=8080, host="0.0.0.0", debug=True)
