# BRD — Document Text Correction & Editor Platform

**Document Version:** 0.1  
**Status:** Draft for architecture/product review  
**Phases:** Phase 1 — Visual Document Editor; Phase 2 — Conversational Document Editor  
**Primary Stack:** Angular 20 + Python/FastAPI + PostgreSQL  
**Initial Hosting:** Firebase Hosting (Spark/free plan) for Angular frontend

---

# 1. Business Requirements Document (BRD)

## 1.1 Product Vision

Build a general-purpose document correction platform that allows a user to upload an existing document as a PDF or image, identify text within the document, correct only the required text, and download the corrected document while preserving the original visual appearance as closely as technically possible.

The platform must **not depend on predefined bill/invoice templates**.

It must support arbitrary document layouts such as:

- Petrol/fuel receipts
- Retail bills
- Restaurant bills
- GST invoices
- Purchase invoices
- Hotel bills
- Utility bills
- Quotations
- Receipts
- Statements
- Other printed documents

The core product is therefore a **Document Text Correction Engine**, not a template-based invoice generator.

---

## 1.2 Problem Statement

Users frequently receive documents containing small mistakes such as:

- Spelling errors
- Incorrect name
- Incorrect address
- Incorrect email
- Incorrect phone number
- Incorrect date
- Incorrect receipt/invoice number
- Incorrect product description
- Incorrect quantity/value
- Other text/value errors

Recreating the entire document is inconvenient because the user wants to preserve the original layout, branding, formatting, paper appearance, and surrounding content.

The product should allow the user to correct the required text without rebuilding the entire document.

---

## 1.3 Target User Experience

### Phase 1

```text
Upload PDF / Image
        ↓
Analyze document
        ↓
Display document
        ↓
Select text
        ↓
Edit selected text
        ↓
Preview
        ↓
Download corrected document
```

### Phase 2

```text
Upload document
        ↓
Document preview + Chat
        ↓
User:
"Change the name from ABC to XYZ"
        ↓
System identifies the target text
        ↓
Apply localized edit
        ↓
Show preview
        ↓
User:
"Change the phone number too"
        ↓
Apply second edit
        ↓
Final preview
        ↓
Download
```

---

## 1.4 Core Product Principle

### Preserve the original document.

The system should follow:

> **Change only what the user explicitly edits. Preserve everything else.**

For image documents, pixels outside the approved edit region should remain unchanged wherever technically possible.

For PDF documents, unrelated PDF objects should remain unchanged wherever technically possible.

The system must not regenerate the entire document unnecessarily.

---

# 2. Scope

## 2.1 Phase 1 — Visual Document Text Editor

### In scope

- PDF upload
- JPG/JPEG upload
- PNG upload
- Image/document preview
- Multi-page PDF support
- Document orientation detection
- OCR for image/scanned documents
- Text extraction for text-based PDFs
- Text bounding boxes
- Text selection
- Inline text editing
- Add text
- Delete text
- Search text
- Replace text
- Undo/redo
- Edit history
- Preview before download
- Export to original or supported format
- Background preservation
- Localized text reconstruction
- Basic font/style estimation
- Multilingual printed text support
- Error handling
- Document validation

### Phase 1 does not require

- AI conversational editing
- Complex invoice template recognition
- Full table reconstruction
- Handwriting editing
- Automatic financial calculations
- Automatic tax recalculation
- Document generation from scratch
- General image-generation functionality

---

# 3. Phase 2 — Conversational Document Editor

## 3.1 Goal

Provide a ChatGPT-style editing experience where the user can describe document changes using natural language.

Example:

> Change the name from ABC Technologies to XYZ Technologies.

The UI should show:

```text
┌─────────────────────────┬────────────────────────────┐
│                         │                            │
│     Document Preview    │       Conversation         │
│                         │                            │
│     [Edited Document]   │ User: Change ABC to XYZ   │
│                         │                            │
│                         │ AI: I found ABC on page 1 │
│                         │     and changed it to XYZ │
│                         │                            │
└─────────────────────────┴────────────────────────────┘
```

