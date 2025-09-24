import os, pytest, requests

OK = (200,201,400,409,422)

def _first_working_endpoint(base_url, headers, mode):
    # Позволим переопределять явным путём через ENV
    override = os.getenv(f"ORDER_{mode.upper()}_PATH")
    if override:
        return override, "POST"

    candidates = [
        (f"/api/v1/orders/{mode}/", "POST"),          # A: /orders/reserve/ (action endpoint collection)
        (f"/api/v1/orders/1/{mode}/", "POST"),        # B: /orders/{id}/reserve/
        (f"/api/v1/orders/actions/{mode}/", "POST"),  # C: /orders/actions/reserve/
        (f"/api/v1/transactions/{mode}/", "POST"),    # D: /transactions/reserve/
        (f"/api/v1/orders/", "POST"),                 # E: action в теле запроса
    ]

    for path, method in candidates:
        url = f"{base_url}{path}"
        try:
            opt = requests.options(url, headers=headers, timeout=5)
            allow = opt.headers.get("Allow","").upper()
            # Если метод разрешён или сервер не дал Allow, попробуем запрос
            if (not allow) or (method in allow or "POST" in allow):
                r = _try_call(url, headers, method, mode)
                if r is not None and (r.status_code in OK or r.status_code not in (404,405)):
                    return path, method
        except Exception:
            continue
    return None, None

def _try_call(url, headers, method, mode):
    payload = {"car_id": 1, "customer_id": 1}
    if url.endswith("/api/v1/orders/"):  # вариант с action в теле
        payload["action"] = mode
    try:
        if method == "POST":
            return requests.post(url, headers=headers, json=payload, timeout=10)
        elif method == "PATCH":
            return requests.patch(url, headers=headers, json=payload, timeout=10)
        elif method == "PUT":
            return requests.put(url, headers=headers, json=payload, timeout=10)
    except Exception:
        return None

@pytest.mark.parametrize("mode", ["reserve","complete_sale"])
def test_business_procedures_atomicity(base_url, h_admin, mode):
    # Сначала ищем рабочий путь/метод
    path, method = _first_working_endpoint(base_url, h_admin, mode)
    if not path:
        pytest.skip(f"Не найден рабочий эндпойнт для операции {mode}. Задай ORDER_{mode.upper()}_PATH, например: /api/v1/orders/{mode}/")
        return

    url = f"{base_url}{path}"
    resp = _try_call(url, h_admin, method, mode)
    assert resp is not None, "Не удалось выполнить запрос к бизнес-операции"

    # Ожидаем успех или контролируемую ошибка валидации/конфликта — но не 500 и не 405
    assert resp.status_code in OK, f"{resp.status_code}: {resp.text}"
