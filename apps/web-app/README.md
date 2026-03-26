# web-app

Frontend application built with Vue 3 + Vite for the AI query system.

## Requirements

- Node.js >= 20
- npm

## Run locally

```bash
cd apps/web-app
npm install
npm run dev
```

Default local URL:

```text
http://localhost:5173
```

## Build

```bash
cd apps/web-app
npm install
npm run build
```

## Preview production build

```bash
cd apps/web-app
npm install
npm run preview
```

## API configuration

The app sends search requests from `src/composables/useSearch.js`.

Default API URL:

```text
http://localhost:8080/api/search
```

If you want to use another backend URL, create file `.env` in `apps/web-app`:

```dotenv
VITE_SEARCH_API_URL=http://localhost:8080/api/search
```

Example if your backend exposes another endpoint:

```dotenv
VITE_SEARCH_API_URL=http://localhost:8080/api/chat
```

## Scripts

- `npm run dev`: start development server
- `npm run build`: build for production
- `npm run preview`: preview built app