The preview can be positioned left or right depending on the final UX decision.

---

## 3.2 Phase 2 Conversational Capabilities

Examples:

- "Change ABC to XYZ."
- "Correct the email address."
- "Change the phone number to 9876543210."
- "Replace Chennai with Bengaluru."
- "Change the date to 10/10/2026."
- "Undo the last change."
- "Show me what changed."
- "Apply the same correction on page 3."

The system must identify the intended target before applying an ambiguous change.

---

# 4. Functional Requirements

## FR-001 — Document Upload

The system shall allow users to upload supported documents.

Supported initial formats:

- PDF
- JPG/JPEG
- PNG

### Acceptance Criteria

- User can select a supported file.
- Unsupported files are rejected.
- File size limits are enforced.
- Upload progress is displayed.
- Upload errors are displayed clearly.
- Original file is stored without modification.
- A unique document ID is generated.

---

## FR-002 — Document Classification

The system shall determine whether a document is:

- Text-based PDF
- Scanned/image PDF
- Image document

### Acceptance Criteria

- Text-based PDFs use PDF text extraction where possible.
- Scanned PDFs use OCR.
- Image uploads use image preprocessing + OCR.
- The system does not unnecessarily OCR a high-quality text PDF.

---

## FR-003 — Image Preprocessing

The system shall preprocess photographed/scanned documents where required.

Potential operations:

- Rotation correction
- Deskew
- Perspective correction
- Noise reduction
- Contrast improvement
- Shadow reduction
- Resolution normalization

### Acceptance Criteria

- Original image remains preserved.
- Preprocessing creates a working representation.
- The original source is never overwritten.
- Preprocessing does not modify unrelated content in the final output.

---

## FR-004 — OCR

The system shall extract text and location information from image/scanned documents.

OCR output shall contain at minimum:

- Text
- Page
- Bounding box
- Confidence
- Language when available

Example:

```json
{
  "text": "H5429",
  "page": 1,
  "bbox": [280, 200, 360, 225],
  "confidence": 0.97
}
```

### Acceptance Criteria

- OCR text is displayed in the document editor.
- Bounding boxes map correctly to the document.
- Low-confidence OCR is identified.
- OCR failure does not corrupt the original document.

---

## FR-005 — Text Selection

Users shall be able to select detected text.

### Acceptance Criteria

- Selected text is visually highlighted.
- Correct page/coordinate is identified.
- Selection works for PDF text and OCR text.
- Selection remains aligned when zooming.

---

## FR-006 — Text Editing

Users shall be able to change selected text.

### Acceptance Criteria

- Existing text can be edited.
- Replacement text stays within the intended region where possible.
- Font/style/size/rotation are preserved or closely approximated.
- Text does not unexpectedly move unrelated content.
- Edit can be cancelled.

---

## FR-007 — Localized Visual Reconstruction

For image/scanned documents, only the edited area shall be reconstructed.

### Acceptance Criteria

- The system creates an edit mask.
- Original pixels outside the edit region are preserved.
- The replacement text blends with the local document appearance.
- No unnecessary white rectangle is introduced.
- No global image regeneration is performed.
- Document perspective is respected.
- Replacement text follows the local baseline/orientation.

---

## FR-008 — PDF Text Editing

For text-based PDFs:

### Acceptance Criteria

- Existing text objects are detected.
- Unmodified PDF content is preserved where possible.
- Only the affected text region/object is changed.
- PDF page size remains unchanged.
- Page order remains unchanged.
- Images and unrelated graphics remain unchanged.

---

## FR-009 — Undo / Redo

### Acceptance Criteria

- Every edit is represented as an operation.
- Undo reverses the latest edit.
- Redo reapplies the edit.
- Multiple edits can be undone/redone.
- Original source remains recoverable.

