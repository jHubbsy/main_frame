"""Enhanced input handling for rich content including images."""

from __future__ import annotations

import asyncio
import base64
import mimetypes
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML, AnyFormattedText
from prompt_toolkit.key_binding import KeyBindings

from mainframe.cli.display import print_error, print_info

# Image formats we can handle
SUPPORTED_IMAGE_TYPES = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'
}

# Maximum image size (10MB)
MAX_IMAGE_SIZE = 10 * 1024 * 1024


class ImageContent:
    """Represents an image attached to a message."""

    def __init__(self, file_path: str | Path, mime_type: str | None = None):
        self.file_path = Path(file_path)
        self.mime_type = mime_type or mimetypes.guess_type(str(self.file_path))[0] or 'image/png'
        self._base64_data: str | None = None

    @property
    def base64_data(self) -> str:
        """Get base64 encoded image data."""
        if self._base64_data is None:
            with open(self.file_path, 'rb') as f:
                self._base64_data = base64.b64encode(f.read()).decode('utf-8')
        return self._base64_data

    @property
    def data_uri(self) -> str:
        """Get data URI for the image."""
        return f"data:{self.mime_type};base64,{self.base64_data}"

    def __str__(self) -> str:
        return f"[Image: {self.file_path.name}]"


class RichMessage:
    """A message that can contain text and images."""

    def __init__(self, text: str = "", images: list[ImageContent] | None = None):
        self.text = text
        self.images = images or []

    @property
    def has_images(self) -> bool:
        return bool(self.images)

    def add_image(self, image: ImageContent) -> None:
        """Add an image to this message."""
        self.images.append(image)

    def to_anthropic_format(self) -> list[dict[str, Any]]:
        """Convert to Anthropic message format."""
        content = []

        # Add text if present
        if self.text.strip():
            content.append({"type": "text", "text": self.text})

        # Add images
        for image in self.images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image.mime_type,
                    "data": image.base64_data
                }
            })

        return content

    def __str__(self) -> str:
        parts = []
        if self.text.strip():
            parts.append(self.text)
        if self.images:
            parts.extend(str(img) for img in self.images)
        return "\n".join(parts)


