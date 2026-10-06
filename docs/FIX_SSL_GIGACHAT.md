# 🔧 Исправление ошибки SSL при работе с GigaChat API

## Дата
2026-01-15

## Проблема

При запуске приложения на удалённом сервере возникает ошибка:

```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain
```

**Полный лог:**
```
File "/opt/101slovo3/backend/app/services/llm/gigachat.py", line 116, in _refresh
    raise LlmUnavailable(f"Token refresh failed: {e}")
app.core.exceptions.LlmUnavailable: Token refresh failed: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain
INFO:     194.9.225.16:0 - "POST /lesson/start HTTP/1.0" 503 Service Unavailable
```

## Причина

GigaChat API использует самоподписанные сертификаты НУЦ Минцифры России. Python по умолчанию не доверяет этим сертификатам, если они не установлены в системе.

## Решение

### Вариант 1: Отключить проверку SSL (быстро, для разработки)

**Шаг 1:** Добавьте переменную в `backend/.env`:

```env
GIGACHAT_VERIFY_SSL=False
```

**Шаг 2:** Перезапустите бэкенд:

```bash
cd backend
uvicorn app.main:app --reload
```

**Результат:** Приложение будет работать без проверки SSL сертификатов.

**⚠️ Внимание:** Этот вариант небезопасен для продакшена! Используйте только для разработки и тестирования.

---

### Вариант 2: Установить корневой сертификат НУЦ Минцифры (правильно, для продакшена)

#### Для Ubuntu/Debian

**Шаг 1:** Скачайте корневой сертификат НУЦ Минцифры:

```bash
cd /opt/101slovo3/backend
mkdir -p certs
cd certs

# Скачайте сертификат
wget https://gu-st.ru/content/lending/russian_trusted_sub_ca.cer
wget https://gu-st.ru/content/lending/russian_trusted_root_ca.cer

# Конвертируйте в PEM формат
openssl x509 -inform DER -in russian_trusted_root_ca.cer -out russian_trusted_root_ca.pem
openssl x509 -inform DER -in russian_trusted_sub_ca.cer -out russian_trusted_sub_ca.pem
```

**Шаг 2:** Установите сертификаты в систему:

```bash
# Скопируйте сертификаты в системную директорию
sudo cp russian_trusted_root_ca.pem /usr/local/share/ca-certificates/
sudo cp russian_trusted_sub_ca.pem /usr/local/share/ca-certificates/

# Обновите кэш сертификатов
sudo update-ca-certificates
```

**Шаг 3:** Укажите путь к сертификату в `backend/.env`:

```env
GIGACHAT_VERIFY_SSL=True
GIGACHAT_CA_CERT_PATH=/etc/ssl/certs/ca-certificates.crt
```

**Шаг 4:** Перезапустите бэкенд:

```bash
cd /opt/101slovo3/backend
uvicorn app.main:app --reload
```

#### Для CentOS/RHEL

**Шаг 1:** Скачайте и установите сертификаты:

```bash
cd /opt/101slovo3/backend
mkdir -p certs
cd certs

wget https://gu-st.ru/content/lending/russian_trusted_sub_ca.cer
wget https://gu-st.ru/content/lending/russian_trusted_root_ca.cer

openssl x509 -inform DER -in russian_trusted_root_ca.cer -out russian_trusted_root_ca.pem
openssl x509 -inform DER -in russian_trusted_sub_ca.cer -out russian_trusted_sub_ca.pem

sudo cp russian_trusted_root_ca.pem /etc/pki/ca-trust/source/anchors/
sudo cp russian_trusted_sub_ca.pem /etc/pki/ca-trust/source/anchors/

sudo update-ca-trust
```

**Шаг 2:** Настройте `backend/.env`:

```env
GIGACHAT_VERIFY_SSL=True
GIGACHAT_CA_CERT_PATH=/etc/pki/tls/certs/ca-bundle.crt
```

#### Для macOS

**Шаг 1:** Скачайте сертификаты:

```bash
cd /opt/101slovo3/backend
mkdir -p certs
cd certs

curl -O https://gu-st.ru/content/lending/russian_trusted_sub_ca.cer
curl -O https://gu-st.ru/content/lending/russian_trusted_root_ca.cer

openssl x509 -inform DER -in russian_trusted_root_ca.cer -out russian_trusted_root_ca.pem
openssl x509 -inform DER -in russian_trusted_sub_ca.cer -out russian_trusted_sub_ca.pem
```

**Шаг 2:** Установите сертификаты в систему:

```bash
# Откройте Keychain Access
open -a "Keychain Access"

# Импортируйте сертификаты
# File -> Import Items -> выберите .pem файлы

# Или через командную строку:
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain russian_trusted_root_ca.pem
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain russian_trusted_sub_ca.pem
```

**Шаг 3:** Настройте `backend/.env`:

```env
GIGACHAT_VERIFY_SSL=True
GIGACHAT_CA_CERT_PATH=/opt/101slovo3/backend/certs/russian_trusted_root_ca.pem
```