---

## FR-010 — Preview

### Acceptance Criteria

- User can preview the corrected document before download.
- Original and edited versions can be compared.
- Changes can be visually reviewed.
- User can cancel edits before final export.

---

## FR-011 — Export

### Acceptance Criteria

- User can download the corrected document.
- PDF input produces PDF output.
- Image input can produce image output.
- Multi-page documents remain multi-page.
- Page dimensions are preserved.
- Output is not unnecessarily recompressed.
- Export failure does not lose the original.

---

# 5. Phase 2 User Stories

## US-201 — Conversational Edit

**As a user**, I want to describe a correction in natural language so that I do not need to manually locate the text.

### Acceptance Criteria

- User can enter a natural-language edit request.
- System identifies the target text.
- System identifies page/location.
- System proposes the change when ambiguity exists.
- User can approve/reject the change.
- Preview updates after approval.

---

## US-202 — Conversational Name Change

**Example:**

> Change the name from ABC to XYZ.

### Acceptance Criteria

- System searches the document for ABC.
- If one unique match exists, it can propose the change.
- If multiple matches exist, the system asks which occurrence.
- Change is applied only after sufficient confidence/confirmation.
- Preview displays the result.

---

## US-203 — Conversational Undo

**Example:**

> Undo that change.

### Acceptance Criteria

- Latest operation is identified.
- Operation is reverted.
- Preview is updated.
- Earlier operations remain intact.

---

## US-204 — Conversational Multi-Step Editing

**Example:**

```text
User: Change ABC to XYZ.
User: Also change Chennai to Bengaluru.
User: Change the phone number.
```

### Acceptance Criteria

- Each operation is tracked independently.
- User can undo one operation.
- User can undo all changes.
- Preview reflects current operation state.

---

# 6. Non-Functional Requirements

## Performance

- Initial preview should load quickly for normal documents.
- OCR should run asynchronously for large/scanned documents.
- UI must remain responsive during processing.
- Large files must not block the browser unnecessarily.

## Accuracy

- Text location accuracy is critical.
- Visual replacement accuracy is critical.
- OCR confidence must be retained.
- Low-confidence operations should require confirmation.

## Quality

- Preserve original dimensions.
- Preserve image resolution where possible.
- Avoid unnecessary recompression.
- Preserve PDF structure where possible.
- Avoid global regeneration.

## Security

- Uploaded documents must be treated as user-provided untrusted content.
- Do not execute JavaScript embedded in uploaded PDFs.
- Do not execute uploaded document code.
- Sanitize file names.
- Validate MIME type and file signature.
- Limit file size and page count.
- Use temporary processing storage.
- Delete temporary files according to retention policy.
- Never expose another user's document by ID.

---

# 7. Important Product Boundary

The product is a **document correction/editor tool**.

It is not intended to:

- Generate fake documents from scratch.
- Modify documents without user authorization.
- Hide the fact that a document was altered where disclosure is legally/business required.
- Automatically alter financial totals without explicit user action.
- Automatically fabricate supporting information.
- Automatically modify signatures, seals, stamps, or identity documents.
- Bypass document security controls.
- Remove audit/security controls from protected documents.

The system should preserve the original document and maintain an edit-operation history.

---

# 8. Cursor / Claude Code Development Rules

Create a project-level rule file such as:

```text
.cursor/rules/document-editor.mdc
```

or the equivalent Claude Code project instruction file.

## Strict Rules

### Rule 1 — Preserve Original

NEVER overwrite the original uploaded document.

Always create:

```text
original
working representation
edit operations
final output
```

---

### Rule 2 — Localized Editing Only

NEVER regenerate the entire image/document when only one text region is being edited.

Only modify the intended region.

---

### Rule 3 — No Global Image Generation

Do not use a generative image model to regenerate the complete bill/invoice/receipt.

Use localized reconstruction/inpainting/compositing only where required.

