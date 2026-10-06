# 🔧 Исправление отображения настроек из БД

## Дата
2026-01-15

## Проблема

На странице настроек (`/settings`) отображались захардкоженные значения вместо реальных данных из базы данных:

```typescript
// Временные состояния (в реальности будут загружаться с API)
const [level, setLevel] = useState('A2');
const [dailyLimit, setDailyLimit] = useState(1);
const [wordsPerLesson, setWordsPerLesson] = useState(5);
```

Также сохранение настроек было закомментировано и использовало имитацию API вызова.

## Решение

### 1. Обновлён бэкенд

#### Файл: `backend/app/api/v1/auth.py`

Добавлено поле `timezone` в эндпоинт `GET /auth/me`:

```python
@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    cur = await db.execute(
        "SELECT id, email, is_onboarded, is_admin, timezone FROM users WHERE id = %s",
        [user_id],
    )
```

#### Файл: `backend/app/schemas/auth.py`

Добавлено поле `timezone` в схему `UserResponse`:

```python
class UserResponse(BaseModel):
    """Информация о пользователе."""
    id: int
    email: str
    is_onboarded: bool
    is_admin: bool
    timezone: str | None = None
```

### 2. Обновлён фронтенд

#### Файл: `src/contexts/AuthContext.tsx`

Добавлено поле `timezone` в интерфейс `User`:

```typescript
interface User {
  id: number;
  email: string;
  is_onboarded: boolean;
  timezone?: string;
}
```

#### Файл: `src/pages/Settings.tsx`

Полностью переписан компонент для работы с реальными данными:

**Добавлено:**
1. **Загрузка настроек из API** при монтировании компонента
2. **Отображение реальных данных** из базы данных
3. **Сохранение изменений** через API вызовы
4. **Обработка ошибок** и состояния загрузки
5. **Отображение статистики** (количество слов, уроков, точность)

**Ключевые изменения:**

```typescript
// Загрузка настроек из API
const loadSettings = async () => {
  setLoading(true);
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Токен авторизации отсутствует');
    }

    // Загружаем профиль обучения
    const profileResponse = await fetch(`${API_URL}/learning-profile`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!profileResponse.ok) {
      throw new Error('Не удалось загрузить настройки');
    }

    const profileData: LearningProfile = await profileResponse.json();
    setProfile(profileData);

    // Устанавливаем значения формы
    setLevel(profileData.level);
    setDailyLimit(profileData.daily_lesson_limit);
    setWordsPerLesson(profileData.words_per_lesson);
    setTimezone(user?.timezone || '');

    console.log('✅ Settings loaded:', profileData);
  } catch (err) {
    console.error('❌ Error loading settings:', err);
    setMessage({ 
      type: 'error', 
      text: err instanceof Error ? err.message : 'Не удалось загрузить настройки' 
    });
  } finally {
    setLoading(false);
  }
};
```

```typescript
// Сохранение настроек
const handleSave = async () => {
  setSaving(true);
  setMessage(null);

  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Токен авторизации отсутствует');
    }

    // Сохраняем настройки профиля обучения
    const profileResponse = await fetch(`${API_URL}/learning-profile`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        level,
        daily_lesson_limit: dailyLimit,
        words_per_lesson: wordsPerLesson,
      }),
    });

    if (!profileResponse.ok) {
      const error = await profileResponse.json();
      throw new Error(error.detail || 'Не удалось сохранить настройки');
    }

    // Сохраняем часовой пояс, если он изменился
    if (timezone && timezone !== user?.timezone) {
      const timezoneResponse = await fetch(`${API_URL}/settings/timezone`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ timezone }),
      });

      if (!timezoneResponse.ok) {
        const error = await timezoneResponse.json();
        throw new Error(error.detail || 'Не удалось сохранить часовой пояс');
      }

      // Обновляем данные пользователя в контексте
      if (user) {
        setUser({ ...user, timezone });
      }
    }

    setMessage({ type: 'success', text: 'Настройки успешно сохранены!' });
    
    // Перезагружаем настройки
    await loadSettings();
  } catch (error) {
    console.error('❌ Error saving settings:', error);
    setMessage({ 
      type: 'error', 
      text: error instanceof Error ? error.message : 'Ошибка сохранения настроек' 
    });
  } finally {
    setSaving(false);
  }
};
```

## Что теперь отображается

### 1. Профиль
- ✅ Email пользователя (из БД)