#### Для Windows

**Шаг 1:** Скачайте сертификаты через браузер или PowerShell:

```powershell
cd C:\opt\101slovo3\backend
mkdir certs
cd certs

Invoke-WebRequest -Uri "https://gu-st.ru/content/lending/russian_trusted_sub_ca.cer" -OutFile "russian_trusted_sub_ca.cer"
Invoke-WebRequest -Uri "https://gu-st.ru/content/lending/russian_trusted_root_ca.cer" -OutFile "russian_trusted_root_ca.cer"
```

**Шаг 2:** Установите сертификаты:

```powershell
# Откройте MMC (Microsoft Management Console)
mmc

# File -> Add/Remove Snap-in -> Certificates -> Add -> Computer account -> Local computer
# Import certificates into Trusted Root Certification Authorities
```

**Шаг 3:** Настройте `backend/.env`:

```env
GIGACHAT_VERIFY_SSL=True
GIGACHAT_CA_CERT_PATH=C:\opt\101slovo3\backend\certs\russian_trusted_root_ca.cer
```

---

## Изменения в коде

### 1. Добавлена переменная `GIGACHAT_VERIFY_SSL`

**Файл:** `backend/app/config.py`

```python
GIGACHAT_VERIFY_SSL: bool = True  # Отключите для разработки (False)
```

### 2. Обновлён `gigachat.py`

**Файл:** `backend/app/services/llm/gigachat.py`

Теперь SSL контекст создаётся с учётом настройки:

```python
# Создаём SSL контекст с учётом настройки проверки
if settings.GIGACHAT_VERIFY_SSL:
    ssl_context = ssl.create_default_context()
else:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    logger.warning("⚠️ SSL verification disabled for GigaChat API")
```

Это изменение применено в двух местах:
- Метод `_refresh()` (получение OAuth токена)
- Метод `_make_request()` (вызов Chat API)

---

## Проверка работы

### 1. Проверьте логи бэкенда

При отключённой проверке SSL вы увидите:

```
⚠️ SSL verification disabled for GigaChat OAuth
⚠️ SSL verification disabled for GigaChat API
```

### 2. Проверьте работу API

```bash
# Запустите урок через фронтенд
# В логах бэкенда должно быть:
✅ GigaChat token refreshed successfully
🔍 GigaChat HTTP REQUEST
📥 GigaChat HTTP RESPONSE
Status: 200
```

### 3. Проверьте генерацию предложений

```bash
# Создайте новый урок
# В логах должно быть:
📝 Формирование target_words для группы 0
✅ LLM evaluation completed
```

---

## Рекомендации

### Для разработки

Используйте `GIGACHAT_VERIFY_SSL=False` для быстрого старта без установки сертификатов.

### Для продакшена

**Обязательно** установите корневые сертификаты НУЦ Минцифры и используйте `GIGACHAT_VERIFY_SSL=True`.

Это обеспечит:
- ✅ Безопасное соединение с GigaChat API
- ✅ Защиту от MITM атак
- ✅ Соответствие требованиям безопасности

---

## Частые проблемы

### Проблема 1: Сертификаты не помогают

**Симптом:** Ошибка SSL сохраняется после установки сертификатов

**Решение:**
1. Проверьте, что сертификаты установлены правильно:
   ```bash
   # Ubuntu/Debian
   ls -la /usr/local/share/ca-certificates/
   
   # CentOS/RHEL
   ls -la /etc/pki/ca-trust/source/anchors/
   ```

2. Обновите кэш сертификатов:
   ```bash
   # Ubuntu/Debian
   sudo update-ca-certificates --fresh
   
   # CentOS/RHEL
   sudo update-ca-trust extract
   ```

3. Перезапустите бэкенд

### Проблема 2: Неправильный путь к сертификату

**Симптом:** `FileNotFoundError: [Errno 2] No such file or directory`

**Решение:**
1. Проверьте путь в `GIGACHAT_CA_CERT_PATH`
2. Убедитесь, что файл существует:
   ```bash
   ls -la /path/to/cert.pem
   ```

### Проблема 3: Сертификат не в PEM формате

**Симптом:** Ошибка парсинга сертификата

**Решение:**
Конвертируйте сертификат в PEM формат:
```bash
openssl x509 -inform DER -in cert.cer -out cert.pem
```

---

## Статус

✅ Добавлена переменная `GIGACHAT_VERIFY_SSL`  
✅ Обновлён `gigachat.py` для поддержки отключения SSL  
✅ Обновлён `.env.example`  
✅ Создана документация по установке сертификатов  
✅ Проект успешно собирается  
✅ Готово к использованию

---

## Связанные файлы

- `backend/app/config.py` - добавлена переменная `GIGACHAT_VERIFY_SSL`
- `backend/app/services/llm/gigachat.py` - обновлена логика SSL
- `backend/.env.example` - добавлен пример настройки
- `docs/FIX_SSL_GIGACHAT.md` - этот документ

---

**Версия:** 1.24.0  
**Дата:** 2026-01-15