---

### Rule 4 — Preserve Unedited Content

Do not modify:

- logos
- images
- borders
- tables
- background
- unrelated text
- paper texture
- shadows
- document dimensions

unless explicitly requested.

---

### Rule 5 — Never Use White Rectangle Replacement as the Default

Do not implement:

```text
cover text with white rectangle
+
write replacement
```

unless the original region is actually a plain white background and the strategy has been explicitly selected.

---

### Rule 6 — Coordinate-Based Editing

Every text edit must retain:

- page number
- bounding box
- original text
- replacement text
- font/style information where available
- rotation
- language/direction where available

---

### Rule 7 — Operation-Based Architecture

Do not directly mutate the master document for every edit.

Represent edits as operations:

```json
{
  "type": "replace_text",
  "page": 1,
  "blockId": "block-123",
  "oldText": "ABC",
  "newText": "XYZ"
}
```

---

### Rule 8 — Ambiguous Edits

Never silently modify multiple matching values when the user request is ambiguous.

Example:

> Change 2500 to 3000

If `2500` appears three times, ask for clarification or present the matches.

---

### Rule 9 — OCR Confidence

Never treat low-confidence OCR as guaranteed truth.

Store:

```text
ocrConfidence
```

and request confirmation for uncertain edits.

---

### Rule 10 — No Financial Auto-Calculation

Do not automatically change totals, tax, GST, quantity, or calculations because another field changed.

Example:

Changing quantity from 2 to 3 must NOT automatically change the total unless a future explicit calculation feature is enabled and the user requests it.

---

### Rule 11 — Multilingual Support

Do not assume English.

The document model must support:

- Unicode
- language
- RTL/LTR direction
- complex script shaping
- mixed-language documents

---

### Rule 12 — Tests Are Mandatory

Every editing-engine change must include tests for:

- text PDF
- scanned PDF
- JPG
- PNG
- multi-page PDF
- multilingual text
- multiple matching values
- undo/redo
- export

---

### Rule 13 — Do Not Add Dependencies Without Review

Before adding a PDF/OCR/image library:

1. Verify license.
2. Verify maintenance status.
3. Verify browser/server compatibility.
4. Verify Angular/Python compatibility.
5. Verify commercial usage rights.
6. Document why the dependency is required.

---

### Rule 14 — Keep Frontend and Backend Responsibilities Separate

Angular handles:

- UI
- preview
- selection
- editing controls
- conversation UI
- state presentation

Python handles:

- PDF processing
- OCR
- image processing
- document analysis
- rendering/export
- validation

---

### Rule 15 — No Business Logic Duplication

Do not duplicate document-processing logic in Angular and Python.

The backend is the authoritative document-processing layer.

---

# 9. Project Knowledge for Cursor / Claude Code

## Product

A general-purpose document text correction platform.

## Primary use cases

```text
PDF → edit text → PDF
Image → OCR → edit text → Image
Image → OCR → edit text → PDF
PDF → edit text → PDF
```

## Phase 1

Visual editor.

## Phase 2

Conversational editor with document preview.

## Input

- PDF
- JPG/JPEG
- PNG

## Core processing

```text
PDF text extraction
OCR
Image preprocessing
Text localization
Font/style estimation
Localized reconstruction
PDF/image export
```

## Core principle

```text
Original Document
+
Edit Operations
=
Final Document
```

## Technology

```text
Frontend: Angular 20
Backend: Python + FastAPI
Database: PostgreSQL
PDF: PyMuPDF
OCR: Pluggable OCR engine
Storage: Object storage
Hosting: Firebase Hosting initially
```

## Data model

Core entities:

```text
User
Document
DocumentPage
TextBlock
EditOperation
Conversation
ConversationMessage
ExportJob
```

---

# 10. Technical Architecture

