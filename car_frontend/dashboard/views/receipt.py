from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime
from django.conf import settings
import requests

API_BASE = getattr(settings, "API_BASE_URL", "http://127.0.0.1:8000/api/v1")


def _fetch_receipt_context(request, tx_id: int):
    """
    Забираем контекст у DRF: GET /transactions/{id}/receipt_context/
    Возвращаем (ctx, status_code). Нормализуем дату (в ctx.transaction.transaction_date_fmt).
    """
    token = request.session.get("api_token")
    if not token:
        return ({"not_found": True, "tx_id": tx_id, "error": "no token"}, 401)

    url = f"{API_BASE}/transactions/{tx_id}/receipt_context/"
    headers = {"Authorization": f"Token {token}"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        return ({"not_found": True, "tx_id": tx_id, "error": str(e)}, 502)

    if resp.status_code == 404:
        return ({"not_found": True, "tx_id": tx_id}, 404)

    try:
        resp.raise_for_status()
        ctx = resp.json() or {}
    except Exception as e:
        return ({"not_found": True, "tx_id": tx_id, "error": f"Bad response: {e}"}, 502)

    tx = ctx.get("transaction") or {}
    raw_dt = tx.get("transaction_date")
    dt = parse_datetime(raw_dt) if raw_dt else None
    if dt is not None:
        dt = localtime(dt)
        tx["transaction_date_obj"] = dt
        tx["transaction_date_fmt"] = dt.strftime("%d.%m.%Y %H:%M")
    ctx["transaction"] = tx
    ctx["tx"] = tx
    ctx["tx_id"] = ctx.get("tx_id", tx_id)
    ctx["not_found"] = False

    ctx.setdefault("company", {
        "name": "ООО HaifAvto",
        "inn": "7701234567",
        "address": "г. Москва, ул. Примерная, 1",
        "phone": "+7 (495) 000-00-00",
    })
    return (ctx, 200)


def receipt_page(request, tx_id: int):
    """HTML-страница чека"""
    ctx, code = _fetch_receipt_context(request, tx_id)
    if code == 401:
        return redirect("users_dashboard")
    return render(request, "dashboard/receipt.html", ctx, status=(200 if code == 200 else code))


def receipt_pdf(request, tx_id: int):
    """Скачиваемый PDF чека (WeasyPrint)"""
    ctx, code = _fetch_receipt_context(request, tx_id)
    if code == 401:
        return redirect("users_dashboard")
    if code != 200:
        return render(request, "dashboard/receipt.html", ctx, status=code)

    try:
        from weasyprint import HTML, CSS
    except Exception:
        return HttpResponse(
            "PDF-генератор не установлен. Установите weasyprint.",
            status=501, content_type="text/plain; charset=utf-8"
        )

    html_str = render_to_string("dashboard/receipt_pdf.html", ctx, request=request)
    html = HTML(string=html_str, base_url=request.build_absolute_uri("/"))
    pdf_bytes = html.write_pdf(stylesheets=[CSS(string='@page { size: A4; margin: 18mm; }')])

    filename = f"receipt-{ctx['transaction'].get('id', tx_id)}.pdf"
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp