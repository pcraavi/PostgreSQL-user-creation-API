# -*- coding: utf-8 -*-
"""
pg_user_api - PostgreSQL Database User Management API
======================================================
A Flask REST API for managing PostgreSQL users across
multiple environments (dev, qa, uat, prod).

Requirements:
    pip install flask psycopg2-binary

Run:
    python app.py
"""

import os
import secrets
import logging
from functools import wraps
from flask import Flask, request, jsonify
from psycopg2.extensions import AsIs
import psycopg2

from database import get_db_registry, log_operation
from auth import check_basic_auth
from notifications import send_notification

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["DEBUG"] = True

# ── API credentials (who can call this API) ───────────────────────────────────
API_USERNAME = os.environ.get("PG_API_USER", "pgadmin")
API_PASSWORD = os.environ.get("PG_API_PASS", "Ch@ngeMe2024!")

# ── DBA credentials (the PostgreSQL role that executes DDL) ───────────────────
# Override via environment variables before starting:
#   $env:PG_ADMIN_USER = "role_create"
#   $env:PG_ADMIN_PASS = "your_password"
PG_ADMIN_USER = os.environ.get("PG_ADMIN_USER", "role")
PG_ADMIN_PASS = os.environ.get("PG_ADMIN_PASS", "-")


# ──────────────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────────────
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_basic_auth(auth.username, auth.password,
                                            API_USERNAME, API_PASSWORD):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def resolve_host(env, dbname):
    row = get_db_registry(env, dbname)
    if row is None:
        msg = "No registry entry found for env='{}' database='{}'".format(env, dbname)
        logger.warning(msg)
        return None, None, msg
    return row["hostname"], str(row["port"]), None


def pg_connect(hostname, port, dbname):
    return psycopg2.connect(
        user=PG_ADMIN_USER,
        password=PG_ADMIN_PASS,
        host=hostname,
        port=port,
        database=dbname,
        connect_timeout=60,
    )


def build_response(username, password, status, hostname, dbname, port, env):
    return jsonify({
        "username": username,
        "password": password,
        "status":   status,
        "hostname": hostname,
        "database": dbname,
        "port":     port,
        "env":      env,
    })


def user_exists(cursor, username):
    cursor.execute(
        "SELECT COUNT(*) FROM pg_catalog.pg_roles WHERE rolname = %s", [username]
    )
    (n,) = cursor.fetchone()
    return n > 0


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "PostgreSQL User Management API",
        "version": "2.0.0",
        "auth":    "HTTP Basic Auth required on all /api/* endpoints",
    })



