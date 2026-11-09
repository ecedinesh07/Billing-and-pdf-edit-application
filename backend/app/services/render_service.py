"""Localized document reconstruction for export.

Applies immutable edit operations to a *copy* of the original.
Never modifies the uploaded master file.

For text PDFs: remove only the target glyphs, then redraw with the
document's embedded font / size / color / baseline when available.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

from app.models.document import OperationType


@dataclass
class AppliedEdit:
    operation_type: str
    page_number: int
    old_value: str | None
    new_value: str | None
    bbox: dict | None
    font_size: float | None = None
    font_family: str | None = None
    block_id: str | None = None


@dataclass
class GlyphSource:
    """A labeled text line on the page used to harvest real ink glyphs."""

    text: str
    bbox: dict  # x0,y0,x1,y1 in image pixels
    page_number: int = 1


@dataclass
class ImageTextStyle:
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont
    font_size: int
    bold: bool
    mono: bool
    letter_spacing: float
    scale_y: float
    text_color: tuple[int, ...]
    fill: tuple[int, ...]
    cover_box: tuple[int, int, int, int]
    origin: tuple[int, int]
    ink_height: int
    ink_width: int
    ink_box: tuple[int, int, int, int]



@dataclass
class SpanStyle:
    font_name: str
    font_size: float
    color: tuple[float, float, float]
    origin: tuple[float, float]
    bbox: fitz.Rect
    flags: int
    fontbuffer: bytes | None = None
    fontfile_ext: str | None = None


class RenderService:
    def render(
        self,
        *,
        original: Path,
        dest: Path,
        mime_type: str,
        edits: list[AppliedEdit],
        glyph_sources: list[GlyphSource] | None = None,
    ) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Collapse chained edits on the same block so only the final text is painted
        # onto the pristine original (avoids leftover longer intermediate text).
        edits = self.coalesce_edits(edits)
        if mime_type == "application/pdf":
            self._render_pdf(original, dest, edits)
        else:
            self._render_image(original, dest, edits, glyph_sources=glyph_sources or [])

    @staticmethod
    def coalesce_edits(edits: list[AppliedEdit]) -> list[AppliedEdit]:
        """Fold sequential ops on the same region into one final replace/delete.

        Example: A→B then B→A becomes a no-op (original left untouched).
        Example: A→B then B→C becomes a single A→C against the original PDF.
        """
        groups: dict[str, list[AppliedEdit]] = {}
        order: list[str] = []

        for edit in edits:
            key = RenderService._edit_group_key(edit)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(edit)

        coalesced: list[AppliedEdit] = []
        for key in order:
            group = groups[key]
            first = group[0]
            last = group[-1]

            # Prefer earliest non-empty old_value as the text that exists on the original.
            original_text = next((e.old_value for e in group if e.old_value), first.old_value)
            final_type = last.operation_type
            final_text = "" if final_type == OperationType.DELETE_TEXT.value else (last.new_value or "")

            # Reverted to original content — keep pristine glyphs/fonts.
            if (
                final_type == OperationType.REPLACE_TEXT.value
                and original_text is not None
                and final_text == original_text
            ):
                continue

            # No effective change.
            if (
                final_type == OperationType.REPLACE_TEXT.value
                and first.old_value is not None
                and final_text == first.old_value
                and len(group) == 1
            ):
                continue

            coalesced.append(
                AppliedEdit(
                    operation_type=final_type,
                    page_number=first.page_number,
                    old_value=original_text,
                    new_value=final_text,
                    bbox=first.bbox,
                    font_size=first.font_size or last.font_size,
                    font_family=first.font_family or last.font_family,
                    block_id=first.block_id or last.block_id,
                )
            )
        return coalesced

    @staticmethod
    def _edit_group_key(edit: AppliedEdit) -> str:
        if edit.block_id:
            return f"block:{edit.block_id}"
        if edit.bbox and all(k in edit.bbox for k in ("x0", "y0", "x1", "y1")):
            return (
                f"bbox:{edit.page_number}:"
                f"{round(float(edit.bbox['x0']), 1)}:"
                f"{round(float(edit.bbox['y0']), 1)}:"
                f"{round(float(edit.bbox['x1']), 1)}:"
                f"{round(float(edit.bbox['y1']), 1)}"
            )
        return f"text:{edit.page_number}:{edit.old_value}"

    def _render_pdf(self, original: Path, dest: Path, edits: list[AppliedEdit]) -> None:
        doc = fitz.open(original)
        try:
            by_page: dict[int, list[AppliedEdit]] = {}
            for edit in edits:
                by_page.setdefault(edit.page_number, []).append(edit)

            for page_number, page_edits in by_page.items():
                if page_number < 1 or page_number > doc.page_count:
                    continue
                page = doc[page_number - 1]
                pending: list[
                    tuple[AppliedEdit, SpanStyle | None, fitz.Rect, bool, tuple[float, float, float]]
                ] = []
                redact_images = fitz.PDF_REDACT_IMAGE_NONE

                for edit in page_edits:
                    rect = self._rect_from_edit(page, edit)
                    if rect is None:
                        continue

                    style = self._lookup_span_style(doc, page, rect, edit.old_value)
                    cover = self._build_cover_rect(page, rect, edit, style)
                    image_backed = self._cover_intersects_image(page, cover)
                    if image_backed:
                        # Blank scanned pixels under the edit; do not remove whole images.
                        redact_images = fitz.PDF_REDACT_IMAGE_PIXELS

                    fontsize = self._resolve_fontsize(style, edit, cover, image_backed)
                    cover = self._widen_cover_for_text(page, cover, edit, style, fontsize)

                    fill = self._sample_background(page, cover)
                    # Redact only (no replacement text) so a default font is never injected here.
                    page.add_redact_annot(cover, fill=fill)
                    pending.append((edit, style, cover, image_backed, fill))

                page.apply_redactions(
                    images=redact_images,
                    graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                    text=fitz.PDF_REDACT_TEXT_REMOVE,
                )

                for edit, style, cover, image_backed, fill in pending:
                    # Paint sampled paper over the cover so no old glyphs can ghost
                    # under the replacement (common on form/table PDFs).
                    page.draw_rect(cover, color=fill, fill=fill, width=0, overlay=True)

                    if edit.operation_type == OperationType.DELETE_TEXT.value:
                        continue
                    new_text = edit.new_value or ""
                    if not new_text:
                        continue
                    self._draw_styled_text(
                        page,
                        new_text,
                        style,
                        cover,
                        edit,
                        image_backed=image_backed,
                    )

            doc.save(dest.as_posix(), garbage=4, deflate=True, clean=True)
        finally:
            doc.close()

    def _build_cover_rect(
        self,
        page: fitz.Page,
        rect: fitz.Rect,
        edit: AppliedEdit,
        style: SpanStyle | None,
    ) -> fitz.Rect:
        """Union same-line value spans so fragmented OCR/text does not leave ghosts."""
        cover = fitz.Rect(style.bbox) if style else fitz.Rect(rect)
        cover |= fitz.Rect(rect)

        tokens = []
        if edit.old_value:
            tokens = [t for t in edit.old_value.replace(":", " ").split() if len(t) > 1]

        y_mid = (cover.y0 + cover.y1) / 2.0
        line_tol = max(3.0, cover.height * 0.9)

        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    sb = fitz.Rect(span["bbox"])
                    if sb.x1 < rect.x0 - 2:
                        # Keep field labels to the left intact.
                        continue
                    span_mid = (sb.y0 + sb.y1) / 2.0
                    if abs(span_mid - y_mid) > line_tol:
                        continue
                    text = (span.get("text") or "").strip()
                    intersects = abs(sb & cover) > 0
                    token_hit = any(
                        tok.lower() in text.lower() or text.lower().rstrip(":") in tok.lower()
                        for tok in tokens
                    )
                    same_line_value = sb.x0 <= cover.x1 + 10 and sb.x0 >= cover.x0 - 1
                    if intersects or (token_hit and same_line_value):
                        cover |= sb

        if edit.old_value:
            for hit in page.search_for(edit.old_value):
                if abs(((hit.y0 + hit.y1) / 2.0) - y_mid) <= line_tol and hit.x1 >= rect.x0 - 2:
                    cover |= hit

        # Slight pad so anti-aliased glyph edges / descenders are fully covered.
        return fitz.Rect(cover.x0 - 0.75, cover.y0 - 0.75, cover.x1 + 0.75, cover.y1 + 0.75) & page.rect

    def _cover_intersects_image(self, page: fitz.Page, cover: fitz.Rect) -> bool:
        """True only when the edit region itself sits on image pixels (scans)."""
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") == 1 and abs(fitz.Rect(block["bbox"]) & cover) > 1.0:
                return True
        # Large full-page scan image: treat as image-backed when cover is on-page.
        for img in page.get_images(full=True):
            try:
                rects = page.get_image_rects(img[0])
            except Exception:  # noqa: BLE001
                continue
            for irect in rects:
                area = abs(fitz.Rect(irect))
                if area < page.rect.get_area() * 0.55:
                    continue
                if abs(fitz.Rect(irect) & cover) > 1.0:
                    return True
        return False

    def _resolve_fontsize(
        self,
        style: SpanStyle | None,
        edit: AppliedEdit,
        cover: fitz.Rect,
        image_backed: bool,
    ) -> float:
        reported = (style.font_size if style else None) or edit.font_size
        visual = max(6.0, float(cover.height) * 0.72)
        if image_backed:
            # OCR/text-layer sizes on scans are often much smaller than visible ink.
            if reported is None or reported < visual * 0.85:
                return visual
            return float(reported)
        return float(reported or visual)

    def _widen_cover_for_text(
        self,
        page: fitz.Page,
        cover: fitz.Rect,
        edit: AppliedEdit,
        style: SpanStyle | None,
        fontsize: float,
    ) -> fitz.Rect:
        new_text = edit.new_value or ""
        if edit.operation_type == OperationType.DELETE_TEXT.value or not new_text:
            return cover

        width_needed = None
        font = self._build_font(style, edit.font_family)
        if font is not None:
            try:
                width_needed = float(font.text_length(new_text, fontsize=fontsize))
            except Exception:  # noqa: BLE001
                width_needed = None
        if width_needed is None and edit.old_value:
            ratio = len(new_text) / max(len(edit.old_value), 1)
            width_needed = cover.width * ratio

        if width_needed and width_needed > cover.width:
            return fitz.Rect(
                cover.x0,
                cover.y0,
                min(page.rect.x1, cover.x0 + width_needed + 2),
                cover.y1,
            )
        return cover

    def _draw_styled_text(
        self,
        page: fitz.Page,
        text: str,
        style: SpanStyle | None,
        cover: fitz.Rect,
        edit: AppliedEdit,
        *,
        image_backed: bool = False,
    ) -> None:
        fontsize = self._resolve_fontsize(style, edit, cover, image_backed)
        color = style.color if style else (0.0, 0.0, 0.0)
        if style:
            origin = style.origin
        else:
            origin = (cover.x0, cover.y0 + fontsize * 0.85)

        family = style.font_name if style else edit.font_family
        flags = style.flags if style else 0

        # Exact match for PDF Base-14 faces (Helvetica/Times/Courier) — do not
        # substitute Arial or the weight/spacing will visibly change.
        base14 = self._base14_fontname(family, flags)
        if base14 is not None:
            tracking = self._estimate_base14_tracking(base14, style, edit.old_value, fontsize)
            self._insert_text_with_tracking(
                page,
                text=text,
                origin=origin,
                fontsize=fontsize,
                fontname=base14,
                color=color,
                tracking=tracking,
            )
            return

        font = self._build_font(style, edit.font_family)
        tracking = self._estimate_char_tracking(font, style, edit.old_value, fontsize)

        # Custom/embedded faces: TextWriter with a matching installed TTF.
        if font is not None:
            writer = fitz.TextWriter(page.rect)
            if abs(tracking) > 0.05 and len(text) > 1:
                cursor_x = float(origin[0])
                baseline = float(origin[1])
                for index, ch in enumerate(text):
                    writer.append((cursor_x, baseline), ch, font=font, fontsize=fontsize)
                    advance = float(font.text_length(ch, fontsize=fontsize))
                    cursor_x += advance
                    if index < len(text) - 1:
                        cursor_x += tracking
            else:
                writer.append(origin, text, font=font, fontsize=fontsize)
            writer.write_text(page, color=color)
            return

        # Last resort: mapped Base-14 face.
        page.insert_text(
            origin,
            text,
            fontsize=fontsize,
            fontname=self._map_font(family, flags),
            color=color,
        )

    def _insert_text_with_tracking(
        self,
        page: fitz.Page,
        *,
        text: str,
        origin: tuple[float, float],
        fontsize: float,
        fontname: str,
        color: tuple[float, float, float],
        tracking: float,
    ) -> None:
        if abs(tracking) <= 0.05 or len(text) <= 1:
            page.insert_text(origin, text, fontsize=fontsize, fontname=fontname, color=color)
            return
        cursor_x = float(origin[0])
        baseline = float(origin[1])
        for index, ch in enumerate(text):
            page.insert_text((cursor_x, baseline), ch, fontsize=fontsize, fontname=fontname, color=color)
            # Approximate advance for Base-14 using Helvetica-like width via text length helper.
            try:
                advance = float(fitz.get_text_length(ch, fontname=fontname, fontsize=fontsize))
            except Exception:  # noqa: BLE001
                advance = fontsize * 0.5
            cursor_x += advance
            if index < len(text) - 1:
                cursor_x += tracking

    def _estimate_base14_tracking(
        self,
        fontname: str,
        style: SpanStyle | None,
        old_text: str | None,
        fontsize: float,
    ) -> float:
        if style is None or not old_text or len(old_text) < 2:
            return 0.0
        try:
            natural = float(fitz.get_text_length(old_text, fontname=fontname, fontsize=fontsize))
        except Exception:  # noqa: BLE001
            return 0.0
        if natural <= 0:
            return 0.0
        return (float(style.bbox.width) - natural) / (len(old_text) - 1)

    @staticmethod
    def _base14_fontname(font_family: str | None, flags: int = 0) -> str | None:
        """Return PyMuPDF Base-14 fontname when the PDF already used a standard face."""
        raw = (font_family or "").strip()
        if not raw:
            return None
        name = raw.lower().replace(" ", "")
        if "+" in name:
            name = name.split("+", 1)[-1]
        bold = bool(flags & 2**4) or "bold" in name
        italic = bool(flags & 2**1) or "italic" in name or "oblique" in name

        if name.startswith("helvetica") or name in {"helv", "hebo", "heit", "hebi"}:
            if bold and italic:
                return "hebi"
            if bold:
                return "hebo"
            if italic:
                return "heit"
            return "helv"
        if name.startswith("times") or name in {"tiro", "tibo", "tiit", "tibi"}:
            if bold and italic:
                return "times-bolditalic"
            if bold:
                return "times-bold"
            if italic:
                return "times-italic"
            return "times-roman"
        if name.startswith("courier") or name in {"cour", "cobo", "coit", "cobi"}:
            if bold and italic:
                return "cobo"
            if bold:
                return "cobo"
            if italic:
                return "coit"
            return "cour"
        return None


    def _estimate_char_tracking(
        self,
        font: fitz.Font | None,
        style: SpanStyle | None,
        old_text: str | None,
        fontsize: float,
    ) -> float:
        """Recover original letter-spacing from span width vs natural glyph width."""
        if font is None or style is None or not old_text or len(old_text) < 2:
            return 0.0
        try:
            natural = float(font.text_length(old_text, fontsize=fontsize))
        except Exception:  # noqa: BLE001
            return 0.0
        if natural <= 0:
            return 0.0
        return (float(style.bbox.width) - natural) / (len(old_text) - 1)

    def _build_font(self, style: SpanStyle | None, fallback_family: str | None) -> fitz.Font | None:
        family = (style.font_name if style else fallback_family) or ""
        flags = style.flags if style else 0

        # PDF Base-14 faces must stay on the native insert_text path — never load a
        # substitute TTF (Arial for Helvetica, etc.) or weight/spacing will change.
        if self._base14_fontname(family, flags) is not None:
            return None

        # Prefer installed system fonts first. PDF subset buffers often re-embed as the
        # wrong family (e.g. Arial-BoldMT → NotoSerif-Regular) and change the look.
        for path in self._candidate_system_fonts(family, flags):
            try:
                return fitz.Font(fontfile=path)
            except Exception:  # noqa: BLE001
                continue

        if style and style.fontbuffer:
            try:
                font = fitz.Font(fontbuffer=style.fontbuffer)
                # Reject buffers that MuPDF remaps to an unrelated fallback face.
                name = (font.name or "").lower()
                target = family.lower().replace(" ", "").replace("-", "")
                if target and name:
                    compact = name.replace(" ", "").replace("-", "")
                    if "noto" in compact and "noto" not in target:
                        raise ValueError("subset remapped to Noto fallback")
                return font
            except Exception:  # noqa: BLE001
                pass

        return None

    def _lookup_span_style(
        self,
        doc: fitz.Document,
        page: fitz.Page,
        rect: fitz.Rect,
        old_text: str | None,
    ) -> SpanStyle | None:
        best: dict | None = None
        best_score = -1.0
        raw = page.get_text("dict")
        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = (span.get("text") or "").strip()
                    if not text:
                        continue
                    sb = fitz.Rect(span["bbox"])
                    inter = abs(sb & rect)
                    if inter <= 0 and not (old_text and old_text.strip() in text):
                        continue
                    score = inter
                    if old_text and text == old_text.strip():
                        score += 1000
                    elif old_text and old_text.strip() in text:
                        score += 100
                    if score > best_score:
                        best_score = score
                        best = span

        if best is None:
            return None

        font_name = str(best.get("font") or "")
        fontsize = float(best.get("size") or 0) or max(6.0, float(rect.height) * 0.78)
        color = self._color_int_to_rgb(int(best.get("color") or 0))
        origin = best.get("origin")
        if origin and len(origin) >= 2:
            origin_t = (float(origin[0]), float(origin[1]))
        else:
            bbox = fitz.Rect(best["bbox"])
            origin_t = (bbox.x0, bbox.y1 - fontsize * 0.15)

        fontbuffer, ext = self._extract_font_buffer(doc, page, font_name)
        return SpanStyle(
            font_name=font_name,
            font_size=fontsize,
            color=color,
            origin=origin_t,
            bbox=fitz.Rect(best["bbox"]),
            flags=int(best.get("flags") or 0),
            fontbuffer=fontbuffer,
            fontfile_ext=ext,
        )

    def _extract_font_buffer(
        self,
        doc: fitz.Document,
        page: fitz.Page,
        font_name: str,
    ) -> tuple[bytes | None, str | None]:
        if not font_name:
            return None, None

        target = font_name.lower().replace(" ", "")
        candidates: list[tuple[int, int, str]] = []
        for item in page.get_fonts(full=True):
            xref = int(item[0])
            basefont = str(item[3] or "")
            # Match "LiberationSerif" to "IMQWKY+LiberationSerif"
            base_norm = basefont.lower().replace(" ", "")
            short = base_norm.split("+")[-1]
            score = 0
            if short == target or base_norm.endswith(target):
                score = 3
            elif target in short or short in target:
                score = 2
            elif target.replace("-", "") in short.replace("-", ""):
                score = 1
            if score:
                candidates.append((score, xref, basefont))

        # Prefer exact/highest score; if bold flag later needed, caller passes bold name.
        candidates.sort(key=lambda c: c[0], reverse=True)
        for _, xref, _ in candidates:
            try:
                extracted = doc.extract_font(xref)
            except Exception:  # noqa: BLE001
                continue
            # (name, ext, type, content)
            content = extracted[3] if extracted and len(extracted) > 3 else None
            ext = extracted[1] if extracted and len(extracted) > 1 else None
            if content:
                return content, ext
        return None, None

    def _render_image(
        self,
        original: Path,
        dest: Path,
        edits: list[AppliedEdit],
        *,
        glyph_sources: list[GlyphSource],
    ) -> None:
        with Image.open(original) as img:
            working = img.convert("RGBA")
            rgb = img.convert("RGB")

            # Harvest real ink glyphs from the pristine image BEFORE clearing any region.
            page_sources = list(glyph_sources)
            for edit in edits:
                if edit.old_value and edit.bbox:
                    page_sources.append(
                        GlyphSource(text=edit.old_value, bbox=edit.bbox, page_number=edit.page_number)
                    )
            page_atlas = self._build_glyph_atlas(rgb, page_sources)

            for edit in edits:
                if edit.page_number != 1 or not edit.bbox:
                    continue
                x0 = float(edit.bbox["x0"])
                y0 = float(edit.bbox["y0"])
                x1 = float(edit.bbox["x1"])
                y1 = float(edit.bbox["y1"])
                box = (
                    int(x0),
                    int(y0),
                    int(max(x1, x0 + 1)),
                    int(max(y1, y0 + 1)),
                )

                style = self._analyze_image_text_style(rgb, box, edit)
                new_text = edit.new_value or ""

                # Local line glyphs win over page-wide atlas (same font weight/size/color).
                local_sources = []
                if edit.old_value:
                    local_sources.append(
                        GlyphSource(text=edit.old_value, bbox=edit.bbox, page_number=edit.page_number)
                    )
                local_atlas = self._build_glyph_atlas(rgb, local_sources) if local_sources else {}
                atlas = self._merge_glyph_atlases(page_atlas, local_atlas, style)

                # Erase only ink pixels (keep exact paper texture/color). Widen if new text is longer.
                ix0, iy0, ix1, iy1 = style.ink_box
                cover = [
                    max(0, ix0 - 1),
                    max(0, iy0 - 1),
                    min(working.width, ix1 + 1),
                    min(working.height, iy1 + 1),
                ]
                if edit.operation_type != OperationType.DELETE_TEXT.value and new_text:
                    needed = self._measure_glyph_text_width(new_text, atlas, style)
                    cover[2] = min(working.width, max(cover[2], cover[0] + needed + 1))

                self._erase_ink_keep_paper(working, rgb, tuple(cover))

                if edit.operation_type == OperationType.DELETE_TEXT.value:
                    continue
                if not new_text:
                    continue

                # Rebuild from real bill glyphs; recolor to this line's ink.
                self._compose_text_from_glyphs(working, new_text, atlas, style)

            suffix = dest.suffix.lower()
            save_img = working.convert("RGB") if suffix in {".jpg", ".jpeg"} else working
            save_kwargs: dict = {}
            if suffix in {".jpg", ".jpeg"}:
                save_kwargs["quality"] = 95
                save_kwargs["subsampling"] = 0
            save_img.save(dest, **save_kwargs)

    def _build_glyph_atlas(
        self,
        rgb: Image.Image,
        sources: list[GlyphSource],
    ) -> dict[str, object]:
        """Build a map of character -> list of real ink crops + spacing metrics."""
        samples: dict[str, list[Image.Image]] = {}
        gaps: list[int] = []
        space_widths: list[int] = []
        char_heights: list[int] = []

        for source in sources:
            text = (source.text or "").strip()
            if not text or not source.bbox:
                continue
            box = (
                int(source.bbox["x0"]),
                int(source.bbox["y0"]),
                int(source.bbox["x1"]),
                int(source.bbox["y1"]),
            )
            segments = self._segment_char_boxes(rgb, box)
            if not segments:
                continue
            mapping = self._align_chars_to_segments(text, segments)
            if not mapping:
                continue

            for i, (ch, seg) in enumerate(mapping):
                crop = rgb.crop(seg).convert("RGBA")
                samples.setdefault(ch, []).append(crop)
                char_heights.append(max(1, seg[3] - seg[1]))
                if i + 1 < len(mapping):
                    next_seg = mapping[i + 1][1]
                    gap = next_seg[0] - seg[2]
                    # Large gaps are word spaces; small gaps are tracking.
                    if gap >= max(3, int(0.45 * (seg[2] - seg[0]))):
                        space_widths.append(gap)
                    elif gap >= 0:
                        gaps.append(gap)

        median_gap = sorted(gaps)[len(gaps) // 2] if gaps else 1
        median_space = sorted(space_widths)[len(space_widths) // 2] if space_widths else max(4, median_gap * 3)
        median_h = sorted(char_heights)[len(char_heights) // 2] if char_heights else 16
        # Pick a representative glyph per character (median width).
        atlas_glyphs: dict[str, Image.Image] = {}
        for ch, crops in samples.items():
            crops_sorted = sorted(crops, key=lambda im: im.width)
            atlas_glyphs[ch] = crops_sorted[len(crops_sorted) // 2]
        return {
            "glyphs": atlas_glyphs,
            "gap": max(0, median_gap),
            "space": max(2, median_space),
            "height": max(1, median_h),
        }

    def _merge_glyph_atlases(
        self,
        page_atlas: dict[str, object],
        local_atlas: dict[str, object],
        style: ImageTextStyle,
    ) -> dict[str, object]:
        """Prefer glyphs/metrics from the edited line; fall back to page harvest."""
        page_glyphs: dict[str, Image.Image] = dict(page_atlas.get("glyphs", {}) or {})  # type: ignore[arg-type]
        local_glyphs: dict[str, Image.Image] = dict(local_atlas.get("glyphs", {}) or {})  # type: ignore[arg-type]
        merged = {**page_glyphs, **local_glyphs}

        gap = local_atlas.get("gap", page_atlas.get("gap", style.letter_spacing))
        space = local_atlas.get("space", page_atlas.get("space", max(4, style.ink_height // 2)))
        height = local_atlas.get("height", page_atlas.get("height", style.ink_height))
        # Prefer the exact ink height of the line being edited.
        height = style.ink_height or height
        return {
            "glyphs": merged,
            "gap": max(0, int(gap or 0)),
            "space": max(2, int(space or 4)),
            "height": max(1, int(height or style.ink_height)),
        }

    def _segment_char_boxes(
        self,
        rgb: Image.Image,
        box: tuple[int, int, int, int],
    ) -> list[tuple[int, int, int, int]]:
        ink = self._tight_ink_bbox(rgb, box) or box
        crop = rgb.crop(ink).convert("L")
        width, height = crop.size
        if width < 2 or height < 2:
            return [ink]

        pix = crop.load()
        # Adaptive ink cutoff from local paper brightness.
        vals = [pix[x, y] for y in range(height) for x in range(0, width, max(1, width // 40))]
        vals_sorted = sorted(vals)
        paper = vals_sorted[int(len(vals_sorted) * 0.75)] if vals_sorted else 200
        ink_cut = max(40, min(150, paper - 30))
        threshold = max(1, int(height * 0.05))
        col_dark = []
        for x in range(width):
            dark = sum(1 for y in range(height) if pix[x, y] < ink_cut)
            col_dark.append(dark)

        segments: list[tuple[int, int]] = []
        in_run = False
        start = 0
        for x, dark in enumerate(col_dark):
            if dark >= threshold and not in_run:
                in_run = True
                start = x
            elif dark < threshold and in_run:
                in_run = False
                if x - start >= 1:
                    segments.append((start, x))
        if in_run and width - start >= 1:
            segments.append((start, width))

        # Merge segments separated by 1px noise gaps.
        merged: list[tuple[int, int]] = []
        for seg in segments:
            if not merged:
                merged.append(seg)
                continue
            prev = merged[-1]
            if seg[0] - prev[1] <= 1:
                merged[-1] = (prev[0], seg[1])
            else:
                merged.append(seg)

        boxes = [
            (ink[0] + a, ink[1], ink[0] + b, ink[3])
            for a, b in merged
            if b - a >= 1
        ]
        return boxes

    def _align_chars_to_segments(
        self,
        text: str,
        segments: list[tuple[int, int, int, int]],
    ) -> list[tuple[str, tuple[int, int, int, int]]] | None:
        chars = [ch for ch in text if not ch.isspace()]
        if not chars or not segments:
            return None
        if len(segments) == len(chars):
            return list(zip(chars, segments))

        line_x0 = segments[0][0]
        line_x1 = segments[-1][2]
        span = max(1, line_x1 - line_x0)
        mapped: list[tuple[str, tuple[int, int, int, int]]] = []
        for i, ch in enumerate(chars):
            target_cx = line_x0 + ((i + 0.5) / len(chars)) * span
            best = min(segments, key=lambda s: abs(((s[0] + s[2]) / 2) - target_cx))
            mapped.append((ch, best))
        return self._split_collided_mappings(mapped)

    def _split_collided_mappings(
        self,
        mapped: list[tuple[str, tuple[int, int, int, int]]],
    ) -> list[tuple[str, tuple[int, int, int, int]]]:
        from collections import defaultdict

        groups: dict[tuple[int, int, int, int], list[str]] = defaultdict(list)
        order: list[tuple[int, int, int, int]] = []
        for ch, seg in mapped:
            if seg not in groups:
                order.append(seg)
            groups[seg].append(ch)

        result: list[tuple[str, tuple[int, int, int, int]]] = []
        for seg in order:
            chars = groups[seg]
            if len(chars) == 1:
                result.append((chars[0], seg))
                continue
            x0, y0, x1, y1 = seg
            slice_w = max(1, (x1 - x0) / len(chars))
            for i, ch in enumerate(chars):
                sx0 = int(x0 + i * slice_w)
                sx1 = int(x0 + (i + 1) * slice_w) if i < len(chars) - 1 else x1
                result.append((ch, (sx0, y0, max(sx0 + 1, sx1), y1)))
        return result

    def _measure_glyph_text_width(
        self,
        text: str,
        atlas: dict[str, object],
        style: ImageTextStyle,
    ) -> int:
        glyphs: dict[str, Image.Image] = atlas.get("glyphs", {})  # type: ignore[assignment]
        gap = int(atlas.get("gap", style.letter_spacing) or 0)
        space = int(atlas.get("space", max(4, style.ink_height // 2)) or 4)
        target_h = max(1, style.ink_height)
        width = 0.0
        for index, ch in enumerate(text):
            if ch == " ":
                width += space
            else:
                g = self._lookup_glyph(glyphs, ch)
                if g is not None:
                    scale = target_h / max(1, g.height)
                    width += max(1, g.width * scale)
                else:
                    width += self._text_width(ch, style.font)
            if index < len(text) - 1 and ch != " " and text[index + 1] != " ":
                width += gap
        return int(math.ceil(width))

    def _compose_text_from_glyphs(
        self,
        working: Image.Image,
        text: str,
        atlas: dict[str, object],
        style: ImageTextStyle,
    ) -> bool:
        """Rebuild text from real bill ink glyphs; match color/height/spacing of the line."""
        glyphs: dict[str, Image.Image] = atlas.get("glyphs", {})  # type: ignore[assignment]
        gap = int(atlas.get("gap", max(0, int(style.letter_spacing))) or 0)
        space = int(atlas.get("space", max(4, style.ink_height // 2)) or 4)
        target_h = max(1, style.ink_height)
        ink_color = style.text_color[:3] if style.text_color else (30, 30, 30)
        x, y = style.origin

        # Prefit: for mono/digit runs, stretch tracking so new text fills original ink width.
        natural = self._measure_glyph_text_width(text, atlas, style)
        if style.mono and natural > 0 and style.ink_width > 0:
            non_space = max(1, sum(1 for ch in text if ch != " ") - 1)
            delta = style.ink_width - natural
            gap = max(0, gap + int(round(delta / non_space)))

        cursor = float(x)
        used_glyph = False
        prepared: list[tuple[str, Image.Image | None, int]] = []
        for ch in text:
            if ch == " ":
                prepared.append((ch, None, space))
                continue
            glyph_src = self._lookup_glyph(glyphs, ch)
            if glyph_src is not None:
                layer = self._glyph_to_colored_ink(glyph_src, ink_color, target_h)
                prepared.append((ch, layer, layer.width))
                used_glyph = True
            else:
                layer = self._synthesize_char_ink(ch, style, ink_color, target_h)
                prepared.append((ch, layer, layer.width))

        for index, (ch, layer, adv) in enumerate(prepared):
            if ch == " ":
                cursor += adv
                continue
            assert layer is not None
            working.paste(layer, (int(round(cursor)), int(y)), layer)
            cursor += adv
            if index < len(prepared) - 1 and prepared[index + 1][0] != " " and ch != " ":
                cursor += max(0, gap)

        return used_glyph or bool(text)

    def _glyph_to_colored_ink(
        self,
        glyph_src: Image.Image,
        ink_color: tuple[int, int, int],
        target_h: int,
    ) -> Image.Image:
        """Turn a paper+ink crop into soft ink of the line's exact color (paper dropped)."""
        glyph = glyph_src.convert("RGBA")
        if abs(glyph.height - target_h) > 1:
            new_w = max(1, int(round(glyph.width * (target_h / max(1, glyph.height)))))
            glyph = glyph.resize((new_w, target_h), Image.Resampling.LANCZOS)
        alpha = self._ink_alpha_mask(glyph)
        layer = Image.new("RGBA", glyph.size, (*ink_color, 0))
        layer.putalpha(alpha)
        return layer

    def _synthesize_char_ink(
        self,
        ch: str,
        style: ImageTextStyle,
        ink_color: tuple[int, int, int],
        target_h: int,
    ) -> Image.Image:
        """Fallback only when the page has no matching glyph — still uses line ink color."""
        adv = max(1, int(self._text_width(ch, style.font)))
        canvas_h = max(target_h + 4, style.font_size + 4)
        fallback = Image.new("RGBA", (adv + 6, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(fallback)
        draw.text((1, 1), ch, fill=(*ink_color, 255), font=style.font)
        # Crop to ink then scale to line height so weight matches neighboring glyphs.
        tight = self._tight_ink_bbox(fallback.convert("RGB"), (0, 0, fallback.width, fallback.height))
        if tight:
            fallback = fallback.crop(tight)
        if fallback.height != target_h:
            new_w = max(1, int(round(fallback.width * (target_h / max(1, fallback.height)))))
            fallback = fallback.resize((new_w, target_h), Image.Resampling.LANCZOS)
        alpha = self._ink_alpha_mask(fallback)
        layer = Image.new("RGBA", fallback.size, (*ink_color, 0))
        layer.putalpha(alpha)
        return layer

    @staticmethod
    def _lookup_glyph(glyphs: dict[str, Image.Image], ch: str) -> Image.Image | None:
        if ch in glyphs:
            return glyphs[ch]
        if ch.upper() in glyphs:
            return glyphs[ch.upper()]
        if ch.lower() in glyphs:
            return glyphs[ch.lower()]
        # Digits sometimes OCR as lookalikes — limited safe aliases only.
        aliases = {"O": "0", "0": "O", "I": "1", "1": "I", "l": "1", "B": "8", "S": "5"}
        alt = aliases.get(ch)
        if alt and alt in glyphs:
            return glyphs[alt]
        return None

    @staticmethod
    def _ink_alpha_mask(glyph: Image.Image) -> Image.Image:
        """Keep ink (+ soft edges); drop paper so background stays exact."""
        gray = glyph.convert("L")
        vals = list(gray.getdata())
        if not vals:
            return Image.new("L", glyph.size, 0)
        ordered = sorted(vals)
        paper = ordered[int(len(ordered) * 0.75)]
        darkest = ordered[max(0, int(len(ordered) * 0.02))]
        ink_cut = max(40, min(175, paper - 28))
        # Full opacity by the true ink core so color is not washed out.
        core = max(0, min(ink_cut - 8, darkest + 18))
        span = max(8.0, float(ink_cut - core))

        def _alpha(p: int) -> int:
            if p >= ink_cut:
                return 0
            if p <= core:
                return 255
            return max(0, min(255, int(255 * (ink_cut - p) / span)))

        return gray.point(_alpha)

    def _analyze_image_text_style(
        self,
        rgb: Image.Image,
        box: tuple[int, int, int, int],
        edit: AppliedEdit,
    ) -> ImageTextStyle:
        """Measure original ink so redraw matches size, weight, spacing, and color."""
        x0, y0, x1, y1 = box
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(rgb.width, max(x0 + 1, x1))
        y1 = min(rgb.height, max(y0 + 1, y1))
        box = (x0, y0, x1, y1)

        fill = self._sample_image_background(rgb.convert("RGBA"), box)
        text_color = self._sample_image_text_color(rgb, box)
        ink = self._tight_ink_bbox(rgb, box)
        ink_box = ink or box
        ink_h = max(1, ink_box[3] - ink_box[1])
        ink_w = max(1, ink_box[2] - ink_box[0])

        old_text = (edit.old_value or "").strip() or "Ag"
        mono = self._estimate_monospace(old_text, ink_w, ink_h)
        bold = self._estimate_bold(rgb, ink_box, ink_h, mono=mono)

        # Fit width first for mono receipts (digit runs), then stretch height if glyphs are tall.
        family_hint = "courier" if mono else (edit.font_family or "arial")
        font_size = self._fit_font_size_to_ink(
            old_text,
            ink_w=ink_w,
            ink_h=ink_h,
            bold=bold,
            mono=mono,
            family=family_hint,
        )
        font = self._load_image_font(font_size, family_hint, bold=bold, mono=mono)

        natural_h = max(1, self._text_height(old_text, font))
        scale_y = ink_h / natural_h
        # Thermal/receipt glyphs are often taller than Latin fonts — allow stretch.
        scale_y = max(0.85, min(scale_y, 2.2))

        natural_w = self._text_width(old_text, font)
        gaps = max(len(old_text) - 1, 1)
        letter_spacing = (ink_w - natural_w) / gaps if natural_w > 0 else 0.0
        # Receipts often have wide tracking.
        letter_spacing = max(-1.0, min(letter_spacing, max(8.0, ink_h * 0.55)))

        return ImageTextStyle(
            font=font,
            font_size=font_size,
            bold=bold,
            mono=mono,
            letter_spacing=letter_spacing,
            scale_y=scale_y,
            text_color=text_color + (255,),
            fill=fill if len(fill) == 4 else (*fill[:3], 255),
            cover_box=box,
            origin=(ink_box[0], ink_box[1]),
            ink_height=ink_h,
            ink_width=ink_w,
            ink_box=ink_box,
        )

    def _erase_ink_keep_paper(
        self,
        working: Image.Image,
        rgb: Image.Image,
        cover: tuple[int, int, int, int],
    ) -> None:
        """Remove only dark ink pixels; leave original paper texture/color untouched."""
        x0, y0, x1, y1 = cover
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(rgb.width, max(x0 + 1, x1))
        y1 = min(rgb.height, max(y0 + 1, y1))
        if x1 <= x0 or y1 <= y0:
            return

        # Adaptive threshold from local brightness (thermal paper varies).
        sample = rgb.crop((x0, y0, x1, y1)).convert("L")
        hist = sample.histogram()
        total = sum(hist) or 1
        cum = 0
        paper_level = 200
        for value, count in enumerate(hist):
            cum += count
            if cum / total >= 0.7:
                paper_level = value
                break
        ink_cut = max(40, min(150, paper_level - 35))

        px_work = working.load()
        px_rgb = rgb.load()
        # Column-wise paper reference from above/below the cover.
        for x in range(x0, x1):
            paper_colors: list[tuple[int, int, int]] = []
            for yy in range(max(0, y0 - 8), y0):
                r, g, b = px_rgb[x, yy][:3]
                if (r + g + b) / 3 >= ink_cut + 10:
                    paper_colors.append((r, g, b))
            for yy in range(y1, min(rgb.height, y1 + 8)):
                r, g, b = px_rgb[x, yy][:3]
                if (r + g + b) / 3 >= ink_cut + 10:
                    paper_colors.append((r, g, b))
            if paper_colors:
                pr = sum(c[0] for c in paper_colors) // len(paper_colors)
                pg = sum(c[1] for c in paper_colors) // len(paper_colors)
                pb = sum(c[2] for c in paper_colors) // len(paper_colors)
            else:
                fill = self._sample_image_background(working, (x0, y0, x1, y1))
                pr, pg, pb = fill[0], fill[1], fill[2]

            for y in range(y0, y1):
                r, g, b = px_rgb[x, y][:3]
                if (r + g + b) / 3 < ink_cut:
                    # Soft blend for anti-aliased glyph edges.
                    luma = (r + g + b) / 3.0
                    t = max(0.0, min(1.0, (ink_cut - luma) / max(1.0, ink_cut - 20)))
                    nr = int(r + (pr - r) * t)
                    ng = int(g + (pg - g) * t)
                    nb = int(b + (pb - b) * t)
                    px_work[x, y] = (nr, ng, nb, 255)

    def _measure_styled_text_width(self, text: str, style: ImageTextStyle) -> int:
        if not text:
            return 0
        width = 0.0
        for index, ch in enumerate(text):
            width += self._text_width(ch, style.font)
            if index < len(text) - 1:
                width += style.letter_spacing
        return int(math.ceil(width))

    def _fit_font_size_to_ink(
        self,
        sample_text: str,
        *,
        ink_w: int,
        ink_h: int,
        bold: bool,
        mono: bool,
        family: str | None,
    ) -> int:
        """Choose size so natural glyph width/height stay close to original ink."""
        probe = sample_text.strip()[:24] or "Ag"
        # Start near height, then adjust so width also lands near ink_w.
        target_h = max(8, int(ink_h * 0.92))
        low, high = max(6, target_h // 3), max(target_h * 3, target_h + 10)
        best = target_h
        for _ in range(16):
            mid = (low + high) // 2
            font = self._load_image_font(mid, family, bold=bold, mono=mono)
            h = self._text_height(probe, font)
            w = self._text_width(probe, font)
            if h <= 0:
                break
            best = mid
            # Prefer matching height; for mono digit lines also pull toward width.
            score_h = h - target_h
            if mono and len(probe) >= 4:
                target_w = max(1.0, float(ink_w))
                score_w = w - target_w
                # Blend: if much wider than ink, shrink even if height is short.
                if score_w > 4 and score_h >= -2:
                    high = mid - 1
                    continue
            if abs(score_h) <= 1:
                break
            if score_h < 0:
                low = mid + 1
            else:
                high = mid - 1
        return max(6, best)

    def _estimate_monospace(self, text: str, ink_w: int, ink_h: int) -> bool:
        cleaned = "".join(ch for ch in text if not ch.isspace())
        if len(cleaned) < 2:
            return False
        # Digits/receipt IDs and tall thermal glyphs lean mono/dot-matrix.
        digit_ratio = sum(ch.isdigit() for ch in cleaned) / len(cleaned)
        avg_w = ink_w / max(len(cleaned), 1)
        tall = ink_h >= avg_w * 1.25
        upper_ratio = sum(ch.isupper() for ch in cleaned) / len(cleaned)
        return (
            digit_ratio >= 0.5
            or tall
            or (upper_ratio >= 0.7 and ink_h >= 12)
        )

    def _estimate_bold(
        self,
        rgb: Image.Image,
        ink_box: tuple[int, int, int, int],
        ink_h: int,
        *,
        mono: bool = False,
    ) -> bool:
        region = rgb.crop(ink_box).convert("L")
        pixels = list(region.getdata())
        if not pixels:
            return False
        dark = [p for p in pixels if p < 140]
        if not dark:
            return False
        density = len(dark) / max(len(pixels), 1)
        # Thermal receipts look "dark" from low contrast but strokes are thin — avoid bold.
        if mono:
            return density > 0.55
        return density > 0.42

    def _tight_ink_bbox(
        self,
        rgb: Image.Image,
        box: tuple[int, int, int, int],
    ) -> tuple[int, int, int, int] | None:
        region = rgb.crop(box).convert("L")
        w, h = region.size
        pix = region.load()
        vals = [pix[x, y] for y in range(0, h, max(1, h // 20)) for x in range(0, w, max(1, w // 40))]
        ordered = sorted(vals) if vals else [200]
        paper = ordered[int(len(ordered) * 0.75)]
        ink_cut = max(40, min(150, paper - 30))
        min_x, min_y, max_x, max_y = w, h, -1, -1
        for y in range(h):
            for x in range(w):
                if pix[x, y] < ink_cut:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
        if max_x < 0:
            return None
        return (box[0] + min_x, box[1] + min_y, box[0] + max_x + 1, box[1] + max_y + 1)

    @staticmethod
    def _text_width(text: str, font: ImageFont.ImageFont | ImageFont.FreeTypeFont) -> float:
        if hasattr(font, "getlength"):
            try:
                return float(font.getlength(text))
            except Exception:  # noqa: BLE001
                pass
        try:
            box = font.getbbox(text)
            return float(box[2] - box[0])
        except Exception:  # noqa: BLE001
            return float(len(text) * 8)

    @staticmethod
    def _text_height(text: str, font: ImageFont.ImageFont | ImageFont.FreeTypeFont) -> int:
        try:
            box = font.getbbox(text)
            return max(1, int(box[3] - box[1]))
        except Exception:  # noqa: BLE001
            return 0

    def _rect_from_edit(self, page: fitz.Page, edit: AppliedEdit) -> fitz.Rect | None:
        if edit.bbox and all(k in edit.bbox for k in ("x0", "y0", "x1", "y1")):
            rect = fitz.Rect(
                float(edit.bbox["x0"]),
                float(edit.bbox["y0"]),
                float(edit.bbox["x1"]),
                float(edit.bbox["y1"]),
            )
            return rect & page.rect

        if edit.old_value:
            hits = page.search_for(edit.old_value)
            if len(hits) == 1:
                return hits[0]
        return None

    def _sample_background(self, page: fitz.Page, rect: fitz.Rect) -> tuple[float, float, float]:
        candidates = [
            fitz.Rect(rect.x0, max(0, rect.y0 - 3), rect.x1, max(0.5, rect.y0 - 0.5)),
            fitz.Rect(rect.x0, min(page.rect.height, rect.y1 + 0.5), rect.x1, min(page.rect.height, rect.y1 + 3)),
            fitz.Rect(max(0, rect.x0 - 3), rect.y0, max(0.5, rect.x0 - 0.5), rect.y1),
        ]
        for sample in candidates:
            color = self._average_pixmap_color(page, sample)
            if color is not None:
                return color
        return (1.0, 1.0, 1.0)

    def _average_pixmap_color(
        self,
        page: fitz.Page,
        sample: fitz.Rect,
    ) -> tuple[float, float, float] | None:
        clip = sample & page.rect
        if clip.width < 1 or clip.height < 1:
            return None
        try:
            pix = page.get_pixmap(clip=clip, alpha=False)
        except Exception:  # noqa: BLE001
            return None
        if pix.width * pix.height == 0:
            return None

        samples = pix.samples
        n = pix.width * pix.height
        r = sum(samples[i] for i in range(0, len(samples), 3)) / n
        g = sum(samples[i + 1] for i in range(0, len(samples), 3)) / n
        b = sum(samples[i + 2] for i in range(0, len(samples), 3)) / n
        return (r / 255.0, g / 255.0, b / 255.0)

    @staticmethod
    def _color_int_to_rgb(color_int: int) -> tuple[float, float, float]:
        r = ((color_int >> 16) & 255) / 255.0
        g = ((color_int >> 8) & 255) / 255.0
        b = (color_int & 255) / 255.0
        return (r, g, b)

    @staticmethod
    def _map_font(font_family: str | None, flags: int = 0) -> str:
        name = (font_family or "").lower()
        bold = bool(flags & 2**4) or "bold" in name
        italic = bool(flags & 2**1) or "italic" in name or "oblique" in name
        if "times" in name or ("serif" in name and "sans" not in name) or "liberation" in name:
            if bold and italic:
                return "times-bolditalic"
            if bold:
                return "times-bold"
            if italic:
                return "times-italic"
            return "times-roman"
        if "courier" in name or "mono" in name:
            if bold and italic:
                return "cobo"
            if bold:
                return "cobo"
            if italic:
                return "coit"
            return "cour"
        if bold and italic:
            return "hebi"
        if bold:
            return "hebo"
        if italic:
            return "heit"
        return "helv"

    @staticmethod
    def _candidate_system_fonts(family: str, flags: int) -> list[str]:
        name = family.lower()
        bold = bool(flags & 2**4) or "bold" in name
        italic = bool(flags & 2**1) or "italic" in name or "oblique" in name
        roots = [
            "C:/Windows/Fonts",
            "/usr/share/fonts",
            "/usr/local/share/fonts",
        ]
        filenames: list[str] = []
        if "liberation" in name and "serif" in name:
            if bold and italic:
                filenames += ["LiberationSerif-BoldItalic.ttf"]
            elif bold:
                filenames += ["LiberationSerif-Bold.ttf"]
            elif italic:
                filenames += ["LiberationSerif-Italic.ttf"]
            else:
                filenames += ["LiberationSerif-Regular.ttf"]
        if "times" in name or ("serif" in name and "sans" not in name and "arial" not in name):
            if bold and italic:
                filenames += ["timesbi.ttf", "Times New Roman Bold Italic.ttf"]
            elif bold:
                filenames += ["timesbd.ttf", "Times New Roman Bold.ttf", "timesbd.ttf"]
            elif italic:
                filenames += ["timesi.ttf", "Times New Roman Italic.ttf"]
            else:
                filenames += ["times.ttf", "Times New Roman.ttf"]
        # Never substitute Arial for Helvetica — Base-14 path must handle those faces.
        # Mapping Helvetica → Arial Bold/Regular visibly changes weight and spacing.
        if "arial" in name and "helvetica" not in name:
            if bold and italic:
                filenames += ["arialbi.ttf", "Arial Bold Italic.ttf", "Arial-BoldItalicMT.ttf"]
            elif bold:
                filenames += ["arialbd.ttf", "Arial Bold.ttf", "Arial-BoldMT.ttf", "arialbd.ttf"]
            elif italic:
                filenames += ["ariali.ttf", "Arial Italic.ttf"]
            else:
                filenames += ["arial.ttf", "Arial.ttf"]
        if "calibri" in name:
            if bold:
                filenames += ["calibrib.ttf", "Calibri Bold.ttf"]
            else:
                filenames += ["calibri.ttf", "Calibri.ttf"]
        if not filenames:
            # Last-resort readable faces — still prefer bold when requested.
            if bold:
                filenames += ["arialbd.ttf", "Arial Bold.ttf", "timesbd.ttf"]
            filenames += ["arial.ttf", "Arial.ttf", "calibri.ttf"]

        paths: list[str] = []
        for root in roots:
            for fn in filenames:
                paths.append(f"{root}/{fn}")
        return paths

    @staticmethod
    def _sample_image_background(img: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = box
        band = img.crop((x0, max(0, y0 - 3), x1, max(1, y0)))
        if band.width == 0 or band.height == 0:
            return (255, 255, 255, 255)
        colors = list(band.getdata())
        if not colors:
            return (255, 255, 255, 255)
        r = sum(c[0] for c in colors) // len(colors)
        g = sum(c[1] for c in colors) // len(colors)
        b = sum(c[2] for c in colors) // len(colors)
        a = sum(c[3] for c in colors) // len(colors) if len(colors[0]) > 3 else 255
        return (r, g, b, a)

    @staticmethod
    def _sample_image_text_color(img: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
        """Use the darkest ink core (not AA edges) so redraw matches true print color."""
        region = img.crop(box)
        pixels = list(region.getdata())
        if not pixels:
            return (0, 0, 0)
        ranked = sorted(pixels, key=lambda c: sum(c[:3]))
        floor = sum(ranked[0][:3]) / 3.0
        # Only pixels near the true floor — excludes anti-aliased fringes.
        darks = [c for c in ranked if sum(c[:3]) / 3.0 <= floor + 18]
        if len(darks) < 4:
            darks = ranked[: max(4, len(ranked) // 50)]
        r = sum(c[0] for c in darks) // len(darks)
        g = sum(c[1] for c in darks) // len(darks)
        b = sum(c[2] for c in darks) // len(darks)
        return (r, g, b)

    @staticmethod
    def _load_image_font(
        size: int,
        family: str | None = None,
        *,
        bold: bool = False,
        mono: bool = False,
    ) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
        name = (family or "").lower()
        candidates: list[str] = []
        # Thermal/receipt style: thin monospace first (never bold Courier unless required).
        if mono or "courier" in name or "mono" in name or "consol" in name:
            if bold:
                candidates += ["C:/Windows/Fonts/courbd.ttf", "C:/Windows/Fonts/consolab.ttf"]
            candidates += [
                "C:/Windows/Fonts/cour.ttf",
                "C:/Windows/Fonts/courbd.ttf",  # fallback only if regular missing
                "C:/Windows/Fonts/consola.ttf",
                "C:/Windows/Fonts/lucon.ttf",
                "C:/Windows/Fonts/consolai.ttf",
            ]
        if "serif" in name or "liberation" in name or "times" in name:
            if bold:
                candidates += [
                    "C:/Windows/Fonts/timesbd.ttf",
                    "C:/Windows/Fonts/LiberationSerif-Bold.ttf",
                ]
            candidates += [
                "C:/Windows/Fonts/times.ttf",
                "C:/Windows/Fonts/LiberationSerif-Regular.ttf",
            ]
        if bold and not mono:
            candidates += [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/calibrib.ttf",
            ]
        candidates += [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "arial.ttf",
        ]
        # Prefer regular Courier over bold when mono and not bold.
        if mono and not bold:
            candidates = [
                "C:/Windows/Fonts/cour.ttf",
                "C:/Windows/Fonts/consola.ttf",
                "C:/Windows/Fonts/lucon.ttf",
                *[c for c in candidates if "bd" not in c.lower() and "bold" not in c.lower()],
            ]
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
        return ImageFont.load_default()


