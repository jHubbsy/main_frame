"""Image analysis tool for vision capabilities."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from mainframe.providers.base import ContentBlock, Message, Role
from mainframe.tools.base import ToolContext, ToolResult

# Tool metadata
name = "analyze_image"
description = "Analyze an image file and describe its contents or answer questions about it."

parameters = {
    "type": "object",
    "properties": {
        "image_path": {
            "type": "string",
            "description": "Path to the image file to analyze"
        },
        "question": {
            "type": "string",
            "description": (
                "Optional specific question about the image. "
                "If not provided, will give a general description."
            ),
        }
    },
    "required": ["image_path"],
}


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Analyze an image file using the vision model."""
    image_path = params["image_path"]
    question = params.get("question", "")

    if ctx.provider is None:
        return ToolResult.error("No provider available for image analysis")

    try:
        path = Path(image_path)

        if not path.exists():
            return ToolResult.error(f"Image file not found: {image_path}")

        if not path.is_file():
            return ToolResult.error(f"Path is not a file: {image_path}")

        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type or not mime_type.startswith("image/"):
            return ToolResult.error(f"File is not a recognized image format: {image_path}")

        max_size = 10 * 1024 * 1024
        if path.stat().st_size > max_size:
            return ToolResult.error(
                f"Image file too large: {path.stat().st_size / 1024 / 1024:.1f}MB "
                f"(max: {max_size / 1024 / 1024}MB)"
            )

        try:
            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            return ToolResult.error(f"Failed to read image file: {e}")

        if question:
            prompt_text = f"Please analyze this image and answer the following question: {question}"
        else:
            prompt_text = (
                "Please analyze this image and provide a detailed description of what you see, "
                "including any text, objects, people, and other notable elements."
            )

        message = Message(
            role=Role.USER,
            content=[
                ContentBlock(type="image", image_data=image_data, image_mime_type=mime_type),
                ContentBlock(type="text", text=prompt_text),
            ],
        )

        result = await ctx.provider.complete(messages=[message], max_tokens=1024)
        return ToolResult.success(result.message.text)

    except Exception as e:
        return ToolResult.error(f"Image analysis failed: {e}")