```text
                         Angular 20
                              |
                         HTTPS / REST
                              |
                              v
                    +--------------------+
                    |     FastAPI        |
                    +--------------------+
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
        Document API     OCR Service     Edit Service
              |               |               |
              +---------------+---------------+
                              |
                              v
                  Normalized Document Model
                              |
                 +------------+------------+
                 |                         |
                 v                         v
           PostgreSQL                Object Storage
        metadata/operations          original/output
                 |                         |
                 +------------+------------+
                              |
                              v
                    Rendering / Export
                              |
                              v
                        Final Document
```

---

# 11. Frontend Architecture

Recommended Angular structure:

```text
src/app/
├── core/
│   ├── auth/
│   ├── api/
│   ├── guards/
│   └── interceptors/
│
├── features/
│   ├── upload/
│   ├── document-editor/
│   ├── document-viewer/
│   ├── text-editor/
│   ├── preview/
│   ├── export/
│   └── conversation/        # Phase 2
│
├── shared/
│   ├── components/
│   ├── models/
│   └── utilities/
│
└── app.routes.ts
```

Prefer modern Angular patterns:

- Standalone components
- Signals where appropriate
- Typed services
- Strict TypeScript
- Lazy-loaded features
- Reactive state management where needed

---

# 12. Backend Architecture

Recommended Python structure:

```text
backend/
├── app/
│   ├── api/
│   │   ├── documents.py
│   │   ├── uploads.py
│   │   ├── edits.py
│   │   └── exports.py
│   │
│   ├── domain/
│   │   ├── documents/
│   │   ├── edits/
│   │   └── ocr/
│   │
│   ├── services/
│   │   ├── pdf_service.py
│   │   ├── ocr_service.py
│   │   ├── image_service.py
│   │   ├── edit_service.py
│   │   └── export_service.py
│   │
│   ├── repositories/
│   ├── models/
│   ├── schemas/
│   └── main.py
│
├── tests/
├── requirements.txt
└── Dockerfile
```

---

# 13. Normalized Document Model

The editor must not depend directly on raw PDF/OCR output.

Example:

```json
{
  "documentId": "doc-123",
  "sourceType": "image",
  "pages": [
    {
      "pageNumber": 1,
      "width": 1200,
      "height": 3000,
      "blocks": [
        {
          "id": "block-001",
          "type": "text",
          "text": "Receipt No.",
          "bbox": [100, 500, 300, 540],
          "language": "en",
          "direction": "ltr",
          "confidence": 0.99
        }
      ]
    }
  ]
}
```

---

# 14. Edit Operation Model

Every modification should be represented as an immutable operation.

Example:

```json
{
  "operationId": "op-001",
  "documentId": "doc-123",
  "type": "replace_text",
  "page": 1,
  "blockId": "block-001",
  "oldText": "H5429",
  "newText": "H5439",
  "bbox": [300, 500, 400, 540],
  "createdAt": "2026-10-07T00:00:00Z"
}
```

Future operation types:

```text
replace_text
insert_text
delete_text
move_text
resize_text
rotate_text
```

---

# 15. PostgreSQL Initial Schema

Recommended logical tables:

```text
users
documents
document_pages
text_blocks
edit_operations
exports
conversations
conversation_messages
```

### documents

```text
id
user_id
original_filename
source_type
mime_type
page_count
original_storage_key
created_at
updated_at
```

### text_blocks

```text
id
document_id
page_id
text
x
y
width
height
font_family
font_size
font_weight
rotation
language
direction
ocr_confidence
```

### edit_operations

```text
id
document_id
page_id
block_id
operation_type
old_value
new_value
bbox
status
created_at
```

---

# 16. Phase 2 Conversation Architecture

```text
Angular Chat UI
      |
      v
Conversation API
      |
      v
Intent / Edit Parser
      |
      v
Document Search
      |
      v
Candidate Matches
      |
      +---- one confident match ----> Edit Operation
      |
      +---- multiple matches --------> Ask User
      |
      +---- low confidence ----------> Ask Confirmation
      |
      v
Rendering Engine
      |
      v
Updated Preview
```

