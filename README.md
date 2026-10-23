# Tanglish SRT Studio — deployable full-stack project

This package includes the webpage AND FastAPI backend. It will not work as a static-only website.

## Deploy to Render
1. Upload all files/folders in this project to a GitHub repository.
2. In Render choose **New + → Blueprint**, connect the repo, and let Render use `render.yaml`.
   Or choose **New + → Web Service**:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. In the service's Environment settings, add `OPENAI_API_KEY` with your own OpenAI API key.
4. Deploy/redeploy.
5. Visit `https://YOUR-SERVICE.onrender.com/api/health`. Expected `ok: true`; `api_key_configured` should be `true`.
6. Open the service root URL and test upload.

## Security
Never put the API key in `public/index.html`, GitHub, or a client-side JavaScript file. Configure it only in the hosting provider's secret Environment settings. The key is not included in this ZIP. API usage may cost money.

## Local run
Python 3.11+, then:
```bash
pip install -r requirements.txt
```
Set `OPENAI_API_KEY` as an environment variable and run:
```bash
uvicorn main:app --reload --port 8000
```
Open `http://127.0.0.1:8000`.

25 MB upload cap; segment-level SRT timing. For public use, add rate limits/authentication.
