import json
import os
import re
import sys
import uuid
from pathlib import Path

from hierarchy.build import search_with_fallback, build_category_tree

CATEGORY_NODES = build_category_tree()

import requests
from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import Text, cast, desc, select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import SessionLocal, init_db  # noqa: E402
from database.models import Shop  # noqa: E402


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
DB_INITIALIZED = False


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("STREETLENS_SECRET_KEY", "streetlens-dev-secret")
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
    app.config["FASTAPI_ENDPOINT"] = os.getenv(
        "STREETLENS_API_URL", "http://127.0.0.1:8000/image-analyzer"
    )
    app.config["FASTAPI_TIMEOUT"] = int(os.getenv("STREETLENS_API_TIMEOUT", "90"))

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/analyze")
    def analyze_image():
        uploaded_file = request.files.get("image")
        validation_error = _validate_upload(uploaded_file)
        if validation_error:
            flash(validation_error, "error")
            return redirect(url_for("index"))

        saved_filename = _save_upload(uploaded_file)
        saved_path = UPLOAD_FOLDER / saved_filename

        try:
            api_data = _send_to_fastapi(
                saved_path,
                uploaded_file.filename,
                uploaded_file.mimetype,
                app.config["FASTAPI_ENDPOINT"],
                app.config["FASTAPI_TIMEOUT"],
            )
        except (requests.RequestException, ValueError) as exc:
            saved_path.unlink(missing_ok=True)
            flash(f"Image analysis failed: {exc}", "error")
            return redirect(url_for("index"))

        if api_data.get("error"):
            saved_path.unlink(missing_ok=True)
            flash(api_data["error"], "error")
            return redirect(url_for("index"))

        extracted_data = _normalize_api_response(api_data)
        extracted_data["image_path"] = f"uploads/{saved_filename}"
        return render_template(
            "result.html",
            action_url=url_for("save_shop"),
            data=extracted_data,
            image_url=url_for("static", filename=f"uploads/{saved_filename}"),
            mode="new",
            page_title="Review Extracted Data",
            submit_label="Save",
        )

    @app.post("/shops")
    def save_shop():
        form_data, errors = _shop_form_data(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return (
                _render_result_from_form(
                    form_data,
                    url_for("save_shop"),
                    "new",
                    "Save",
                    miscellaneous_text=request.form.get("miscellaneous_data", ""),
                ),
                400,
            )

        try:
            _ensure_db()
            with SessionLocal() as session:
                shop = Shop(**form_data)
                session.add(shop)
                session.commit()
                shop_id = shop.id
        except SQLAlchemyError as exc:
            flash(f"Database save failed: {exc}", "error")
            return (
                _render_result_from_form(
                    form_data,
                    url_for("save_shop"),
                    "new",
                    "Save",
                    miscellaneous_text=request.form.get("miscellaneous_data", ""),
                ),
                500,
            )

        flash("Shop record saved.", "success")
        return redirect(url_for("edit_shop", shop_id=shop_id))

    @app.get("/search")
    def search():
        shop_name = request.args.get("shop_name", "").strip()
        category = request.args.get("category", "").strip()
        phone_number = request.args.get("phone_number", "").strip()

        shops = []
        categories = []
        try:
            _ensure_db()
            with SessionLocal() as session:
                categories = [
                    row[0]
                    for row in session.execute(
                        select(Shop.category)
                        .where(Shop.category.is_not(None), Shop.category != "")
                        .distinct()
                        .order_by(Shop.category)
                    )
                ]

                query = select(Shop)
                if shop_name:
                    query = query.where(Shop.shop_name.ilike(f"%{shop_name}%"))
                if category:
                    node = CATEGORY_NODES.get(category)
                    if node:
                        shops = search_with_fallback(node, session)
                    else:
                        shops = []
                if phone_number:
                    query = query.where(cast(Shop.phone_number, Text).like(f"%{phone_number}%"))

                shops = session.scalars(query.order_by(desc(Shop.created_at))).all()
        except SQLAlchemyError as exc:
            flash(f"Search failed: {exc}", "error")

        return render_template(
            "search.html",
            categories=categories,
            filters={
                "shop_name": shop_name,
                "category": category,
                "phone_number": phone_number,
            },
            shops=shops,
        )

    @app.get("/shops/<int:shop_id>/edit")
    def edit_shop(shop_id):
        try:
            _ensure_db()
            with SessionLocal() as session:
                shop = session.get(Shop, shop_id)
                if not shop:
                    flash("Shop record not found.", "error")
                    return redirect(url_for("search"))
                data = _shop_to_form_data(shop)
        except SQLAlchemyError as exc:
            flash(f"Could not load shop record: {exc}", "error")
            return redirect(url_for("search"))

        return render_template(
            "result.html",
            action_url=url_for("update_shop", shop_id=shop_id),
            data=data,
            image_url=_image_url(data.get("image_path")),
            mode="edit",
            page_title="Edit Saved Data",
            submit_label="Update",
        )

    @app.post("/shops/<int:shop_id>")
    def update_shop(shop_id):
        form_data, errors = _shop_form_data(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return (
                _render_result_from_form(
                    form_data,
                    url_for("update_shop", shop_id=shop_id),
                    "edit",
                    "Update",
                    shop_id=shop_id,
                    miscellaneous_text=request.form.get("miscellaneous_data", ""),
                ),
                400,
            )

        try:
            _ensure_db()
            with SessionLocal() as session:
                shop = session.get(Shop, shop_id)
                if not shop:
                    flash("Shop record not found.", "error")
                    return redirect(url_for("search"))

                for field, value in form_data.items():
                    setattr(shop, field, value)
                session.commit()
        except SQLAlchemyError as exc:
            flash(f"Update failed: {exc}", "error")
            return (
                _render_result_from_form(
                    form_data,
                    url_for("update_shop", shop_id=shop_id),
                    "edit",
                    "Update",
                    shop_id=shop_id,
                    miscellaneous_text=request.form.get("miscellaneous_data", ""),
                ),
                500,
            )

        flash("Shop record updated.", "success")
        return redirect(url_for("edit_shop", shop_id=shop_id))

    @app.post("/shops/<int:shop_id>/delete")
    def delete_shop(shop_id):
        try:
            _ensure_db()
            with SessionLocal() as session:
                shop = session.get(Shop, shop_id)
                if not shop:
                    flash("Shop record not found.", "error")
                    return redirect(_search_redirect_url())

                shop_name = shop.shop_name
                session.delete(shop)
                session.commit()
        except SQLAlchemyError as exc:
            flash(f"Delete failed: {exc}", "error")
            return redirect(_search_redirect_url())

        flash(f"Deleted {shop_name}.", "success")
        return redirect(_search_redirect_url())

    return app


def _ensure_db():
    global DB_INITIALIZED
    if DB_INITIALIZED:
        return
    init_db()
    DB_INITIALIZED = True


def _validate_upload(uploaded_file):
    if not uploaded_file or uploaded_file.filename == "":
        return "Choose an image before submitting."

    extension = uploaded_file.filename.rsplit(".", 1)[-1].lower()
    if "." not in uploaded_file.filename or extension not in ALLOWED_EXTENSIONS:
        return "Upload a PNG, JPG, JPEG, or WEBP image."

    return None


def _save_upload(uploaded_file):
    original_name = secure_filename(uploaded_file.filename)
    extension = original_name.rsplit(".", 1)[-1].lower()
    saved_filename = f"{uuid.uuid4().hex}.{extension}"
    uploaded_file.save(UPLOAD_FOLDER / saved_filename)
    return saved_filename


def _send_to_fastapi(path, original_filename, mimetype, endpoint, timeout):
    with path.open("rb") as image_file:
        files = {
            "file": (
                secure_filename(original_filename) or path.name,
                image_file,
                mimetype or "application/octet-stream",
            )
        }
        response = requests.post(endpoint, files=files, timeout=timeout)
        response.raise_for_status()
        return response.json()


def _normalize_api_response(api_data):
    miscellaneous_data = api_data.get("miscellaneous_data", api_data.get("miscellaneous", {}))
    phone_numbers = _coerce_phone_numbers(api_data.get("phone_number", []))

    return {
        "shop_name": _clean_text(api_data.get("shop_name")),
        "phone_number": phone_numbers,
        "phone_number_text": ", ".join(phone_numbers),
        "category": _clean_text(api_data.get("category")),
        "address": _clean_text(api_data.get("address")),
        "gst_number": _clean_text(api_data.get("gst_number")),
        "miscellaneous_data": miscellaneous_data or {},
        "miscellaneous_text": _json_text(miscellaneous_data or {}),
        "extracted_text": _clean_text(api_data.get("extracted_text")),
        "image_path": "",
    }


def _shop_form_data(form):
    errors = []
    shop_name = form.get("shop_name", "").strip()
    if not shop_name:
        errors.append("Shop name is required.")

    miscellaneous_text = form.get("miscellaneous_data", "").strip()
    try:
        miscellaneous_data = json.loads(miscellaneous_text) if miscellaneous_text else None
    except json.JSONDecodeError:
        errors.append("Miscellaneous data must be valid JSON.")
        miscellaneous_data = None

    form_data = {
        "shop_name": shop_name,
        "phone_number": _parse_phone_numbers(form.get("phone_number", "")),
        "category": form.get("category", "").strip() or None,
        "address": form.get("address", "").strip() or None,
        "gst_number": form.get("gst_number", "").strip() or None,
        "miscellaneous_data": miscellaneous_data,
        "extracted_text": form.get("extracted_text", "").strip() or None,
        "image_path": form.get("image_path", "").strip() or None,
    }
    return form_data, errors


def _parse_phone_numbers(value):
    return [item.strip() for item in re.split(r"[,\n]", value or "") if item.strip()]


def _coerce_phone_numbers(value):
    if value in (None, "NA"):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return _parse_phone_numbers(str(value))


def _shop_to_form_data(shop):
    phone_numbers = shop.phone_number or []
    miscellaneous_data = shop.miscellaneous_data or {}

    return {
        "shop_name": shop.shop_name or "",
        "phone_number": phone_numbers,
        "phone_number_text": ", ".join(phone_numbers),
        "category": shop.category or "",
        "address": shop.address or "",
        "gst_number": shop.gst_number or "",
        "miscellaneous_data": miscellaneous_data,
        "miscellaneous_text": _json_text(miscellaneous_data),
        "extracted_text": shop.extracted_text or "",
        "image_path": shop.image_path or "",
    }


def _render_result_from_form(
    form_data, action_url, mode, submit_label, shop_id=None, miscellaneous_text=None
):
    data = {
        **form_data,
        "phone_number_text": ", ".join(form_data.get("phone_number") or []),
        "miscellaneous_text": (
            miscellaneous_text
            if miscellaneous_text is not None
            else _json_text(form_data.get("miscellaneous_data") or {})
        ),
    }
    return render_template(
        "result.html",
        action_url=action_url,
        data=data,
        image_url=_image_url(data.get("image_path")),
        mode=mode,
        page_title="Review Extracted Data" if mode == "new" else "Edit Saved Data",
        shop_id=shop_id,
        submit_label=submit_label,
    )


def _image_url(image_path):
    if not image_path:
        return None
    return url_for("static", filename=image_path)


def _clean_text(value):
    if value in (None, "NA"):
        return ""
    return str(value).strip()


def _json_text(value):
    if not value:
        return ""
    return json.dumps(value, ensure_ascii=False, indent=2)


def _search_redirect_url():
    allowed_filters = ("shop_name", "category", "phone_number")
    filters = {
        key: request.form.get(key, "").strip()
        for key in allowed_filters
        if request.form.get(key, "").strip()
    }
    return url_for("search", **filters)


app = create_app()


if __name__ == "__main__":
    flask_port = int(os.getenv("STREETLENS_FLASK_PORT", "5000"))
    flask_debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(debug=flask_debug, port=flask_port, use_reloader=flask_debug)
