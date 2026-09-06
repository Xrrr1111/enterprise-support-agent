from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo_assets"
FONT = Path("C:/Windows/Fonts/msyh.ttc")


def policy_image(text: str, output: Path, size: tuple[int, int] = (1500, 520)) -> None:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT), 48)
    title_font = ImageFont.truetype(str(FONT), 58)
    draw.text((70, 55), "客户服务知识卡", fill="#17324d", font=title_font)
    draw.multiline_text((70, 175), text, fill="#111827", font=font, spacing=22)
    image.save(output, format="PNG")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "member-delivery.md").write_text(
        "# 星云会员配送\n\n星云会员的月度礼盒在每月 1 日生成订单，通常在 3 个工作日内发出。",
        encoding="utf-8",
    )
    policy_image("易碎品签收后 48 小时内可提交破损照片。\n超过时限需转人工复核。", OUTPUT / "fragile-policy.png")
    scan_image = OUTPUT / "invoice-policy-source.png"
    policy_image("电子发票可在订单完成后 7 天内申请。\n抬头修改需在开票前完成。", scan_image, (1500, 650))
    image = Image.open(scan_image)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    pdf = canvas.Canvas(str(OUTPUT / "invoice-policy-scan.pdf"), pagesize=A4)
    pdf.drawInlineImage(Image.open(io.BytesIO(buffer.getvalue())), 45, 430, width=505, height=219)
    pdf.showPage()
    pdf.save()
    scan_image.unlink()
    print(f"Generated demo assets in {OUTPUT}")


if __name__ == "__main__":
    main()