The conversation engine must never directly manipulate pixels.

It generates an **edit operation**.

The document engine executes the operation.

This separation is critical.

---

# 17. Phase 2 Example

User:

> Change the name from ABC to XYZ.

System:

```text
I found "ABC" on page 1.

ABC → XYZ

[Apply] [Cancel]
```

After applying:

```text
Edit applied successfully.

[Undo]
```

This provides a controlled editing workflow rather than blindly applying LLM output.

---

# 18. AI Boundary

AI may be used for:

- Understanding user instructions
- Finding candidate text
- Classifying document content
- Detecting ambiguity
- Suggesting corrections
- Conversational interaction

AI must NOT be the authoritative source for:

- Final document pixels
- PDF reconstruction
- Coordinates
- File integrity
- Security decisions
- User authorization

The deterministic document engine remains authoritative.

---

# 19. Deployment Architecture — Initial

## Firebase Hosting

Angular application:

```text
Angular 20
   ↓
ng build
   ↓
Firebase Hosting
   ↓
https://<project>.web.app
```

Firebase Hosting provides CDN delivery and SSL, and the Spark plan currently includes no-cost Hosting quotas. Firebase documentation currently lists 10 GB of Hosting storage at no cost. citeturn0search4turn0search12

## Important Firebase limitation

Firebase Hosting on Spark is suitable for the Angular frontend.

However, the Python FastAPI backend should **not be assumed to run on the Firebase Spark plan**.

Firebase documentation states that deploying Cloud Functions requires the Blaze plan. Cloud Run also requires an associated billing account and moves a Spark project to Blaze. citeturn0search16turn0search9

Therefore the initial architecture should be:

```text
                    Internet
                       |
                       v
              Firebase Hosting
                 Angular 20
                       |
                       | HTTPS
                       v
               Python FastAPI
                       |
              +--------+--------+
              |                 |
              v                 v
         PostgreSQL       Object Storage
```

The FastAPI and PostgreSQL hosting provider can be selected separately.

### Future Firebase architecture

When the project is ready to move to Blaze:

```text
Firebase Hosting
       |
       v
Firebase / Google Cloud
       |
       +--> Python Cloud Functions
       |
       +--> Cloud Storage
       |
       +--> PostgreSQL / SQL Connect
```

Firebase currently supports Python for Cloud Functions, but deployment requires Blaze. citeturn0search2turn0search3

---

# 20. Local Development

Use:

```text
Angular
localhost:4200

FastAPI
localhost:8000

PostgreSQL
localhost:5432
```

Example:

```text
Angular
  |
  | HTTP
  v
FastAPI
  |
  +---- PostgreSQL
  |
  +---- Local object storage
  |
  +---- OCR engine
```

Use Docker Compose for repeatable backend development.

---

# 21. Deployment Environments

At minimum:

```text
Development
     ↓
Test
     ↓
Production
```

Firebase Hosting can provide preview channels for frontend validation before production deployment. citeturn0search6

---

# 22. Observability

Track:

- Upload failures
- OCR failures
- OCR duration
- Rendering duration
- Export failures
- API latency
- Document processing errors
- Browser errors
- Storage failures
- User edit failures

Do not log document contents unnecessarily.

Never log:

- full uploaded documents
- sensitive invoice information
- passwords/tokens
- complete OCR text unless explicitly required and protected

---

# 23. Data Retention

This must be decided before production.

Recommended initial policy:

```text
Original document
       |
       +--> retained while user session/project requires it
       |
       +--> deleted according to retention policy
```

Temporary OCR/rendering files should have a shorter lifetime.

Example policy:

```text
Temporary files: 1–24 hours
Unfinished documents: configurable
Completed documents: user-controlled
Deleted documents: hard-delete after retention period
```

The exact policy must be finalized based on product/legal requirements.

