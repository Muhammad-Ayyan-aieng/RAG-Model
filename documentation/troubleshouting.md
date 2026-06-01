# Troubleshooting: Common Issues and Solutions

## Overview

This document covers common issues encountered during development, deployment, and operation.

## Installation Issues

### Issue: `ModuleNotFoundError: No module named 'src'`

**Cause:** Running from wrong directory

**Solution:** Run from project root, not inside src folder

```bash
cd rag-assistant
python -m src.main
Issue: sentence-transformers download slow
Cause: First download fetches 90MB model

Solution: Be patient (5-10 minutes) or pre-download

Issue: NumPy version conflict
Cause: ChromaDB incompatible with NumPy 2.0

Solution: Pin NumPy to 1.26.4 in requirements.txt

API Issues
Issue: GROQ_API_KEY not set
Cause: Missing environment variable

Solution: Create .env file with GROQ_API_KEY=gsk_...

Issue: Rate limit exceeded (429)
Cause: Exceeded Groq free tier (1,000 requests/day)

Solution: Wait or upgrade Groq account

Issue: Documents not found in search
Possible Causes:

Upload failed silently

Distance threshold too strict

Chunks not properly embedded

Solutions:

Check upload response for errors

Lower threshold from 0.7 to 0.5 temporarily

Verify ChromaDB has data (/health endpoint)

Deployment Issues (Hugging Face)
Issue: Space stuck in "Starting..."
Cause: App not binding to port 7860

Solution: Ensure Dockerfile uses EXPOSE 7860 and CMD uses --port 7860

Issue: Data lost after restart
Cause: Free tier uses ephemeral storage

Solutions:

Accept for demos (upload fresh)

Upgrade to paid persistent storage ($5/month)

Implement backup to Dataset

Issue: Build fails with "COPY frontend/ not found"
Cause: Dockerfile expects frontend folder

Solution: Create empty frontend folder or remove COPY line

Authentication Issues
Issue: 401 Unauthorized on admin endpoints
Cause: Missing or wrong x-admin-password header

Solution: Include header with correct password from .env

Issue: Public users can see admin panel
Cause: Admin page not password-protected

Solution: Admin panel calls /documents/ on load to verify password

Database Issues
Issue: ChromaDB out of memory
Cause: Too many chunks loaded simultaneously

Solution: Increase RAM or reduce batch size in ingestion

Issue: Search results are poor quality
Possible Causes:

Chunk size too small/large

Distance threshold too strict

Poor document quality

Solutions:

Adjust CHUNK_SIZE (try 300 or 800)

Loosen threshold to 0.8

Clean documents before upload

Frontend Issues
Issue: CORS errors in browser
Cause: Frontend and backend on different ports/domains

Solution: Configure CORS in src/main.py to allow frontend origin

Issue: Upload fails with no error
Cause: File size exceeds limit or wrong format

Solution: Check public limits (5MB, PDF/TXT only)

Performance Issues
Issue: Upload takes too long
Cause: Large document or slow embedding

Solutions:

Split large PDFs before upload

Use async processing for production

Optimize chunk size

Issue: Query response slow
Possible Causes:

Large ChromaDB collection

Complex question

LLM API latency

Solutions:

Limit top_k to 3

Implement caching

Use faster LLM model

Debugging Checklist
Issue	Check
App won't start	Check .env has all keys
Upload fails	Check file size and type
No answers	Check ChromaDB has data
Wrong answers	Check chunk quality
Delete fails	Check admin password header
Getting Help
Resource	Link
FastAPI docs	fastapi.tiangolo.com
ChromaDB docs	docs.trychroma.com
Groq console	console.groq.com
Hugging Face docs	huggingface.co/docs
Key Takeaway
Most issues fall into categories:

Configuration (.env, Dockerfile, README.md)

Dependencies (versions, conflicts)

Deployment (ports, secrets, storage)

Code bugs (use logs to debug)

Start with logs, check common causes, then escalate to documentation.