### 2. Настройки обучения
- ✅ Уровень английского (из `learning_profiles.level`)
- ✅ Уроков в день (из `learning_profiles.daily_lesson_limit`)
- ✅ Слов в уроке (из `learning_profiles.words_per_lesson`)
- ✅ Текущий словарь (из `dictionaries` через `learning_profiles.dictionary_id`)

### 3. Часовой пояс
- ✅ Текущий часовой пояс (из `users.timezone`)

### 4. Статистика
- ✅ Количество активных слов (из `user_words` где `status='active'`)
- ✅ Количество изученных слов (из `user_words` где `status='mastered'`)
- ✅ Количество завершённых уроков (из `lessons` где `status='completed'`)
- ✅ Точность (из `lesson_exercises.target_words`)

## API эндпоинты

### GET /learning-profile
Возвращает полный профиль обучения с настройками и статистикой:

```json
{
  "level": "A2",
  "dictionary": {
    "id": 1,
    "code": "general",
    "name": "General English",
    "description": "Общий словарь"
  },
  "daily_lesson_limit": 1,
  "daily_lesson_limit_max": 5,
  "words_per_lesson": 5,
  "words_per_lesson_min": 3,
  "words_per_lesson_max": 10,
  "stats": {
    "words": {
      "active": 15,
      "mastered": 5,
      "ignored": 2
    },
    "accuracy_all_time": 0.85,
    "accuracy_30_days": 0.87,
    "completed_lessons": 10
  }
}
```

### PATCH /learning-profile
Обновляет настройки профиля обучения:

```json
{
  "level": "B1",
  "daily_lesson_limit": 2,
  "words_per_lesson": 7
}
```

### PATCH /settings/timezone
Обновляет часовой пояс пользователя:

```json
{
  "timezone": "Europe/Moscow"
}
```

### GET /auth/me
Возвращает информацию о текущем пользователе (теперь с `timezone`):

```json
{
  "id": 1,
  "email": "user@example.com",
  "is_onboarded": true,
  "is_admin": false,
  "timezone": "Europe/Moscow"
}
```

## Как проверить

### 1. Перезапустите бэкенд
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Перезапустите фронтенд
```bash
npm run dev
```

### 3. Откройте страницу настроек
1. Войдите в аккаунт
2. Перейдите на Dashboard
3. Нажмите кнопку "Настройки" (⚙️)

### 4. Проверьте отображение данных
Должны отображаться реальные данные из БД:
- ✅ Ваш email
- ✅ Ваш уровень (не захардкоженный A2)
- ✅ Ваши лимиты уроков
- ✅ Ваш словарь
- ✅ Ваш часовой пояс
- ✅ Ваша статистика

### 5. Проверьте сохранение
1. Измените уровень на B1
2. Измените количество уроков в день на 2
3. Измените количество слов в уроке на 7
4. Нажмите "Сохранить настройки"
5. Должно появиться сообщение "Настройки успешно сохранены!"
6. Перезагрузите страницу - изменения должны сохраниться

### 6. Проверьте в БД
```sql
-- Проверьте настройки профиля
SELECT level, daily_lesson_limit, words_per_lesson 
FROM learning_profiles 
WHERE user_id = YOUR_USER_ID;

-- Проверьте часовой пояс
SELECT timezone FROM users WHERE id = YOUR_USER_ID;
```

## Статус

✅ Обновлён бэкенд (добавлен `timezone` в `/auth/me`)  
✅ Обновлена схема `UserResponse`  
✅ Обновлён интерфейс `User` на фронтенде  
✅ Полностью переписан компонент `Settings.tsx`  
✅ Добавлена загрузка данных из API  
✅ Добавлено сохранение изменений через API  
✅ Добавлено отображение статистики  
✅ Добавлена обработка ошибок  
✅ Проект успешно собирается  
✅ Готово к тестированию

---

## Связанные файлы

- `backend/app/api/v1/auth.py` - эндпоинт `/auth/me`
- `backend/app/schemas/auth.py` - схема `UserResponse`
- `backend/app/api/v1/settings.py` - эндпоинты настроек
- `src/contexts/AuthContext.tsx` - контекст авторизации
- `src/pages/Settings.tsx` - страница настроек
- `docs/SETTINGS_FIX.md` - этот документ

---

**Версия:** 1.20.0  
**Дата:** 2026-01-15