---

# 24. Security Requirements

## File Security

- Validate extension AND MIME/signature.
- Limit file size.
- Limit page count.
- Reject malformed files.
- Process files in isolated workers.
- Never execute embedded document scripts.
- Sanitize filenames.
- Use random storage keys.
- Use authorization checks for every document operation.

## API Security

- HTTPS only.
- Authentication before accessing private documents.
- Authorization on every document ID.
- Rate limiting.
- Request size limits.
- Input validation.
- Secure CORS configuration.
- No secrets in frontend source code.

---

# 25. Quality Validation for Pixel Preservation

The system should maintain an edit mask.

Example:

```text
Original image
        +
Edit mask
        +
Edited image
```

Automated validation should compare:

```text
outside mask → expected unchanged
inside mask  → allowed to change
```

For example:

```python
difference = abs(original - edited)

outside_edit_region = difference[mask == 0]

# Outside the edit region should remain unchanged
```

For PDFs, validation should compare page dimensions, object counts/positions where practical, and rasterized output outside the edit area.

---

# 26. Performance Strategy

Do not process everything synchronously.

For small documents:

```text
Upload → OCR → Edit → Export
```

For large documents:

```text
Upload
  ↓
Create processing job
  ↓
Background worker
  ↓
OCR
  ↓
Document model
  ↓
Ready for editing
```

The frontend should receive job status:

```text
UPLOADING
PROCESSING
OCR_RUNNING
READY
EDITING
EXPORTING
COMPLETED
FAILED
```

---

# 27. Recommended MVP

### MVP-1

```text
PDF/Image upload
        ↓
OCR/text extraction
        ↓
Text selection
        ↓
Text replacement
        ↓
Localized reconstruction
        ↓
Preview
        ↓
Download
```

### MVP-2

Add:

```text
Undo/redo
Search/replace
Multilingual support
Better font matching
Multi-page editing
```

### MVP-3

Add Phase 2:

```text
Chat
 ↓
Natural-language edit
 ↓
Target detection
 ↓
Confirmation
 ↓
Edit operation
 ↓
Preview
```

---

# 28. Major Risks / Items to Consider Before Final Architecture Sign-Off

## R1 — Exact visual preservation

This is the hardest technical problem.

A photographed document does not have a separate background/text layer. Perfect reconstruction is not guaranteed for every document.

**Recommendation:** define measurable visual-quality targets and use localized processing.

---

## R2 — Font detection

The original font may not be available.

**Recommendation:** use:

1. Exact embedded font where available.
2. Closest font match.
3. Local visual reconstruction/inpainting where font cannot be reliably reproduced.

---

## R3 — OCR errors

OCR can misread:

```text
0 / O
1 / I / l
5 / S
8 / B
```

**Recommendation:** preserve confidence and require confirmation for low-confidence edits.

---

## R4 — Complex layouts

Tables, columns, rotated text and mixed layouts require more than plain OCR.

**Recommendation:** build the normalized document model first; add table/layout intelligence incrementally.

---

## R5 — Multilingual documents

Indian and international documents may contain mixed languages.

**Recommendation:** use Unicode-first storage and rendering, language metadata per text block, and proper text shaping.

---

## R6 — Camera images

Perspective, shadows, folds and low resolution can significantly affect OCR and reconstruction.

**Recommendation:** add a dedicated document-image preprocessing pipeline.

---

## R7 — Large documents

OCR and rendering can be CPU-intensive.

**Recommendation:** use background jobs and worker processes rather than blocking FastAPI requests.

---

## R8 — Firebase free-tier architecture

Firebase Hosting is suitable for the Angular frontend on the Spark plan, but Python backend deployment through Firebase Cloud Functions requires Blaze. Cloud Run also requires billing/Blaze. citeturn0search0turn0search16turn0search9

**Recommendation:** Phase 1 can use Firebase Hosting for Angular and keep FastAPI/PostgreSQL on separate infrastructure. Decide the backend hosting provider before production.