@app.route("/api/v1/users/all", methods=["GET"])
@require_auth
def list_all_users():
    env    = request.args.get("env")
    dbname = request.args.get("database")

    hostname, port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    try:
        conn   = pg_connect(hostname, port, dbname)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT usename,
                   CASE
                     WHEN usesuper AND usecreatedb THEN 'superuser, create database'
                     WHEN usesuper               THEN 'superuser'
                     WHEN usecreatedb            THEN 'create database'
                     ELSE ''
                   END AS role_attributes
            FROM   pg_catalog.pg_user
            ORDER  BY usename
        """)
        rows = cursor.fetchall()
        conn.close()
        return jsonify({
            "env":      env,
            "hostname": hostname,
            "database": dbname,
            "port":     port,
            "users":    [{"username": r[0], "attributes": r[1]} for r in rows],
        })
    except Exception as exc:
        logger.error("list_all_users: %s", exc)
        return jsonify({"error": str(exc)}), 500



@app.route("/api/v1/users/app", methods=["GET"])
@require_auth
def create_app_user():
    env        = request.args.get("env")
    dbname     = request.args.get("database")
    servername = request.args.get("servername")
    svc_port   = request.args.get("port")

    hostname, db_port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    username = "{}_{}".format(servername, svc_port)
    password = secrets.token_urlsafe(16)

    try:
        conn   = pg_connect(hostname, db_port, dbname)
        cursor = conn.cursor()
        if not user_exists(cursor, username):
            cursor.execute("CREATE USER {} CONNECTION LIMIT 200 PASSWORD '{}'".format(AsIs(username), password))
            cursor.execute("ALTER ROLE {} IN DATABASE {} SET search_path TO public".format(AsIs(username), AsIs(dbname)))
            status = "user created"
        else:
            status = "user already exists"
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("create_app_user: %s", exc)
        return jsonify({"error": str(exc)}), 500

    log_operation(env, dbname, username, "create_app_user", status)
    return build_response(username, password, status, hostname, dbname, db_port, env)



@app.route("/api/v1/users/app-k8s", methods=["GET"])
@require_auth
def create_app_user_k8s():
    env        = request.args.get("env")
    dbname     = request.args.get("database")
    env_prefix = request.args.get("env_prefix")
    farmname   = request.args.get("farmname")

    hostname, port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    username = "{}_{}".format(env_prefix, farmname)
    password = secrets.token_urlsafe(16)

    try:
        conn   = pg_connect(hostname, port, dbname)
        cursor = conn.cursor()
        if not user_exists(cursor, username):
            cursor.execute("CREATE USER {} CONNECTION LIMIT 200 PASSWORD '{}'".format(AsIs(username), password))
            cursor.execute("ALTER ROLE {} IN DATABASE {} SET search_path TO public".format(AsIs(username), AsIs(dbname)))
            status = "user created"
        else:
            status = "user already exists"
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("create_app_user_k8s: %s", exc)
        return jsonify({"error": str(exc)}), 500

    log_operation(env, dbname, username, "create_app_user_k8s", status)
    return build_response(username, password, status, hostname, dbname, port, env)



@app.route("/api/v1/users/devqa", methods=["GET"])
@require_auth
def create_devqa_user():
    env      = request.args.get("env")
    dbname   = request.args.get("database")
    username = request.args.get("username")
    password = secrets.token_urlsafe(16)

    hostname, port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    try:
        conn   = pg_connect(hostname, port, dbname)
        cursor = conn.cursor()
        if not user_exists(cursor, username):
            cursor.execute("CREATE USER {} CONNECTION LIMIT 20 PASSWORD '{}'".format(AsIs(username), password))
            cursor.execute("ALTER ROLE {} IN DATABASE {} SET search_path TO public".format(AsIs(username), AsIs(dbname)))
            status = "user created"
        else:
            status = "user already exists"
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("create_devqa_user: %s", exc)
        return jsonify({"error": str(exc)}), 500

    log_operation(env, dbname, username, "create_devqa_user", status)
    return build_response(username, password, status, hostname, dbname, port, env)



@app.route("/api/v1/users/devlead", methods=["GET"])
@require_auth
def create_devlead_user():
    env      = request.args.get("env")
    dbname   = request.args.get("database")
    username = request.args.get("username")
    password = secrets.token_urlsafe(16)

    hostname, port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    try:
        conn   = pg_connect(hostname, port, dbname)
        cursor = conn.cursor()
        if not user_exists(cursor, username):
            cursor.execute("CREATE USER {} CONNECTION LIMIT 20 PASSWORD '{}'".format(AsIs(username), password))
            cursor.execute("ALTER ROLE {} IN DATABASE {} SET search_path TO public".format(AsIs(username), AsIs(dbname)))
            status = "user created"
        else:
            status = "user already exists"
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("create_devlead_user: %s", exc)
        return jsonify({"error": str(exc)}), 500

    log_operation(env, dbname, username, "create_devlead_user", status)
    return build_response(username, password, status, hostname, dbname, port, env)



@app.route("/api/v1/users/readonly", methods=["GET"])
@require_auth
def create_readonly_user():
    env      = request.args.get("env")
    dbname   = request.args.get("database")
    username = request.args.get("username")
    password = secrets.token_urlsafe(16)

    hostname, port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    try:
        conn   = pg_connect(hostname, port, dbname)
        cursor = conn.cursor()
        if not user_exists(cursor, username):
            cursor.execute("CREATE USER {} CONNECTION LIMIT 20 PASSWORD '{}'".format(AsIs(username), password))
            cursor.execute("ALTER ROLE {} IN DATABASE {} SET search_path TO public".format(AsIs(username), AsIs(dbname)))
            status = "user created"
        else:
            status = "user already exists"
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("create_readonly_user: %s", exc)
        return jsonify({"error": str(exc)}), 500

    log_operation(env, dbname, username, "create_readonly_user", status)
    return build_response(username, password, status, hostname, dbname, port, env)



@app.route("/api/v1/users/dba", methods=["GET"])
@require_auth
def create_dba_user():
    env      = request.args.get("env")
    dbname   = request.args.get("database")
    username = request.args.get("username")
    password = secrets.token_urlsafe(16)

    hostname, port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    try:
        conn   = pg_connect(hostname, port, dbname)
        cursor = conn.cursor()
        if not user_exists(cursor, username):
            cursor.execute("CREATE USER {} CREATEDB CREATEROLE LOGIN CONNECTION LIMIT 20 PASSWORD '{}'".format(AsIs(username), password))
            cursor.execute("ALTER ROLE {} SET search_path TO public".format(AsIs(username)))
            status = "dba user created"
        else:
            status = "user already exists"
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("create_dba_user: %s", exc)
        return jsonify({"error": str(exc)}), 500

    log_operation(env, dbname, username, "create_dba_user", status)
    return build_response(username, password, status, hostname, dbname, port, env)



@app.route("/api/v1/users/reset", methods=["GET"])
@require_auth
def reset_user_password():
    env      = request.args.get("env")
    dbname   = request.args.get("database")
    username = request.args.get("username")
    password = secrets.token_urlsafe(16)

    hostname, port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    try:
        conn   = pg_connect(hostname, port, dbname)
        cursor = conn.cursor()
        if user_exists(cursor, username):
            cursor.execute("ALTER ROLE {} PASSWORD '{}'".format(AsIs(username), password))
            status = "password reset"
        else:
            status = "user not found"
            password = None
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("reset_user_password: %s", exc)
        return jsonify({"error": str(exc)}), 500

    log_operation(env, dbname, username, "reset_password", status)
    return build_response(username, password, status, hostname, dbname, port, env)



@app.route("/api/v1/users/search-path", methods=["GET"])
@require_auth
def update_search_path():
    env      = request.args.get("env")
    dbname   = request.args.get("database")
    username = request.args.get("username")
    schema   = request.args.get("schema", "public")

    hostname, port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    try:
        conn   = pg_connect(hostname, port, dbname)
        cursor = conn.cursor()
        if user_exists(cursor, username):
            cursor.execute("ALTER ROLE {} IN DATABASE {} SET search_path TO {}".format(
                AsIs(username), AsIs(dbname), AsIs(schema)))
            status = "search_path set to {}".format(schema)
        else:
            status = "user not found"
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("update_search_path: %s", exc)
        return jsonify({"error": str(exc)}), 500

    log_operation(env, dbname, username, "set_search_path", status)
    return jsonify({
        "username": username,
        "schema":   schema,
        "status":   status,
        "hostname": hostname,
        "database": dbname,
        "port":     port,
        "env":      env,
    })



@app.route("/api/v1/users/find", methods=["GET"])
@require_auth
def find_user():
    env      = request.args.get("env")
    dbname   = request.args.get("database")
    username = request.args.get("username")

    hostname, port, err = resolve_host(env, dbname)
    if err:
        return jsonify({"error": err}), 404

    try:
        conn   = pg_connect(hostname, port, dbname)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT usename,
                   CASE
                     WHEN usesuper AND usecreatedb THEN 'superuser, create database'
                     WHEN usesuper               THEN 'superuser'
                     WHEN usecreatedb            THEN 'create database'
                     ELSE 'standard'
                   END AS role_attributes
            FROM   pg_catalog.pg_user
            WHERE  usename = %s
        """, [username])
        row = cursor.fetchone()
        conn.close()
        if row:
            return jsonify({"found": True,  "username": row[0], "attributes": row[1],
                            "hostname": hostname, "database": dbname, "port": port, "env": env})
        return jsonify({"found": False, "username": username,
                        "hostname": hostname, "database": dbname, "port": port, "env": env})
    except Exception as exc:
        logger.error("find_user: %s", exc)
        return jsonify({"error": str(exc)}), 500


# http://localhost:5000/api/v1/registry
@app.route("/api/v1/registry", methods=["GET"])
@require_auth
def list_registry():
    from database import list_all_registry
    rows = list_all_registry()
    return jsonify({"count": len(rows), "databases": rows})


# ──────────────────────────────────────────────────────────────────────────────
# Error handlers
# ──────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "code": 404}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed", "code": 405}), 405

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error", "detail": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
