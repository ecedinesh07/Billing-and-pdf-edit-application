# BRD — Document Text Correction & Editor Platform

**Document Version:** 0.1  
**Status:** Draft for architecture/product review  
**Phases:** Phase 1 — Visual Document Editor; Phase 2 — Conversational Document Editor  
**Primary Stack:** Angular 20 + Python/FastAPI + PostgreSQL  
**Initial Hosting:** Firebase Hosting (Spark/free plan) for Angular frontend

---

## 1. Product Vision

Build a general-purpose document correction platform that allows a user to upload an existing document as a PDF or image, identify text within the document, correct only the required text, and download the corrected document while preserving the original visual appearance as closely as technically possible.

The platform must **not depend on predefined bill/invoice templates**.

It must support arbitrary document layouts such as petrol/fuel receipts, retail bills, restaurant bills, GST invoices, purchase invoices, hotel bills, utility bills, quotations, receipts, statements, and other printed documents.

The core product is a **Document Text Correction Engine**, not a template-based invoice generator.

### Core principle

> **Change only what the user explicitly edits. Preserve everything else.**

```text
Original Document + Edit Operations = Final Document
```

---

## 2. Phases

### Phase 1 — Visual Document Text Editor

Upload → Analyze → Display → Select text → Edit → Preview → Download

In scope: PDF/JPG/PNG upload, multi-page PDF, orientation detection, OCR, text extraction, bounding boxes, selection, inline edit, add/delete/search/replace, undo/redo, preview, export, localized reconstruction, basic font estimation, multilingual printed text.

Out of scope for Phase 1: conversational AI editing, template recognition, full table reconstruction, handwriting, auto tax/financial recalculation, document generation from scratch.

### Phase 2 — Conversational Document Editor

Split view: document preview + chat. Natural-language edits generate **edit operations**; the deterministic document engine executes them. Ambiguous matches require confirmation.

---

## 3. Functional Requirements (summary)

| ID | Requirement |
|---|---|
| FR-001 | Document upload (PDF/JPG/PNG), validation, progress, unique ID, original preserved |
| FR-002 | Classification: text PDF vs scanned PDF vs image |
| FR-003 | Image preprocessing without overwriting original |
| FR-004 | OCR with text, page, bbox, confidence, language |
| FR-005 | Text selection aligned under zoom |
| FR-006 | Text editing with local style approximation |
| FR-007 | Localized visual reconstruction (edit mask; no global regen) |
| FR-008 | PDF text editing preserving unrelated objects |
| FR-009 | Undo/redo as operations |
| FR-010 | Preview / compare before download |
| FR-011 | Export preserving format, pages, dimensions |

---

## 4. Non-Functional

- Async OCR for large documents; responsive UI
- Pixel/coordinate accuracy; retain OCR confidence
- Preserve dimensions/resolution; avoid unnecessary recompression
- Treat uploads as untrusted; validate MIME + signature; authorize by document ID
- Do not log full document contents or sensitive invoice text

---

## 5. Product Boundaries

Not intended to: generate fake documents; modify without authorization; auto-alter financial totals; fabricate supporting info; modify signatures/seals/IDs; bypass document security.

---

## 6. Architecture

```text
Angular 20  --HTTPS/REST-->  FastAPI
                              |-- Document API
                              |-- OCR Service
                              |-- Edit Service
                              v
                     Normalized Document Model
                              |
                 PostgreSQL + Object Storage
                              |
                     Rendering / Export
```

**Frontend hosting:** Firebase Hosting (Spark OK for Angular).  
**Backend:** FastAPI + PostgreSQL on separate infrastructure initially (Cloud Functions/Cloud Run require Blaze/billing).

Local: Angular `:4200`, FastAPI `:8000`, PostgreSQL `:5432`.

---

## 7. Data model

Entities: User, Document, DocumentPage, TextBlock, EditOperation, Conversation, ConversationMessage, ExportJob.

Edit operations are immutable (`replace_text`, `insert_text`, `delete_text`, …).

---

## 8. Development order

1. Angular shell → 2. Upload → 3. FastAPI upload API → 4. PDF text extraction → 5. OCR → 6. Normalized model → 7. Viewer + selection → 8. Edit engine → 9. Localized reconstruction → 10. Preview/export → 11. Pixel tests → 12. Undo/search → 13–15. Phase 2 conversation.

---

## 9. Open decisions (before production)

Max upload size/pages, extra image formats, image→PDF export, retention, auth for MVP, OCR engine, font strategy, table editing phase, handwriting, languages, comparison UI, watermark/label, backend/Postgres hosts, concurrency limits, Phase 2 quotas.

See also: `.cursor/rules/document-editor.mdc` for mandatory engineering invariants.

---

## 10. Final invariant

> The user's uploaded document is the source of truth. AI and OCR may understand the document, but only controlled edit operations may modify it.