---

## R9 — Storage cost

Original files and generated files can become the largest storage component.

**Recommendation:** establish file-size, retention and deletion rules from the beginning.

---

## R10 — Edit history

For legitimate correction workflows, users may need to know what changed.

**Recommendation:** keep immutable edit operations and provide an optional change summary.

---

## R11 — Document integrity

The system must not silently corrupt the original.

**Recommendation:** maintain:

```text
original
+
operations
=
derived output
```

Never make the exported file the new master source.

---

## R12 — Conversational ambiguity

Example:

> Change 2500 to 3000.

If 2500 occurs five times, the AI must not guess.

**Recommendation:** show candidate locations and ask the user to choose.

---

# 29. Architecture Decision Summary

| Decision | Recommendation |
|---|---|
| Product type | Generic document correction editor |
| Templates | Not required for core editing |
| Input | PDF + JPG/JPEG + PNG |
| Phase 1 | Visual editor |
| Phase 2 | Conversational editor |
| PDF engine | PyMuPDF |
| OCR | Pluggable OCR service |
| Frontend | Angular 20 |
| Backend | Python/FastAPI |
| Database | PostgreSQL |
| Storage | Object storage |
| Edit model | Immutable operations |
| Image editing | Localized reconstruction |
| Background | Preserve original/background |
| AI | Instruction understanding, not final document rendering |
| Authentication | Required before private document access |
| Frontend hosting | Firebase Hosting |
| Initial Firebase plan | Spark for frontend |
| Python on Firebase | Requires Blaze for Cloud Functions |
| Cloud Run on Firebase | Requires billing/Blaze |
| Deployment approach | Firebase frontend + separately hosted backend initially |
| Phase 2 UI | Preview + chat split view |
| Primary quality goal | Only intended text changes |

---

# 30. Open Decisions Before Development

The following should be finalized before implementation starts:

1. Maximum upload file size.
2. Maximum PDF page count.
3. Supported image formats beyond JPG/PNG.
4. Whether output image format must always match input.
5. Whether image input can be exported as PDF.
6. Document retention period.
7. Whether login is mandatory in MVP.
8. Whether anonymous/free editing is allowed.
9. OCR engine selection.
10. Exact font matching strategy.
11. Whether table/cell editing is Phase 1 or Phase 2.
12. Whether handwritten text is supported.
13. Supported language list for MVP.
14. Whether original-vs-edited comparison is required.
15. Whether edit history is visible to users.
16. Whether a corrected-document watermark/label is required for any workflows.
17. Backend hosting provider for the initial free deployment.
18. PostgreSQL hosting provider.
19. Maximum concurrent processing jobs.
20. Whether AI/conversational editing requires login/quota enforcement.

---

# 31. Recommended Immediate Development Order

```text
STEP 1
Angular application shell
        ↓
STEP 2
Upload PDF/Image
        ↓
STEP 3
FastAPI upload/document API
        ↓
STEP 4
PDF text extraction
        ↓
STEP 5
OCR pipeline
        ↓
STEP 6
Normalized document model
        ↓
STEP 7
Document viewer + text selection
        ↓
STEP 8
Edit operation engine
        ↓
STEP 9
Localized image/PDF reconstruction
        ↓
STEP 10
Preview + export
        ↓
STEP 11
Pixel-preservation tests
        ↓
STEP 12
Undo/redo + search/replace
        ↓
STEP 13
Phase 2 conversational UI
        ↓
STEP 14
Natural-language edit parser
        ↓
STEP 15
Confirmation + conversational edit execution
```

---

# 32. Final Product Principle

The platform should be built around one invariant:

> **The user's uploaded document is the source of truth. AI and OCR may understand the document, but only controlled edit operations may modify it.**

This keeps the product technically predictable, testable, extensible and suitable for many document types without requiring a template for every bill or invoice.
