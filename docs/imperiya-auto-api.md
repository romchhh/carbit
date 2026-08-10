# Імперія Авто — Public API v2

- **Документація (Swagger):** https://api.imperiya-auto.com.ua/api/v2/docs
- **OpenAPI JSON:** `docs/imperiya-auto-api.openapi.json` (експорт з `/api/v2/docs-json`)
- **Base URL:** `https://api.imperiya-auto.com.ua`
- **Авторизація:** заголовок `X-API-Key: <IMPERIYA_API_KEY>`

## Ендпоінти

### Оголошення (Cars)

| Метод | Шлях | Опис |
|-------|------|------|
| `GET` | `/api/v2/cars` | Список оголошень з фільтрацією та пагінацією |
| `GET` | `/api/v2/cars/{id}` | Деталі оголошення |
| `GET` | `/api/v2/cars/my` | Свої оголошення (paginated) |
| `GET` | `/api/v2/cars/my/{id}` | Деталі свого оголошення |
| `POST` | `/api/v2/cars` | Створити Ad у статусі DRAFT_API |
| `PATCH` | `/api/v2/cars/{id}` | Оновити Ad (лише DRAFT_API) |
| `DELETE` | `/api/v2/cars/{id}` | Видалити Ad (лише DRAFT_API) |

#### Query-параметри `GET /api/v2/cars`

| Параметр | Тип | Опис |
|----------|-----|------|
| `page` | number | Сторінка (default: 1) |
| `limit` | number | Розмір сторінки (default: 20, max ~50) |
| `makeId` | number | ID марки |
| `modelId` | number | ID моделі |
| `generationId` | number | Покоління |
| `configurationId` | number | Комплектація |
| `yearFrom` / `yearTo` | number | Рік випуску |
| `priceFrom` / `priceTo` | number | Ціна (USD у нашій інтеграції) |
| `mileageFrom` / `mileageTo` | number | Пробіг у **тисячах** км |
| `bodyTypeId` | number[] | Тип кузова |
| `transmissionId` | number[] | КПП |
| `engineTypeId` | number[] | Тип двигуна |
| `driveTypeId` | number[] | Привід |
| `colorId` | number[] | Колір |
| `regionId` | number[] | Регіон |
| `leasing` | boolean | Лізинг |
| `sortBy` | enum | `date`, `price_asc`, `price_desc`, `year_new`, `year_old`, `mileage` |

#### Відповідь `GET /api/v2/cars`

```json
{
  "data": [
    {
      "id": 51533,
      "url": "https://imperiya-auto.com.ua/listing/nissan-juke-51533",
      "title": "Nissan Juke",
      "productionYear": 2017,
      "make": "Nissan",
      "model": "Juke",
      "mileage": 60,
      "price": { "usd": 13800, "uah": 621622 },
      "images": [{ "url": "...", "mediumUrl": "...", "smallUrl": "..." }],
      "city": "Одеса",
      "region": "Одеська",
      "createdAt": "2026-08-10T15:24:16.713Z"
    }
  ],
  "pagination": {
    "totalPageCount": 13154,
    "totalOffersCount": 26308,
    "page": 1,
    "pageSize": 20
  }
}
```

> **Пробіг:** поле `mileage` — у тисячах км (60 → 60 000 км).  
> **Фото:** `images[].mediumUrl` — для карток у Carbit.

### Довідники (References)

| Метод | Шлях |
|-------|------|
| `GET` | `/api/v2/references/makes` |
| `GET` | `/api/v2/references/makes/{makeId}/models` |
| `GET` | `/api/v2/references/models/{modelId}/generations` |
| `GET` | `/api/v2/references/generations/{generationId}/configurations` |
| `GET` | `/api/v2/references/regions` |
| `GET` | `/api/v2/references/regions/{regionId}/cities` |
| `GET` | `/api/v2/references/body-types` |
| `GET` | `/api/v2/references/colors` |
| `GET` | `/api/v2/references/transmissions` |
| `GET` | `/api/v2/references/engine-types` |
| `GET` | `/api/v2/references/drive-types` |
| `GET` | `/api/v2/references/dealers` |
| `GET` | `/api/v2/references/imported-countries` |
| `GET` | `/api/v2/references/paintwork-conditions` |
| `GET` | `/api/v2/references/technical-states` |

## Інтеграція в Carbit

| Компонент | Шлях |
|-----------|------|
| HTTP-клієнт | `backend/app/services/imperiya/client.py` |
| Мапінг → `ListingOut` | `backend/app/services/imperiya/mapper.py` |
| Пошук | `backend/app/services/imperiya/service.py` |
| Multi-source | `backend/app/services/search/multi_source.py` |
| Env | `IMPERIYA_API_KEY` у `.env` |
| ID оголошення | `imperiya_{id}` |
| source | `imperiya` |
| UI label | «Імперія Авто» |
| Іконка | `frontend/public/icons/source-imperiya.png` (з `web-app-manifest-192x192.png`) |