class RichInputHandler:
    """Enhanced input handler for rich content."""

    def __init__(self, history_file: str | None = None):
        self.current_message = RichMessage()
        self.history_file = history_file
        self._setup_prompt_session()

    def _setup_prompt_session(self) -> None:
        """Setup prompt_toolkit session with custom key bindings."""
        from prompt_toolkit.history import FileHistory

        # Create key bindings
        kb = KeyBindings()

        @kb.add('c-v')  # Ctrl+V for paste
        async def paste_handler(event) -> None:
            """Handle paste events - check for images."""
            # Try to get clipboard content
            try:
                # This is a placeholder - actual clipboard handling is platform-specific
                await self._handle_paste()
            except Exception as e:
                print_error(f"Paste error: {e}")

        @kb.add('c-i')  # Ctrl+I to add image
        async def add_image_handler(event) -> None:
            """Manually add an image file."""
            await self._prompt_for_image()

        @kb.add('c-l')  # Ctrl+L to list attached content
        def list_attachments(event) -> None:
            """List current attachments."""
            self._show_attachments()

        # Setup prompt session
        history = FileHistory(self.history_file) if self.history_file else None
        self.prompt_session: PromptSession[str] = PromptSession(
            history=history,
            key_bindings=kb,
            multiline=False,
        )

    async def get_input(self, prompt: str = "> ") -> RichMessage:
        """Get rich input from user."""
        # Reset current message
        self.current_message = RichMessage()

        # Show help if there are shortcuts
        if not hasattr(self, '_shown_help'):
            print_info(
                "Rich input enabled. Ctrl+I: add image, Ctrl+L: list attachments, Ctrl+V: paste"
            )
            self._shown_help = True

        try:
            # Get text input
            text_input = await self.prompt_session.prompt_async(
                self._build_prompt(prompt)
            )

            # Handle special commands
            text_input = text_input.strip()

            # Check for file drag-and-drop (simulated by file paths)
            if text_input.startswith('file://') or self._looks_like_file_path(text_input):
                await self._handle_file_input(text_input)
                # Get additional text input if desired
                if self.current_message.has_images:
                    additional_text = await self.prompt_session.prompt_async(
                        "Add message text (optional): "
                    )
                    if additional_text.strip():
                        self.current_message.text = additional_text.strip()
            else:
                self.current_message.text = text_input

            return self.current_message

        except (EOFError, KeyboardInterrupt) as e:
            raise e
        except Exception as e:
            print_error(f"Input error: {e}")
            return RichMessage()

    def _build_prompt(self, base_prompt: str) -> AnyFormattedText:
        """Build the prompt with attachment indicators."""
        if not self.current_message.has_images:
            return base_prompt

        # Show attachment count
        img_count = len(self.current_message.images)
        suffix = "s" if img_count != 1 else ""
        return HTML(f'<ansigreen>[{img_count} image{suffix}]</ansigreen> {base_prompt}')

    def _looks_like_file_path(self, text: str) -> bool:
        """Check if text looks like a file path."""
        # Remove file:// prefix if present
        if text.startswith('file://'):
            text = text[7:]

        path = Path(text)
        return (
            path.exists() and
            path.is_file() and
            path.suffix.lower() in SUPPORTED_IMAGE_TYPES
        )

    async def _handle_file_input(self, file_input: str) -> None:
        """Handle file input (drag and drop or paste)."""
        # Clean up the input
        if file_input.startswith('file://'):
            file_input = file_input[7:]

        file_path = Path(file_input.strip().strip('"\''))

        if not file_path.exists():
            print_error(f"File not found: {file_path}")
            return

        if not file_path.is_file():
            print_error(f"Not a file: {file_path}")
            return

        if file_path.suffix.lower() not in SUPPORTED_IMAGE_TYPES:
            print_error(f"Unsupported image type: {file_path.suffix}")
            return

        # Check file size
        if file_path.stat().st_size > MAX_IMAGE_SIZE:
            size_mb = file_path.stat().st_size / 1024 / 1024
            max_mb = MAX_IMAGE_SIZE / 1024 / 1024
            print_error(f"Image too large: {size_mb:.1f}MB (max: {max_mb}MB)")
            return

        try:
            image = ImageContent(file_path)
            self.current_message.add_image(image)
            print_info(f"Added image: {file_path.name} ({file_path.stat().st_size / 1024:.1f}KB)")
        except Exception as e:
            print_error(f"Error loading image: {e}")

    async def _handle_paste(self) -> None:
        """Handle paste operation."""
        # This is a placeholder for clipboard handling
        # Real implementation would need platform-specific clipboard libraries
        print_info("Paste handling not yet implemented")

    async def _prompt_for_image(self) -> None:
        """Prompt user to select an image file."""
        try:
            file_path = await asyncio.to_thread(
                input, "Enter image path: "
            )
            if file_path.strip():
                await self._handle_file_input(file_path.strip())
        except (EOFError, KeyboardInterrupt):
            pass

    def _show_attachments(self) -> None:
        """Show current attachments."""
        if not self.current_message.has_images:
            print_info("No attachments")
            return

        print_info("Current attachments:")
        for i, image in enumerate(self.current_message.images, 1):
            size_kb = image.file_path.stat().st_size / 1024
            print_info(f"  {i}. {image.file_path.name} ({size_kb:.1f}KB)")


async def get_rich_input(
    prompt: str = "> ",
    history_file: str | None = None,
) -> RichMessage:
    """Get rich input from user with support for images and other content."""
    handler = RichInputHandler(history_file)
    return await handler.get_input(prompt)


def demo_rich_input() -> None:
    """Demo function to test rich input."""
    async def _demo() -> None:
        print_info("Rich Input Demo")
        print_info("Try entering a file path to an image, or use Ctrl+I to add one")

        while True:
            try:
                message = await get_rich_input("demo> ")

                if message.text.lower() in ('/quit', '/exit'):
                    break

                print_info("Received message:")
                print_info(f"  Text: {message.text}")
                if message.has_images:
                    print_info(f"  Images: {len(message.images)}")
                    for img in message.images:
                        print_info(f"    - {img.file_path.name}")

                # Show how to convert for AI
                anthropic_format = message.to_anthropic_format()
                print_info(f"  Anthropic format: {len(anthropic_format)} content blocks")

            except (EOFError, KeyboardInterrupt):
                break

        print_info("Demo ended")

    asyncio.run(_demo())


if __name__ == "__main__":
    demo_rich_input()
